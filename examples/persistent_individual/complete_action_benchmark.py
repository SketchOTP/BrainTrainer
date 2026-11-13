"""Brain-chosen, continuous food interaction with task-level cost accounting."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import json
from pathlib import Path
import random
import time
from motor_benchmark import MotorIndividual,PROGRAM
from confirmation_individual import ConfirmationMotorIndividual

CONDITIONS=('normal','effort','baseline','candidate')
SCENARIOS=('sustained','intermittent')
PER_PHASE=8


def individual(seed,condition,identity):
    if condition=='candidate':return ConfirmationMotorIndividual(PROGRAM,seed=seed,identity=identity)
    return MotorIndividual(PROGRAM,seed=seed,condition='adaptive' if condition=='baseline' else condition,identity=identity)


def offer(e,seed,opportunity,distance,mirror):
    # Food identity and location are externally supplied; neither encodes value.
    food=opportunity%2
    sign=1 if (opportunity+int(mirror))%2==0 else -1
    for index in (0,1):e.place('object-'+str(index),e.position+sign*distance,index==food)
    e.place('toy',e.position,False)
    return 'object-'+str(food)


def opportunity(e,seed,op,distance,mirror,budget,phase,scenario):
    offered=offer(e,seed,op,distance,mirror);started=e.time;reserve=e.reserve
    events=[];motor_start=len(e.motor_records);requested=False;contact=False;interruptions=0
    outcome=None;pre_pending=[]
    for t in range(budget):
        # The model never receives this physical schedule.
        strength=.2 if phase=='impaired' else 1.0
        if scenario=='intermittent' and strength==.2 and random.Random(seed*1000003+e.time+901001).random()<.1:
            strength=1.0
        e.body_strength=strength;e.obstacle_present=e.time%53==17
        pre_pending=list(e.pending)
        event=e.tick()
        choice=event['choice'];requested |= choice['action']==12 and choice['target']==offered
        for record in event['lifecycle_events']:
            contact|=record['event']=='contact' and record['target']==offered
            interruptions+=record['event']=='interrupted'
        events.append({'event':event,'body_strength':strength,'obstacle_present':e.obstacle_present,
                       'pending_before':pre_pending,'pending_after':list(e.pending)})
        if event['outcome']['completed']:
            outcome=event['outcome'];break
    motors=e.motor_records[motor_start:]
    exhausted=any(m['reason']=='reserve-exhausted' for m in motors)
    blocked=any(m['reason'] in ('obstacle','boundary') for m in motors)
    # Explicit host opportunity timeout cancels the unfinished action; it does
    # not reset brain, chemistry, feedback queue, body, clock, or estimator.
    cancelled=e.active_action is not None
    timeout_action=None
    if cancelled:
        timeout_action=e.active_action.copy();e.active_action=None
    return {'opportunity':op,'phase':phase,'offered':offered,'start_tick':started,
            'ticks':e.time-started,'requested_eat':bool(requested),'contact':bool(contact),
            'completed':outcome is not None,'completion':outcome,'interruptions':interruptions,
            'blocked':blocked,'exhausted':exhausted,'timed_out':outcome is None,
            'timeout_canceled_action':timeout_action,'reserve_cost':reserve-e.reserve,
            'motor':motors,'events':events}


def calibration(spec):
    seed,condition,mirror,distance=spec;start=time.monotonic()
    e=individual(seed,condition,f'cb02-dev-{seed}-{int(mirror)}')
    result=opportunity(e,seed,0,distance,mirror,64,'healthy','sustained')
    return {'seed':seed,'condition':condition,'mirror':mirror,'distance':distance,
            'result':result,'elapsed_seconds':time.monotonic()-start}


def history(spec):
    seed,condition,scenario,distance,budget=spec;start=time.monotonic();cpu=time.process_time()
    e=individual(seed,condition,f'cb02-{seed}-{scenario}');results=[]
    for op in range(PER_PHASE*3):
        phase=('healthy','impaired','recovery')[op//PER_PHASE]
        results.append(opportunity(e,seed,op,distance,bool(seed%2),budget,phase,scenario))
    return {'seed':seed,'condition':condition,'scenario':scenario,'distance':distance,'budget':budget,
            'results':results,'final_state':e.motor_snapshot(),
            'cpu_seconds':time.process_time()-cpu,'elapsed_seconds':time.monotonic()-start}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--calibration',action='store_true');parser.add_argument('--seeds',nargs='+',type=int,required=True)
    parser.add_argument('--distance',type=float);parser.add_argument('--budget',type=int);parser.add_argument('--workers',type=int,default=4);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    if a.calibration:specs=[(s,c,m,d) for s in a.seeds for c in CONDITIONS for m in (False,True) for d in (1.,1.5,2.)];fn=calibration
    else:
        parser.error('fresh evaluation is not qualified: see COMPLETE_ACTION_CALIBRATION_RESULTS.md')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=a.workers) as pool,a.output.open('x') as out:
        for row in pool.map(fn,specs):
            out.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n');out.flush()
            print(row['seed'],row['condition'],row.get('distance'),row.get('scenario',row.get('mirror')),flush=True)

if __name__=='__main__':main()
