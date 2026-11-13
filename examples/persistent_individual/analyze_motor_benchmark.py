"""Seed-level descriptive summaries and paired differences for motor benchmark."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
import statistics


def ci(values):
    rng=random.Random(20261107);n=len(values)
    ordered=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
    return [ordered[249],ordered[9749]]


def describe(row,start,end):
    records=[r for r in row['motor'] if start<=r['tick']<end]
    valid=[r for r in records if r['motor_success'] is not None]
    success=sum(r['motor_success'] for r in valid)
    cost=sum(r['cost'] for r in valid)
    n=len(valid)
    return {'ticks':end-start,'attempts':len(records),'eligible':n,'successes':success,
      'success_rate':success/n if n else 0., 'progress_per_tick':sum(r['progress'] for r in valid)/(end-start),
      'utility_per_tick':(success-.25*cost)/(end-start),'utility_per_attempt':(success-.25*cost)/n if n else 0.,
      'cost':cost,'effort_rate':sum(r['mode']=='effort' for r in valid)/n if n else 0.,
      'brier':sum((r['prediction']-int(r['motor_success']))**2 for r in valid)/n if n else 0.,
      'predicted_success':sum(r['prediction'] for r in valid)/n if n else 0.,
      'false_failure_alerts':sum(r['prediction']<.5 and r['motor_success'] for r in valid),
      'blocked':sum(r['motor_success'] is None for r in records),
      'cancels_kept_evidence':all(r.get('cancel_kept_evidence') for r in records if r['motor_success'] is None)}


def main():
    p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    rows=[json.loads(s) for s in a.raw.read_text().splitlines()];cases={}
    for row in rows:
        key=(row['seed'],row['condition'])
        if key in cases:raise ValueError('duplicate case')
        cases[key]=row
    seeds=sorted({k[0] for k in cases});conditions=('normal','effort','adaptive')
    if len(cases)!=len(seeds)*3 or any((s,c) not in cases for s in seeds for c in conditions):raise ValueError('missing cases')
    stages={'healthy':(0,180),'impaired':(180,360),'recovery':(360,540),
            'impaired_early':(180,225),'impaired_late':(315,360),
            'recovery_early':(360,405),'recovery_late':(495,540)}
    all_metrics={}
    per={}
    for stage,(start,end) in stages.items():
        for condition in conditions:
            data=[describe(cases[(s,condition)],start,end) for s in seeds];per[(stage,condition)]=data
            keys=('success_rate','progress_per_tick','utility_per_tick','utility_per_attempt','cost','effort_rate','brier','predicted_success')
            all_metrics[f'{stage}_{condition}']={'mean_'+k:statistics.mean(d[k] for d in data) for k in keys}
            all_metrics[f'{stage}_{condition}'].update({k:sum(d[k] for d in data) for k in ('attempts','eligible','successes','false_failure_alerts','blocked')})
    for stage in stages:
        for other in ('normal','effort'):
            for measure in ('success_rate','utility_per_tick','cost','brier'):
                diff=[x[measure]-y[measure] for x,y in zip(per[(stage,'adaptive')],per[(stage,other)])]
                all_metrics[f'{stage}_adaptive_minus_{other}_{measure}']={'mean':statistics.mean(diff),'ci95':ci(diff),'seed_values':diff}
    result={'seeds':seeds,'cases':len(rows),'metrics':all_metrics,
            'continuity_all':all(r['checkpoint_continuation_equal'] for r in rows),
            'cancel_evidence_unchanged_all':all(d['cancels_kept_evidence'] for key,data in per.items() for d in data),
            'minimum_final_reserve':min(r['final_reserve'] for r in rows),
            'summed_cpu_seconds':sum(r['cpu_seconds'] for r in rows)}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    for key in ('healthy_normal','healthy_effort','healthy_adaptive','impaired_normal','impaired_effort','impaired_adaptive','recovery_normal','recovery_effort','recovery_adaptive','impaired_adaptive_minus_normal_success_rate','healthy_adaptive_minus_effort_cost'):
        print(key,result['metrics'][key])
    print('continuity',result['continuity_all'],'canceled evidence unchanged',result['cancel_evidence_unchanged_all'])

if __name__=='__main__':main()
