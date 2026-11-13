#!/usr/bin/env python3
"""Inspect action and recall changes after an unmarked toxic outcome."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from creature_brain.simulation import Simulation
from experience_probe import setup


def run(saved,mode,seconds):
    sim=Simulation.from_dict(deepcopy(saved));c=setup(sim,object_id='unmarked-toxic-fruit',food_x=10.4)
    sim.world.objects['unmarked-toxic-fruit'].toxin=1.0;sim.autonomy_mode=mode
    before=c.experience.total_observations;segments=[];prev=before;events=[]
    for i in range(round(seconds/sim.dt)):
        f=sim.step()['creatures'][0];block=i//50
        while len(segments)<=block:segments.append({'seconds':block*10,'outcomes':Counter(),'actions':Counter(),'recall_actions':Counter(),'cue_sources':Counter()})
        row=segments[block];row['outcomes'][f['outcome']]+=1;row['actions'][str(f['action'])]+=1
        if f['commanded']:raise RuntimeError('external cue during evaluation')
        if f['action']!=c.brain.output().action:raise RuntimeError('non-genome motor')
        if f['intention']:
            if f['intention'].get('source') not in ('experience','aversion','habituation'):raise RuntimeError('scripted intention')
            row['recall_actions'][str(f['intention']['action'])]+=1
            row['cue_sources'][f['intention']['source']]+=1
        if c.experience.total_observations>prev:
            e=c.experience.episodes[-1];prev=c.experience.total_observations
            if e['target']=='unmarked-toxic-fruit' and e['toxin']>0:events.append({'seconds':round((i+1)*sim.dt,2),'value':e['value'],'toxin':e['toxin']})
        if not f['alive']:break
    return {'mode':mode,'alive':c.body.alive,'seconds':(i+1)*sim.dt,'segments':segments,'toxic_experiences':events,
            'association':c.experience.associations.get('8:12'),'new_experiences':c.experience.total_observations-before}


def main():
    p=argparse.ArgumentParser();p.add_argument('trained',type=Path);p.add_argument('--seconds',type=float,default=90);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    saved=json.loads(a.trained.read_text());results=[run(saved,mode,a.seconds) for mode in ('observe','learned')]
    a.output.write_text(json.dumps({'training_checkpoint':str(a.trained),'results':results},indent=2,allow_nan=False)+'\n')
    for r in results:print(r['mode'],'poison records',len(r['toxic_experiences']),'ate ticks',sum(x['outcomes']['ate'] for x in r['segments']),'alive',r['alive'],flush=True)
if __name__=='__main__':main()
