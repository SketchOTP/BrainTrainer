"""Small, development-only outcome diagnostic; not confirmatory evaluation."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import sys

from creature_brain.benchmark.qualification import QualificationExperiment


def trial(args):
    program,seed,body,task,mirror,condition,good=args
    start=time.monotonic()
    exp=QualificationExperiment(program,seed=seed,embodiment=body,condition=condition,
          task=task,mirror=mirror,max_steps=16,opportunities_per_phase=8)
    # Independently counterbalance each fixed brain/world seed. This changes
    # the environment's concealed outcome, never the observations or policy.
    exp.initial_good=good
    while exp.opportunity<8:exp.tick()
    return {'seed':seed,'embodiment':body,'task':task,'mirror':mirror,
            'condition':condition,'initial_good':good,'history':exp.history,
            'elapsed_seconds':time.monotonic()-start}


def main(program,output):
    output=Path(output)
    if output.exists():raise FileExistsError('choose a new output')
    jobs=[(program,seed,body,task,mirror,condition,good)
          for seed in range(4) for body in ('walking','swimming')
          for task in ('preference','embodied') for mirror in (False,True)
          for condition in ('feedback','feedback_withheld') for good in (0,1)]
    started=time.monotonic()
    with ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(trial,jobs,chunksize=1))
    groups={}
    for row in rows:
        key=f"{row['embodiment']}/{row['task']}/{row['condition']}"
        group=groups.setdefault(key,{'runs':0,'opportunities':0,'completed':0,'high_value':0,
                 'actions':Counter(),'targets':Counter(),'consumed_targets':Counter(),'energy_delta':0.0})
        group['runs']+=1
        for event in row['history']:
            group['actions'][str(event['choice']['action'])]+=1
            group['targets'][str(event['choice']['target'])]+=1
            if event['opportunity_end']:group['opportunities']+=1
            if event['outcome']['completed']:
                group['completed']+=1;group['high_value']+=int(event['success'])
                group['consumed_targets'][str(event['outcome']['target'])]+=1
                group['energy_delta']+=event['outcome']['energy_delta']
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'schema':1,'program_sha256':hashlib.sha256(Path(program).read_bytes()).hexdigest(),
          'scope':'exploratory development seeds 0..3; fixed 16-tick budget, not timing selection',
          'qualified_learning_control':False,'rows':rows,'groups':groups,
          'wall_seconds':time.monotonic()-started},allow_nan=False)+'\n')
    print(json.dumps({'output':str(output),'cases':len(rows),'wall_seconds':time.monotonic()-started}))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
