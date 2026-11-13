"""Opt-in, portable confirmation-motor host and explicit migration."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from confirmation_individual import ConfirmationMotorIndividual
from motor_benchmark import MotorIndividual,PROGRAM


@unittest.skipUnless(PROGRAM.is_file(),'requires the locally supplied brain program')
class ConfirmationIndividualTests(unittest.TestCase):
    def test_explicit_migration_preserves_individual_and_baseline(self):
        base=MotorIndividual(PROGRAM,seed=4,condition='adaptive',identity='unchanged')
        for _ in range(12):base.tick()
        before=base.motor_snapshot();candidate=ConfirmationMotorIndividual.from_baseline(base)
        self.assertEqual(before,base.motor_snapshot())
        result=candidate.motor_snapshot()
        self.assertEqual(result['individual'],before['individual'])
        self.assertEqual(result['reserve'],before['reserve'])
        self.assertEqual(result['body_strength'],before['body_strength'])
        for field in ('evidence','decisions','pending'):
            self.assertEqual(result['model'][field],before['model'][field])
        with self.assertRaises(ValueError):MotorIndividual.restore_motor(result)

    def test_real_process_restart_matches_full_continuation(self):
        e=ConfirmationMotorIndividual(PROGRAM,seed=5,identity='survives')
        e.body_strength=.2
        for _ in range(12):e.tick()
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.json';result=Path(d)/'result.json';e.save_motor(source)
            code=("import sys;sys.path.insert(0,'examples/persistent_individual');"
                  "from confirmation_individual import ConfirmationMotorIndividual;"
                  "e=ConfirmationMotorIndividual.load_motor(sys.argv[1]);"
                  "[e.tick() for _ in range(8)];e.save_motor(sys.argv[2])")
            subprocess.run([sys.executable,'-c',code,str(source),str(result)],cwd=ROOT,check=True)
            for _ in range(8):e.tick()
            self.assertEqual(json.dumps(e.motor_snapshot(),sort_keys=True),
                             json.dumps(ConfirmationMotorIndividual.load_motor(result).motor_snapshot(),sort_keys=True))

if __name__=='__main__':unittest.main()
