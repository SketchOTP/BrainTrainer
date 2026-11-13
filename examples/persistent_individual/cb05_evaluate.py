"""Prospective CB-05 panel: two passive predictors on the same natural actions."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import resource
import time

from cb05_condition_table import SEEDS, table, verify
from complete_action_prediction import CompleteActionObserver, observed_snapshot, restore_observed
from inherited_preparation import prepare_inherited, clone_prepared_motor, prepared_snapshot
from motor_benchmark import MotorIndividual, PROGRAM


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def opportunity(e, observer, config):
    """Run one offered scene; terminal outcome is always created by the host."""
    # The test explicitly standardizes hunger at each opportunity, not a
    # natural metabolism. Energy, brain chemistry/history, RNG, reserve,
    # observation model and time remain continuous.
    e.hunger=config['hunger']
    side=config['side'];food=config['food_index'];distance=2.0
    for index in (0,1):e.place('object-'+str(index),e.position+side*distance,index==food)
    e.place('toy',e.position,False)
    e.body_strength=.2 if config['phase']=='impaired' else 1.0
    start=e.time;deadline=start+64;reserve_start=e.reserve
    offered='object-'+str(food);motor_start=len(e.motor_records)
    events=[];prediction_events=[];completed=False;unsupported=0
    while e.time<deadline:
        e.obstacle_present=e.time%53==17
        outcome=observer.tick(e,opportunity_deadline=deadline)
        event=outcome['host_event'];predictions=outcome['action_prediction_events']
        events.append(event);prediction_events.extend(predictions)
        unsupported+=event['outcome']['status']=='unavailable-action'
        if event['outcome']['completed']:
            completed=True;break
    timeout_action=None
    if e.active_action is not None:
        # The legacy host actually cancels at the opportunity boundary; tell
        # the observer only after that real cancellation, never synthesize eat.
        timeout_action=deepcopy(e.active_action)
        e.active_action=None
        action=timeout_action['choice']
        terminal=observer.record_timeout(action_id=action['id'],target=action['target'],tick=e.time)
        if terminal is not None:prediction_events.append(terminal)
    if observer.pending:
        raise AssertionError('unreconciled forecast after opportunity boundary')
    motions=deepcopy(e.motor_records[motor_start:])
    return {'config':config,'start_tick':start,'deadline':deadline,'end_tick':e.time,
            'offered':offered,'start_reserve':reserve_start,'end_reserve':e.reserve,
            'total_opportunity_cost':reserve_start-e.reserve,'completed':completed,
            'no_eat_request':not any(p['kind']=='forecast' for p in prediction_events),
            'unsupported_ticks':unsupported,'timeout_action':timeout_action,
            'events':events,'motor':motions,'predictions':prediction_events}


def case(spec):
    seed,all_rows=spec;start=time.monotonic();cpu=time.process_time()
    source=MotorIndividual(PROGRAM,seed=seed,condition='adaptive',identity=f'cb05-{seed}')
    receipt=prepare_inherited(source,PROGRAM)
    host=clone_prepared_motor(source,'baseline');host.initial_good=(seed//2)%2
    initial=prepared_snapshot(host);observer=CompleteActionObserver();results=[]
    for config in all_rows:
        results.append(opportunity(host,observer,config))
    # Last state includes receipt, body, queues, motor model, and both predictors.
    result={'seed':seed,'preparation':receipt,'initial_checkpoint_sha256':_hash(initial),
            'initial_checkpoint':initial,'opportunities':results,
            'final_checkpoint':observed_snapshot(host,observer),
            'elapsed_seconds':time.monotonic()-start,'cpu_seconds':time.process_time()-cpu,
            'peak_worker_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--conditions',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=4)
    args=p.parse_args();data=json.loads(args.conditions.read_text())
    if data.get('schema')!='cb05-condition-table-v1':p.error('invalid condition table schema')
    rows=data['rows'];verify(rows)
    # Reject silently substituted order; the predeclared generator is the owner.
    if rows!=table():p.error('condition table differs from declared deterministic order')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool,args.output.open('x') as out:
        for result in pool.map(case,((s,[r for r in rows if r['seed']==s]) for s in SEEDS)):
            out.write(json.dumps(result,sort_keys=True,allow_nan=False)+'\n');out.flush()
            print('seed',result['seed'],'opportunities',len(result['opportunities']),
                  'forecasts',sum(p['kind']=='forecast' for o in result['opportunities'] for p in o['predictions']),flush=True)

if __name__=='__main__':main()
