"""Aggregate paired, counterbalanced seed-level retention observations."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
import statistics


def interval(values,seed=20261107):
    rng=random.Random(seed); n=len(values)
    means=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
    return [means[249],means[9749]]


def main():
    p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    rows=[json.loads(x) for x in a.raw.read_text().splitlines()]; groups=defaultdict(dict)
    for r in rows:
        key=(r['seed'],r['mirror'],r['good_type']);condition=r['freeze_tract']
        if condition in groups[key]:raise ValueError('duplicate case')
        groups[key][condition]=r
    seeds=sorted({k[0] for k in groups})
    if len(rows)!=len(seeds)*8 or any(set(v)!={False,True} for v in groups.values()):raise ValueError('incomplete pairs')
    metrics={};stats=defaultdict(list)
    for seed in seeds:
        pairs=[v for k,v in groups.items() if k[0]==seed]
        if len(pairs)!=4:raise ValueError('missing counterbalance')
        for stage in ('immediate','delayed','restarted'):
            for freeze in (False,True):
                cases=[p[freeze] for p in pairs]
                for measure,fn in {
                    'aligned':lambda q: q['aligned'],
                    'attention':lambda q:q['attention'] is not None,
                    'eat_requested':lambda q:q['first_eat'] is not None,
                    'completion':lambda q:q['completion'] is not None,
                    'beneficial_completion':lambda q:bool(q['completion'] and q['completion']['energy_delta']>0),
                }.items():stats[(stage,freeze,measure)].append(sum(fn(c[stage]) for c in cases)/4)
    for (stage,freeze,measure),values in stats.items():
        metrics[f'{stage}_{"frozen" if freeze else "ordinary"}_{measure}']={'mean':statistics.mean(values),'seed_values':values}
    for stage in ('immediate','delayed','restarted'):
        diffs=[x-y for x,y in zip(stats[(stage,False,'aligned')],stats[(stage,True,'aligned')])]
        metrics[stage+'_advantage']={'mean':statistics.mean(diffs),'ci95':interval(diffs),'seed_values':diffs}
    drops=[x-y for x,y in zip(stats[('immediate',False,'aligned')],stats[('delayed',False,'aligned')])]
    metrics['ordinary_forgetting']={'mean':statistics.mean(drops),'ci95':interval(drops),'seed_values':drops}
    result={'seeds':seeds,'cases':len(rows),'metrics':metrics,'continuity_all':all(r['continuity'] for r in rows),
            'training_completions':sum(sum(t['event'] is not None for t in r['training']) for r in rows),
            'interval_ticks':sum(r['interval_first']['ticks']+r['interval_second']['ticks'] for r in rows),
            'nonfood_moves':sum(r['interval_first']['moves']+r['interval_second']['moves'] for r in rows),
            'elapsed_case_seconds_sum':sum(r['elapsed_seconds'] for r in rows),
            'parent_cpu_seconds_sum':sum(r['parent_cpu_seconds'] for r in rows),
            'child_cpu_seconds_sum':sum(r['child_cpu_seconds'] for r in rows),
            'peak_worker_kib_max':max(r['peak_worker_kib'] for r in rows)}
    result['gates']={'immediate':metrics['immediate_advantage']['mean']>=.1 and metrics['immediate_advantage']['ci95'][0]>0,
      'delayed':metrics['delayed_advantage']['mean']>=.1 and metrics['delayed_advantage']['ci95'][0]>0,
      'forgetting':metrics['ordinary_forgetting']['ci95'][1]<=.1,'mechanical':result['continuity_all']}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
