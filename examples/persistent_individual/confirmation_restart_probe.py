"""Real-process, brain-chosen action plus pending-confirmation restart probe.

Seed 2 is run with the existing walking environment, no injected choice or
learning signal. Once the brain has chosen an ongoing eat with pending model
confirmations, the experiment saves and exits; an external placement then
brings food into contact and the brain's own actions continue. A second exit
occurs after observed consumption and before its feedback is delivered.
"""
import argparse
from contextlib import nullcontext
import hashlib
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from confirmation_individual import ConfirmationMotorIndividual
from motor_benchmark import PROGRAM,place_world

ROOT=Path(__file__).resolve().parents[2]


def setup():
    e=ConfirmationMotorIndividual(PROGRAM,seed=2,identity='restart-confirmation-probe')
    for t in range(342):
        e.body_strength=.2 if t<240 else 1.0
        place_world(e,2)
        e.tick()
    assert e.active_action is not None and e.active_action['choice']['action']==12
    assert (12,'walking') in e.model.confirmations and not e.pending
    return e


def consume(e):
    # Let the exact ongoing action continue naturally for one tick before any
    # placement. Its same-action normal confirmation is consumed by _move.
    action=deepcopy(e.active_action['choice']);before=len(e.motor_records)
    first=e.tick()
    assert (12,'walking') not in e.model.confirmations and len(e.motor_records)==before+1
    confirmation=deepcopy(e.motor_records[-1])
    assert confirmation['executing_action_id']==action['id']
    assert confirmation['executing_target']==action['target'] and confirmation['mode']=='normal'
    # Owner-controlled environmental placement brings the same target into
    # contact. The brain still independently chooses the subsequent actions.
    e.place('object-0',e.position+.5,True)
    e.place('object-1',e.position-.5,True)
    e.place('toy',e.position,False)
    events=[first,e.tick(),e.tick()]
    completed=[v['outcome'] for v in events if v['outcome']['completed']]
    assert len(completed)==1 and len(e.pending)==1
    assert e.pending[0]['action_id']==completed[0]['action_id']
    assert e.pending[0]['target']==completed[0]['target']
    return {'events':events,'confirmation_motor':confirmation}


def feedback(e):
    calls=[];original_queue=e.brain.queue_inputs;original_delivery=e._deliver_pending
    batch=[]
    def capture(inputs):
        calls.append({'pending_batch':deepcopy(batch),'inputs':deepcopy(inputs)});return original_queue(inputs)
    def tracked_delivery():
        batch[:]=deepcopy(e.pending)
        e.brain.queue_inputs=capture
        try:return original_delivery()
        finally:del e.brain.queue_inputs
    e._deliver_pending=tracked_delivery
    try:events=[e.tick() for _ in range(4)]
    finally:del e._deliver_pending
    return events,calls


def worker(operation,source,destination,receipt):
    if operation=='setup':
        e=setup();result={'identity':e.identity,'tick':e.time,'active_action':e.active_action,
                          'confirmations':e.model.to_dict()['confirmations'],'pending_feedback':e.pending}
    elif operation=='consume':
        e=ConfirmationMotorIndividual.load_motor(source);result=consume(e)
    elif operation=='feedback':
        e=ConfirmationMotorIndividual.load_motor(source);events,calls=feedback(e);result={'events':events,'feedback_queue_calls':calls}
    else:raise ValueError('unknown operation')
    e.save_motor(destination);Path(receipt).write_text(json.dumps(result,sort_keys=True)+'\n')


def run(evidence_dir=None):
    if evidence_dir is None:workspace=tempfile.TemporaryDirectory(prefix='confirmation-restart-probe-')
    else:
        evidence_dir=Path(evidence_dir);evidence_dir.mkdir(parents=True,exist_ok=False)
        workspace=nullcontext(str(evidence_dir))
    with workspace as d:
        d=Path(d);a=d/'active.json';b=d/'feedback.json';c=d/'final.json'
        receipts=[d/'setup.json',d/'consume.json',d/'feedback-events.json']
        def child(op,source,destination,receipt):
            p=subprocess.run([sys.executable,__file__,'--worker',op,str(source),str(destination),str(receipt)],
                             cwd=ROOT,capture_output=True,text=True,timeout=180)
            if p.returncode:raise RuntimeError(f'{op} child exited {p.returncode}: {p.stderr}')
            return json.loads(receipt.read_text()),p.returncode
        initial,status_a=child('setup','-',a,receipts[0]);before=ConfirmationMotorIndividual.load_motor(a)
        original_action=deepcopy(before.active_action['choice']);original_conf=deepcopy(before.model.confirmations)
        expected_consume=consume(before);expected_snapshot=before.motor_snapshot()
        (d/'uninterrupted-consume.json').write_text(json.dumps({'result':expected_consume,'snapshot':expected_snapshot},sort_keys=True)+'\n')
        after,status_b=child('consume',a,b,receipts[1]);actual=ConfirmationMotorIndividual.load_motor(b)
        assert json.dumps(expected_consume,sort_keys=True)==json.dumps(after,sort_keys=True)
        assert json.dumps(expected_snapshot,sort_keys=True)==json.dumps(actual.motor_snapshot(),sort_keys=True)
        assert after['events'][-1]['outcome']['action_id']==original_action['id']
        assert after['events'][-1]['outcome']['target']==original_action['target']
        assert (12,'walking') not in actual.model.confirmations
        assert all(actual.model.confirmations.get(k)==v for k,v in original_conf.items() if k!=(12,'walking'))
        expected_events,expected_calls=feedback(before);expected_snapshot=before.motor_snapshot()
        (d/'uninterrupted-feedback.json').write_text(json.dumps({'events':expected_events,'feedback_queue_calls':expected_calls,'snapshot':expected_snapshot},sort_keys=True)+'\n')
        result,status_c=child('feedback',b,c,receipts[2]);actual=ConfirmationMotorIndividual.load_motor(c)
        assert json.dumps(expected_events,sort_keys=True)==json.dumps(result['events'],sort_keys=True)
        assert json.dumps(expected_calls,sort_keys=True)==json.dumps(result['feedback_queue_calls'],sort_keys=True)
        matching_calls=[call for call in expected_calls if any(
            p['action_id']==original_action['id'] and p['target']==original_action['target']
            for p in call['pending_batch'])]
        assert len(matching_calls)==1,(matching_calls,actual.pending)
        assert not any(p['action_id']==original_action['id'] for p in actual.pending), actual.pending
        assert json.dumps(expected_snapshot,sort_keys=True)==json.dumps(actual.motor_snapshot(),sort_keys=True)
        assert not any(event['outcome']['completed'] and event['outcome']['action_id']==original_action['id']
                       for event in result['events'])
        hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.iterdir()) if p.is_file()}
        sources=[Path(__file__),Path(__file__).with_name('individual.py'),
                 Path(__file__).with_name('motor_benchmark.py'),Path(__file__).with_name('confirmation_individual.py'),
                 Path(__file__).with_name('recovery_model.py'),Path(__file__).with_name('self_model.py'),
                 ROOT/'src/creature_brain/benchmark/action_lifecycle.py',PROGRAM]
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        return {'source_sha256':source_hashes,'evidence_dir':str(evidence_dir) if evidence_dir is not None else None,'evidence_sha256':hashes,
                'setup':initial,'original_action':original_action,'confirmation_count':len(original_conf),
                'confirmation_motor':after['confirmation_motor'],
                'observed_consumption':after['events'][-1]['outcome'],
                'pending_feedback_after_consumption':json.loads(b.read_text())['individual']['pending'],
                'feedback_queue_calls_for_original_action':len(matching_calls),
                'feedback_queue_calls_total':len(expected_calls),'repeat_consumptions_for_original_action':0,
                'matched_full_state_and_events':True,'child_exit_codes':[status_a,status_b,status_c],
                'limitations':['After one naturally selected confirming movement, food was externally placed in contact.',
                               'A confirmation for the same eat action and one for another action were pending while eating was underway.',
                               'The checkpoint after consumption has pending feedback; the eating action is then complete.']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',nargs=4);p.add_argument('--receipt',type=Path);p.add_argument('--evidence-dir',type=Path)
    a=p.parse_args()
    if a.worker:return worker(*a.worker)
    result=run(a.evidence_dir);text=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open('x') as f:f.write(text)
    print(text)

if __name__=='__main__':main()
