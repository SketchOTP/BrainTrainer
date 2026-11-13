"""CB-04 bounded development qualification; all cases remain in denominators."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import resource
import time
from complete_action_benchmark import CONDITIONS, opportunity
from inherited_preparation import prepare_inherited, clone_prepared_motor, prepared_snapshot, restore_prepared
from motor_benchmark import MotorIndividual,PROGRAM
from retention_study import interval

ROOT=Path(__file__).resolve().parents[2]


def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def signature(e):
    return {'brain':e.brain.to_dict(),'rng':e.rng.getstate(),'time':e.time,'position':e.position,
            'velocity':e.velocity,'energy':e.energy,'hunger':e.hunger,'objects':deepcopy(e.objects),
            'pending':deepcopy(e.pending),'active_action':deepcopy(e.active_action),
            'receipt':deepcopy(e._inherited_preparation)}


def case(seed):
    started=time.monotonic();cpu=time.process_time()
    original=MotorIndividual(PROGRAM,seed=seed,condition='adaptive',identity=f'cb04-dev-{seed}')
    receipt=prepare_inherited(original,PROGRAM)
    source=prepared_snapshot(original);expected=digest(signature(original));immediate=[];delayed=[]
    for mirror in (False,True):
        for condition in CONDITIONS:
            e=clone_prepared_motor(original,condition)
            assert digest(signature(e))==expected,'nonidentical prepared clone'
            initial=digest(prepared_snapshot(e))
            assert e.energy==.5 and e.hunger==.8
            result=opportunity(e,seed,0,2.0,mirror,64,'healthy','sustained')
            immediate.append({'seed':seed,'mirror':mirror,'condition':condition,'initial_checkpoint_sha256':initial,
                              'result':result,'final_checkpoint':prepared_snapshot(e)})
    # Each layout starts from its own disposable, identical prepared clone.
    for mirror in (False,True):
        e=clone_prepared_motor(original,'normal')
        assert digest(signature(e))==expected
        for i in (0,1):e.place(f'object-{i}',e.position,False)
        e.place('toy',e.position,False)
        observation=interval(e,0,640)
        post_interval=prepared_snapshot(e)
        probe=restore_prepared(deepcopy(post_interval))
        # Standardize external needs/scene on the disposable probe only.
        probe.energy=.5;probe.hunger=.8
        result=opportunity(probe,seed,0,2.0,mirror,64,'healthy','sustained')
        delayed.append({'seed':seed,'mirror':mirror,'condition':'normal','interval':observation,
                        'post_interval_checkpoint':post_interval,'result':result,
                        'probe_final_checkpoint':prepared_snapshot(probe)})
    assert digest(signature(original))==expected,'prepared source mutated'
    return {'seed':seed,'preparation':receipt,'prepared_checkpoint':source,'matched_start_sha256':expected,
            'immediate':immediate,'delayed':delayed,'elapsed_seconds':time.monotonic()-started,
            'cpu_seconds':time.process_time()-cpu,'peak_worker_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,default=4);args=p.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool,args.output.open('x') as f:
        for row in pool.map(case,range(4)):
            f.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n');f.flush()
            print('seed',row['seed'],'immediate',sum(x['result']['completed'] for x in row['immediate']),
                  'delayed',sum(x['result']['completed'] for x in row['delayed']),flush=True)

if __name__=='__main__':main()
