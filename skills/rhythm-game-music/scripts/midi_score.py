"""SMF 0/1 decoder for symbolic import and independent rendered-event checks."""
import struct
from pathlib import Path
def decode(path):
    data=Path(path).read_bytes();assert data[:4]==b'MThd','not MIDI';header=struct.unpack('>I',data[4:8])[0];fmt,count,ppq=struct.unpack('>HHH',data[8:14]);assert fmt in (0,1) and ppq and not ppq&0x8000,'SMF 0/1 PPQ required'
    pos=8+header;events=[];meters=[];tempos=[];end_tick=0
    for track in range(count):
        assert data[pos:pos+4]==b'MTrk';size=struct.unpack('>I',data[pos+4:pos+8])[0];pos+=8;end=pos+size;tick=0;running=None
        def vlq():
            nonlocal pos
            value=0
            for _ in range(4):
                b=data[pos];pos+=1;value=value*128+(b&127)
                if b<128:return value
            raise ValueError('invalid VLQ')
        while pos<end:
            tick+=vlq();status=data[pos]
            if status>=128:pos+=1
            else:assert running is not None;status=running
            if status==255:
                kind=data[pos];pos+=1;n=vlq();payload=data[pos:pos+n];pos+=n
                if kind==81:tempos.append((tick,int.from_bytes(payload,'big')))
                if kind==88:meters.append((tick,payload[0],2**payload[1]))
            elif status in (240,247):n=vlq();pos+=n;running=None
            else:
                assert 128<=status<240;running=status;n=1 if status>>4 in (12,13) else 2;payload=data[pos:pos+n];pos+=n
                if status>>4 in (8,9):events.append((tick,status>>4==9 and payload[1]>0,status&15,payload[0],payload[1],track))
        assert pos==end;end_tick=max(end_tick,tick)
    tempo_values={v for t,v in tempos};meter_values={(n,d) for t,n,d in meters}
    assert len(tempo_values)<=1,'tempo-map MIDI requires explicit beat mapping, not constant-tempo import'
    assert len(meter_values)<=1,'meter changes require explicit transcription'
    tempo=next(iter(tempo_values),500000);meter=next(iter(meter_values),(4,4));active={};notes=[]
    for tick,on,ch,p,v,track in sorted(events,key=lambda e:(e[0],e[1])):
        key=(track,ch,p)
        if on:active.setdefault(key,[]).append((tick,v))
        elif active.get(key):
            start,velocity=active[key].pop(0);assert tick>start,'zero-length MIDI note';notes.append({'midi':p,'beat':start/ppq,'duration':(tick-start)/ppq,'velocity':velocity,'channel':ch,'track':track})
    assert not any(active.values()),'unmatched note-on'
    return {'bpm':60e6/tempo,'tempoMicroseconds':tempo,'beatsPerBar':meter[0],'denominator':meter[1],'beats':end_tick/ppq,'notes':sorted(notes,key=lambda n:(n['beat'],n['midi']))}
