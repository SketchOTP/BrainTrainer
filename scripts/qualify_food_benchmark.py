"""Calibrate the recovered food benchmark on development seeds only."""
from concurrent.futures import ProcessPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import resource
import time

from creature_brain.benchmark.qualification import QualificationExperiment

BUDGETS=(2,4,8,16,32)


def trial(args):
    program, seed, body, task, mirror, budget = args
    start=time.monotonic();cpu=time.process_time()
    exp=QualificationExperiment(program,seed=seed,embodiment=body,condition='feedback',
                                 task=task,mirror=mirror,max_steps=budget,opportunities_per_phase=20)
    first=None
    # Qualification asks whether a seed completes an interaction within 20
    # opportunities. Stop on the first one; failure is right-censored.
    while exp.opportunity < 20:
        event=exp.tick()
        if event['outcome']['completed']:
            first=exp.time
            break
    return {'seed':seed,'embodiment':body,'task':task,'mirror':mirror,'budget':budget,
            'completed':first is not None,'first_interaction_tick':first,
            'ticks':exp.time,'opportunities_exposed':exp.opportunity+(exp.step_in_opportunity>0),
            'history':exp.history,'elapsed_seconds':time.monotonic()-start,
            'cpu_seconds':time.process_time()-cpu,
            'worker_peak_rss_kib_cumulative':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--program',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,default=4)
    a=p.parse_args()
    if a.workers<1:p.error('workers must be positive')
    program=Path(a.program).resolve()
    jobs=[(str(program),seed,body,task,mirror,budget)
          for budget in BUDGETS for body in ('walking','swimming')
          for task in ('preference','embodied') for mirror in (False,True)
          for seed in range(16)]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    casefile=a.output.with_suffix('.cases.jsonl')
    if casefile.exists() or a.output.exists():raise FileExistsError('choose a new output; retained evidence is never overwritten')
    started=time.monotonic();rows=[]
    with casefile.open('x') as f, ProcessPoolExecutor(max_workers=a.workers) as pool:
        for row in pool.map(trial,jobs,chunksize=1):
            rows.append(row)
            f.write(json.dumps(row,allow_nan=False)+'\n');f.flush()
            print(f"{len(rows)}/{len(jobs)} budget={row['budget']} body={row['embodiment']} task={row['task']} mirror={row['mirror']} seed={row['seed']}",flush=True)
    metrics={}
    for budget in BUDGETS:
        for body in ('walking','swimming'):
            for task in ('preference','embodied'):
                for mirror in (False,True):
                    subset=[r for r in rows if (r['budget'],r['embodiment'],r['task'],r['mirror'])==(budget,body,task,mirror)]
                    n=sum(r['completed'] for r in subset)
                    metrics[f'{budget}/{body}/{task}/{int(mirror)}']={
                        'completed_seeds':n,'total_seeds':len(subset),'completion_rate':n/len(subset),
                        'first_interaction_ticks':[r['first_interaction_tick'] for r in subset],
                        'censored_seeds':[r['seed'] for r in subset if not r['completed']]}
    eligible=[budget for budget in BUDGETS if all(metrics[f'{budget}/{body}/{task}/{mirror}']['completion_rate']>=.8
               for body in ('walking','swimming') for task in ('preference','embodied') for mirror in (0,1))]
    root=Path(__file__).resolve().parents[1]
    sources=['scripts/qualify_food_benchmark.py','src/creature_brain/benchmark/qualification.py',
             'src/creature_brain/benchmark/food.py','src/creature_brain/benchmark/contract.py',
             'src/creature_brain/benchmark/embodiment.py','src/creature_brain/neural.py',
             'src/creature_brain/svrule.py','src/creature_brain/genome.py','src/creature_brain/sensory.py']
    report={'schema':1,'program_sha256':hashlib.sha256(program.read_bytes()).hexdigest(),
            'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources},
            'seed_range':[0,15],'budgets':BUDGETS,'opportunities_limit':20,
            'threshold':'at least 13/16 seeds in each body, task and mirrored layout',
            'completion_definition':'at least one completed consumption within 20 opportunities; other seeds censored',
            'selected_budget':min(eligible) if eligible else None,'metrics':metrics,
            'wall_seconds':time.monotonic()-started,'cases':len(rows)}
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'output':str(a.output),'selected_budget':report['selected_budget'],'cases':len(rows)}),flush=True)

if __name__=='__main__':main()
