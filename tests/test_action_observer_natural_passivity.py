"""The optional observer does not alter an unforced prepared creature."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from complete_action_prediction import CompleteActionObserver
from inherited_preparation import prepare_inherited,clone_prepared_motor,prepared_snapshot
from motor_benchmark import MotorIndividual,PROGRAM

@unittest.skipUnless(PROGRAM.is_file(),'requires local brain program')
class NaturalObserverPassivityTests(unittest.TestCase):
    def test_natural_brain_and_body_trajectory_matches_without_observer(self):
        source=MotorIndividual(PROGRAM,seed=1,condition='adaptive',identity='passivity')
        prepare_inherited(source,PROGRAM)
        plain=clone_prepared_motor(source,'baseline');observed=clone_prepared_motor(source,'baseline')
        for host in (plain,observed):
            host.place('object-0',2.0,True);host.place('object-1',-2.0,False);host.place('toy',0,False)
        observer=CompleteActionObserver();forecasts=0
        for _ in range(64):
            a=plain.tick();b=observer.tick(observed,opportunity_deadline=64)
            self.assertEqual(a,b['host_event'])
            forecasts+=sum(r['kind']=='forecast' for r in b['action_prediction_events'])
        self.assertGreater(forecasts,0)
        self.assertEqual(json.dumps(prepared_snapshot(plain),sort_keys=True),
                         json.dumps(prepared_snapshot(observed),sort_keys=True))
        self.assertEqual(plain.motor_records,observed.motor_records)

if __name__=='__main__':unittest.main()
