"""Frozen paired-seed prospective completion/cost prediction analysis."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import random
import statistics

SEEDS=tuple(range(700,716));BOOTSTRAPS=10000;BOOTSTRAP_SEED=20261107


def bootstrap(values):
    r=random.Random(BOOTSTRAP_SEED);n=len(values)
    samples=sorted(sum(values[r.randrange(n)] for _ in range(n))/n for _ in range(BOOTSTRAPS))
    return [samples[249],samples[9749]]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();cases=[]
    with a.raw.open() as f:
        for line in f:cases.append(json.loads(line))
    if sorted(x['seed'] for x in cases)!=list(SEEDS):raise ValueError('missing or duplicate fresh seed')
    counts=Counter();by_seed={};coverage=defaultdict(Counter);calibration={name:defaultdict(Counter) for name in ('baseline','candidate')}
    for case in cases:
        seed=case['seed'];opps=case['opportunities']
        if len(opps)!=24 or [x['config']['opportunity'] for x in opps]!=list(range(24)):raise ValueError('bad opportunities')
        forecasts={};terminals={};brier=[];cost=[]
        for o in opps:
            cfg=o['config'];counts['opportunities']+=1;counts['no_eat_request']+=o['no_eat_request'];counts['completed_opportunities']+=o['completed'];counts['unsupported_ticks']+=o['unsupported_ticks']
            keys=(('phase',cfg['phase']),('hunger',str(cfg['hunger'])),('side',str(cfg['side'])),('food',str(cfg['food_index'])))
            for key in keys:
                coverage[key]['opportunities']+=1;coverage[key]['no_request']+=o['no_eat_request'];coverage[key]['completed_opportunities']+=o['completed']
            for event in o['predictions']:
                aid=event['action_id']
                if event['kind']=='forecast':
                    if aid in forecasts:raise ValueError('duplicate action forecast')
                    forecasts[aid]=(event,cfg);counts['forecasts']+=1
                    counts['prior_only']+=event['candidate']['evidence_count']==0
                    for key in keys:coverage[key]['forecasts']+=1
                elif event['kind']=='terminal':
                    if aid in terminals or aid not in forecasts:raise ValueError('duplicate or unmatched terminal')
                    forecast,origin=forecasts[aid]
                    if event['target']!=forecast['target'] or event['forecast']!=forecast:raise ValueError('forecast mutated or target mismatch')
                    terminals[aid]=event;counts['terminal_'+event['terminal']]+=1
                    if event['terminal']=='unknown':
                        counts['censored']+=1
                        for key in keys:coverage[key]['censored']+=1
                        continue
                    if event['terminal'] not in ('completed','interrupted','timeout'):raise ValueError('unexpected terminal')
                    y=int(event['terminal']=='completed');counts['scored_forecasts']+=1;counts['completed_actions']+=y;counts['noncompleted_actions']+=1-y
                    for key in keys:coverage[key]['scored_forecasts']+=1;coverage[key]['completed_actions']+=y
                    pb=forecast['baseline']['completion_probability'];pc=forecast['candidate']['completion_probability']
                    cb=forecast['baseline']['expected_reserve_cost'];cc=forecast['candidate']['expected_reserve_cost'];actual=event['observed_cost']
                    if not all(isinstance(x,(int,float)) for x in (pb,pc,cb,cc,actual)) or not 0<=pb<=1 or not 0<=pc<=1 or actual<0:raise ValueError('invalid forecast')
                    brier.append(((pb-y)**2,(pc-y)**2));cost.append((abs(cb-actual),abs(cc-actual)))
                    for name,prob in (('baseline',pb),('candidate',pc)):
                        b=min(int(prob*4),3);bucket=calibration[name][str(b)]
                        bucket['n']+=1;bucket['probability_sum']+=prob;bucket['completed']+=y
                else:raise ValueError('unknown prediction event')
        if set(forecasts)!=set(terminals):raise ValueError('unreconciled forecast')
        by_seed[str(seed)]={'forecasts':len(forecasts),'scored':len(brier),
            'brier_baseline':statistics.mean(x[0] for x in brier) if brier else None,
            'brier_candidate':statistics.mean(x[1] for x in brier) if brier else None,
            'cost_mae_baseline':statistics.mean(x[0] for x in cost) if cost else None,
            'cost_mae_candidate':statistics.mean(x[1] for x in cost) if cost else None}
    for bins in calibration.values():
        for row in bins.values():
            row['mean_predicted']=row['probability_sum']/row['n'];row['observed_rate']=row['completed']/row['n']
    # A conditional usefulness claim needs a score in every fresh seed,
    # at least 32 scored actions total, and both completion outcomes present.
    enough=all(x['scored']>0 for x in by_seed.values()) and counts['scored_forecasts']>=32 and counts['completed_actions']>0 and counts['noncompleted_actions']>0
    comparisons={}
    for name,key in (('completion_brier','brier'),('cost_mae','cost_mae')):
        ds=[x[key+'_baseline']-x[key+'_candidate'] for x in by_seed.values() if x['scored']]
        comparisons[name]={'seed_differences':ds,'mean_baseline_minus_candidate':statistics.mean(ds) if ds else None,
                           'ci95':bootstrap(ds) if ds else None,'coverage_qualified':enough,
                           'usefulness_pass':bool(enough and bootstrap(ds)[0]>0)}
    result={'schema':'cb05-prospective-summary-v1','seeds':list(SEEDS),'counts':dict(counts),'by_seed':by_seed,
            'coverage':{kind+':'+value:dict(count) for (kind,value),count in coverage.items()},
            'calibration':{name:dict(bins) for name,bins in calibration.items()},'comparisons':comparisons,
            'insufficient_coverage':not enough,
            'cpu_seconds_sum':sum(x['cpu_seconds'] for x in cases),'max_worker_peak_kib':max(x['peak_worker_kib'] for x in cases),
            'raw_sha256':hashlib.sha256(a.raw.read_bytes()).hexdigest()}
    with a.output.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'counts':result['counts'],'comparisons':result['comparisons'],'insufficient_coverage':result['insufficient_coverage']},indent=2))

if __name__=='__main__':main()
