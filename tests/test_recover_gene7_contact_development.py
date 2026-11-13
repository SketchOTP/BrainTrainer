"""Recovery guards; no experimental cases are run by these tests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import recover_gene7_contact_development as recovery


class RecoveryGuards(unittest.TestCase):
    def test_manifest_keys_are_exact_and_typed(self):
        manifest = {'seeds': [0], 'bodies': ['walking'], 'mirrors': [False],
                    'good_types': [0], 'controls': ['ordinary', 'gene7_frozen']}
        self.assertEqual(len(recovery.expected_keys(manifest)), 2)
        with self.assertRaises(ValueError):
            recovery.key_for({'seed': True, 'body': 'walking', 'mirror': False,
                              'good': 0, 'control': 'ordinary'})

    def test_scan_rejects_duplicate_and_truncated_rows(self):
        manifest = {'seeds': [0], 'bodies': ['walking'], 'mirrors': [False],
                    'good_types': [0], 'controls': ['ordinary']}
        row = {'seed': 0, 'body': 'walking', 'mirror': False, 'good': 0, 'control': 'ordinary'}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'cases.jsonl'
            payload = json.dumps(row)
            with patch.object(recovery, 'validate_row', side_effect=lambda value, *_: recovery.key_for(value)):
                path.write_text(payload + '\n' + payload + '\n')
                with self.assertRaisesRegex(ValueError, 'duplicate'):
                    recovery.scan_original(path, manifest)
                path.write_text(payload)
                with self.assertRaisesRegex(ValueError, 'incomplete'):
                    recovery.scan_original(path, manifest)
                path.write_text(payload + '\n')
                found, digest = recovery.scan_original(path, manifest)
                self.assertEqual(found, recovery.expected_keys(manifest))
                self.assertEqual(digest, recovery.file_sha(path))


if __name__ == '__main__':
    unittest.main()
