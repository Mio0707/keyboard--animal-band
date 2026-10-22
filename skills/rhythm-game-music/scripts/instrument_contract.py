"""Check sounding MIDI presets against render selections, including reused sections.

Silent stems retain their performer; their unused MIDI preset does not change the
instrument. Pitched drum samples use the verified source MIDI instead of the
melody MIDI (which is only a pitch/time control score).
"""
import hashlib
import json
from pathlib import Path

TRACKS = ('dog', 'bear', 'cat', 'lion')

def sounding_presets(path):
    data = Path(path).read_bytes()
    assert data[:4] == b'MThd', f'{path}: not MIDI'
    pos = 8 + int.from_bytes(data[4:8], 'big')
    events = []
    order = 0
    while pos < len(data):
        assert data[pos:pos+4] == b'MTrk', f'{path}: invalid track'
        size = int.from_bytes(data[pos+4:pos+8], 'big')
        pos += 8
        stop = pos + size
        tick = 0
        running = None
        def vlq():
            nonlocal pos
            value = 0
            for _ in range(4):
                value = value * 128 + (data[pos] & 127)
                last = data[pos]
                pos += 1
                if last < 128:
                    return value
            raise ValueError('invalid MIDI delta')
        while pos < stop:
            tick += vlq()
            status = data[pos]
            if status >= 128:
                pos += 1
            else:
                assert running is not None, 'missing MIDI running status'
                status = running
            if status == 255:
                pos += 1
                length = vlq()
                pos += length
            elif status in (240, 247):
                length = vlq()
                pos += length
                running = None
            else:
                assert 128 <= status < 240
                running = status
                kind, channel = status >> 4, status & 15
                length = 1 if kind in (12, 13) else 2
                payload = data[pos:pos+length]
                pos += length
                events.append((tick, order, kind, channel, payload))
                order += 1
        assert pos == stop, 'invalid MIDI length'
    programs = {}
    active = set()
    for _, _, kind, channel, payload in sorted(events):
        if kind == 12:
            programs[channel] = payload[0]
        elif kind == 9 and payload[1]:
            active.add((channel, programs.get(channel, 0)))
    return active

def verify(folder):
    folder = Path(folder)
    m = json.loads((folder / 'manifest.json').read_text())
    result = {}
    for mode, segment in m['segments'].items():
        result[mode] = {}
        for track in TRACKS:
            selection = m['renderSelection']['tracks'][track]
            expected = selection['program']
            assert m['programs'][track] == expected, f'{track}: conflicting preset metadata'
            asset = segment['assets'][track]
            wav = folder / asset['file']
            assert hashlib.sha256(wav.read_bytes()).hexdigest() == asset['sha256'], f'{wav}: stale audio hash'
            midi = wav.with_suffix('.mid')
            active = sounding_presets(midi)
            # No note-ons means silence, not an instrument change.
            if active and selection.get('renderEngine') == 'pitched-drum-sample':
                source = m['design']['cowbellSource']
                assert (source['bank'], source['program'], source['note']) == (selection['bank'], expected, selection['sourceNote'])
                source_wav = folder / source['file']
                assert hashlib.sha256(source_wav.read_bytes()).hexdigest() == source['sha256']
                assert sounding_presets(source_wav.with_suffix('.mid')) == {(selection['channel'], expected)}, f'{mode}/{track}: source sample preset differs'
                status = 'verified pitched sample'
            elif active:
                expected_channel = 9 if track == 'dog' else 0
                assert active == {(expected_channel, expected)}, f'{folder.name}/{mode}/{track}: sounding presets {active} differ from {(expected_channel, expected)}'
                status = 'matched'
            else:
                status = 'silent'
            events = json.loads((folder / ('drum-events.json' if track == 'dog' else 'performance-events.json')).read_text())
            meta = events['segments'][mode] if track == 'dog' else events['segments'][mode]['tracks'][track]
            assert meta['midiSha256'] == hashlib.sha256(midi.read_bytes()).hexdigest(), f'{mode}/{track}: stale action events'
            assert meta['wavSha256'] == asset['sha256'], f'{mode}/{track}: stale audio events'
            result[mode][track] = status
    return result
