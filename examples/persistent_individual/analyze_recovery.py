"""Seed-level paired recovery benchmark analysis; event data remain in raw cases."""
import argparse,json,random,statistics
from pathlib import Path
from collections import defaultdict

CONDITIONS=('normal','effort','baseline','candidate')
SCENARIOS=('sustained','brief','noisy')


def stats(row,start,end):
    records=[r for r in row['motor'] if start<=r['tick']<end]
    eligible=[r for r in records if r['motor_success'] is not None]
    if not eligible: raise ValueError('no eligible movement attempts')
    n=len(eligible);ticks=end-start
    return {'success':sum(r['motor_success'] for r in eligible)/n,
            'success_per_attempt':sum(r['motor_success'] is True for r in records)/len(records),
            'effort':sum(r['mode']=='effort' for r in eligible)/n,
            'cost':sum(r['cost'] for r in records),
            'progress_per_tick':sum(r['progress'] for r in records)/ticks,
            'success_per_tick':sum(r['motor_success'] is True for r in records)/ticks,
            'utility_per_tick':sum((int(r['motor_success'])-.25*r['cost']) for r in eligible)/ticks,
            'brier':sum((r['prediction']-int(r['motor_success']))**2 for r in eligible)/n,
            'predicted':sum(r['prediction'] for r in eligible)/n,
            'false_failure':sum(r['prediction']<.5 and r['motor_success'] for r in eligible),
            'attempts':len(records),'eligible':n,'blocked':len(records)-n}


def interval(values):
    rng=random.Random(20261107);n=len(values)
    means=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
    return [means[249],means[9749]]


def main():
    p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('out',type=Path);args=p.parse_args()
    rows=[json.loads(s) for s in args.raw.read_text().splitlines()]
    bykey={(r['seed'],r['scenario'],r['condition']):r for r in rows}
    if len(rows)!=len(bykey):raise ValueError('duplicate keys')
    seeds=sorted({r['seed'] for r in rows})
    if len(bykey)!=len(seeds)*len(SCENARIOS)*len(CONDITIONS):raise ValueError('missing cases')
    output={'seeds':seeds,'cases':len(rows),'continuity_all':all(r['checkpoint_continuation_equal'] for r in rows),
            'case_cpu_seconds_sum':sum(r['cpu_seconds'] for r in rows),'minimum_final_reserve':min(r['final_reserve'] for r in rows),
            'results':{},'paired':{}}
    for scenario in SCENARIOS:
        recovery=210 if scenario=='brief' else 360
        windows={'healthy':(0,180),'impaired':(180,recovery),'recovery':(recovery,540),
                 'recovery_early':(recovery,recovery+45),'recovery_late':(495,540)}
        for window,(start,end) in windows.items():
            for cond in CONDITIONS:
                values=[stats(bykey[(seed,scenario,cond)],start,end) for seed in seeds]
                keys=('success','success_per_attempt','effort','cost','progress_per_tick','success_per_tick','utility_per_tick','brier','predicted','false_failure')
                output['results'][f'{scenario}_{window}_{cond}']={k:statistics.mean(v[k] for v in values) for k in keys}
                output['results'][f'{scenario}_{window}_{cond}'].update({k:sum(v[k] for v in values) for k in ('attempts','eligible','blocked')})
            for metric in ('success','success_per_attempt','effort','cost','progress_per_tick','success_per_tick','utility_per_tick','brier'):
                diffs=[stats(bykey[(seed,scenario,'candidate')],start,end)[metric]-stats(bykey[(seed,scenario,'baseline')],start,end)[metric] for seed in seeds]
                output['paired'][f'{scenario}_{window}_{metric}']={'mean':statistics.mean(diffs),'ci95':interval(diffs),'seed_values':diffs}
    args.out.write_text(json.dumps(output,indent=2)+'\n')
    for k in ('sustained_recovery_early_effort','sustained_recovery_late_effort','sustained_impaired_success','sustained_healthy_cost','brief_recovery_early_effort','brief_impaired_success'):
        print(k,output['paired'][k])
    print('continuity',output['continuity_all'],'cases',len(rows))

if __name__=='__main__':main()
