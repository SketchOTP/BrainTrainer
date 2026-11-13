"""Paired body-strength recovery study, using actual brain-selected movements."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import time
from motor_benchmark import MotorIndividual, PROGRAM, place_world
from recovery_individual import RecoveryMotorIndividual
from recovery_model import ConfirmRecoveryModel, RecoveryProbeModel

class ConfirmIndividual(RecoveryMotorIndividual):
    RECOVERY_SCHEMA='creature-brain-confirm-recovery-dev-v1'
    def __init__(self, program, *, seed, identity=None):
        super().__init__(program,seed=seed,identity=identity)
        self.model=ConfirmRecoveryModel()
    @classmethod
    def restore_motor(cls,data):
        data=deepcopy(data);model=data['model'];data['model']=RecoveryProbeModel().to_dict()
        obj=super().restore_motor(data);obj.model=ConfirmRecoveryModel.from_dict(model);return obj

TICKS=540
CONDITIONS=('candidate',)
SCENARIOS=('sustained','brief')


def advance(e,seed,ticks,scenario):
    events=[]
    for _ in range(ticks):
        end=360 if scenario=='sustained' else 210
        e.body_strength=.2 if 180<=e.time<end else 1.0
        e.obstacle_present=e.time%53==17
        place_world(e,seed)
        event=e.tick()
        events.append({'time':event['time'],'choice':event['choice'],'outcome':event['outcome'],
                       'lifecycle_events':event['lifecycle_events']})
    return events


def case(spec):
    seed,condition,scenario=spec;start=time.monotonic();cpu=time.process_time()
    if condition=='candidate':e=ConfirmIndividual(PROGRAM,seed=seed,identity=f'recovery-{seed}-{scenario}')
    else:e=MotorIndividual(PROGRAM,seed=seed,condition=condition if condition in ('normal','effort') else 'adaptive',
                           identity=f'recovery-{seed}-{scenario}')
    events=advance(e,seed,450,scenario)
    snapshot=json.loads(json.dumps(e.motor_snapshot()))
    clone=(ConfirmIndividual if condition=='candidate' else MotorIndividual).restore_motor(snapshot)
    index=len(e.motor_records)
    events_a=advance(e,seed,90,scenario); records_a=e.motor_records[index:]
    events_b=advance(clone,seed,90,scenario); records_b=clone.motor_records
    continuity=(events_a==events_b and records_a==records_b and
                json.dumps(e.motor_snapshot(),sort_keys=True)==json.dumps(clone.motor_snapshot(),sort_keys=True))
    events.extend(events_a)
    return {'seed':seed,'condition':condition,'scenario':scenario,'ticks':len(events),'events':events,
            'motor':e.motor_records,'checkpoint_continuation_equal':continuity,'final_reserve':e.reserve,
            'elapsed_seconds':time.monotonic()-start,'cpu_seconds':time.process_time()-cpu}


def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',nargs='+',type=int,required=True)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();specs=[(s,c,sc) for s in args.seeds for sc in SCENARIOS for c in CONDITIONS]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool,args.output.open('x') as out:
        for row in pool.map(case,specs):
            out.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n');out.flush()
            print(row['seed'],row['scenario'],row['condition'],len(row['motor']),row['checkpoint_continuation_equal'],flush=True)

if __name__=='__main__':main()
