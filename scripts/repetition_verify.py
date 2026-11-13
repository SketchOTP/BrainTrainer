#!/usr/bin/env python3
"""Compare genome behavior with and without the new habituation cue."""
from collections import Counter
from copy import deepcopy
import argparse,json
from pathlib import Path
from creature_brain.simulation import Simulation
from experience_probe import setup

p=argparse.ArgumentParser();p.add_argument('checkpoint',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
base=json.loads(a.checkpoint.read_text());out={}
for mode in ('recall-only','learned'):
 sim=Simulation.from_dict(deepcopy(base));c=setup(sim,object_id='new-safe-fruit',food_x=10.4,distractor=True);sim.autonomy_mode='learned'
 if mode=='recall-only':
  c.experience.intention=c.experience.recall
  c.experience.note_action=lambda **kwargs:None
 counts=Counter();sources=Counter();last=None;run=0;max_run=0
 for i in range(300):
  f=sim.step()['creatures'][0]
  if f['action']!=c.brain.output().action or f['commanded']:raise RuntimeError('motor or external cue mismatch')
  if f['intention']:
   source=f['intention']['source']
   if source not in ('experience','aversion','habituation'):raise RuntimeError('unexpected cue source')
   sources[source]+=1
  k=(f['target'],f['action']) if f['target'] and f['outcome'] not in ('moved','idle','sleeping','unavailable-action') else None
  run=run+1 if k and k==last else int(k is not None);last=k;max_run=max(max_run,run);counts[f['outcome']]+=1
  if not f['alive']:break
 out[mode]={'outcomes':dict(counts),'sources':dict(sources),'longest_repeat_ticks':max_run,'ticks':i+1,'alive':c.body.alive}
 print(mode,out[mode],flush=True)
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n')
