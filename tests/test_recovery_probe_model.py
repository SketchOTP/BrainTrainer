"""The optional recovery probe remains outcome-bound and checkpoint-safe."""
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples/persistent_individual'))
from recovery_model import RecoveryProbeModel
from self_model import SuccessModel


class RecoveryProbeModelTests(unittest.TestCase):
    def test_migration_preserves_evidence_pending_and_decisions(self):
        original = SuccessModel()
        for i in range(10):
            action = original.begin(str(i), 4, 'walking', ('normal', 'effort'))
            original.complete(str(i), 4, action['mode'], i % 3 != 0, cost=.1)
        pending = original.begin('pending', 4, 'walking', ('normal', 'effort'))
        before = original.to_dict()
        candidate = RecoveryProbeModel.from_baseline(original)
        restored = RecoveryProbeModel.from_dict(json.loads(json.dumps(candidate.to_dict())))
        self.assertEqual(original.to_dict(), before)
        migrated = candidate.to_dict()
        self.assertEqual(migrated['evidence'], before['evidence'])
        self.assertEqual(migrated['decisions'], before['decisions'])
        self.assertEqual(migrated['pending'], before['pending'])
        with self.assertRaises(ValueError):
            SuccessModel.from_dict(migrated)
        self.assertTrue(restored.complete('pending', 4, pending['mode'], True, cost=.1))
        self.assertTrue(candidate.complete('pending', 4, pending['mode'], True, cost=.1))
        for i in range(25):
            first = candidate.begin('x'+str(i),4,'walking',('normal','effort'))
            second = restored.begin('x'+str(i),4,'walking',('normal','effort'))
            self.assertEqual(first,second)
            candidate.complete('x'+str(i),4,first['mode'],i%3!=0,cost=.1)
            restored.complete('x'+str(i),4,second['mode'],i%3!=0,cost=.1)
        self.assertEqual(candidate.to_dict(),restored.to_dict())

    def test_pending_and_model_survive_process_restart(self):
        model=RecoveryProbeModel()
        plan=model.begin('pending',4,'walking',('normal','effort'))
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.json'; result=Path(d)/'result.json'
            source.write_text(json.dumps(model.to_dict()))
            code=("import json,sys;sys.path.insert(0,'examples/persistent_individual');"
                  "from recovery_model import RecoveryProbeModel;"
                  "m=RecoveryProbeModel.from_dict(json.load(open(sys.argv[1])));"
                  "m.complete('pending',4,sys.argv[3],False,cost=.1);"
                  "json.dump(m.to_dict(),open(sys.argv[2],'w'))")
            subprocess.run([sys.executable,'-c',code,str(source),str(result),plan['mode']],cwd=ROOT,check=True)
            model.complete('pending',4,plan['mode'],False,cost=.1)
            self.assertEqual(model.to_dict(),json.loads(result.read_text()))

    def test_unrelated_failure_and_temporary_obstruction_do_not_change_evidence(self):
        model=RecoveryProbeModel()
        p=model.begin('requested',4,'walking',('normal','effort'))
        evidence=model.to_dict()['evidence']
        self.assertFalse(model.complete('unrelated',4,p['mode'],False,cost=.1))
        self.assertEqual(model.to_dict()['evidence'],evidence)
        self.assertTrue(model.cancel('requested'))
        self.assertEqual(model.to_dict()['evidence'],evidence)
        self.assertFalse(model.complete('requested',4,p['mode'],False,cost=.1))

    def test_single_noise_does_not_erase_healthy_competence(self):
        model=RecoveryProbeModel()
        for i in range(20):
            model.begin(str(i),4,'walking',('normal',))
            model.complete(str(i),4,'normal',True,cost=.01)
        before=model.predict(4,'walking','normal')['success_probability']
        model.begin('noise',4,'walking',('normal',))
        model.complete('noise',4,'normal',False,cost=.01)
        after=model.predict(4,'walking','normal')['success_probability']
        self.assertGreater(before,.8)
        self.assertGreater(after,.65)
        self.assertLess(after,before)
        for i in range(5):
            model.begin('recover'+str(i),4,'walking',('normal',))
            model.complete('recover'+str(i),4,'normal',True,cost=.01)
        self.assertGreater(model.predict(4,'walking','normal')['success_probability'],after)

    def test_probe_trades_off_recovery_speed_and_impaired_failures(self):
        def run(cls):
            model=cls();out=[]
            for i in range(240):
                p=model.begin(str(i),4,'walking',('normal','effort'))
                success=not 60<=i<120 or p['mode']=='effort'
                model.complete(str(i),4,p['mode'],success,cost=.1 if p['mode']=='effort' else .01)
                out.append((p['mode'],success))
            return out
        baseline=run(SuccessModel);candidate=run(RecoveryProbeModel)
        self.assertLess(sum(x[0]=='effort' for x in candidate[120:180]),sum(x[0]=='effort' for x in baseline[120:180]))
        self.assertGreater(sum(not x[1] for x in candidate[60:120]),sum(not x[1] for x in baseline[60:120]))

if __name__=='__main__':unittest.main()
