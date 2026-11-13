#!/usr/bin/env python3
"""Recheck held-out transfer after the event attribution correction."""
from copy import deepcopy
import json
from pathlib import Path
from creature_brain.simulation import Simulation
from experience_probe import setup,run

path=Path('runs/experience-learning/final-v2-training-checkpoint.json')
trained=json.loads(path.read_text());results=[]
for x in (4.0,16.0):
    row={'food_x':x,'branches':{}}
    for mode in ('observe','learned'):
        sim=Simulation.from_dict(deepcopy(trained));setup(sim,object_id='additional-held-out-fruit',food_x=x,distractor=True);sim.autonomy_mode=mode
        row['branches'][mode]=run(sim,60)
    results.append(row)
    print('held-out x=',x,'ate:',{k:v['outcomes'].get('ate',0) for k,v in row['branches'].items()},flush=True)
Path('runs/adaptive-learning/positive-transfer.json').write_text(json.dumps({'training_checkpoint':str(path),'results':results},indent=2,allow_nan=False)+'\n')
