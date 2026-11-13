#!/usr/bin/env python3
"""Counterbalanced cross-category test with explicit observable labels.

The labels are provided by the test environment; no pixels are classified and
no hidden toxin value is read by the learner before contact.
"""
from collections import Counter
from copy import deepcopy
import json,math
from pathlib import Path
from creature_brain.simulation import Simulation
from experience_probe import setup

base=json.loads(Path('runs/experience-learning/final-v2-training-checkpoint.json').read_text())
results=[]
for mark,other in (('mark-a','mark-b'),('mark-b','mark-a')):
 sim=Simulation.from_dict(deepcopy(base));c=next(iter(sim.creatures.values()))
 c.experience.risks.clear();c.experience.percept_history.clear();training=[]
 for i in range(2):
  name='training-hazard-'+str(i);setup(sim,object_id=name,food_x=10.4)
  item=sim.world.objects[name];item.percepts=[mark];item.toxin=1;sim.autonomy_mode='observe'
  learned=False;counts=Counter()
  for tick in range(450):
   f=sim.step()['creatures'][0]
   if f['commanded'] or f['intention'] is not None or f['action']!=c.brain.output().action:raise RuntimeError('unexpected training cue or motor')
   counts[f['outcome']]+=1
   group=c.experience.percept_history.get(mark,{}).get('12',{})
   if name in group.get('harmful',[]):learned=True;break
   if not f['alive']:break
  training.append({'object':name,'seconds':(tick+1)*sim.dt,'harm_observed':learned,'outcomes':dict(counts),'alive':c.body.alive})
  if not learned or not c.body.alive:break
 print(mark,'training',training,flush=True)
 if len(training)!=2 or not all(t['harm_observed'] and t['alive'] for t in training):
  results.append({'harmful_mark':mark,'training':training,'completed':False});continue
 saved=sim.to_dict();branches={}
 for label,percept,toxin in [('learned-marker',mark,1),('unseen-marker',other,1),('safe-lookalike',mark,0)]:
  trial=Simulation.from_dict(deepcopy(saved));ct=setup(trial,object_id='new-category-object',food_x=10.4)
  item=trial.world.objects['new-category-object'];item.category=11;item.percepts=[percept];item.toxin=toxin;trial.autonomy_mode='learned'
  counts=Counter();sources=Counter();first_intent=None;first_ate=None;max_distance=0;first_action=None
  for tick in range(300):
   frame=trial.step()['creatures'][0]
   if frame['commanded'] or frame['action']!=ct.brain.output().action:raise RuntimeError('unexpected motor or teaching cue')
   counts[frame['outcome']]+=1
   if first_action is None:first_action=frame['action']
   pose=trial.world.agents[ct.creature_id];max_distance=max(max_distance,math.hypot(pose.x-item.x,pose.y-item.y))
   if frame['intention']:
    source=frame['intention'].get('source')
    if source not in ('experience','aversion','habituation'):raise RuntimeError('scripted goal')
    sources[source]+=1
    if first_intent is None:first_intent={'tick':tick,'source':source,'action':frame['intention']['action']}
   if frame['outcome']=='ate' and first_ate is None:first_ate=(tick+1)*trial.dt
   if not frame['alive']:break
  branches[label]={'percept':percept,'category':item.category,'hidden_toxin':toxin,'first_intention':first_intent,'first_action':first_action,'first_ate_seconds':first_ate,'max_distance':max_distance,'outcomes':dict(counts),'sources':dict(sources),'alive':ct.body.alive}
 print(mark,'branches',branches,flush=True)
 results.append({'harmful_mark':mark,'training':training,'completed':True,'branches':branches})
Path('runs/adaptive-learning/percept-transfer-v4.json').write_text(json.dumps({'description':'two counterbalanced synthetic percept labels; category and identity held out; learner never reads hidden toxin before action','results':results},indent=2,allow_nan=False)+'\n')
