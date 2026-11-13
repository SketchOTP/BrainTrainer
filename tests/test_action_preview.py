"""Preview is derived on a disposable clone and invalidated by real changes."""
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from inherited_preparation import prepare_inherited,clone_prepared_motor
from motor_benchmark import MotorIndividual,PROGRAM
from complete_action_prediction import CompleteActionObserver,observed_snapshot
from preview_action import state_token,preview_next_action

@unittest.skipUnless(PROGRAM.exists(),'requires local program')
class ActionPreviewTests(unittest.TestCase):
    def build(self):
        source=MotorIndividual(PROGRAM,seed=1,condition='adaptive',identity='preview-test')
        prepare_inherited(source,PROGRAM);host=clone_prepared_motor(source,'baseline')
        host.place('object-0',2);host.place('object-1',-2,False);host.place('toy',0,False)
        return host,CompleteActionObserver()

    def test_preexecution_preview_does_not_change_real_state_and_matches_next_tick(self):
        host,observer=self.build()
        before=json.dumps(observed_snapshot(host,observer),sort_keys=True)
        preview=preview_next_action(host,observer,opportunity_deadline=64)
        self.assertEqual(before,json.dumps(observed_snapshot(host,observer),sort_keys=True))
        self.assertEqual(preview['state_token'],state_token(host,observer,opportunity_deadline=64))
        self.assertNotEqual(preview['state_token'],state_token(host,observer,opportunity_deadline=63))
        self.assertIsNotNone(preview['forecast'])
        actual=observer.tick(host,opportunity_deadline=64)
        forecasts=[x for x in actual['action_prediction_events'] if x['kind']=='forecast']
        self.assertEqual(forecasts,[preview['forecast']])
        self.assertNotEqual(preview['state_token'],state_token(host,observer))

    def test_no_target_returns_no_forecast_without_mutation(self):
        host,observer=self.build()
        host.place('object-0',2,False);host.place('object-1',-2,False)
        before=json.dumps(observed_snapshot(host,observer),sort_keys=True)
        preview=preview_next_action(host,observer)
        self.assertIsNone(preview['forecast'])
        self.assertEqual(before,json.dumps(observed_snapshot(host,observer),sort_keys=True))
        self.assertEqual(preview['state_token'],state_token(host,observer))

    def test_changed_environment_invalidates_preview(self):
        host,observer=self.build();preview=preview_next_action(host,observer)
        host.place('object-0',4)
        self.assertNotEqual(preview['state_token'],state_token(host,observer))

if __name__=='__main__':unittest.main()
