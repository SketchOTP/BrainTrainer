#!/usr/bin/env python3
"""Compare post-contact avoidance of a new physical hazard without teacher cues."""
from collections import Counter
from copy import deepcopy
import argparse,json,math
from pathlib import Path
from creature_brain.simulation import Simulation
from experience_probe import setup

p=argparse.ArgumentParser();p.add_argument('checkpoint',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
base=json.loads(a.checkpoint.read_text());out={}
for mode in ('observe','learned'):
 sim=Simulation.from_dict(deepcopy(base));c=setup(sim,object_id='new-contact-hazard',food_x=10.4)
 obj=sim.world.objects['new-contact-hazard'];obj.kind='danger';obj.category=20;obj.portable=False;sim.autonomy_mode=mode
 counts=Counter();sources=Counter();contact_ticks=0;first_risk=None;maxdist=0
 for i in range(300):
  f=sim.step()['creatures'][0]
  if f['commanded'] or f['action']!=c.brain.output().action:raise RuntimeError('unexpected motor or external cue')
  if f['intention']:
   source=f['intention']['source']
   if source not in ('experience','aversion','habituation'):raise RuntimeError('scripted goal')
   sources[source]+=1
  pose=sim.world.agents[c.creature_id];dist=math.hypot(pose.x-obj.x,pose.y-obj.y);maxdist=max(maxdist,dist)
  contact_ticks+=int(dist<=sim.world.interaction_radius)
  if first_risk is None and obj.object_id in c.experience.risks:first_risk=(i+1)*sim.dt
  counts[f['outcome']]+=1
  if not f['alive']:break
 out[mode]={'ticks':i+1,'contact_ticks':contact_ticks,'first_harm_memory_seconds':first_risk,'max_distance':maxdist,'outcomes':dict(counts),'sources':dict(sources),'alive':c.body.alive}
 print(mode,out[mode],flush=True)
a.output.write_text(json.dumps(out,indent=2)+'\n')
