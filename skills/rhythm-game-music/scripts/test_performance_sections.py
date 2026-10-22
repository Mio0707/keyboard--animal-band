import copy,unittest
from performance_sections import rewrite
from test_song_bundle import fixture
from song_bundle import arrange
class PerformanceSections(unittest.TestCase):
    def test_six_routes_have_four_bar_units_and_preserve_theme(self):
        for style in ('electronic','jazz-funk','bossa-nova','swing-jazz','drift-phonk'):
            source=fixture();recipe=arrange(source,'swing-jazz');recipe['style']=style;before=copy.deepcopy(recipe['sectionScores']['theme']);r=rewrite(recipe,source,50,True,0,4)
            self.assertEqual(r['sectionScores']['theme'],before)
            for mode in ('build','drop'):
                self.assertEqual(r['sectionScores'][mode]['bars'],4)
                for notes in r['sectionScores'][mode]['tracks'].values():
                    for n in notes:self.assertTrue(0<=n['beat']<n['beat']+n['duration']<=12+1e-5)
    def test_acoustic_interludes_exchange_lead_role(self):
        for style in ('jazz-funk','bossa-nova','swing-jazz'):
            s=fixture();r=arrange(s,'swing-jazz');r['style']=style;r=rewrite(r,s,50,True)
            self.assertEqual(r['sectionScores']['build']['tracks']['lion'],[])
            self.assertTrue(r['sectionScores']['drop']['tracks']['lion'])
    def test_phonk_withdraws_low_end_and_restores_joint_anchors(self):
        s=fixture();r=arrange(s,'drift-phonk');build=r['sectionScores']['build']['tracks'];drop=r['sectionScores']['drop']['tracks']
        self.assertEqual(build['cat'],[]);self.assertFalse(any(n['midi']==36 for n in build['dog']))
        kick={n['beat'] for n in drop['dog'] if n['midi']==36};bass={n['beat'] for n in drop['cat']};self.assertEqual(kick,bass)
    def test_custom_unit_length_is_explicit(self):
        s=fixture();s['performanceClipBars']=8;r=arrange(s,'drift-phonk');self.assertEqual(r['sectionScores']['drop']['bars'],8)
if __name__=='__main__':unittest.main()
