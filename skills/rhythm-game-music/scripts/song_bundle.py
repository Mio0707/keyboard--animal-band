#!/usr/bin/env python3
"""Portable score -> explicit arrangement -> MIDI/PCM/events/player. No example-song imports."""
import argparse, hashlib, json, math, os, re, shutil, struct, subprocess, sys, wave
from pathlib import Path
try:import numpy as np
except ImportError:np=None

ROOT=Path(__file__).resolve().parents[1]
TRACKS=('dog','bear','cat','lion')
def read(p): return json.loads(Path(p).read_text())
def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def validate_song(s):
    for k in ('id','title','source','melody','chords'):assert s.get(k),f'missing {k}'
    assert isinstance(s['id'],str) and re.fullmatch('[a-z][a-z0-9-]*',s['id']),'id must be a lowercase safe slug'
    assert finite(s['bpm']) and 30<=s['bpm']<=300,'bpm outside 30..300'
    assert s['beatsPerBar'] in (2,3,4),'fixed quarter-note meter 2/4, 3/4 or 4/4 required; transcribe other meters explicitly'
    length=s['beats'];assert finite(length) and length>0 and abs(length/s['beatsPerBar']-round(length/s['beatsPerBar']))<1e-7,'incomplete playback bar'
    for n in s['melody']:
        assert finite(n['beat']) and finite(n['duration']) and 0<=n['beat']<n['beat']+n['duration']<=length+1e-6,'melody timing'
        assert isinstance(n['midi'],int) and 0<=n['midi']<=127,'melody pitch'
    last=0
    for c in s['chords']:
        assert abs(c['beat']-last)<1e-6 and c['duration']>0,'chords must cover score without gaps/overlaps'
        assert isinstance(c['root'],int) and c['voicing'] and all(isinstance(p,int) and 0<=p<=127 for p in c['voicing']),'chord pitches'
        last=c['beat']+c['duration']
    assert abs(last-length)<1e-6,'chord end differs from melody form'
    assert s['source'].get('url') or s['source'].get('file'),'source provenance required'
    return s

def arrange(song,style,bpm=None):
    s=validate_song(song);assert style in ('swing-jazz','drift-phonk'),'starter supports swing-jazz/drift-phonk; author an explicit arrangement JSON for other styles'
    meter=s['beatsPerBar'];beats=s['beats'];jazz=style=='swing-jazz';bpm=bpm or s['bpm']
    sections={mode:{'bars':bars,'tracks':{k:[] for k in TRACKS}} for mode,bars in [('theme',round(beats/meter)),('build',4),('drop',round(beats/meter)*2),('hold',2)]}
    def add(mode,k,p,t,d,v):
        end=sections[mode]['bars']*meter
        if 0<=t<end and d>0:sections[mode]['tracks'][k].append({'midi':int(p),'beat':round(t,6),'duration':round(min(d,end-t),6),'velocity':int(v),'channel':9 if k=='dog' else 0})
    def harmony(t):return next(c for c in s['chords'] if c['beat']<=t%beats<c['beat']+c['duration'])
    def swing(t):
        whole=math.floor(t);f=t-whole
        return whole+(f*1.24 if f<=.5 else .62+(f-.5)*.76)
    for mode,spec in sections.items():
        end=spec['bars']*meter;strong=mode=='drop'
        if mode in ('theme','drop'):
            notes=[]
            for cycle in range(2 if strong else 1):
                for original in s['melody']:
                    at=original['beat'];time=(swing(at) if jazz else at)+cycle*beats
                    notes.append((time,original,cycle))
            notes.sort(key=lambda x:x[0])
            for i,(at,n,cycle) in enumerate(notes):
                nxt=notes[i+1][0] if i+1<len(notes) else end
                phrase_end=any(abs(n['beat']+n['duration']-p)<.01 for p in s.get('phraseEnds',[]))
                d=min(n['duration']*(.90 if jazz else .72),nxt-at-.04)
                if not jazz:d=min(d,.65)
                pitch=n['midi']+(0 if jazz else 12)
                add(mode,'lion',pitch,at,max(.04,d-(.15 if jazz and phrase_end else 0)),76 if jazz else 83)
                # Sparse second-chorus response only in long source rests, never over source attacks.
                if strong and cycle==1 and nxt-at>1.7:
                    c=harmony(at);answer=c['voicing'][-1]+12
                    for dt,pp in ((1,answer),(1.5,answer-2)):
                        if at+dt+.18<nxt-.10:add(mode,'lion',pp,at+dt,.16,57 if jazz else 66)
        elif mode=='build':
            # Fragment one actual source phrase; band's answer leads into the new chorus.
            phrase=[n for n in s['melody'] if s.get('hookStart',0)<=n['beat']<s.get('hookStart',0)+meter*2]
            origin=s.get('hookStart',0)
            for n in phrase:
                at=n['beat']-origin
                if at<end-meter:add(mode,'lion',n['midi']+(0 if jazz else 12),swing(at) if jazz else at,min(n['duration']*.8,.7),64)
        for bar in range(spec['bars']):
            b=bar*meter;c=harmony(b);root=c['root'];next_root=harmony(b+meter)['root'];unit=meter/4
            if mode=='hold':
                for p in c['voicing'][1:]:add(mode,'bear',p,b+.5*unit,meter*.65,28)
                continue
            if jazz:
                # Ride: quarter, quarter + late eighth, quarter, quarter + late eighth.
                for t,v in [(0,43),(1,34),(1.62,25),(2,45),(3,35),(3.62,26)]:add(mode,'dog',51,b+t*unit,.10,v+(4 if strong else 0))
                for t in (1,3):add(mode,'dog',44,b+t*unit,.08,32)
                add(mode,'dog',36,b,.08,25)
                if strong and bar%4==3:
                    for t in (2.62,3.62):add(mode,'dog',38,b+t*unit,.08,27)
                two_feel=mode=='theme' and bar<max(1,spec['bars']//2) or mode=='build' and bar<2
                bass=[(0,root),(2,root+7)] if two_feel else [(0,root),(1,root+7),(2,root+12),(3,next_root+(1 if next_root<root else -1))]
                for t,p in bass:add(mode,'cat',p,b+t*unit,.83*unit,66 if t==0 else 59)
                onset=[n['beat'] for n in spec['tracks']['lion']]
                comp=(.62,2.62) if bar%2==0 else (1.62,3.25)
                if mode=='build':comp=(.62,) if bar<2 else (0,1.62,2.62)
                for t in comp:
                    at=b+t*unit
                    if mode!='build' and any(abs(x-at)<.11 for x in onset):continue
                    for p in c['voicing']:add(mode,'bear',p,at,.45*unit,43 if not strong else 49)
                if mode=='build' and bar==spec['bars']-1:
                    # Short ensemble pickup rather than an electronic snare riser.
                    for p in c['voicing']:add(mode,'bear',p,b+3*unit,.36*unit,63)
            else:
                kicks=(0,.75,2,2.75) if strong else (0,1.5,2.75)
                if mode=='build' and bar>=2:kicks=()
                for t in kicks:add(mode,'dog',36,b+t*unit,.10,104 if t==0 else 87)
                for t in (1,3):add(mode,'dog',39,b+t*unit,.10,83)
                for j in range(8):add(mode,'dog',42,b+j*.5*unit,.055,38 if j%2==0 else 25)
                if strong and bar%2:
                    for t in (2.75,3.25):add(mode,'dog',42,b+t*unit,.045,24)
                if not(mode=='build' and bar>=2):
                    for t,p,d in [(0,root,.65),(1.5,root,.3),(2.75,root+12,.34)]:add(mode,'cat',p,b+t*unit,d*unit,89)
                if bar%2==0:
                    for p in c['voicing'][1:]:add(mode,'bear',p,b,min(meter*1.4,end-b),29)
        for k in TRACKS:spec['tracks'][k].sort(key=lambda n:(n['beat'],n['midi']))
    result={'version':1,'songId':s['id'],'title':s['title'],'style':style,'bpm':bpm,'beatsPerBar':meter,'source':s['source'],'sourceScore':s,'sectionScores':sections,
      'trackLabels':{'dog':'爵士鼓','bear':'原声钢琴','cat':'低音提琴','lion':'次中音萨克斯'} if jazz else {'dog':'808鼓组','bear':'暗色氛围','cat':'失真低音','lion':'808牛铃'},
      'sectionLabels':{'theme':'主题','build':'鼓贝间奏' if jazz else '低频抽离','drop':'合奏变奏' if jazz else '牛铃爆发','hold':'等待'},
      'design':{'groove':'medium swing, late eighth .62; two-feel to walking; sparse piano answers' if jazz else 'straight broken kick, offbeat clap, pitched 808 cowbell and kick-ducked saturated bass','sourcePolicy':'Explicit melody and harmony; complete source phrase length retained, ornaments omitted as documented','mixLevels':dict(zip(TRACKS,[.72,.78,.80,.78] if jazz else [.90,.31,1.05,.66])),'qualityStatus':'technical candidate; human audition pending'}}
    from performance_sections import rewrite
    tonic=s.get('tonicMidi',s['chords'][0]['root']);pitches={p%12 for p in s['chords'][0]['voicing']}
    return rewrite(result,s,tonic,s.get('mode')=='minor' or (tonic+3)%12 in pitches,s.get('hookStart',0),s.get('performanceClipBars',4))

def vlq(x):
    out=[x&127];x>>=7
    while x:out.insert(0,(x&127)|128);x>>=7
    return bytes(out)
def midi(path,notes,bpm,meter,beats,program=None,channel=0):
    body=b'\0\xff\x51\x03'+round(60e6/bpm).to_bytes(3,'big')+bytes([0,255,88,4,meter,2,24,8])
    if program is not None:body+=bytes([0,192|channel,program])
    events=[]
    for n in notes:
        events.extend([(round(n['beat']*960),1,n),(round((n['beat']+n['duration'])*960),0,n)])
    previous=0
    for tick,on,n in sorted(events,key=lambda e:(e[0],e[1],e[2]['midi'])):
        body+=vlq(tick-previous)+bytes([(144 if on else 128)|channel,n['midi'],n['velocity'] if on else 0]);previous=tick
    body+=vlq(round(beats*960)-previous)+b'\xff\x2f\x00';Path(path).write_bytes(b'MThd'+struct.pack('>IHHH',6,0,1,960)+b'MTrk'+struct.pack('>I',len(body))+body)
def synth(mid,out,sf,fs,sr):
    env=os.environ.copy();lib=str(Path(fs).resolve().parent.parent/'lib');env['DYLD_LIBRARY_PATH']=lib+(':'+env['DYLD_LIBRARY_PATH'] if env.get('DYLD_LIBRARY_PATH') else '')
    subprocess.run([str(fs),'-ni','-g','.65','-r',str(sr),'-R','0','-C','0','-T','wav','-O','s16','-F',str(out),str(sf),str(mid)],env=env,check=True,capture_output=True,timeout=120)
    with wave.open(str(out)) as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,sr),'unexpected render format'
        return np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,2).astype(float)/32768
def wav(path,a,sr):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);assert np.isfinite(a).all() and np.max(abs(a),initial=0)<1,'PCM clipping'
    with wave.open(str(p),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes(np.round(a*32767).astype('<i2').tobytes())
    return {'file':str(p.name),'frames':len(a),'duration':len(a)/sr,'peak':float(np.max(abs(a),initial=0)),'rms':float(np.sqrt(np.mean(a*a))),'sha256':sha(p)}
def render(recipe,plan,sf,fs,out,pilot=False,reuse_from=None):
    if np is None:raise RuntimeError('Rendering requires NumPy in this Python environment; install numpy or select an existing environment that provides it')
    from sound_library import validate
    from check_arrangement import check
    validate(plan,sf);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    assert recipe['style']==plan['style'],'sound plan style differs'
    sr=44100;spb=60/recipe['bpm'];meter=recipe['beatsPerBar'];sections=recipe['sectionScores'];audio={};seed=None;anchor=None;source_meta=None
    previous=read(Path(reuse_from)/'manifest.json') if reuse_from else None;reuse=set(recipe.get('reuseSections',[])) if previous else set()
    if previous:
        assert (previous['bpm'],previous['beatsPerBar'])==(recipe['bpm'],meter),'cannot reuse stems at another clock'
        assert previous.get('soundfont',{}).get('sha256')==sha(sf),'cannot reuse a different soundfont'
    reuse_audio={}
    assert meter in (2,3,4) and 30<=recipe['bpm']<=300,'unsupported playback clock'
    for mode,spec in sections.items():
        assert isinstance(spec['bars'],int) and spec['bars']>0
        if mode in reuse:
            assert spec==previous['sectionScores'][mode],'reused score changed'
            continue
        for k in TRACKS:
            for n in spec['tracks'][k]:
                assert all(finite(n[x]) for x in ('beat','duration')) and 0<=n['beat']<n['beat']+n['duration']<=spec['bars']*meter+1e-5,'out-of-bounds score'
                assert all(isinstance(n[x],int) and lo<=n[x]<=hi for x,lo,hi in [('midi',0,127),('velocity',1,127),('channel',0,15)]),'MIDI range'
                assert n['channel']==(9 if k=='dog' else 0),'track channel differs'
                if k=='dog':assert n['midi'] in plan['tracks'][k]['allowedNotes'],'unverified drum key'
    if pilot:sections={'theme':sections['theme']}
    for mode,spec in sections.items():
        if mode in reuse:continue
        audio[mode]={};length=round(spec['bars']*meter*spb*sr);folder=out/'assets'/mode;folder.mkdir(parents=True,exist_ok=True)
        for k in TRACKS:
            selection=plan['tracks'][k];sampled=selection.get('renderEngine')=='pitched-drum-sample';mid=folder/f'{k}.mid';raw=folder/f'{k}-raw.wav'
            midi(mid,spec['tracks'][k],recipe['bpm'],meter,spec['bars']*meter,None if sampled else selection['program'],9 if k=='dog' else 0)
            if sampled:
                assert selection['bank']==128 and selection['channel']==9,'sample recipe must point to drum preset'
                assert selection['sourceNote'] in map(int,selection['noteSources']),'unverified source drum key'
                if seed is None:
                    source=out/'assets/source';source.mkdir(exist_ok=True);p=source/'cowbell.mid';raw_seed=source/'cowbell.wav'
                    midi(p,[{'midi':selection['sourceNote'],'beat':0,'duration':.5,'velocity':100}],120,4,4,selection['program'],9)
                    seed=synth(p,raw_seed,sf,fs,sr).mean(axis=1)[:int(.55*sr)]
                    window=seed[int(.015*sr):int(.18*sr)];freq=np.fft.rfftfreq(65536,1/sr);power=abs(np.fft.rfft(window*np.hanning(len(window)),65536));mask=(freq>=350)&(freq<=1300)
                    anchor=float(freq[np.where(mask)[0][np.argmax(power[mask])]]);seed/=max(np.max(abs(seed)),1e-9);seed[-220:]*=np.linspace(1,0,220)
                    source_meta={'file':'assets/source/cowbell.wav','sha256':sha(raw_seed),'bank':selection['bank'],'program':selection['program'],'note':selection['sourceNote'],'pitchAnchorHz':anchor,'method':'dominant 350..1300Hz FFT partial; not harmonic fundamental or listening proof'}
                a=np.zeros((length,2))
                for n in spec['tracks'][k]:
                    ratio=440*2**((n['midi']-69)/12)/anchor;count=min(round((n['duration']*spb+.025)*sr),int(len(seed)/ratio));start=round(n['beat']*spb*sr);count=min(count,length-start)
                    if count<2:continue
                    sound=np.interp(np.arange(count)*ratio,np.arange(len(seed)),seed);sound=np.tanh(sound*1.6)/1.6*np.exp(-np.arange(count)/(sr*.18));fade=min(110,count//2);sound[:fade]*=np.linspace(0,1,fade);sound[-fade:]*=np.linspace(1,0,fade)
                    a[start:start+count]+=sound[:,None]*n['velocity']/100*.27
            else:
                a=synth(mid,raw,sf,fs,sr);raw.unlink();a=np.pad(a,((0,max(0,length-len(a))),(0,0)))[:length]
            if recipe['style']=='drift-phonk' and k=='cat':
                a=np.tanh(a*3.5)/1.7;duck=np.ones(length);span=int(.2*sr);curve=1-.62*np.exp(-np.arange(span)/(sr*.045))
                for n in spec['tracks']['dog']:
                    if n['midi']==36:
                        start=round(n['beat']*spb*sr);count=min(span,length-start);duck[start:start+count]=np.minimum(duck[start:start+count],curve[:count])
                a*=duck[:,None]
            a*=recipe['design']['mixLevels'][k];a[:220]*=np.linspace(0,1,220)[:,None];a[-882:]*=np.linspace(1,0,882)[:,None];audio[mode][k]=a
        print('rendered',mode,flush=True)
    peak=max(float(np.max(sum(abs(a) for a in tracks.values()))) for tracks in audio.values());gain=min(8,.86/max(peak,1e-9));segments={}
    for mode in reuse:
        audio[mode]={}
        for k in (*TRACKS,'mix'):
            asset=previous['segments'][mode]['assets'][k];source=(Path(reuse_from)/asset['file']).resolve();assert sha(source)==asset['sha256'],'reused asset hash changed'
            dest=out/asset['file'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
            if k in TRACKS:
                shutil.copy2(source.with_suffix('.mid'),dest.with_suffix('.mid'))
                with wave.open(str(source)) as w:audio[mode][k]=np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,2).astype(float)/32767/gain
        reuse_audio[mode]=previous['segments'][mode]
    audio={mode:audio[mode] for mode in sections}
    def write(rel,a):
        meta=wav(out/rel,a*gain,sr);meta['file']=rel;return meta
    drum_events={'version':1,'segments':{}};performer_events={'version':1,'segments':{}}
    for mode,tracks in audio.items():
        if mode in reuse:
            segments[mode]=reuse_audio[mode]
            drum_events['segments'][mode]=read(Path(reuse_from)/'drum-events.json')['segments'][mode]
            performer_events['segments'][mode]=read(Path(reuse_from)/'performance-events.json')['segments'][mode]
            continue
        spec=sections[mode];assets={k:write(f'assets/{mode}/{k}.wav',a) for k,a in tracks.items()};assets['mix']=write(f'assets/{mode}/mix.wav',sum(tracks.values()));duration=len(tracks['dog'])/sr
        segments[mode]={'bars':spec['bars'],'beats':spec['bars']*meter,'duration':spec['bars']*meter*spb,'assets':assets}
        # Event times use the exact tempo encoded in exported MIDI, including tick rounding.
        midi_spb=round(60e6/recipe['bpm'])/1e6;drums=[];poses={}
        for k,notes in spec['tracks'].items():
            def moment(t):return round(round(t*960)/960*midi_spb,6)
            if k=='dog':
                for n in notes:
                    p=n['midi'];kind='kick' if p in (35,36) else 'snare' if p in (37,38,39,40) else 'hat' if p in (42,44,46) else 'cymbal' if p in (49,51,52,53,55,57,59) else 'tom'
                    drums.append({'time':moment(n['beat']),'kind':kind,'note':p,'velocity':n['velocity']})
            else:
                grouped={}
                for n in notes:
                    time=moment(n['beat']);e=grouped.setdefault(time,{'time':time,'duration':0,'velocity':0,'notes':[]});e['duration']=max(e['duration'],round(moment(n['beat']+n['duration'])-time,6));e['velocity']=max(e['velocity'],n['velocity']);e['notes']=sorted(set(e['notes']+[n['midi']]))
                events=sorted(grouped.values(),key=lambda e:e['time']);until=0
                for e in events:until=max(until,e['time']+e['duration']);e['soundingUntil']=round(until,6)
                poses[k]={'wavSha256':assets[k]['sha256'],'midiSha256':sha(out/f'assets/{mode}/{k}.mid'),'events':events}
        drum_events['segments'][mode]={'duration':segments[mode]['duration'],'wavSha256':assets['dog']['sha256'],'midiSha256':sha(out/f'assets/{mode}/dog.mid'),'events':sorted(drums,key=lambda e:e['time'])};performer_events['segments'][mode]={'duration':segments[mode]['duration'],'tracks':poses}
    preview=write('assets/preview.wav',np.concatenate([sum(audio[k].values()) for k in ('theme','build','drop') if k in audio]))
    auditions={}
    for name,ids in [('drums-bass',['dog','cat']),('melody-harmony',['lion','bear']),('melody-rhythm',['lion','dog','cat']),('ensemble',list(TRACKS))]:auditions[name]=write(f'assets/auditions/{name}.wav',sum(audio['theme'][k] for k in ids))
    selection=json.loads(json.dumps(plan));selection['soundfont'].pop('path',None)
    for v in selection['tracks'].values():v['actualPresetName']=v['name']
    m={k:v for k,v in recipe.items() if k not in ('sourceScore','sectionScores')};m.update(segments=segments,sectionScores=sections,preview=preview,auditions=auditions,sharedGain=gain,programs={k:v['program'] for k,v in plan['tracks'].items()},renderSelection=selection,soundfont={'name':Path(sf).name,'sha256':sha(sf)},sourceScoreHash=hashlib.sha256(json.dumps(recipe['sourceScore'],sort_keys=True).encode()).hexdigest())
    if reuse:m['design']['reusedSections']={mode:{k:a['sha256'] for k,a in segments[mode]['assets'].items()} for mode in reuse}
    if all(k in audio for k in ('theme','build','drop')):
        span=round(meter*4*spb*sr);m['sectionPreview']=write('assets/section-transitions.wav',np.concatenate([sum(audio['theme'].values())[-span:],sum(audio['build'].values()),sum(audio['drop'].values()),sum(audio['theme'].values())[:span]]))
    if source_meta:m['design']['cowbellSource']=source_meta
    save(out/'manifest.json',m);save(out/'arrangement.json',recipe);save(out/'drum-events.json',drum_events);save(out/'performance-events.json',performer_events)
    report=check(out/'manifest.json');save(out/'checks.json',report);assert report['technical_status']=='passed',report
    print(json.dumps({'output':str(out),'status':report['technical_status'],'preview':str(out/preview['file'])},ensure_ascii=False))

def pack(output,bundles):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);registry=[]
    for folder in map(Path,bundles):
        m=read(folder/'manifest.json');verify_bundle(folder)
        assert all(isinstance(m.get(k),str) and re.fullmatch('[a-z][a-z0-9-]*',m[k]) for k in ('songId','style')),'bundle ids must be safe slugs'
        assert not output.resolve().is_relative_to(folder.resolve()),'pack output cannot be inside its input bundle'
        dest=output/'arrangements'/m['songId']/m['style'];dest.parent.mkdir(parents=True,exist_ok=True)
        assert dest.resolve()!=folder.resolve(),'pack output must be separate'
        shutil.copytree(folder,dest,dirs_exist_ok=True);registry.append({'songId':m['songId'],'title':m['title'],'style':m['style'],'base':str(dest.relative_to(output))+'/'})
    template=ROOT/'assets/portable-player'
    shutil.copytree(template,output,dirs_exist_ok=True);save(output/'catalog.json',registry)
    page=output/'index.html';page.write_text(page.read_text().replace('src="player.js"',f'src="player.js?v={sha(output/"player.js")[:12]}"'))
    print(json.dumps({'entry':str(output/'index.html'),'serve':'python3 -m http.server 4192 --bind 127.0.0.1 --directory '+str(output),'arrangements':len(registry)},ensure_ascii=False))
def verify_bundle(folder):
    from check_arrangement import check
    from midi_score import decode
    from instrument_contract import verify as verify_instruments
    verify_instruments(folder)
    folder=Path(folder).resolve();m=read(folder/'manifest.json');report=check(folder/'manifest.json');assert report['technical_status']=='passed',report
    drums=read(folder/'drum-events.json');poses=read(folder/'performance-events.json')
    for mode,spec in m['segments'].items():
        for k in TRACKS:
            wav_path=(folder/spec['assets'][k]['file']).resolve();assert wav_path.is_relative_to(folder),'asset escapes bundle';mid=wav_path.with_suffix('.mid');assert sha(wav_path)==spec['assets'][k]['sha256'],'WAV changed after checks'
            meta=drums['segments'][mode] if k=='dog' else poses['segments'][mode]['tracks'][k]
            assert meta['wavSha256']==sha(wav_path) and meta['midiSha256']==sha(mid),'event provenance changed'
            midi_data=decode(mid);spb=midi_data['tempoMicroseconds']/1e6;notes=midi_data['notes']
            onsets=sorted({round(n['beat']*spb,6) for n in notes});actual=sorted({e['time'] for e in meta['events']});assert onsets==actual,'event onsets differ from MIDI'
            for e in meta['events']:
                at=[n for n in notes if round(n['beat']*spb,6)==e['time']]
                if k=='dog':assert e['note'] in {n['midi'] for n in at},'drum event pitch differs'
                else:assert sorted({n['midi'] for n in at})==sorted(e['notes']),'event pitches differ from MIDI'
    return report
def import_midi(path,output,title,song_id,channel):
    from midi_score import decode
    m=decode(path);assert m['denominator']==4 and m['beatsPerBar'] in (2,3,4),'import supports 2/4, 3/4, 4/4 only'
    notes=[{k:n[k] for k in ('midi','beat','duration')} for n in m['notes'] if n['channel']==channel];assert notes,'no notes on selected channel'
    end=0
    for n in notes:assert n['beat']>=end-1e-6,'selected channel is polyphonic; select/transcribe melody first';end=n['beat']+n['duration']
    length=math.ceil(max(n['beat']+n['duration'] for n in notes)/m['beatsPerBar'])*m['beatsPerBar']
    save(output,{'version':1,'id':song_id,'title':title,'bpm':round(m['bpm'],4),'beatsPerBar':m['beatsPerBar'],'beats':length,'source':{'file':Path(path).name,'sha256':sha(path),'importChannel':channel},'melody':notes,'chords':[],'status':'melody imported; phrase boundaries and harmony must be authored/reviewed before arrange'})
def build(song,style,plan,sf,fs,output,recipe=None):
    validate_song(song)
    recipe=recipe if recipe is not None else arrange(song,style)
    assert recipe['style']==style and plan['style']==style,'style differs across request, score and sound plan'
    assert recipe['sourceScore']==song and recipe['songId']==song['id'],'arrangement belongs to another source song'
    assert set(recipe['sectionScores'])=={'theme','build','drop','hold'},'complete performance sections required'
    output=Path(output)
    # Complete editable sources stay outside the shareable performance directory.
    save(output/'song.json',song);save(output/'arrangement.json',recipe)
    render(recipe,plan,sf,fs,output/'final')
    verify_bundle(output/'final')
    pack(output/'performance',[output/'final'])
    return output/'performance'

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('validate');q.add_argument('song')
    q=sub.add_parser('verify-bundle');q.add_argument('folder')
    q=sub.add_parser('import-midi');q.add_argument('midi');q.add_argument('--channel',type=int,default=0);q.add_argument('--title',required=True);q.add_argument('--id',required=True);q.add_argument('--output',required=True)
    q=sub.add_parser('arrange');q.add_argument('song');q.add_argument('--style',required=True);q.add_argument('--bpm',type=float);q.add_argument('--output',required=True)
    q=sub.add_parser('render');q.add_argument('recipe');q.add_argument('--sound-plan',required=True);q.add_argument('--soundfont',required=True);q.add_argument('--fluidsynth',required=True);q.add_argument('--output',required=True);q.add_argument('--pilot',action='store_true');q.add_argument('--reuse-from')
    q=sub.add_parser('pack');q.add_argument('--output',required=True);q.add_argument('bundles',nargs='+')
    q=sub.add_parser('build');q.add_argument('song');q.add_argument('--style',required=True);q.add_argument('--arrangement');q.add_argument('--sound-plan',required=True);q.add_argument('--soundfont',required=True);q.add_argument('--fluidsynth',required=True);q.add_argument('--output',required=True)
    q=sub.add_parser('doctor');q.add_argument('--soundfont');q.add_argument('--fluidsynth')
    a=p.parse_args()
    if a.cmd=='validate':validate_song(read(a.song));print('song valid')
    elif a.cmd=='verify-bundle':verify_bundle(a.folder);print('bundle audio/MIDI/events verified')
    elif a.cmd=='import-midi':import_midi(a.midi,a.output,a.title,a.id,a.channel)
    elif a.cmd=='arrange':save(a.output,arrange(read(a.song),a.style,a.bpm));print(a.output)
    elif a.cmd=='render':render(read(a.recipe),read(a.sound_plan),a.soundfont,a.fluidsynth,a.output,a.pilot,a.reuse_from)
    elif a.cmd=='pack':pack(a.output,a.bundles)
    elif a.cmd=='build':build(read(a.song),a.style,read(a.sound_plan),a.soundfont,a.fluidsynth,a.output,read(a.arrangement) if a.arrangement else None)
    else:print(json.dumps({'python':sys.version.split()[0],'numpy':np.__version__ if np is not None else None,'fluidsynth':bool(a.fluidsynth and Path(a.fluidsynth).is_file() or shutil.which('fluidsynth')),'soundfont':bool(a.soundfont and Path(a.soundfont).is_file()),'scope':'local fixed-tempo symbolic scores; no automatic audio transcription'},ensure_ascii=False))
if __name__=='__main__':main()
