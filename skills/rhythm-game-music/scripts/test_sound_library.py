"""Integration tests against a freshly scanned local library; no musical-taste assertions."""
import copy,json,os,unittest
from pathlib import Path
import sound_library as sl
ROOT=Path(__file__).resolve().parents[1]
class MappingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  catalog=Path(os.environ.get('RHYTHM_SOUND_CATALOG',ROOT/'data/local-sound-library.json'))
  if not catalog.is_file():raise unittest.SkipTest('Run sound_library.py scan and set RHYTHM_SOUND_CATALOG for these local-library integration checks')
  cls.catalog=json.loads(catalog.read_text())
  cls.profiles=json.loads((ROOT/'assets/style-sound-profiles.json').read_text())
  cls.sf=cls.catalog['soundfont']['path']
  cls.plan=sl.resolve(cls.catalog,cls.profiles,'bossa-nova')
 def test_all_routes_resolve_to_actual_presets(self):
  for style in self.profiles['styles']:self.assertTrue(sl.validate(sl.resolve(self.catalog,self.profiles,style),self.sf))
 def test_pandeiro_cannot_be_silently_substituted(self):
  with self.assertRaisesRegex(ValueError,'Pandeiro'):sl.resolve(self.catalog,self.profiles,'bossa-nova',['pandeiro'])
 def test_unknown_semantic_requirement_is_not_ignored(self):
  with self.assertRaisesRegex(ValueError,'No implemented'):sl.resolve(self.catalog,self.profiles,'bossa-nova',['guzheng'])
 def test_stale_soundfont_hash_is_rejected(self):
  p=copy.deepcopy(self.plan);p['soundfont']['sha256']='stale'
  with self.assertRaisesRegex(ValueError,'SHA256'):sl.validate(p,self.sf)
 def test_missing_program_does_not_fall_back(self):
  p=copy.deepcopy(self.plan);p['tracks']['bear']['program']=999
  with self.assertRaisesRegex(ValueError,'does not exist'):sl.validate(p,self.sf)
 def test_melodic_and_drum_bank_same_program_are_distinct(self):
  p=copy.deepcopy(self.plan);p['tracks']['dog']['bank']=0
  with self.assertRaisesRegex(ValueError,'bank'):sl.validate(p,self.sf)
 def test_extra_articulation_bank_is_not_falsely_supported(self):
  p=copy.deepcopy(self.plan);p['tracks']['bear'].update(bank=20,program=48)
  with self.assertRaisesRegex(ValueError,'bank'):sl.validate(p,self.sf)
 def test_missing_drum_key_is_rejected(self):
  p=copy.deepcopy(self.plan);p['tracks']['dog']['allowedNotes']=[128]
  with self.assertRaisesRegex(ValueError,'keys'):sl.validate(p,self.sf)
 def test_brush_selection_keeps_actual_sample_evidence(self):
  self.assertIn('Brush Snr 1',' '.join(self.plan['tracks']['dog']['noteSources']['38']))
  self.assertNotIn('Brush Snr 1',' '.join(self.plan['tracks']['dog']['noteSources']['37']))
 def test_web_inventory_is_a_limited_subset(self):
  samples=[v for library in self.catalog['sampleLibraries'] for v in library['instruments'].values()]
  self.assertEqual(len(samples),4)
  self.assertTrue(all(s['exists'] for v in samples for s in v['samples']))
if __name__=='__main__':unittest.main(verbosity=2)
