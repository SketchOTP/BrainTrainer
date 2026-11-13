import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from analyze_gene7_reversal_diagnostics import analyze_case
from analyze_gene7_reversal_lag import analyze_case as analyze_lag


class ReversalDiagnosticTests(unittest.TestCase):
    def test_maps_food_eat_and_tracks_lagged_feedback_and_migration(self):
        def dendrite(source, destination, weight):
            return {'source': source, 'destination': destination, 'variables': [weight] + [0.0]*7}
        tract = {'gene_id': 7, 'source': 'driv', 'destination': 'comb',
                 'dendrites': [dendrite(2,163,.6)], 'weak': [], 'helper': {}, 'migrations': 0}
        attn = {'gene_id': 9, 'source': 'comb', 'destination': 'attn',
                'dendrites': [dendrite(163,3,0),dendrite(168,8,0)]}
        decn = {'gene_id': 10, 'source': 'comb', 'destination': 'decn',
                'dendrites': [dendrite(163,4,0),dendrite(168,4,0)]}
        steps=[]
        phases=['experience','evaluation','reversal','reversal_evaluation']
        for op in range(80):
            choice={'action': 12 if op==40 else 0, 'target':'object-1' if op==40 else None}
            outcome={'completed': op==40, 'target':'object-1' if op==40 else None}
            event={'opportunity':op, 'phase':phases[op//20], 'choice':choice, 'outcome':outcome,
                   'opportunity_end':True,'success':op==40}
            pending=[{'target':'object-1','hunger_adjustment':-.25}] if op==41 else []
            delta=[{'gene_id':7,'source':'driv','destination':'comb',
                    'dendrites':[{'index':0,'value':dendrite(2,168,.4)}], 'metadata':{}}] if op==41 else []
            steps.append({'event':event,'pending_before':pending,'tract_delta':delta})
        row={'seed':0,'body':'walking','mirror':False,'good':0,'control':'ordinary',
             'initial_tracts':[tract,attn,decn],'steps':steps}
        result=analyze_case(row)
        self.assertEqual(result['first_new_eat_opportunity'],0)
        self.assertEqual(result['first_new_consumption_opportunity'],0)
        self.assertEqual(result['first_new_feedback_opportunity'],1)
        self.assertEqual(result['new_feedback_events'],1)
        self.assertEqual(result['new_feedback_ticks_dendrite_delta'],1)
        self.assertEqual(result['migration_events'],1)
        self.assertEqual(result['snapshots']['40']['old_food_eat']['count'],1)
        self.assertEqual(result['snapshots']['60']['new_food_eat']['count'],1)
        self.assertIsNone(result['first_success_after_new_feedback_opportunity'])
        lag=analyze_lag(row)
        self.assertEqual(lag['first_new_success_opportunity'],0)
        self.assertEqual(lag['first_crossing_opportunity'],1)
        self.assertIsNone(lag['first_success_after_crossing_opportunity'])


if __name__ == '__main__': unittest.main()
