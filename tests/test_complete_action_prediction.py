"""Passive forecasts preserve brain choices, action identity and actual costs."""
import json
from pathlib import Path
import sys
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from complete_action_prediction import CompleteActionObserver, observed_snapshot, restore_observed
from inherited_preparation import prepare_inherited, clone_prepared_motor
from motor_benchmark import MotorIndividual,PROGRAM


def build(seed=0):
    host=MotorIndividual(PROGRAM,seed=seed,condition='adaptive',identity='observer-test')
    host.place('object-0',3.0);host.place('object-1',-3.0);host.place('toy',0,False)
    return host


def choose(host,action,attention=3):
    decision=4 if action==12 else 11
    host.brain.tick=lambda *args,**kwargs:SimpleNamespace(attention=attention,decision=decision,action=action)


@unittest.skipUnless(PROGRAM.exists(),'requires owner program')
class CompleteActionPredictionTests(unittest.TestCase):
    def test_same_action_choices_and_costs_remain_passive(self):
        plain=build();observed=build();observer=CompleteActionObserver()
        for action in (12,10,12,11):
            choose(plain,action);choose(observed,action)
            event=plain.tick();result=observer.tick(observed,opportunity_deadline=64)
            self.assertEqual(event,result['host_event'])
            self.assertEqual(json.dumps(plain.motor_snapshot(),sort_keys=True),json.dumps(observed.motor_snapshot(),sort_keys=True))
        self.assertEqual(observer.terminal_count,2)

    def test_forecast_before_start_and_no_unrelated_interruption_cost(self):
        e=build();observer=CompleteActionObserver();choose(e,12)
        result=observer.tick(e,opportunity_deadline=64)
        self.assertEqual([x['kind'] for x in result['action_prediction_events']],['forecast'])
        first=result['action_prediction_events'][0]
        self.assertEqual((first['action_id'],first['target'],first['deadline']),('0','object-0',32))
        self.assertEqual(first['baseline']['evidence_count'],0)
        first_cost=e.motor_records[-1]['cost'];self.assertGreater(first_cost,0)
        choose(e,10);result=observer.tick(e,opportunity_deadline=64)
        terminal=result['action_prediction_events'][0]
        self.assertEqual(terminal['terminal'],'interrupted');self.assertEqual(terminal['action_id'],'0')
        self.assertAlmostEqual(terminal['observed_cost'],first_cost)
        self.assertNotEqual(e.motor_records[-1]['executing_action_id'],'0')
        self.assertIsNone(observer.record_timeout(action_id='0',target='object-0',tick=e.time))
        self.assertEqual(observer.terminal_count,1)

    def test_switch_target_emits_new_forecast_and_old_terminal(self):
        e=build();observer=CompleteActionObserver();choose(e,12,3);observer.tick(e,opportunity_deadline=64)
        choose(e,12,8);r=observer.tick(e,opportunity_deadline=64)['action_prediction_events']
        self.assertEqual([(x['kind'],x['action_id']) for x in r],[('forecast','1'),('terminal','0')])
        self.assertEqual(r[1]['terminal'],'interrupted');self.assertEqual(r[0]['target'],'object-1')
        self.assertEqual(set(observer.pending),{'1'})

    def test_missing_target_does_not_create_forecast(self):
        e=build();observer=CompleteActionObserver();choose(e,12,19)
        self.assertEqual(observer.tick(e,opportunity_deadline=64)['action_prediction_events'],[])
        self.assertFalse(observer.pending)

    def test_timeout_and_unknown_are_distinct_and_unknown_is_censored(self):
        e=build();observer=CompleteActionObserver();choose(e,12);observer.tick(e,opportunity_deadline=5)
        unknown=observer._finish('0','object-0','unknown',1,'target-lost')
        self.assertEqual(unknown['terminal'],'unknown')
        self.assertEqual(next(iter(observer.baseline.values()))['observed'],0)
        e.active_action=None;choose(e,12);observer.tick(e,opportunity_deadline=5)
        old=e.active_action['choice'];e.active_action=None
        terminal=observer.record_timeout(action_id=old['id'],target=old['target'],tick=e.time)
        self.assertEqual(terminal['terminal'],'timeout')
        self.assertEqual(next(iter(observer.baseline.values()))['observed'],1)

    def test_natural_completed_eat_is_credited_once(self):
        source=MotorIndividual(PROGRAM,seed=1,condition='adaptive',identity='complete-test')
        prepare_inherited(source,PROGRAM);host=clone_prepared_motor(source,'baseline')
        host.place('object-0',.5);host.place('object-1',-.5,False);host.place('toy',0,False)
        observer=CompleteActionObserver();records=[]
        for _ in range(12):
            records.extend(observer.tick(host,opportunity_deadline=64)['action_prediction_events'])
            if any(r['kind']=='terminal' and r['terminal']=='completed' for r in records):break
        forecasts=[r for r in records if r['kind']=='forecast']
        done=[r for r in records if r['kind']=='terminal' and r['terminal']=='completed']
        self.assertEqual(len(forecasts),1);self.assertEqual(len(done),1)
        self.assertEqual(done[0]['action_id'],forecasts[0]['action_id'])
        self.assertEqual(done[0]['target'],forecasts[0]['target'])
        self.assertEqual(observer.terminal_count,1)
        self.assertEqual(next(iter(observer.baseline.values()))['completed'],1)
        self.assertIsNone(observer.record_timeout(action_id=done[0]['action_id'],target=done[0]['target'],tick=host.time))
        self.assertEqual(observer.terminal_count,1)

    def test_real_process_restart_with_brain_selected_pending_action(self):
        from complete_action_prediction import save_observed,load_observed
        source=MotorIndividual(PROGRAM,seed=1,condition='adaptive',identity='real-observer')
        prepare_inherited(source,PROGRAM);e=clone_prepared_motor(source,'baseline')
        e.place('object-0',2.0);e.place('object-1',-2.0,False);e.place('toy',0,False)
        observer=CompleteActionObserver()
        for _ in range(20):
            observer.tick(e,opportunity_deadline=64)
            if observer.pending:break
        self.assertTrue(observer.pending)
        self.assertIsNotNone(e.active_action)
        with tempfile.TemporaryDirectory() as d:
            start=Path(d)/'start.json';end=Path(d)/'end.json';events=Path(d)/'events.json'
            save_observed(e,observer,start)
            code=("import json,sys;sys.path.insert(0,'examples/persistent_individual');"
                  "from complete_action_prediction import load_observed,save_observed;"
                  "e,o=load_observed(sys.argv[1]);"
                  "v=[o.tick(e,opportunity_deadline=64) for _ in range(8)];"
                  "save_observed(e,o,sys.argv[2]);json.dump(v,open(sys.argv[3],'w'))")
            subprocess.run([sys.executable,'-c',code,str(start),str(end),str(events)],cwd=ROOT,check=True)
            expected=[observer.tick(e,opportunity_deadline=64) for _ in range(8)]
            other,other_observer=load_observed(end)
            self.assertEqual(json.dumps(expected,sort_keys=True),json.dumps(json.loads(events.read_text()),sort_keys=True))
            self.assertEqual(json.dumps(observed_snapshot(e,observer),sort_keys=True),
                             json.dumps(observed_snapshot(other,other_observer),sort_keys=True))

    def test_terminal_id_cannot_be_credited_twice_after_restore(self):
        e=build();observer=CompleteActionObserver();choose(e,12);observer.tick(e,opportunity_deadline=64)
        choose(e,10);observer.tick(e,opportunity_deadline=64)
        clone=CompleteActionObserver.from_dict(json.loads(json.dumps(observer.to_dict())))
        self.assertEqual(clone.terminal_ids[0]['action_id'],'0')
        self.assertIsNone(clone.record_timeout(action_id='0',target='object-0',tick=e.time))
        self.assertEqual(clone.terminal_count,1)
        e.time=0;choose(e,12)
        with self.assertRaises(ValueError):clone.tick(e,opportunity_deadline=64)

    def test_prepared_checkpoint_restores_pending_forecast_once(self):
        source=MotorIndividual(PROGRAM,seed=1,condition='adaptive',identity='prepared-test')
        prepare_inherited(source,PROGRAM);e=clone_prepared_motor(source,'baseline')
        e.place('object-0',3.);e.place('object-1',-3.);e.place('toy',0,False)
        observer=CompleteActionObserver();choose(e,12);observer.tick(e,opportunity_deadline=64)
        restored,other=restore_observed(json.loads(json.dumps(observed_snapshot(e,observer))))
        self.assertEqual(other.to_dict(),observer.to_dict())
        self.assertEqual(restored._inherited_preparation,e._inherited_preparation)
        self.assertEqual(restored.active_action,e.active_action)
        choose(e,10);choose(restored,10)
        self.assertEqual(observer.tick(e,opportunity_deadline=64),other.tick(restored,opportunity_deadline=64))
        self.assertEqual(observer.to_dict(),other.to_dict())

if __name__=='__main__':unittest.main()
