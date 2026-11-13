import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('independent_replay', ROOT/'scripts/replay_saved_gene7_continuations.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReplayEvidenceTests(unittest.TestCase):
    def test_extract_checks_exact_sample_hash_and_duplicates(self):
        key = (0, 'walking', False, 0, 'ordinary')
        row = {'seed': 0, 'body': 'walking', 'mirror': False, 'good': 0, 'control': 'ordinary'}
        data = (json.dumps(row)+'\n').encode()
        with tempfile.TemporaryDirectory(dir=ROOT) as directory, patch.object(mod, 'SAMPLES', (key,)):
            path = Path(directory)/'case.jsonl'
            path.write_bytes(data)
            rel = str(path.relative_to(ROOT))
            digest = hashlib.sha256(data).hexdigest()
            self.assertEqual(mod.extract([path], {rel: digest})[key], row)
            with self.assertRaisesRegex(ValueError, 'digest differs'):
                mod.extract([path], {rel: '0'*64})
            path.write_bytes(data+data)
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                mod.extract([path], {rel: hashlib.sha256(data+data).hexdigest()})


if __name__ == '__main__':
    unittest.main()
