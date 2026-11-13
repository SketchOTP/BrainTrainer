#!/usr/bin/env python3
"""Probe sensory-only interruption of repeated actual genome actions."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from creature_brain.simulation import Simulation
from experience_probe import setup

base=json.loads(Path('runs/experience-learning/final-v2-training-checkpoint.json').read_text());out={}
for mode in ('baseline','silence','look','retreat'):
 sim=Simulation.from_dict(deepcopy(base));c=setup(sim,object_id='new-safe-fruit',food_x=10.4,distractor=True);sim.autonomy_mode='learned'
 default=c.experience.recall;repeats=0;last=None;end=0;cool=0
 def cue(world,creature):
  if mode!='baseline' and sim.steps<end:
   if mode=='silence':return None
   item=world.objects['new-safe-fruit']
   return {'target':item.object_id,'category':item.category,'action':0 if mode=='look' else 5,'strength':.7,'source':'probe'}
  return default(world,creature)
 c.experience.recall=cue;counts=Counter();actions=Counter();max_run=0;triggers=0
 for i in range(300):
  f=sim.step()['creatures'][0];assert f['action']==c.brain.output().action
  key=(f['target'],f['action']) if f['target'] and f['outcome'] not in ('moved','idle','sleeping','unavailable-action') else None
  repeats=repeats+1 if key and key==last else int(key is not None);last=key;max_run=max(max_run,repeats)
  if mode!='baseline' and repeats>=20 and sim.steps>=cool:
   end=sim.steps+15;cool=sim.steps+75;triggers+=1
  counts[f['outcome']]+=1;actions[str(f['action'])]+=1
 out[mode]={'outcomes':dict(counts),'actions':dict(actions),'longest_repeat_ticks':max_run,'triggers':triggers}
 print(mode,out[mode],flush=True)
Path('runs/adaptive-learning/repetition-pilot.json').write_text(json.dumps(out,indent=2)+'\n')
