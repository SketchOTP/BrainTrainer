#!/usr/bin/env python3
"""Compare optional learned aversion sensory signals without overriding motors."""
from collections import Counter
from copy import deepcopy
import json,math
from pathlib import Path
from creature_brain.simulation import Simulation
from experience_probe import setup

path=Path('runs/experience-learning/final-v2-training-checkpoint.json');base=json.loads(path.read_text());out={}
for mode in ('baseline','inhibit','retreat'):
 sim=Simulation.from_dict(deepcopy(base));c=setup(sim,object_id='unmarked-toxic-fruit',food_x=10.4);sim.world.objects['unmarked-toxic-fruit'].toxin=1;sim.autonomy_mode='learned'
 default=c.experience.recall
 def cue(world,creature):
  bad=world.objects['unmarked-toxic-fruit'];pose=world.agents[creature.creature_id]
  if mode!='baseline' and any(e['target']==bad.object_id and e['toxin']>0 for e in creature.experience.episodes) and math.hypot(pose.x-bad.x,pose.y-bad.y)<4:
   return {'target':bad.object_id,'category':bad.category,'action':12 if mode=='inhibit' else 5,'strength':-1.0 if mode=='inhibit' else .7,'source':'probe'}
  return default(world,creature)
 c.experience.recall=cue;counts=Counter();actions=Counter();bad_tick=None
 for i in range(150):
  f=sim.step()['creatures'][0];assert f['action']==c.brain.output().action
  counts[f['outcome']]+=1;actions[str(f['action'])]+=1
  if bad_tick is None and any(e['target']=='unmarked-toxic-fruit' and e['toxin']>0 for e in c.experience.episodes):bad_tick=i
  if not f['alive']:break
 p=sim.world.agents[c.creature_id];fruit=sim.world.objects['unmarked-toxic-fruit']
 out[mode]={'outcomes':dict(counts),'actions':dict(actions),'distance':math.hypot(p.x-fruit.x,p.y-fruit.y),'first_harm_tick':bad_tick,'alive':c.body.alive}
 print(mode,out[mode],flush=True)
Path('runs/adaptive-learning/aversion-pilot.json').write_text(json.dumps(out,indent=2)+'\n')
