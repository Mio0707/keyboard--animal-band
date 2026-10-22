import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from instrument_contract import verify, sounding_presets
from song_bundle import midi

class ContractTests(unittest.TestCase):
    def fixture(self, root):
        assets={};poses={};drums=None
        for k in ('dog','bear','cat','lion'):
            path=root/f'{k}.wav';path.write_bytes(b'test asset identity')
            notes=[] if k=='lion' else [{'midi':36 if k=='dog' else 60,'beat':0,'duration':1,'velocity':70}]
            midi(path.with_suffix('.mid'),notes,96,4,4,33 if k=='cat' else 0,9 if k=='dog' else 0)
            digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            assets[k]={'file':path.name,'sha256':digest(path)}
            meta={'midiSha256':digest(path.with_suffix('.mid')),'wavSha256':digest(path)}
            if k=='dog':drums=meta
            else:poses[k]=meta
        m={'programs':{k:33 if k=='cat' else 0 for k in assets},'renderSelection':{'tracks':{k:{'program':33 if k=='cat' else 0} for k in assets}},'segments':{'theme':{'assets':assets}}}
        for name,value in [('manifest.json',m),('drum-events.json',{'segments':{'theme':drums}}),('performance-events.json',{'segments':{'theme':{'tracks':poses}}})]:
            (root/name).write_text(json.dumps(value))
        return m

    def test_silent_stem_is_not_an_instrument_change(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root)
            self.assertEqual(verify(root)['theme']['lion'],'silent')

    def test_sounding_preset_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root)
            path=root/'cat.mid';data=path.read_bytes();path.write_bytes(data.replace(bytes([0xc0,33]),bytes([0xc0,38])))
            self.assertEqual(sounding_presets(path),{(0,38)})
            with self.assertRaisesRegex(AssertionError,'sounding presets'):verify(root)

    def test_stale_action_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root)
            p=root/'performance-events.json';events=json.loads(p.read_text());events['segments']['theme']['tracks']['cat']['midiSha256']='stale';p.write_text(json.dumps(events))
            with self.assertRaisesRegex(AssertionError,'stale action'):verify(root)

if __name__=='__main__':unittest.main()
