"""Held-out manifest and seed-level analysis safeguards."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_gene7_heldout as heldout
import analyze_gene7_heldout as analysis


class HeldoutTests(unittest.TestCase):
    def test_seed_bootstrap_is_paired_and_deterministic(self):
        import random
        values = [.1, .2, -.1, .2]
        first = analysis.bootstrap(values, random.Random(12), 1000)
        second = analysis.bootstrap(values, random.Random(12), 1000)
        self.assertEqual(first, second)
        self.assertLessEqual(first[0], sum(values)/len(values))
        self.assertGreaterEqual(first[1], sum(values)/len(values))

    def test_manifest_freezes_sources_diagnostics_and_reserved_seeds(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            base_path, output = path/'base.json', path/'heldout.json'
            transfer, reversal, replay = path/'transfer.json', path/'reversal.json', path/'replay.json'
            base = {'budget': 32, 'program': 'p', 'program_sha256': 'h', 'calibration': 'c',
                    'calibration_sha256': 'ch', 'bodies': ['walking', 'swimming'],
                    'mirrors': [False, True], 'good_types': [0, 1], 'controls': ['ordinary', 'gene7_frozen'],
                    'opportunities_per_phase': 20, 'phases': ['experience', 'evaluation', 'reversal', 'reversal_evaluation'],
                    'probe': {'x': 1}, 'checkpoint_after_opportunities': 40, 'status': 'frozen'}
            base_path.write_text(json.dumps(base))
            transfer.write_text(json.dumps({'summaries': {'20': {'pairs': 24}, '60': {'pairs': 24}}}))
            reversal.write_text(json.dumps({'cases': [None] * 256}))
            replay.write_text(json.dumps({'samples': [{'captured_events_pending_inputs_chemistry_rng_and_weak_queues_match': True,
                'independent_midpoint_checkpoint_continuation_and_final_match': True}] * 4}))
            diagnostics = {'transfer': transfer, 'reversal': reversal, 'replay': replay}
            with patch.object(heldout.dev, 'check_manifest'), patch.object(heldout, 'source_digests', return_value={'runner':'digest'}):
                with self.assertRaisesRegex(ValueError, 'diagnostic'):
                    heldout.freeze(base_path, {}, output)
                manifest = heldout.freeze(base_path, diagnostics, output)
                self.assertEqual(manifest['seeds'], list(range(56, 96)))
                heldout.check_manifest(manifest)
                with self.assertRaises(FileExistsError):
                    heldout.freeze(base_path, diagnostics, output)
                transfer.write_text('changed')
                with self.assertRaisesRegex(ValueError, 'diagnostic'):
                    heldout.check_manifest(manifest)

    def test_incomplete_analysis_refused_before_data(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            manifest = path/'manifest.json'
            manifest.write_text('{}')
            with patch.object(heldout, 'check_manifest'):
                with self.assertRaisesRegex(ValueError, 'eight'):
                    analysis.analyze(manifest, [], path/'out.json')

    def test_completed_partial_shard_resume_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest_path, out = root/'manifest.json', root/'shard.json'
            manifest_path.write_text(json.dumps({'seeds': list(range(56, 96))}))
            cases = out.with_suffix('.cases.jsonl')
            cases.write_text(json.dumps({'cpu_seconds': 1, 'worker_peak_rss_kib_cumulative': 8})+'\n')
            start = out.with_suffix('.start.json')
            start.write_text(json.dumps({'schema': 'gene7-heldout-shard-start-v1',
                'manifest_sha256': heldout.digest_file(manifest_path), 'shard': 0, 'seeds': list(range(56, 61))}))
            before = heldout.digest_file(cases)
            key = (56, 'walking', False, 0, 'ordinary')
            with patch.object(heldout, 'check_manifest'), patch.object(heldout, 'expected_keys', return_value={key}), \
                 patch.object(heldout, 'validate_row', return_value=key):
                report = heldout.shard(manifest_path, 0, out, 1, resume=True)
            self.assertEqual(report['resumed_existing_count'], 1)
            self.assertEqual(report['pre_resume_sha256'], before)
            self.assertEqual(report['case_sha256'], before)

    def test_complete_balanced_dataset_and_exact_ten_point_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest_path = root/'manifest.json'
            manifest = {'seeds': list(range(56, 96)), 'bodies': ['walking', 'swimming'],
                        'controls': ['ordinary', 'gene7_frozen'],
                        'mirrors': [False, True], 'good_types': [0, 1],
                        'phases': ['experience', 'evaluation', 'reversal', 'reversal_evaluation'],
                        'scoring': {'bootstrap_seed': 5, 'bootstrap_samples': 100}}
            manifest_path.write_text(json.dumps(manifest))
            reports = []
            for index in range(8):
                case_path = root/f'{index}.jsonl'
                with case_path.open('w') as stream:
                    for seed in manifest['seeds'][index*5:(index+1)*5]:
                        for body in manifest['bodies']:
                            for mirror in (False, True):
                                for good in (0, 1):
                                    for control in manifest['controls']:
                                        snapshot = {'state': [seed, body, mirror, good]}
                                        if control == 'gene7_frozen':
                                            snapshot['qualification_control'] = 'drive-comb-tract-state-frozen-v1'
                                        steps = []
                                        for n in range(80):
                                            success = control == 'ordinary' and n % 20 < 2
                                            steps.append({'event': {'phase': manifest['phases'][n//20],
                                                'choice': {'action': 12, 'attention': 3, 'target': 'object-0'}, 'opportunity_end': True,
                                                'opportunity': n, 'outcome': {'completed': success}, 'success': success}})
                                        row = {'seed': seed, 'body': body, 'mirror': mirror, 'good': good,
                                               'control': control, 'initial_checkpoint': {'snapshot': snapshot},
                                               'probes': {}, 'steps': steps, 'cpu_seconds': 1,
                                               'worker_peak_rss_kib_cumulative': 1}
                                        stream.write(json.dumps(row)+'\n')
                report_path = root/f'{index}.json'
                start_path = root/f'{index}.start.json'
                start_path.write_text(json.dumps({'schema': 'gene7-heldout-shard-start-v1',
                    'manifest_sha256': heldout.digest_file(manifest_path), 'shard': index,
                    'seeds': manifest['seeds'][index*5:(index+1)*5]}))
                report_path.write_text(json.dumps({'schema': 'gene7-heldout-shard-v1', 'shard': index,
                    'manifest_sha256': heldout.digest_file(manifest_path), 'seeds': manifest['seeds'][index*5:(index+1)*5],
                    'cases': 80, 'case_file': str(case_path), 'case_sha256': heldout.digest_file(case_path),
                    'start_receipt': str(start_path), 'start_receipt_sha256': heldout.digest_file(start_path)}))
                reports.append(report_path)
            key_for = lambda row, manifest, allowed: (row['seed'], row['body'], row['mirror'], row['good'], row['control'])
            with patch.object(heldout, 'check_manifest'), patch.object(analysis, 'validate_row', side_effect=key_for):
                result = analysis.analyze(manifest_path, reports, root/'analysis.json')
            self.assertEqual(result['cases'], 640)
            self.assertTrue(result['overall_target_met'])
            self.assertEqual(result['phase_summaries']['walking/evaluation']['paired_difference'], .1)


if __name__ == '__main__':
    unittest.main()
