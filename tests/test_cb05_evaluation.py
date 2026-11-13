"""Prospective panel balance and seed-cluster outcome accounting."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from cb05_condition_table import table,verify,SEEDS,PHASES


class ConditionBalanceTests(unittest.TestCase):
    def test_every_phase_crosses_hunger_food_side_and_value_is_not_parity(self):
        rows=table();self.assertTrue(verify(rows))
        self.assertEqual(len(rows),384)
        for phase in PHASES:
            c=Counter((r['hunger'],r['food_index'],r['side'],r['beneficial_food_index'])
                      for r in rows if r['phase']==phase)
            self.assertEqual(set(c.values()),{8})
        for parity in (0,1):
            assigned=Counter((s//2)%2 for s in SEEDS if s%2==parity)
            self.assertEqual(assigned,{0:4,1:4})

    def test_analysis_retains_no_request_and_clusters_scored_actions_by_seed(self):
        rows=table();cases=[]
        for seed in SEEDS:
            ops=[]
            for r in (x for x in rows if x['seed']==seed):
                events=[]
                if r['opportunity'] in (0,1):
                    y=r['opportunity']==0;aid=str(r['opportunity'])
                    forecast={'kind':'forecast','action_id':aid,'target':'object-0',
                      'candidate':{'completion_probability':.75 if y else .25,'expected_reserve_cost':.5,'evidence_count':1},
                      'baseline':{'completion_probability':.5,'expected_reserve_cost':1.,'evidence_count':1}}
                    terminal={'kind':'terminal','action_id':aid,'target':'object-0','forecast':forecast,
                              'terminal':'completed' if y else 'timeout','observed_cost':.5}
                    events=[forecast,terminal]
                ops.append({'config':r,'no_eat_request':not events,'completed':r['opportunity']==0,
                            'unsupported_ticks':0,'predictions':events})
            cases.append({'seed':seed,'opportunities':ops,'cpu_seconds':0.,'peak_worker_kib':1})
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'raw.jsonl';output=Path(d)/'summary.json'
            source.write_text(''.join(json.dumps(c)+'\n' for c in cases))
            subprocess.run([sys.executable,str(ROOT/'examples/persistent_individual/cb05_analyze.py'),str(source),str(output)],
                           cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
            result=json.loads(output.read_text())
            self.assertEqual(result['counts']['opportunities'],384)
            self.assertEqual(result['counts']['no_eat_request'],16*22)
            self.assertEqual(result['counts']['scored_forecasts'],32)
            self.assertFalse(result['insufficient_coverage'])
            self.assertAlmostEqual(result['comparisons']['completion_brier']['mean_baseline_minus_candidate'],.1875)
            self.assertTrue(result['comparisons']['completion_brier']['usefulness_pass'])
            self.assertTrue(result['comparisons']['cost_mae']['usefulness_pass'])

if __name__=='__main__':unittest.main()
