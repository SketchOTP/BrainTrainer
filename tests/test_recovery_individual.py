"""Recovery model host: explicit checkpoint type and source-preserving conversion."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from motor_benchmark import MotorIndividual, PROGRAM
from recovery_individual import RecoveryMotorIndividual
from confirmation_individual import ConfirmationMotorIndividual
from recovery_model import RecoveryProbeModel, ConfirmRecoveryModel

@unittest.skipUnless(PROGRAM.is_file(),'requires local brain program')
class RecoveryIndividualTests(unittest.TestCase):
    def test_conversion_preserves_identity_brain_body_and_existing_evidence(self):
        e=MotorIndividual(PROGRAM,seed=0,condition='adaptive',identity='individual')
        for _ in range(15):e.tick()
        before=json.dumps(e.motor_snapshot(),sort_keys=True)
        candidate=RecoveryMotorIndividual.from_baseline(e)
        self.assertEqual(json.dumps(e.motor_snapshot(),sort_keys=True),before)
        self.assertEqual(candidate.identity,e.identity)
        self.assertEqual(candidate.brain.to_dict(),e.brain.to_dict())
        self.assertEqual(candidate.model.evidence,e.model.evidence)
        self.assertEqual(candidate.model.pending,e.model.pending)
        self.assertIs(type(candidate.model),RecoveryProbeModel)
        with self.assertRaises(ValueError):MotorIndividual.restore_motor(candidate.motor_snapshot())
        with self.assertRaises(ValueError):RecoveryMotorIndividual.restore_motor(e.motor_snapshot())

    def test_confirmation_host_preserves_evidence_and_checkpoint_type(self):
        e=MotorIndividual(PROGRAM,seed=2,condition='adaptive',identity='saved-individual')
        for _ in range(12):e.tick()
        before=json.dumps(e.motor_snapshot(),sort_keys=True)
        candidate=ConfirmationMotorIndividual.from_baseline(e)
        self.assertEqual(before,json.dumps(e.motor_snapshot(),sort_keys=True))
        self.assertEqual(candidate.identity,e.identity)
        self.assertEqual(candidate.brain.to_dict(),e.brain.to_dict())
        self.assertEqual(candidate.model.evidence,e.model.evidence)
        restored=ConfirmationMotorIndividual.restore_motor(json.loads(json.dumps(candidate.motor_snapshot())))
        self.assertIs(type(restored.model),ConfirmRecoveryModel)
        with self.assertRaises(ValueError):RecoveryMotorIndividual.restore_motor(candidate.motor_snapshot())
        with self.assertRaises(ValueError):MotorIndividual.restore_motor(candidate.motor_snapshot())
        for _ in range(8):candidate.tick();restored.tick()
        self.assertEqual(json.dumps(candidate.motor_snapshot(),sort_keys=True),json.dumps(restored.motor_snapshot(),sort_keys=True))

    def test_real_process_restart_continues_candidate_and_actions(self):
        e=RecoveryMotorIndividual(PROGRAM,seed=0,identity='individual')
        for _ in range(20):e.tick()
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.json';result=Path(d)/'result.json';e.save_motor(source)
            code=('import sys;sys.path.insert(0,"examples/persistent_individual");'
                  'from recovery_individual import RecoveryMotorIndividual;'
                  'e=RecoveryMotorIndividual.load_motor(sys.argv[1]);'
                  '[e.tick() for _ in range(8)];e.save_motor(sys.argv[2])')
            subprocess.run([sys.executable,'-c',code,str(source),str(result)],cwd=ROOT,check=True)
            for _ in range(8):e.tick()
            restored=RecoveryMotorIndividual.load_motor(result)
            self.assertIs(type(restored.model),RecoveryProbeModel)
            self.assertEqual(json.dumps(restored.motor_snapshot(),sort_keys=True),json.dumps(e.motor_snapshot(),sort_keys=True))

if __name__=='__main__':unittest.main()
