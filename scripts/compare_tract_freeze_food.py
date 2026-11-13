"""Exploratory gene-7 freeze vs normal: not global learning-disabled."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
import hashlib,json,resource,sys,time
from pathlib import Path

from creature_brain.benchmark.approach_probe import EatApproachProbe
from creature_brain.benchmark.connection_freeze import freeze_drive_comb_tract_state


def run(args):
    program,seed,body,mirror,good,mode=args
    started=time.monotonic();cpu=time.process_time()
    e=EatApproachProbe(program,seed=seed,embodiment=body,condition='feedback',task='embodied',mirror=mirror,
                       max_steps=16,opportunities_per_phase=8)
    e.initial_good=good
    initial=e.brain.to_dict()['tracts'][5]
    with (freeze_drive_comb_tract_state(e.brain) if mode=='gene7_frozen' else nullcontext()):
        while e.opportunity<8:e.tick()
    final=e.brain.to_dict()['tracts'][5]
    return {'seed':seed,'body':body,'mirror':mirror,'good':good,'mode':mode,
            'initial_tract':initial,'final_tract':final,'tract_unchanged':initial==final,'history':e.history,
            'elapsed_seconds':time.monotonic()-started,'cpu_seconds':time.process_time()-cpu,
            'worker_peak_rss_kib_cumulative':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main(program,path):
    output=Path(path);cases=output.with_suffix('.cases.jsonl')
    if output.exists() or cases.exists():raise FileExistsError('choose new output')
    jobs=[(program,seed,body,mirror,good,mode) for seed in range(4) for body in ('walking','swimming')
          for mirror in (False,True) for good in (0,1) for mode in ('ordinary','gene7_frozen')]
    start=time.monotonic();rows=[];output.parent.mkdir(parents=True,exist_ok=True)
    with cases.open('x') as f,ProcessPoolExecutor(max_workers=4) as pool:
        for row in pool.map(run,jobs,chunksize=1):
            rows.append(row);f.write(json.dumps(row,allow_nan=False)+'\n');f.flush()
            print(f"{len(rows)}/{len(jobs)} {row['body']} {row['mode']}",flush=True)
    groups={}
    for row in rows:
        key=f"{row['body']}/{row['mode']}";g=groups.setdefault(key,{'runs':0,'opportunities':0,
          'completed':0,'high_value':0,'tract_unchanged_runs':0,'actions':Counter(),'targets':Counter()})
        g['runs']+=1;g['tract_unchanged_runs']+=int(row['tract_unchanged'])
        for e in row['history']:
            g['actions'][str(e['choice']['action'])]+=1;g['targets'][str(e['choice']['target'])]+=1
            if e['opportunity_end']:g['opportunities']+=1
            if e['outcome']['completed']:g['completed']+=1;g['high_value']+=int(e['success'])
    root=Path(__file__).resolve().parents[1]
    files=['scripts/compare_tract_freeze_food.py','src/creature_brain/benchmark/connection_freeze.py','src/creature_brain/benchmark/approach_probe.py','src/creature_brain/benchmark/qualification.py','src/creature_brain/benchmark/food.py','src/creature_brain/neural.py','src/creature_brain/svrule.py']
    report={'scope':'exploratory development comparison of gene-7 persistent state only; not global learning-disabled',
       'program_sha256':hashlib.sha256(Path(program).read_bytes()).hexdigest(),
       'sources_sha256':{x:hashlib.sha256((root/x).read_bytes()).hexdigest() for x in files},
       'seeds':list(range(4)),'opportunities_per_run':8,'max_steps':16,'cases':len(rows),'groups':groups,
       'wall_seconds':time.monotonic()-start,'cpu_seconds':sum(r['cpu_seconds'] for r in rows),
       'max_cumulative_worker_rss_kib':max(r['worker_peak_rss_kib_cumulative'] for r in rows)}
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps({'output':str(output),'groups':groups},indent=2))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
