#!/usr/bin/env python3
"""Inspect fixed-tempo beat scores and actual PCM16 stems; never grade musical taste."""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import wave

DEFAULT_ROLES={'dog':'drums','bear':'chords','cat':'bass','lion':'lead'}

def number(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)

def check(path, audio=True):
    path=Path(path).resolve();m=json.loads(path.read_text())
    report={'errors':[], 'unchecked':[], 'segments':{}, 'musical_quality':'not_assessed'}
    errors=report['errors'];unchecked=report['unchecked']
    def finish():
        report['technical_status']='failed' if errors else 'incomplete' if unchecked else 'passed'
        return report
    bpm=m.get('bpm');meter=m.get('beatsPerBar')
    if not number(bpm) or bpm<=0 or not number(meter) or meter<=0:
        errors.append('bpm and beatsPerBar must be finite and positive');return finish()
    if m.get('tempoMap'):
        unchecked.append('tempoMap: this helper supports fixed-tempo manifests only');return finish()
    segments=m.get('segments');scores=m.get('sectionScores')
    if not isinstance(segments,dict) or not segments or not isinstance(scores,dict):
        errors.append('Expected nonempty segments and sectionScores mappings');return finish()
    roles={**DEFAULT_ROLES,**m.get('trackRoles',{})}
    for mode,spec in segments.items():
        label=str(mode);duration=spec.get('duration');beats=spec.get('beats')
        if not number(duration) or duration<=0 or not number(beats) or beats<=0:
            errors.append(f'{label}: positive duration and beats required');continue
        if abs(duration-beats*60/bpm)>1/44100:
            errors.append(f'{label}: duration disagrees with beat clock')
        tracks=scores.get(mode,{}).get('tracks')
        if not isinstance(tracks,dict) or not tracks:
            errors.append(f'{label}: missing score tracks');continue
        result={'tracks':{},'observations':{}};report['segments'][mode]=result
        valid={}
        for track,notes in tracks.items():
            tag=f'{label}/{track}';clean=[]
            if not isinstance(notes,list):errors.append(tag+': expected note list');continue
            for i,n in enumerate(notes):
                if not isinstance(n,dict):errors.append(f'{tag} note {i}: expected object');continue
                at=n.get('beat');length=n.get('duration')
                if not number(at) or not number(length) or at<0 or length<=0 or at+length>beats+1e-5:
                    errors.append(f'{tag} note {i}: invalid or out-of-bounds timing');continue
                ranges={'midi':(0,127),'velocity':(1,127),'channel':(0,15)}
                if any(not isinstance(n.get(k),int) or isinstance(n.get(k),bool) or not lo<=n[k]<=hi for k,(lo,hi) in ranges.items()):
                    errors.append(f'{tag} note {i}: invalid MIDI pitch, velocity or channel');continue
                clean.append(n)
            valid[track]=clean
            onsets=sorted(set(n['beat'] for n in clean))
            result['tracks'][track]={'notes':len(clean),'attacks':len(onsets),
                'pitch_range':[min(n['midi'] for n in clean),max(n['midi'] for n in clean)] if clean else None,
                'mean_note_beats':round(sum(n['duration'] for n in clean)/len(clean),4) if clean else 0,
                'mean_attack_gap_beats':round(sum(b-a for a,b in zip(onsets,onsets[1:]))/(len(onsets)-1),4) if len(onsets)>1 else None}
        def role_notes(role):return [n for k,ns in valid.items() if roles.get(k)==role for n in ns]
        bass=role_notes('bass');kick=[n['beat'] for n in role_notes('drums') if n['midi'] in (35,36)]
        obs=result['observations']
        obs['bass_attacks_near_kick_fraction']=round(sum(any(abs(n['beat']-t)<=.04 for t in kick) for n in bass)/len(bass),4) if bass and kick else None
        lead=role_notes('lead');chords=role_notes('chords')
        overlaps=[{'beat':n['beat'],'accompaniment_pitch':n['midi'],'lead_pitch':x['midi']}
                  for n in chords for x in lead if abs(n['midi']-x['midi'])==1 and n['beat']<x['beat']+x['duration'] and x['beat']<n['beat']+n['duration']]
        obs['adjacent_register_semitone_pairs']=len(overlaps);obs['semitone_examples']=overlaps[:5]
        obs['interpretation']='Descriptive only: complementary rhythm and intentional dissonance can be valid.'
        if not audio:unchecked.append(label+': actual audio skipped');continue
        assets=spec.get('assets',{});pcm={};formats={}
        for track in [*tracks,'mix']:
            asset=assets.get(track)
            if not asset or not asset.get('file'):
                unchecked.append(f'{label}/{track}: no rendered WAV supplied');continue
            file=path.parent/asset['file'];tag=f'{label}/{track}'
            if not file.is_file():errors.append(tag+': audio file missing');continue
            if asset.get('sha256') and hashlib.sha256(file.read_bytes()).hexdigest()!=asset['sha256']:
                errors.append(tag+': SHA256 mismatch')
            try:
                with wave.open(str(file)) as w:
                    channels,width,rate,frames=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes()
                    if abs(frames-duration*rate)>1.01:errors.append(tag+': frame duration mismatch')
                    if width!=2 or w.getcomptype()!='NONE':
                        unchecked.append(tag+': only uncompressed PCM16 sample analysis supported');continue
                    samples=array('h',w.readframes(frames))
                    if sys.byteorder!='little':samples.byteswap()
                if not samples:errors.append(tag+': empty audio');continue
                clipped=sum(x>=32767 or x<=-32768 for x in samples)
                if clipped:errors.append(f'{tag}: {clipped} full-scale samples (clipping risk)')
                peak=max(abs(x) for x in samples)/32768
                rms=math.sqrt(sum(x*x for x in samples)/len(samples))/32768
                result['tracks'].setdefault(track,{})['audio']={'peak':round(peak,6),'rms':round(rms,6),'frames':frames,'sample_rate':rate,'channels':channels}
                formats[track]=(channels,rate,frames);pcm[track]=samples
            except (wave.Error,EOFError,OSError) as e:
                unchecked.append(f'{tag}: WAV sample analysis unsupported: {e}')
        if len(set(formats.values()))>1:errors.append(label+': stems/mix have mismatched channels, rates or frame counts')
        if set(tracks).issubset(pcm) and 'mix' in pcm and len(set(formats.values()))==1:
            residual=max(abs(sum(xs[:-1])-xs[-1]) for xs in zip(*(pcm[k] for k in tracks),pcm['mix']))
            obs['stem_sum_max_error_lsb']=residual
            if residual>len(tracks):
                obs['stem_sum_review']='Does not sum to supplied mix; inspect bus processing, gains and export routing.'
    return finish()

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('manifest',type=Path);ap.add_argument('--output',type=Path);ap.add_argument('--scores-only',action='store_true');a=ap.parse_args()
    try:result=check(a.manifest,not a.scores_only)
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as e:
        result={'technical_status':'failed','musical_quality':'not_assessed','errors':[str(e)]}
    text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if a.output:a.output.write_text(text)
    else:print(text,end='')
    return 1 if result['technical_status']=='failed' else 2 if result['technical_status']=='incomplete' else 0
if __name__=='__main__':sys.exit(main())
