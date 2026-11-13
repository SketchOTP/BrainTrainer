"""Regress summary recovery without rerunning the expensive experiment."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import evaluate_worsening_feedback_gain as runner


class FeedbackGainSummaryTests(unittest.TestCase):
    def test_complete_preserved_cases_recover_summary_and_program_digest(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);program=path/'program.json';program.write_text('program')
            source=path/'producer.py';source.write_text('producer')
            cases=path/'cases.jsonl';output=path/'summary.json'
            with cases.open('w') as stream:
                for seed in range(4):
                    for body in ('walking','swimming'):
                        for mirror in (False,True):
                            for good in (0,1):
                                for mode in ('baseline','gain2'):
                                    history=[]
                                    for n in range(80):
                                        history.append({'phase':runner.PHASES[n//20], 'opportunity':n,
                                            'opportunity_end':True,'success':mode=='gain2',
                                            'outcome':{'completed':True,'energy_delta':.1},
                                            'choice':{'action':12,'target':'object-0'}})
                                    row={'seed':seed,'body':body,'mirror':mirror,'good':good,'mode':mode,
                                         'initial_brain_sha256':'same','initial_observation':{},'history':history,
                                         'checkpoint_continuation_equal':True,'cpu_seconds':1,
                                         'worker_peak_rss_kib_cumulative':1}
                                    stream.write(json.dumps(row)+'\n')
            argv=['runner','--program',str(program),'--output',str(output),'--summarize-existing',str(cases),
                  '--producer-source',str(source)]
            with patch.object(sys,'argv',argv):runner.main()
            result=json.loads(output.read_text())
            self.assertTrue(result['summary_recovered_after_producer_error'])
            self.assertEqual(result['cases'],64)
            self.assertEqual(result['program_sha256'],runner.digest(program))
            self.assertEqual(result['comparisons']['walking/reversal']['mean_gain2_minus_baseline'],1.0)
            self.assertIsNone(result['wall_seconds'])


if __name__ == '__main__':unittest.main()
