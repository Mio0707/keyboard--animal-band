import copy,json,struct,tempfile,unittest
from pathlib import Path
from song_bundle import arrange,validate_song,midi,import_midi
from midi_score import decode

def fixture():
    return {'id':'independent-waltz','title':'Independent three-beat test','bpm':87.5,'beatsPerBar':3,'beats':9,'source':{'file':'original-test-melody'},'melody':[{'midi':62,'beat':0,'duration':1},{'midi':65,'beat':1,'duration':2},{'midi':69,'beat':3,'duration':1.5},{'midi':65,'beat':4.5,'duration':1.5},{'midi':62,'beat':6,'duration':3}],'chords':[{'name':'Dm7','beat':0,'duration':9,'root':38,'voicing':[53,57,60,65]}],'phraseEnds':[3,6,9]}

class SongTests(unittest.TestCase):
    def test_source_not_jasmine_length_or_clock(self):
        s=fixture();validate_song(s)
        for style in ('swing-jazz','drift-phonk'):
            a=arrange(s,style);self.assertEqual((a['bpm'],a['beatsPerBar']),(87.5,3));self.assertEqual(a['sectionScores']['theme']['bars'],3);self.assertEqual(a['sectionScores']['drop']['bars'],4)
            pitches=[n['midi']-(12 if style=='drift-phonk' else 0) for n in a['sectionScores']['theme']['tracks']['lion']]
            self.assertEqual(pitches,[n['midi'] for n in s['melody']])
    def test_all_generated_times_bounded_in_non_four_meter(self):
        for style in ('swing-jazz','drift-phonk'):
            a=arrange(fixture(),style)
            for section in a['sectionScores'].values():
                for notes in section['tracks'].values():
                    for n in notes:self.assertTrue(0<=n['beat']<n['beat']+n['duration']<=section['bars']*3+1e-5)
    def test_no_implicit_mutation_of_source(self):
        s=fixture();before=copy.deepcopy(s);arrange(s,'swing-jazz');self.assertEqual(s,before)
    def test_missing_harmony_rejected(self):
        s=fixture();s['chords']=[]
        with self.assertRaisesRegex(AssertionError,'chords'):validate_song(s)
    def test_song_id_cannot_escape_output_folder(self):
        s=fixture();s['id']='../../outside'
        with self.assertRaisesRegex(AssertionError,'slug'):validate_song(s)
    def test_harmony_gap_rejected(self):
        s=fixture();s['chords'][0]['beat']=1
        with self.assertRaisesRegex(AssertionError,'cover'):validate_song(s)
    def test_out_of_bounds_and_nan_rejected(self):
        s=fixture();s['melody'][0]['duration']=99
        with self.assertRaises(AssertionError):validate_song(s)
        s=fixture();s['bpm']=float('nan')
        with self.assertRaises(AssertionError):validate_song(s)
    def test_midi_import_preserves_pitch_duration_and_meter(self):
        with tempfile.TemporaryDirectory() as d:
            s=fixture();p=Path(d)/'test.mid';notes=[{**n,'velocity':70} for n in s['melody']];midi(p,notes,87.5,3,9,0)
            decoded=decode(p);self.assertEqual(decoded['beatsPerBar'],3);self.assertAlmostEqual(decoded['bpm'],87.5,3)
            self.assertEqual([{k:n[k] for k in ('midi','beat','duration')} for n in decoded['notes']],s['melody'])
            output=Path(d)/'imported.json';import_midi(p,output,'Test','test',0);imported=json.loads(output.read_text());self.assertEqual(imported['beats'],9);self.assertEqual(imported['chords'],[])
    def test_polyphonic_import_is_not_silently_called_melody(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'chord.mid';midi(p,[{'midi':n,'beat':0,'duration':2,'velocity':60} for n in (60,64)],100,4,4,0)
            with self.assertRaisesRegex(AssertionError,'polyphonic'):import_midi(p,Path(d)/'out.json','T','t',0)
    def test_tempo_map_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'map.mid';body=b'\0\xff\x51\x03\x07\xa1\x20\x60\xff\x51\x03\x09\x27\xc0\0\xff\x2f\0';p.write_bytes(b'MThd'+struct.pack('>IHHH',6,0,1,96)+b'MTrk'+struct.pack('>I',len(body))+body)
            with self.assertRaisesRegex(AssertionError,'tempo-map'):decode(p)
    def test_new_styles_fail_explicitly_in_starter(self):
        with self.assertRaisesRegex(AssertionError,'explicit arrangement'):arrange(fixture(),'bossa-nova')

if __name__=='__main__':unittest.main()
