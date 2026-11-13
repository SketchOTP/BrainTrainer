#!/usr/bin/env python3
"""Controlled uncued exposure and held-out transfer for an actual pet brain."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from creature_brain.simulation import Simulation
from creature_brain.world import WorldObject
from creature_brain.experience import ExperienceMemory


def setup(sim, *, object_id, food_x, distractor=False):
    """Set up a test arena. No teaching cue or motor command is issued."""
    sim.world.habitat=None
    sim.world.objects.clear()
    c=next(iter(sim.creatures.values()));p=sim.world.agents[c.creature_id]
    p.x,p.y=10,6;p.carrying=None;p.inside=False;p.shelter=None;p.location='clearing';p.route=[];p.route_target=None;p.elevation=0
    c.command=None;c.exploration=None;c.feedback_body=None;c.feedback_origin=None;c.feedback_elapsed=0;c.feedback_previous=[0.0]*22
    sim.world.add_object(WorldObject(object_id,8,food_x,6,kind='food',quantity=100,regeneration=0))
    if distractor:sim.world.add_object(WorldObject('unfamiliar-toy',21,10,7,kind='toy'))
    return c


def run(sim,seconds):
    c=next(iter(sim.creatures.values())); counts=Counter();intents=Counter();first=None;steps=round(seconds/sim.dt)
    for i in range(steps):
        frame=sim.step()['creatures'][0]
        if frame['commanded']:raise RuntimeError('external teaching cue during test')
        if frame['action']!=c.brain.output().action:raise RuntimeError('non-genome motor')
        counts[frame['outcome']]+=1
        if frame['intention']:
            if frame['intention'].get('source') not in ('experience','aversion','habituation'):raise RuntimeError('scripted intention during test')
            intents[frame['intention']['target']]+=1
        if frame['outcome']=='ate' and first is None:first=(i+1)*sim.dt
        if not frame['alive']:break
    return {'ticks':i+1,'seconds':(i+1)*sim.dt,'outcomes':dict(counts),'learned_intentions':dict(intents),
            'first_ate_seconds':first,'alive':c.body.alive,'total_experiences':c.experience.total_observations,
            'associations':deepcopy(c.experience.associations)}


def main():
    p=argparse.ArgumentParser();p.add_argument('checkpoint',type=Path);p.add_argument('--training-seconds',type=float,default=200);p.add_argument('--test-seconds',type=float,default=120);p.add_argument('--positions',type=float,nargs='+',default=[5.0,13.0,18.0]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not 0<a.training_seconds<=3600 or not 0<a.test_seconds<=3600 or any(not 0<=x<=20 for x in a.positions):p.error('invalid duration or position')
    raw=a.checkpoint.read_bytes();sim=Simulation.from_dict(json.loads(raw)['simulation']);c=setup(sim,object_id='training-fruit',food_x=10.4);sim.autonomy_mode='observe'
    before=c.experience.total_observations
    training=run(sim,a.training_seconds);trained=sim.to_dict()
    print('uncued training:',training['outcomes'],'experiences',training['total_experiences']-before,flush=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.with_name(a.output.stem+'-training-checkpoint.json').write_text(json.dumps(trained,allow_nan=False)+'\n')
    comparisons=[]
    for x in a.positions:
        branches={}
        for mode in ('observe','learned','untrained'):
            branch=Simulation.from_dict(deepcopy(trained));setup(branch,object_id='held-out-fruit',food_x=x,distractor=True);branch.autonomy_mode=mode
            if mode=='untrained':
                next(iter(branch.creatures.values())).experience=ExperienceMemory()
                branch.autonomy_mode='learned'
            branches[mode]=run(branch,a.test_seconds)
        comparisons.append({'food_x':x,'branches':branches})
        print('held-out x=',x, 'ate:', {k:v['outcomes'].get('ate',0) for k,v in branches.items()},flush=True)
    reversal=Simulation.from_dict(deepcopy(trained));setup(reversal,object_id='toxic-novel-fruit',food_x=10.4)
    reversal.world.objects['toxic-novel-fruit'].toxin=1.0;reversal.autonomy_mode='learned'
    reversed_result=run(reversal,a.test_seconds)
    mem=next(iter(reversal.creatures.values())).experience
    reversed_result['toxic_episodes']=sum(e['target']=='toxic-novel-fruit' and e['toxin']>0 for e in mem.episodes)
    result={'checkpoint_sha256':hashlib.sha256(raw).hexdigest(),'training_mode':'observe: no scripted or learned cues',
            'test':'same trained brain and body; unseen object identity and position; learned recall vs observe-only and empty experience memory',
            'initial_experiences':before,'training':training,'comparisons':comparisons,'toxic_reversal':reversed_result}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('training ate',training['outcomes'].get('ate',0),'experiences',training['total_experiences']-before,flush=True)

if __name__=='__main__':main()
