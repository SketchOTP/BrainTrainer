"""Reproducible bounded preference benchmark; feedback control is unqualified."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import resource
import statistics
import time

from .food import FoodExperiment, PHASES


def run_one(args):
    program, seed, body, condition, variant, count, steps = args
    started, cpu = time.monotonic(), time.process_time()
    experiment = FoodExperiment(program, seed=seed, embodiment=body, condition=condition,
              opportunities_per_phase=count, max_steps=steps,
              layout='heldout' if variant == 'layout' else 'training',
              appearance='heldout' if variant == 'appearance' else 'training',
              novel_identity=variant == 'novel_identity')
    restored = None
    continuation_match = None
    while not experiment.done:
        event = experiment.tick()
        if restored is not None and restored.tick() != event:
            continuation_match = False
        if (restored is None and seed == 16 and variant == 'training' and
                experiment.opportunity == count*2):
            restored = FoodExperiment.restore(json.loads(json.dumps(experiment.snapshot())))
            continuation_match = True
    if restored is not None:
        continuation_match = bool(continuation_match and
            json.dumps(experiment.snapshot(), sort_keys=True) == json.dumps(restored.snapshot(), sort_keys=True))
    endings = [event for event in experiment.history if event['opportunity_end']]
    phases = {}
    for phase in PHASES:
        subset = [event for event in endings if event['phase'] == phase]
        phases[phase] = {'opportunities': len(subset),
                         'successes': sum(event['success'] for event in subset),
                         'completed': sum(event['outcome']['completed'] for event in subset),
                         'no_target': sum(event['choice']['target'] is None for event in subset),
                         'unsuccessful': sum(not event['success'] for event in subset)}
    successes = [int(event['success']) for event in endings]
    baseline = successes[:min(5, count)]
    speed = {}
    for key, segment in [('initial', successes[:count*2]), ('reversal', successes[count*2:])]:
        speed[key] = next((i for i in range(8, len(segment)+1)
                           if sum(segment[i-8:i]) >= 6), None)
    return {'seed': seed, 'embodiment': body, 'condition': condition,
            'variant': variant, 'phases': phases, 'learning_speed_rolling_8': speed,
            'early_experience': {'opportunities': len(baseline), 'successes': sum(baseline)},
            'midpoint_checkpoint_continuation_equal': continuation_match,
            'steps': experiment.time, 'history': experiment.history,
            'elapsed_seconds': time.monotonic()-started,
            'cpu_seconds': time.process_time()-cpu,
            'worker_peak_rss_kib_cumulative': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def summarize(runs):
    groups = {}
    for body in ('walking', 'swimming'):
        for variant in ('training', 'layout', 'appearance', 'novel_identity'):
            for split in ('development', 'heldout'):
                relevant = [r for r in runs if r['embodiment']==body and r['variant']==variant
                            and (r['seed'] < 16) == (split == 'development')]
                if not relevant:
                    continue
                pairs = {}
                for r in relevant:
                    pairs.setdefault(r['seed'], {})[r['condition']] = r
                complete = [v for v in pairs.values() if set(v)=={'feedback','feedback_withheld'}]
                summary = {'paired_seeds': len(complete), 'control_qualified': False,
                           'reason': 'feedback withheld is not a learning-disabled control', 'phases': {},
                           'early_experience': {condition: statistics.fmean(
                               p[condition]['early_experience']['successes']/p[condition]['early_experience']['opportunities']
                               for p in complete) for condition in ('feedback','feedback_withheld')} if complete else {}}
                for phase in PHASES:
                    diffs=[]
                    for pair in complete:
                        a,b = pair['feedback']['phases'][phase], pair['feedback_withheld']['phases'][phase]
                        diffs.append(a['successes']/a['opportunities'] - b['successes']/b['opportunities'])
                    if not diffs:
                        continue
                    rng = random.Random(918271)
                    means = sorted(statistics.fmean(rng.choices(diffs,k=len(diffs))) for _ in range(2000))
                    summary['phases'][phase] = {
                        'feedback_success_rate': statistics.fmean(p['feedback']['phases'][phase]['successes']/p['feedback']['phases'][phase]['opportunities'] for p in complete),
                        'withheld_success_rate': statistics.fmean(p['feedback_withheld']['phases'][phase]['successes']/p['feedback_withheld']['phases'][phase]['opportunities'] for p in complete),
                        'paired_difference': statistics.fmean(diffs),
                        'bootstrap_95_percentile': [means[49],means[1949]],
                        'per_seed_differences': diffs}
                groups[f'{body}/{variant}/{split}'] = summary
    return groups


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--program',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--dev-seeds',type=int,default=16)
    p.add_argument('--heldout-seeds',type=int,default=40)
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--steps',type=int,default=2)
    p.add_argument('--opportunities',type=int,default=20)
    p.add_argument('--variant',choices=('training','layout','appearance','novel_identity','all'),default='all')
    p.add_argument('--resume',action='store_true',help='resume only matching retained cases')
    a=p.parse_args()
    if a.dev_seeds<0 or a.dev_seeds>16 or a.heldout_seeds<0 or a.workers<1 or a.steps<1 or a.opportunities<1:
        p.error('invalid benchmark bounds')
    seeds=list(range(a.dev_seeds))+list(range(16,16+a.heldout_seeds))
    variants=('training','layout','appearance','novel_identity') if a.variant=='all' else (a.variant,)
    jobs=[(a.program, seed, body, condition, variant, a.opportunities, a.steps)
          for body in ('walking','swimming') for variant in variants for seed in seeds
          for condition in ('feedback','feedback_withheld')]
    program_sha=hashlib.sha256(Path(a.program).read_bytes()).hexdigest()
    package=Path(__file__).resolve().parents[1]
    source_files=[Path(__file__), package/'benchmark/food.py', package/'benchmark/contract.py', package/'benchmark/embodiment.py',
                  package/'neural.py', package/'svrule.py', package/'genome.py', package/'sensory.py']
    signature=hashlib.sha256(json.dumps({'program':program_sha,'steps':a.steps,'count':a.opportunities,
        'source':{str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}},
        sort_keys=True).encode()).hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    cases_path=a.output.with_suffix('.cases.jsonl')
    runs=[]
    if a.resume and cases_path.exists():
        with cases_path.open() as stream:
            for line in stream:
                saved=json.loads(line)
                if saved['signature'] != signature:
                    raise ValueError('retained cases use a different program, source, or protocol')
                runs.append(saved['run'])
    elif cases_path.exists():
        raise FileExistsError(f'{cases_path} exists; use --resume or a new output')
    existing={(r['seed'],r['embodiment'],r['condition'],r['variant']) for r in runs}
    if len(existing)!=len(runs): raise ValueError('duplicate retained benchmark cases')
    planned={(job[1],job[2],job[3],job[4]) for job in jobs}
    if not existing <= planned: raise ValueError('retained cases exceed the requested seed or variant set')
    jobs=[job for job in jobs if (job[1],job[2],job[3],job[4]) not in existing]
    started=time.monotonic()
    with cases_path.open('a') as stream:
        def collect(results):
            for run in results:
                runs.append(run)
                stream.write(json.dumps({'signature':signature,'run':run},allow_nan=False)+'\n')
                stream.flush()
                print(f"completed {len(runs)}: {run['embodiment']} {run['variant']} seed={run['seed']} {run['condition']}", flush=True)
        if a.workers==1:
            collect(map(run_one,jobs))
        else:
            with ProcessPoolExecutor(max_workers=a.workers) as pool:
                collect(pool.map(run_one,jobs,chunksize=1))
    report={'schema':1,'program_sha256':program_sha,'protocol_signature':signature,
            'config':{'development_seeds':a.dev_seeds,'heldout_seeds':a.heldout_seeds,'max_steps':a.steps,
                      'opportunities_per_phase':a.opportunities,'variants':variants,'workers':a.workers},
            'control_qualification':'unqualified: feedback withheld, not learning disabled',
            'target':{'minimum_difference_percentage_points':10,
                      'required_phases':['evaluation','reversal_evaluation'],
                      'required_paired_95_percentile_lower_bound_above_zero':True,
                      'status':'unassessable until a qualified learning-disabled control exists'},
            'results':summarize(runs),'runs':runs,'wall_seconds':time.monotonic()-started}
    a.output.write_text(json.dumps(report,allow_nan=False)+'\n')
    print(json.dumps({'output':str(a.output),'runs':len(runs),'wall_seconds':report['wall_seconds'],
                      'results':report['results']},indent=2))


if __name__=='__main__':
    main()
