"""Execution-only competence experiment keeps state and attribution explicit."""
import json
from dataclasses import asdict
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from motor_benchmark import MotorIndividual, PROGRAM, advance
from creature_brain.benchmark.contract import ChosenAction


@unittest.skipUnless(PROGRAM.is_file(),'requires local brain program')
class MotorBodyTests(unittest.TestCase):
    def test_brain_driven_snapshot_restores_body_and_model(self):
        e=MotorIndividual(PROGRAM,seed=2,condition='adaptive')
        advance(e,2,25)
        e.body_strength=.2
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'motor.json';e.save_motor(p);restored=MotorIndividual.load_motor(p)
            self.assertEqual(restored.body_strength,.2)
            self.assertEqual(json.dumps(e.motor_snapshot(),sort_keys=True),json.dumps(restored.motor_snapshot(),sort_keys=True))
            self.assertEqual(advance(e,2,12),advance(restored,2,12))
            self.assertEqual(json.dumps(e.motor_snapshot(),sort_keys=True),json.dumps(restored.motor_snapshot(),sort_keys=True))

    def test_model_body_and_brain_survive_real_process_restart(self):
        e=MotorIndividual(PROGRAM,seed=1,condition='adaptive')
        advance(e,1,24)
        with tempfile.TemporaryDirectory() as d:
            before=Path(d)/'before.json';after=Path(d)/'after.json';e.save_motor(before)
            code=("import sys;sys.path.insert(0,'examples/persistent_individual');"
                  "from motor_benchmark import MotorIndividual,advance;"
                  "e=MotorIndividual.load_motor(sys.argv[1]);advance(e,1,8);e.save_motor(sys.argv[2])")
            subprocess.run([sys.executable,'-c',code,str(before),str(after)],cwd=ROOT,check=True)
            advance(e,1,8);restored=MotorIndividual.load_motor(after)
            self.assertEqual(json.dumps(e.motor_snapshot(),sort_keys=True),
                             json.dumps(restored.motor_snapshot(),sort_keys=True))

    def test_environmental_collision_is_unknown_and_does_not_update_evidence(self):
        e=MotorIndividual(PROGRAM,seed=0,condition='adaptive')
        e.time=17;e.obstacle_present=True;e._current_choice=ChosenAction('choice',17,4,3,4,'object-0')
        before=e.model.to_dict()['evidence'];position=e.position;e._move(1)
        self.assertEqual(e.position,position)
        self.assertIsNone(e.motor_records[-1]['motor_success'])
        self.assertEqual(e.motor_records[-1]['reason'],'obstacle')
        self.assertEqual(e.model.to_dict()['evidence'],before)
        self.assertFalse(e.model.pending)

    def test_continued_eat_preserves_original_action_and_unique_attempt(self):
        e=MotorIndividual(PROGRAM,seed=0,condition='adaptive')
        e.place('object-0',3.0)
        original=ChosenAction('original',0,12,3,4,'object-0')
        e.active_action={'choice':asdict(original),'stage':'approach'}
        current=ChosenAction('current',1,12,3,4,'object-0');e.time=1
        executed,_,outcome,_=e._execute_lifecycle(current,e.observe().objects)
        record=e.motor_records[-1]
        self.assertEqual(outcome.action_id,'original')
        self.assertEqual(executed.id,'original')
        self.assertEqual(record['action_id'],'current')
        self.assertEqual(record['executing_action_id'],'original')
        self.assertEqual(record['executing_target'],'object-0')
        self.assertEqual(record['motor_attempt_id'],'original:motor:1')
        self.assertFalse(e.model.pending)
        before=e.model.to_dict()['evidence']
        self.assertFalse(e.model.complete('current',12,record['mode'],True,cost=0.))
        self.assertEqual(e.model.to_dict()['evidence'],before)
        e.time=2
        e._execute_lifecycle(ChosenAction('next',2,12,3,4,'object-0'),e.observe().objects)
        self.assertNotEqual(record['motor_attempt_id'],e.motor_records[-1]['motor_attempt_id'])

    def test_insufficient_reserve_is_unknown_without_model_learning(self):
        e=MotorIndividual(PROGRAM,seed=0,condition='adaptive');e.reserve=0
        e._current_choice=ChosenAction('choice',0,4,3,4,'object-0')
        before=e.model.to_dict()['evidence'];e._move(1)
        self.assertEqual(e.motor_records[-1]['reason'],'reserve-exhausted')
        self.assertEqual(e.model.to_dict()['evidence'],before)

if __name__=='__main__':unittest.main()
