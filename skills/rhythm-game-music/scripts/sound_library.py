#!/usr/bin/env python3
"""Inventory real local assets and resolve explicit style palettes; no timbre/genre quality scores."""
import argparse, hashlib, json, struct
from pathlib import Path

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sf_presets(path):
    b=Path(path).read_bytes()
    if b[:4]!=b'RIFF' or b[8:12]!=b'sfbk':raise ValueError('Not a SoundFont RIFF sfbk')
    def chunks(start,end):
        while start+8<=end:
            tag=b[start:start+4];n=struct.unpack_from('<I',b,start+4)[0]
            if start+8+n>end:raise ValueError('Truncated SoundFont chunk')
            yield tag,start+8,n;start+=8+n+(n%2)
    pd={}
    for tag,p,n in chunks(12,len(b)):
        if tag==b'LIST' and b[p:p+4]==b'pdta':pd={tag:b[q:q+length] for tag,q,length in chunks(p+4,p+n)}
    def rows(tag,fmt):
        size=struct.calcsize(fmt);data=pd[tag]
        if len(data)%size:raise ValueError('Invalid '+tag.decode())
        return list(struct.iter_unpack(fmt,data))
    ph=rows(b'phdr','<20sHHHIII');pb=rows(b'pbag','<HH');pg=rows(b'pgen','<HH')
    ins=rows(b'inst','<20sH');ib=rows(b'ibag','<HH');ig=rows(b'igen','<HH');sh=rows(b'shdr','<20sIIIIIBbHH')
    def zones(bags,gens,start,end):return [dict(gens[bags[i][0]:bags[i+1][0]]) for i in range(start,end)]
    def kr(g):
        x=g.get(43,32512);return x&255,x>>8
    out=[]
    for i,(name,program,bank,bag,*_) in enumerate(ph[:-1]):
        keys=set();sources={};globalp={}
        for z in zones(pb,pg,bag,ph[i+1][3]):
            if 41 not in z:globalp.update(z);continue
            pz={**globalp,**z};idx=z[41];globali={}
            for iz in zones(ib,ig,ins[idx][1],ins[idx+1][1]):
                if 53 not in iz:globali.update(iz);continue
                lo,hi=kr(pz);a,c=kr({**globali,**iz});zonekeys=range(max(lo,a),min(hi,c)+1);keys.update(zonekeys)
                if bank==128:
                    rawname=sh[iz[53]][0].split(b'\0')[0].decode(errors='replace')
                    instname=ins[idx][0].split(b'\0')[0].decode(errors='replace')
                    for key in zonekeys:sources.setdefault(str(key),set()).add(instname+' / '+rawname)
        out.append({'id':f'sf:{bank}:{program}','bank':bank,'program':program,'name':name.split(b'\0')[0].decode(errors='replace'),'kind':'drum_kit' if bank==128 else 'pitched','declaredKeys':sorted(keys),'specialArticulations':'unverified'})
        if bank==128:out[-1]['keySources']={k:sorted(v) for k,v in sources.items()}
    return out

def inventory(sf,web=None):
    sf=Path(sf).resolve();out={'version':1,'soundfont':{'path':str(sf),'sha256':digest(sf),'presets':sf_presets(sf)},'sampleLibraries':[],'limits':['Preset names and key zones are metadata; sound quality and named articulations require audition.']}
    if web:
        p=Path(web).resolve();m=json.loads(p.read_text());inst={}
        for key,v in m['instruments'].items():
            samples=[]
            for s in v['samples']:
                file=p.parent/s['path'];samples.append({**s,'exists':file.is_file(),'sha256':digest(file) if file.is_file() else None})
            inst[key]={**v,'samples':samples}
        out['sampleLibraries'].append({'id':m['libraryId'],'manifest':str(p),'sha256':digest(p),'format':m.get('format'),'sampleRate':m.get('sampleRate'),'instruments':inst})
    # A name-based absence is a discovery gap, not proof that all unnamed samples were auditioned.
    out['discoveryGaps']=[{'instrument':'pandeiro','status':'no_explicit_verified_mapping','rule':'Do not relabel GM tambourine, conga or bongo as pandeiro.'}]
    return out

def validate(plan,sf):
    sf=Path(sf).resolve()
    if digest(sf)!=plan['soundfont']['sha256']:raise ValueError('SoundFont SHA256 mismatch; regenerate selection')
    actual={(p['bank'],p['program']):p for p in sf_presets(sf)}
    for track,v in plan['tracks'].items():
        key=(v['bank'],v['program'])
        if key not in actual:raise ValueError(f'{track}: preset does not exist: {key}')
        if v['bank']!=(128 if v['channel']==9 else 0):raise ValueError('Current MIDI renderer supports melodic bank0 and drum bank128 only')
        if v.get('requiredInstrument')=='pandeiro':raise ValueError('Pandeiro requires its own verified sample mapping')
        missing=set(v.get('allowedNotes',[]))-set(actual[key]['declaredKeys'])
        if missing:raise ValueError(f'{track}: keys not declared in selected preset: {sorted(missing)}')
    return True

def resolve(catalog,profiles,style,requirements=()):
    profile=profiles['styles'][style];available={p['id']:p for p in catalog['soundfont']['presets']};tracks={}
    for track,role in profile['tracks'].items():
        chosen=next((available[x] for x in role['candidates'] if x in available),None)
        if not chosen:raise ValueError(f'{style}/{track}: no available candidate, no silent substitution')
        tracks[track]={**{k:v for k,v in role.items() if k!='candidates'},'noteSources':{str(n):chosen.get('keySources',{}).get(str(n),[]) for n in role.get('allowedNotes',[])},'presetId':chosen['id'],'name':chosen['name'],'bank':chosen['bank'],'program':chosen['program'],'channel':9 if chosen['kind']=='drum_kit' else 0,'articulationStatus':'MIDI timing/velocity programmable; special techniques not audition-verified'}
    gaps=[]
    for item in profile.get('optionalInstruments',[]):
        if item=='pandeiro':gaps.append({'instrument':item,'status':'no_explicit_verified_mapping','substitution':'none automatic'})
    for required in requirements:
        if required=='pandeiro':raise ValueError('Required Pandeiro not mapped; choose a verified library before rendering. No conga/tambourine substitution.')
        raise ValueError('No implemented semantic requirement mapping for '+required)
    plan={'version':1,'style':style,'route':profile['route'],'sources':profile['sources'],'soundfont':{k:catalog['soundfont'][k] for k in ['path','sha256']},'tracks':tracks,'gaps':gaps,'qualityStatus':'not_auditioned','profileNotes':profile['ensemble']}
    validate(plan,catalog['soundfont']['path']);return plan

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('scan');s.add_argument('--soundfont',required=True);s.add_argument('--web-library');s.add_argument('--output',required=True)
    s=sub.add_parser('plan');s.add_argument('--catalog',required=True);s.add_argument('--profiles',default=str(Path(__file__).resolve().parents[1]/'assets/style-sound-profiles.json'));s.add_argument('--style',required=True);s.add_argument('--require',action='append',default=[]);s.add_argument('--output',required=True)
    s=sub.add_parser('verify');s.add_argument('plan');s.add_argument('--soundfont',required=True)
    a=ap.parse_args()
    try:
        if a.cmd=='scan':result=inventory(a.soundfont,a.web_library)
        elif a.cmd=='plan':result=resolve(json.loads(Path(a.catalog).read_text()),json.loads(Path(a.profiles).read_text()),a.style,a.require)
        else:validate(json.loads(Path(a.plan).read_text()),a.soundfont);print('Selection verified against actual SoundFont');return
        Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'output':a.output,'presets':len(result.get('soundfont',{}).get('presets',[])),'style':result.get('style')},ensure_ascii=False))
    except (ValueError,KeyError,OSError,struct.error) as e:ap.exit(2,str(e)+'\n')
if __name__=='__main__':main()
