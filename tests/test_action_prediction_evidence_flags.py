"""Live forecast metadata is honest and leaves frozen numeric behavior unchanged."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from complete_action_prediction import CompleteActionObserver,observed_snapshot,restore_observed
from inherited_preparation import prepare_inherited,clone_prepared_motor
from motor_benchmark import MotorIndividual,PROGRAM

@unittest.skipUnless(PROGRAM.exists(),'requires program')
class EvidenceFlagsTests(unittest.TestCase):
    def test_frozen_checkpoint_restores_and_numeric_forecast_unchanged(self):
        archive=ROOT/'runs/self-model/cb05-prospective/frozen-complete-action-prediction.py'
        self.assertTrue(archive.exists())
        spec=importlib.util.spec_from_file_location('frozen_cb05_observer',archive)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        e=MotorIndividual(PROGRAM,seed=1,condition='adaptive',identity='flags')
        prepare_inherited(e,PROGRAM);e=clone_prepared_motor(e,'baseline')
        e.place('object-0',2);e.place('object-1',-2,False);e.place('toy',0,False)
        old_observer=old.CompleteActionObserver();checkpoint=old.observed_snapshot(e,old_observer)
        new_host,new_observer=restore_observed(json.loads(json.dumps(checkpoint)))
        old_event=old_observer.tick(e,opportunity_deadline=64)
        new_event=new_observer.tick(new_host,opportunity_deadline=64)
        self.assertEqual(old_event['host_event'],new_event['host_event'])
        a=old_event['action_prediction_events'][0];b=new_event['action_prediction_events'][0]
        for key in ('baseline','candidate'):
            for field in ('completion_probability','expected_reserve_cost','evidence_count','cost_evidence_count'):
                self.assertEqual(a[key][field],b[key][field])
            self.assertTrue(b[key]['prior_only']);self.assertTrue(b[key]['insufficient_evidence'])
            self.assertEqual(b[key]['schema'],CompleteActionObserver.SCHEMA)
        self.assertEqual(json.dumps(old.observed_snapshot(e,old_observer)['host'],sort_keys=True),
                         json.dumps(observed_snapshot(new_host,new_observer)['host'],sort_keys=True))
        # The archived version can have an in-flight forecast without the new
        # display fields; restore it as saved, without fabricating metadata.
        prior_pending=old.observed_snapshot(e,old_observer)
        resumed_host,resumed_observer=restore_observed(json.loads(json.dumps(prior_pending)))
        self.assertEqual(resumed_observer.pending,old_observer.pending)
        self.assertEqual(resumed_host.active_action,e.active_action)
        for _ in range(8):
            self.assertEqual(old_observer.tick(e,opportunity_deadline=64)['host_event'],
                             resumed_observer.tick(resumed_host,opportunity_deadline=64)['host_event'])

if __name__=='__main__':unittest.main()
