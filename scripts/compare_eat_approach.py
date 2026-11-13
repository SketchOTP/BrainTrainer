"""Development counterfactual: compare two explicitly different body rules."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib,json,resource,sys,time
from pathlib import Path

from creature_brain.benchmark.qualification import QualificationExperiment
from creature_brain.benchmark.approach_probe import EatApproachProbe


def run(args):
    program,seed,body,mirror,good,mode=args
    started=time.monotonic();cpu=time.process_time()
    cls=QualificationExperiment if mode=='immediate' else EatApproachProbe
    e=cls(program,seed=seed,embodiment=body,condition='feedback',task='embodied',mirror=mirror,
          max_steps=16,opportunities_per_phase=8)
    e.initial_good=good
    while e.opportunity<8:e.tick()
    return {'seed':seed,'body':body,'mirror':mirror,'good':good,'mode':mode,'history':e.history,
            'elapsed_seconds':time.monotonic()-started,'cpu_seconds':time.process_time()-cpu,
            'worker_peak_rss_kib_cumulative':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main(program,path):
    output=Path(path);cases=output.with_suffix('.cases.jsonl')
    if output.exists() or cases.exists():raise FileExistsError('choose new output')
    jobs=[(program,seed,body,mirror,good,mode) for seed in range(8)
          for body in ('walking','swimming') for mirror in (False,True)
          for good in (0,1) for mode in ('immediate','approach_on_eat')]
    start=time.monotonic();rows=[];output.parent.mkdir(parents=True,exist_ok=True)
    with cases.open('x') as f,ProcessPoolExecutor(max_workers=6) as pool:
        for row in pool.map(run,jobs,chunksize=1):
            rows.append(row);f.write(json.dumps(row,allow_nan=False)+'\n');f.flush()
            print(f"{len(rows)}/{len(jobs)} {row['body']} {row['mode']}",flush=True)
    groups={}
    for row in rows:
        key=f"{row['body']}/{row['mode']}";g=groups.setdefault(key,{'runs':0,'opportunities':0,'completed':0,
             'high_value':0,'eat_requests':0,'statuses':Counter(),'targets':Counter(),'actions':Counter()})
        g['runs']+=1
        for e in row['history']:
            g['actions'][str(e['choice']['action'])]+=1;g['targets'][str(e['choice']['target'])]+=1
            g['statuses'][e['outcome']['status']]+=1;g['eat_requests']+=int(e['choice']['action']==12)
            if e['opportunity_end']:g['opportunities']+=1
            if e['outcome']['completed']:g['completed']+=1;g['high_value']+=int(e['success'])
    root=Path(__file__).resolve().parents[1]
    files=['scripts/compare_eat_approach.py','src/creature_brain/benchmark/approach_probe.py','src/creature_brain/benchmark/qualification.py','src/creature_brain/benchmark/food.py','src/creature_brain/benchmark/embodiment.py','src/creature_brain/neural.py','src/creature_brain/svrule.py']
    report={'scope':'exploratory alternate body action semantics, not native emulation or preference proof',
      'program_sha256':hashlib.sha256(Path(program).read_bytes()).hexdigest(),
      'sources_sha256':{x:hashlib.sha256((root/x).read_bytes()).hexdigest() for x in files},
      'seeds':list(range(8)),'opportunities_per_run':8,'max_steps':16,'cases':len(rows),'groups':groups,
      'wall_seconds':time.monotonic()-start,'cpu_seconds':sum(r['cpu_seconds'] for r in rows),
      'max_cumulative_worker_rss_kib':max(r['worker_peak_rss_kib_cumulative'] for r in rows)}
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps({'output':str(output),'groups':groups},indent=2))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
