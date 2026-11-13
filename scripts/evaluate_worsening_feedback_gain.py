"""Paired development diagnostic of an optional sensory response gain.

The study is prespecified here: seeds 0..3, both bodies, mirrors and outcome
assignments, four 20-opportunity phases at 32 ticks, ordinary versus one gain.
This is exploratory development data, not a fresh held-out confirmation.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from hashlib import sha256
import json
from pathlib import Path
import random
import resource
import time

from creature_brain.benchmark.action_lifecycle import LifecycleFoodExperiment
from creature_brain.benchmark.feedback_gain import WorseningFeedbackGainExperiment

ROOT = Path(__file__).resolve().parents[1]
SEEDS = list(range(4))
PHASES = ('experience','evaluation','reversal','reversal_evaluation')
FILES = ('scripts/evaluate_worsening_feedback_gain.py',
         'src/creature_brain/benchmark/feedback_gain.py',
         'src/creature_brain/benchmark/action_lifecycle.py',
         'src/creature_brain/benchmark/food.py', 'src/creature_brain/benchmark/qualification.py',
         'src/creature_brain/benchmark/contract.py', 'src/creature_brain/benchmark/embodiment.py',
         'src/creature_brain/__init__.py','src/creature_brain/neural.py',
         'src/creature_brain/svrule.py','src/creature_brain/sensory.py','src/creature_brain/genome.py')


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def run_case(job):
    program, seed, body, mirror, good, mode = job
    start, cpu = time.monotonic(), time.process_time()
    cls = LifecycleFoodExperiment if mode == 'baseline' else WorseningFeedbackGainExperiment
    extra = {} if mode == 'baseline' else {'worsening_gain': {'gain2':2.0,'gain05':0.5}[mode]}
    e = cls(program, seed=seed, embodiment=body, condition='feedback', task='preference',
            mirror=mirror, max_steps=32, opportunities_per_phase=20, **extra)
    e.initial_good = good
    initial_brain = e.brain.to_dict()
    initial_obs = json.loads(json.dumps(e.observe(), default=lambda o: o.__dict__))
    restored, checkpoints, equal = None, {}, True
    while not e.done:
        event = e.tick()
        if restored is not None:
            equal = equal and restored.tick() == event
        if event['opportunity_end'] and e.opportunity in (20, 40, 60, 80):
            checkpoints[str(e.opportunity)] = e.brain.to_dict()['tracts'][5]
        if event['opportunity_end'] and e.opportunity == 40:
            restored = cls.restore(json.loads(json.dumps(e.snapshot())))
    if restored is None or not equal or json.dumps(e.snapshot(), sort_keys=True) != json.dumps(restored.snapshot(), sort_keys=True):
        raise RuntimeError('checkpoint continuation differs')
    return {'seed':seed,'body':body,'mirror':mirror,'good':good,'mode':mode,
            'initial_brain_sha256':sha256(json.dumps(initial_brain,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'initial_observation':initial_obs, 'history':e.history,'tract_checkpoints':checkpoints,
            'checkpoint_continuation_equal':True,'cpu_seconds':time.process_time()-cpu,
            'elapsed_seconds':time.monotonic()-start,
            'worker_peak_rss_kib_cumulative':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def paired_interval(differences, rng, samples=10000):
    n=len(differences)
    values=sorted(sum(differences[rng.randrange(n)] for _ in range(n))/n for _ in range(samples))
    return [values[int((samples-1)*.025)],values[int((samples-1)*.975)]]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--program',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--workers',type=int,default=8)
    p.add_argument('--gain',choices=('2','0.5'),default='2')
    p.add_argument('--baseline-from',type=Path,help='reuse verified baseline cases from a completed comparison')
    p.add_argument('--baseline-report',type=Path,help='report binding the reused case file')
    p.add_argument('--summarize-existing',type=Path,help='recover summary from preserved complete case JSONL')
    p.add_argument('--producer-source',type=Path,help='exact source used to produce preserved cases')
    a=p.parse_args()
    if not 1<=a.workers<=12:p.error('workers must be 1..12')
    if (a.baseline_from is None)!=(a.baseline_report is None):p.error('baseline cases and report are both required')
    if a.baseline_from is not None and a.summarize_existing is not None:p.error('cannot combine baseline reuse and summary recovery')
    cases=a.output.with_suffix('.cases.jsonl')
    if a.output.exists() or (cases.exists() and a.summarize_existing is None):raise FileExistsError('choose new output')
    if a.summarize_existing is not None and a.producer_source is None:raise ValueError('original producer source required')
    candidate='gain2' if a.gain=='2' else 'gain05'
    jobs=[(str(a.program.resolve()),s,b,m,g,mode) for s in SEEDS for b in ('walking','swimming')
          for m in (False,True) for g in (0,1) for mode in ('baseline',candidate)]
    start=time.monotonic();rows=[];reused=None;a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.baseline_from is not None:
        prior=json.loads(a.baseline_report.read_text())
        if (prior.get('raw_cases_sha256')!=digest(a.baseline_from) or
                prior.get('program_sha256')!=digest(a.program) or prior.get('seeds')!=SEEDS or
                prior.get('max_steps')!=32 or prior.get('opportunities_per_phase')!=20):
            raise ValueError('baseline source does not match program, seeds, or protocol')
        for path in FILES:
            if path not in ('scripts/evaluate_worsening_feedback_gain.py','src/creature_brain/benchmark/feedback_gain.py'):
                if prior['source_sha256'].get(path)!=digest(ROOT/path):raise ValueError('baseline source changed: '+path)
        with a.baseline_from.open() as stream:
            for line in stream:
                row=json.loads(line)
                if row['mode']=='baseline':rows.append(row)
        expected_baseline={(s,b,m,g,'baseline') for _,s,b,m,g,mode in jobs if mode=='baseline'}
        actual={(r['seed'],r['body'],r['mirror'],r['good'],r['mode']) for r in rows}
        if len(rows)!=len(expected_baseline) or actual!=expected_baseline or not all(r['checkpoint_continuation_equal'] for r in rows):
            raise ValueError('reused baseline cases incomplete or duplicated')
        jobs=[job for job in jobs if job[-1]!='baseline']
        reused={'case_file':str(a.baseline_from.resolve()),'case_sha256':digest(a.baseline_from),
                'report_sha256':digest(a.baseline_report),'cases':len(rows)}
    if a.summarize_existing is not None:
        cases=a.summarize_existing
        with cases.open() as stream:
            for line in stream:
                if not line.endswith('\n'):raise ValueError('truncated case line')
                rows.append(json.loads(line))
        expected={(s,b,m,g,mode) for _,s,b,m,g,mode in jobs}
        keys=[(r['seed'],r['body'],r['mirror'],r['good'],r['mode']) for r in rows]
        if len(keys)!=len(expected) or set(keys)!=expected or not all(r['checkpoint_continuation_equal'] for r in rows):
            raise ValueError('case set is incomplete, duplicated, or failed checkpoint validation')
    else:
        with cases.open('x') as stream,ProcessPoolExecutor(max_workers=a.workers) as pool:
            for row in rows:stream.write(json.dumps(row,allow_nan=False)+'\n')
            stream.flush()
            iterator=iter(jobs);pending={pool.submit(run_case,next(iterator)) for _ in range(min(a.workers,len(jobs)))}
            while pending:
                ready,pending=wait(pending,return_when=FIRST_COMPLETED)
                for future in ready:
                    row=future.result();rows.append(row);stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
                    print(f'{len(rows)}/{len(jobs)+(reused["cases"] if reused else 0)} {row["body"]} {row["mode"]}',flush=True)
                    try:pending.add(pool.submit(run_case,next(iterator)))
                    except StopIteration:pass
    pairs=defaultdict(dict);summary=defaultdict(lambda:{'opportunities':0,'success':0,'completed':0,
            'outcome_energy':0.0,'first_new_good':[],'censored_no_new_good':0})
    by_seed=defaultdict(lambda:defaultdict(list))
    for row in rows:
        pairs[(row['seed'],row['body'],row['mirror'],row['good'])][row['mode']]=row
        for phase in PHASES:
            end=[r for r in row['history'] if r['phase']==phase and r['opportunity_end']]
            if len(end)!=20:raise RuntimeError('incomplete phase')
            cell=summary[f'{row["body"]}/{row["mode"]}/{phase}'];cell['opportunities']+=20
            cell['success']+=sum(r['success'] for r in end);cell['completed']+=sum(r['outcome']['completed'] for r in end)
            cell['outcome_energy']+=sum(r['outcome']['energy_delta'] for r in row['history'] if r['phase']==phase)
            by_seed[(row['body'],row['seed'],phase)][row['mode']].append(sum(r['success'] for r in end)/20)
            if phase=='reversal':
                first=next((r['opportunity']-40+1 for r in end if r['success']),None)
                cell['first_new_good'].append(first);cell['censored_no_new_good']+=int(first is None)
    for pair in pairs.values():
        baseline,gain=pair['baseline'],pair[candidate]
        if (baseline['initial_brain_sha256']!=gain['initial_brain_sha256'] or baseline['initial_observation']!=gain['initial_observation'] or
                baseline['history'][0]['choice']!=gain['history'][0]['choice']):raise RuntimeError('initial conditions differ')
    rng=random.Random(20261107);comparisons={}
    for body in ('walking','swimming'):
        for phase in PHASES:
            diffs=[]
            for seed in SEEDS:
                v=by_seed[(body,seed,phase)]
                if len(v[candidate])!=4 or len(v['baseline'])!=4:raise RuntimeError('missing paired branch')
                diffs.append(sum(v[candidate])/4-sum(v['baseline'])/4)
            comparisons[f'{body}/{phase}']={f'mean_{candidate}_minus_baseline':sum(diffs)/len(diffs),
                'seed_differences':diffs,'paired_bootstrap_95':paired_interval(diffs,rng)}
    report={'scope':'exploratory development only; signal-gain extension, not native parity or global learning control',
      'program_sha256':digest(a.program),'source_sha256':{p:digest(ROOT/p) for p in FILES},
      'seeds':SEEDS,'conditions':['baseline',candidate],'opportunities_per_phase':20,'max_steps':32,
      'counterbalance':'both mirrors and both value assignments per seed and body',
      'mechanism':f'multiply positive attributed hunger-adjustment response by {a.gain}, cap at 1; chemistry unchanged',
      'cases':len(rows),'all_initial_pairs_match':True,'all_checkpoint_continuations_match':True,
      'raw_cases_sha256':digest(cases),'summary_recovered_after_producer_error':a.summarize_existing is not None,
      'producer_source_sha256':digest(a.producer_source) if a.producer_source is not None else digest(ROOT/FILES[0]),
      'reused_baseline':reused,
      'summary':dict(summary),'comparisons':comparisons,
      'wall_seconds':None if a.summarize_existing is not None else time.monotonic()-start,
      'summed_worker_cpu_seconds':sum(r['cpu_seconds'] for r in rows),
      'new_worker_cpu_seconds':None if a.summarize_existing is not None else sum(
          r['cpu_seconds'] for r in rows if reused is None or r['mode']!='baseline'),
      'max_cumulative_worker_rss_kib':max(r['worker_peak_rss_kib_cumulative'] for r in rows),
      'limitations':['Four development seeds only; intervals are descriptive.',
       'Signal gain changes transient activity as well as potential learning; changes cannot be attributed to plasticity alone.',
       'Hunger response is a host-level extension, not native parity.']}
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__ == '__main__':main()
