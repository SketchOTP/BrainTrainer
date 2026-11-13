"""Bounded continuous-individual retention experiment, including real process restarts."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import resource
import subprocess
import sys
import tempfile
import time

from individual import Individual

ROOT=Path(__file__).resolve().parents[2]
PROGRAM=ROOT/'research/docking-station-20261103/resources/chichi-brain-program.json'


def normalized(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def interval(e,start,count):
    digest=hashlib.sha256(); actions=Counter(); moves=0
    for i in range(start,start+count):
        if i%64==0:e.place('toy',e.position+(.5 if (i//64)%2==0 else -.5))
        previous=e.position; event=e.tick();moves+=e.position!=previous
        actions[str(event['choice']['action'])]+=1
        digest.update((normalized(event)+'\n').encode())
    return {'event_sha256':digest.hexdigest(),'actions':dict(actions),'moves':moves,'ticks':count}


def train(e,mirror):
    records=[]
    e.place('toy',e.position,False)
    for opportunity in range(20):
        # Both foods are in contact and equally accessible. Presentation is an
        # external environment event, never a brain or body reset.
        for index in (0,1):
            sign=1 if (index==0)^mirror else -1
            e.place('object-'+str(index),e.position+sign*.5,True)
        for tick in range(32):
            event=e.tick()
            if event['outcome']['completed']:
                records.append({'opportunity':opportunity,'tick':tick+1,'event':event});break
        else:records.append({'opportunity':opportunity,'tick':32,'event':None})
    # Deliver outstanding attributed feedback naturally, without clearing state.
    for index in (0,1):e.place('object-'+str(index),e.position,False)
    e.place('toy',e.position+.5,True)
    e.tick()
    return records


def probe(source,mirror):
    e=Individual.restore(deepcopy(source.snapshot()))
    # Only clone conditions are standardized; neural, chemical, RNG and action
    # state are retained. Clear no queues and deliver no fabricated outcomes.
    e.energy=.5;e.hunger=.5;e.place('toy',e.position,False)
    for index in (0,1):
        sign=1 if (index==0)^mirror else -1
        e.place('object-'+str(index),e.position+sign*.5,True)
    first_attention=None;first_eat=None;completed=None;events=[]
    for _ in range(32):
        event=e.tick();events.append(event)
        choice=event['choice']
        if first_attention is None and choice['target'] in ('object-0','object-1'):first_attention=choice['target']
        if first_eat is None and choice['action']==12 and choice['target'] in ('object-0','object-1'):
            first_eat={'target':choice['target'],'action':choice['action'],'tick':len(events)}
        if event['outcome']['completed']:
            completed=event['outcome'];break
    return {'attention':first_attention,'first_eat':first_eat,'completion':completed,
            'aligned':bool(first_eat and first_eat['target']==f'object-{e.initial_good}'),
            'events':events}


def case(spec):
    seed,mirror,good,freeze=spec; started=time.monotonic(); cpu=time.process_time()
    children_start=resource.getrusage(resource.RUSAGE_CHILDREN)
    child_cpu_start=children_start.ru_utime+children_start.ru_stime
    e=Individual(PROGRAM,seed=seed,good_type=good,freeze_tract=freeze,
                 identity=f'cb01-{seed}-{int(mirror)}-{good}')
    training=train(e,mirror); immediate=probe(e,mirror)
    continuous=Individual.restore(deepcopy(e.snapshot()))
    first=interval(continuous,0,320); mid=normalized(continuous.snapshot())
    second=interval(continuous,320,320); end=normalized(continuous.snapshot())
    with tempfile.TemporaryDirectory(prefix='cb01-retention-') as d:
        start=Path(d)/'start.json';middle=Path(d)/'middle.json';finish=Path(d)/'end.json'
        receipt1=Path(d)/'one.json';receipt2=Path(d)/'two.json';e.save(start)
        for src,dst,receipt,offset in ((start,middle,receipt1,0),(middle,finish,receipt2,320)):
            subprocess.run([sys.executable,__file__,'--worker',str(src),str(dst),str(receipt),str(offset)],
                           cwd=ROOT,check=True,stdout=subprocess.DEVNULL,timeout=600)
        r1=json.loads(receipt1.read_text());r2=json.loads(receipt2.read_text())
        reloaded=Individual.load(finish)
        continuity=(mid==normalized(Individual.load(middle).snapshot()) and end==normalized(reloaded.snapshot())
                    and first==r1 and second==r2)
        delayed=probe(continuous,mirror);restarted=probe(reloaded,mirror)
        continuity=continuity and normalized(delayed)==normalized(restarted)
    return {'seed':seed,'mirror':mirror,'good_type':good,'freeze_tract':freeze,
            'training':training,'immediate':immediate,'delayed':delayed,'restarted':restarted,
            'interval_first':first,'interval_second':second,'continuity':continuity,
            'elapsed_seconds':time.monotonic()-started,'parent_cpu_seconds':time.process_time()-cpu,
            'child_cpu_seconds':resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime-child_cpu_start,
            'peak_worker_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',nargs=4);p.add_argument('--seeds',nargs='+',type=int)
    p.add_argument('--output',type=Path);p.add_argument('--workers',type=int,default=4)
    a=p.parse_args()
    if a.worker:
        src,dst,receipt,start=a.worker;e=Individual.load(src);result=interval(e,int(start),320);e.save(dst)
        Path(receipt).write_text(normalized(result)+'\n');return
    if not a.seeds or not a.output:p.error('--seeds and --output required')
    specs=[(s,m,g,f) for s in a.seeds for m in (False,True) for g in (0,1) for f in (False,True)]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=a.workers) as pool, a.output.open('x') as out:
        for result in pool.map(case,specs):
            out.write(normalized(result)+'\n');out.flush()
            print('seed',result['seed'],'mirror',result['mirror'],'good',result['good_type'],
                  'freeze',result['freeze_tract'],'continuity',result['continuity'],flush=True)

if __name__=='__main__':main()
