"""Matched-outcome confirmation and safety of the optional recovery model."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from recovery_model import ConfirmRecoveryModel
from self_model import SuccessModel


class ConfirmRecoveryTests(unittest.TestCase):
    def trained(self):
        m=ConfirmRecoveryModel()
        m.begin('failed',4,'walking',('normal',));m.complete('failed',4,'normal',False,cost=.01)
        for i in range(8):
            m.begin('effort'+str(i),4,'walking',('effort',));m.complete('effort'+str(i),4,'effort',True,cost=.1)
        return m

    def test_noisy_single_success_yields_only_one_real_confirmation(self):
        m=self.trained()
        m.begin('noise',4,'walking',('normal',))
        self.assertTrue(m.complete('noise',4,'normal',True,cost=.01))
        p=m.begin('confirm',4,'walking',('normal','effort'))
        self.assertEqual(p['mode'],'normal');self.assertEqual(p['selection_reason'],'confirm-observed-success')
        m.complete('confirm',4,'normal',False,cost=.01)
        self.assertNotEqual(m.begin('after',4,'walking',('normal','effort'))['selection_reason'],'confirm-observed-success')

    def test_unmatched_or_cancelled_do_not_invent_confirmation(self):
        m=self.trained();p=m.begin('attempt',4,'walking',('normal',));before=m.to_dict()
        self.assertFalse(m.complete('other',4,'normal',True,cost=.01))
        self.assertFalse(m.complete('attempt',5,'normal',True,cost=.01))
        self.assertEqual(before,m.to_dict())
        m.cancel('attempt');self.assertEqual([],m.to_dict()['confirmations'])
        self.assertFalse(m.complete('attempt',4,p['mode'],True,cost=.01))

    def test_confirmation_waits_for_same_action_and_context(self):
        m=self.trained();m.begin('result',4,'walking',('normal',));m.complete('result',4,'normal',True,cost=.01)
        p=m.begin('other',5,'walking',('normal','effort'))
        self.assertNotEqual(p['selection_reason'],'confirm-observed-success')
        p=m.begin('correct',4,'walking',('normal','effort'))
        self.assertEqual(p['selection_reason'],'confirm-observed-success')
        m.cancel('correct');self.assertNotIn('correct',m.confirmation_attempts)

    def test_explicit_migration_and_process_restart_with_pending_confirmation(self):
        original=SuccessModel();original.begin('base',4,'walking',('normal',))
        m=ConfirmRecoveryModel.from_baseline(original)
        self.assertEqual(m.to_dict()['pending'],original.to_dict()['pending'])
        with self.assertRaises(ValueError):SuccessModel.from_dict(m.to_dict())
        m=self.trained();m.begin('result',4,'walking',('normal',));m.complete('result',4,'normal',True,cost=.01)
        p=m.begin('pending-confirm',4,'walking',('normal','effort'))
        self.assertEqual(p['selection_reason'],'confirm-observed-success')
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.json';b=Path(d)/'b.json';a.write_text(json.dumps(m.to_dict()))
            code=("import json,sys;sys.path.insert(0,'examples/persistent_individual');"
                  "from recovery_model import ConfirmRecoveryModel;"
                  "m=ConfirmRecoveryModel.from_dict(json.load(open(sys.argv[1])));"
                  "m.complete('pending-confirm',4,'normal',False,cost=.01);"
                  "json.dump(m.to_dict(),open(sys.argv[2],'w'))")
            subprocess.run([sys.executable,'-c',code,str(a),str(b)],cwd=ROOT,check=True)
            m.complete('pending-confirm',4,'normal',False,cost=.01)
            self.assertEqual(m.to_dict(),json.loads(b.read_text()))

if __name__=='__main__':unittest.main()
