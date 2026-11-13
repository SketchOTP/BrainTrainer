"""Inherited preparation is optional, matched, checkpointed and exactly once."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from motor_benchmark import MotorIndividual,PROGRAM
from confirmation_individual import ConfirmationMotorIndividual
from inherited_preparation import (PROFILE,prepare_inherited,clone_prepared_motor,
                                    prepared_snapshot,restore_prepared,save_prepared,load_prepared)

@unittest.skipUnless(PROGRAM.exists(),'requires owner-provided brain program')
class InheritedPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed=MotorIndividual(PROGRAM,seed=1,condition='adaptive',identity='preparation-test')
        cls.receipt=prepare_inherited(cls.seed,PROGRAM)

    def test_preparation_matches_declared_existing_procedure(self):
        ordinary=MotorIndividual(PROGRAM,seed=1,condition='adaptive',identity='preparation-test')
        self.assertEqual(ordinary.brain.tick_count,0)
        self.assertEqual(ordinary.brain.instincts_processed,0)
        b=ordinary.brain;b.chemicals[213]=1.;b.train_instincts();b.chemicals[213]=0.;b.clear_activity()
        self.assertEqual(json.dumps(b.to_dict(),sort_keys=True),json.dumps(self.seed.brain.to_dict(),sort_keys=True))
        self.assertEqual(self.receipt['profile'],PROFILE)
        self.assertEqual(self.receipt['processed_count'],29)
        self.assertEqual(self.receipt['brain_tick_after'],b.tick_count)
        self.assertEqual(self.receipt['rng_after'],b._rng)
        self.assertEqual(self.seed.time,0)

    def test_four_arms_receive_identical_brain_and_receipt(self):
        samples=[clone_prepared_motor(self.seed,c) for c in ('normal','effort','baseline','candidate')]
        self.assertIsInstance(samples[-1],ConfirmationMotorIndividual)
        state=json.dumps(samples[0].brain.to_dict(),sort_keys=True)
        for s in samples:
            self.assertEqual(json.dumps(s.brain.to_dict(),sort_keys=True),state)
            self.assertEqual(s._inherited_preparation,self.receipt)
            self.assertEqual(s.time,0)

    def test_reprepare_and_conflicting_receipt_are_rejected(self):
        e=clone_prepared_motor(self.seed,'baseline')
        before=json.dumps(prepared_snapshot(e),sort_keys=True)
        with self.assertRaises(ValueError):prepare_inherited(e,PROGRAM)
        for method in (e.snapshot,e.motor_snapshot,e.save,e.save_motor):
            with self.assertRaises(ValueError):method()
        self.assertEqual(json.dumps(prepared_snapshot(e),sort_keys=True),before)
        snap=prepared_snapshot(e);snap['receipt']['identity']='different'
        with self.assertRaises(ValueError):restore_prepared(snap)
        self.assertIsNone(getattr(MotorIndividual(PROGRAM,seed=1,condition='adaptive'),'_inherited_preparation',None))

    def test_roundtrip_keeps_progress_and_never_rehearses_again(self):
        e=clone_prepared_motor(self.seed,'candidate')
        for _ in range(12):e.tick()
        before=e.brain.instincts_processed
        copy=restore_prepared(json.loads(json.dumps(prepared_snapshot(e))))
        for _ in range(6):self.assertEqual(e.tick(),copy.tick())
        self.assertEqual(before,copy.brain.instincts_processed)
        self.assertEqual(json.dumps(prepared_snapshot(e),sort_keys=True),json.dumps(prepared_snapshot(copy),sort_keys=True))

    def test_actual_process_restart_continues_prepared_state(self):
        e=clone_prepared_motor(self.seed,'candidate')
        for _ in range(5):e.tick()
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.json';destination=Path(d)/'destination.json';save_prepared(e,source)
            code=("import sys;sys.path.insert(0,'examples/persistent_individual');"
                  "from inherited_preparation import load_prepared,save_prepared;"
                  "e=load_prepared(sys.argv[1]);[e.tick() for _ in range(4)];save_prepared(e,sys.argv[2])")
            subprocess.run([sys.executable,'-c',code,str(source),str(destination)],cwd=ROOT,check=True,timeout=60)
            for _ in range(4):e.tick()
            actual=load_prepared(destination)
            self.assertEqual(actual.brain.instincts_processed,29)
            self.assertEqual(json.dumps(prepared_snapshot(e),sort_keys=True),json.dumps(prepared_snapshot(actual),sort_keys=True))

if __name__=='__main__':unittest.main()
