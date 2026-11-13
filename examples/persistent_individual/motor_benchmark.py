"""Exploratory motor competence study around an unchanged brain and walking executor."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import json
import math
import os
import tempfile
from pathlib import Path
import random
import time

from individual import Individual
from creature_brain.benchmark.contract import Outcome
from self_model import SuccessModel

ROOT=Path(__file__).resolve().parents[2]
PROGRAM=ROOT/'research/docking-station-20261103/resources/chichi-brain-program.json'
TICKS_PER_PHASE=180


class MotorIndividual(Individual):
    """Experimental body. Brain controls action/target; model only picks motor effort."""
    def __init__(self, program, *, seed, condition, identity=None, good_type=0):
        if condition not in ('normal','effort','adaptive'):raise ValueError('invalid motor condition')
        super().__init__(program,seed=seed,identity=identity,good_type=good_type)
        self.condition=condition
        self.model=SuccessModel()
        self.reserve=100.0
        self.rest_enabled=False
        self.hold_enabled=False
        self.rest_rate=.5
        self.body_strength=1.0
        self.obstacle_present=False
        self.motor_records=[]
        self._current_choice=None

    def _execute_lifecycle(self, choice, objects):
        self._current_choice=choice
        try:return super()._execute_lifecycle(choice,objects)
        finally:self._current_choice=None

    def _execute(self,action,target):
        if self.hold_enabled and action.action==8 and action.target is None:
            return Outcome(action.id,None,8,True,'held',0.,0.)
        if self.rest_enabled and action.action==0 and action.target is None:
            self.reserve=min(100.,self.reserve+self.rest_rate)
            return Outcome(action.id,None,0,True,'rested',0.,0.)
        return super()._execute(action,target)

    def _move(self,direction):
        if self.world is not None:
            from world_body import step
            return step(self,direction)
        choice=self._current_choice
        if choice is None:raise RuntimeError('movement has no brain choice')
        modes={'adaptive':('normal','effort'),'normal':('normal',),'effort':('effort',)}[self.condition]
        before=self.position
        # The lifecycle itself owns the original executing action.  In a
        # continued eat, it can differ from the latest brain choice.
        executing=self.active_action['choice'] if self.active_action is not None else {
            'id':choice.id,'action':choice.action,'target':choice.target}
        action_id=executing['id']
        attempt_id=f'{action_id}:motor:{self.time}'
        evidence_before=deepcopy(self.model.to_dict()['evidence'])
        attempt=self.model.begin(attempt_id,executing['action'],'walking',modes)
        mode=attempt['mode']
        predicted=attempt['predictions'][mode]['success_probability']
        # Body impairment is external and is never supplied to the model.
        strength=self.body_strength
        requested_step=min(.35,.35*strength*(5 if mode=='effort' else 1))
        cost=.10 if mode=='effort' else .01
        # These known physical collisions are an observed environmental reason,
        # not evidence about the creature's motor competence.
        obstacle=self.obstacle_present
        proposed=before+direction*requested_step
        boundary=proposed < -20 or proposed > 20
        insufficient=self.reserve<cost
        if obstacle or boundary or insufficient:
            self.model.cancel(attempt_id)
            reason='obstacle' if obstacle else ('boundary' if boundary else 'reserve-exhausted')
            evidence_unchanged=self.model.to_dict()['evidence']==evidence_before
            spent=0.;success=None
        else:
            evidence_unchanged=None
            self.position=proposed
            self.reserve-=cost
            spent=cost
            success=abs(self.position-before)>=.25
            if not self.model.complete(attempt_id,executing['action'],mode,success,cost=spent):
                raise RuntimeError('matching movement outcome rejected')
            reason='completed' if success else 'insufficient-motion'
        self.motor_records.append({'tick':self.time,'action_id':choice.id,'brain_action':choice.action,
            'brain_target':choice.target,'executing_action_id':action_id,
            'executing_action':executing['action'],'executing_target':executing['target'],
            'motor_attempt_id':attempt_id,'direction':direction,'mode':mode,'prediction':predicted,
            'predictions':attempt['predictions'],'position_before':before,'position_after':self.position,
            'progress':abs(self.position-before),'cost':spent,'reserve_after':self.reserve,
            'motor_success':success,'reason':reason,'cancel_kept_evidence':evidence_unchanged})

    def motor_snapshot(self):
        return {'schema':'creature-brain-motor-example-v1','individual':super().snapshot(),
                'condition':self.condition,'model':self.model.to_dict(),
                'reserve':self.reserve,'body_strength':self.body_strength,'obstacle_present':self.obstacle_present,
                'rest_enabled':self.rest_enabled,'rest_rate':self.rest_rate,**({'hold_enabled':True} if self.hold_enabled else {})}

    @classmethod
    def restore_motor(cls, data):
        if not isinstance(data,dict) or data.get('schema')!='creature-brain-motor-example-v1':
            raise ValueError('invalid motor checkpoint')
        obj=super().restore(data['individual'])
        obj.condition=data['condition'];obj.model=SuccessModel.from_dict(data['model']);obj.reserve=data['reserve']
        obj.body_strength=data['body_strength'];obj.obstacle_present=data['obstacle_present']
        if obj.condition not in ('normal','effort','adaptive') or any(
            isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0
            for v in (obj.reserve,obj.body_strength)) or obj.body_strength>1 or type(obj.obstacle_present) is not bool:
            raise ValueError('invalid motor state')
        obj.hold_enabled=data.get('hold_enabled',False)
        if type(obj.hold_enabled) is not bool:raise ValueError('invalid hold body state')
        obj.rest_enabled=data.get('rest_enabled',False);obj.rest_rate=data.get('rest_rate',.5)
        if type(obj.rest_enabled) is not bool or type(obj.rest_rate) not in (int,float) or not math.isfinite(obj.rest_rate) or not 0<=obj.rest_rate<=1:
            raise ValueError('invalid rest body state')
        obj.motor_records=[];obj._current_choice=None
        return obj

    def save_motor(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
        try:
            with os.fdopen(fd,'w') as stream:
                json.dump(self.motor_snapshot(),stream,allow_nan=False);stream.flush();os.fsync(stream.fileno())
            os.replace(name,path)
        finally:
            if os.path.exists(name):os.unlink(name)

    @classmethod
    def load_motor(cls,path):
        with Path(path).open() as stream:return cls.restore_motor(json.load(stream))


def place_world(e,seed):
    if e.time%32==0:
        rng=random.Random(seed*1000003+e.time)
        sign=1 if rng.randrange(2) else -1
        e.place('object-0',e.position+sign*3.5,True)
        e.place('object-1',e.position-sign*3.5,True)
        e.place('toy',e.position+sign*2.0,True)


def advance(e,seed,ticks):
    events=[]
    for _ in range(ticks):
        # The benchmark changes physics on its clock; the model receives no regime label.
        e.body_strength=.2 if TICKS_PER_PHASE<=e.time<2*TICKS_PER_PHASE else 1.0
        e.obstacle_present=e.time%53==17
        place_world(e,seed)
        event=e.tick()
        events.append({'time':event['time'],'choice':event['choice'],'outcome':event['outcome'],
                       'lifecycle_events':event['lifecycle_events']})
    return events


def case(spec):
    seed,condition=spec;start=time.monotonic();cpu=time.process_time()
    e=MotorIndividual(PROGRAM,seed=seed,condition=condition,identity=f'motor-{seed}')
    events=advance(e,seed,TICKS_PER_PHASE*2+90)
    checkpoint=json.loads(json.dumps(e.motor_snapshot()))
    clone=MotorIndividual.restore_motor(deepcopy(checkpoint))
    # This comparison exercises a separately reconstructed model and brain;
    # observations and placements remain identical on both continuations.
    index=len(e.motor_records)
    events_a=advance(e,seed,90); records_a=e.motor_records[index:]
    events_b=advance(clone,seed,90);records_b=clone.motor_records
    continuity=(events_a==events_b and records_a==records_b and
                json.dumps(e.motor_snapshot(),sort_keys=True)==json.dumps(clone.motor_snapshot(),sort_keys=True))
    events.extend(events_a)
    return {'seed':seed,'condition':condition,'ticks':len(events),'events':events,'motor':e.motor_records,
            'checkpoint_continuation_equal':continuity,'final_reserve':e.reserve,
            'elapsed_seconds':time.monotonic()-start,'cpu_seconds':time.process_time()-cpu}


def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',nargs='+',type=int,required=True)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();specs=[(seed,condition) for seed in a.seeds for condition in ('normal','effort','adaptive')]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=a.workers) as pool,a.output.open('x') as f:
        for row in pool.map(case,specs):
            f.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n');f.flush()
            print(row['seed'],row['condition'],len(row['motor']),row['checkpoint_continuation_equal'],flush=True)

if __name__=='__main__':main()
