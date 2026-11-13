"""Development-only contact timing for the experimental action lifecycle."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import resource
import time

from creature_brain.benchmark.action_lifecycle import LifecycleFoodExperiment, LifecycleDriveCombFrozenExperiment

BUDGETS = (2, 4, 8, 16, 32)


def trial(args):
    program, seed, body, mirror, budget, control = args
    cls = LifecycleDriveCombFrozenExperiment if control else LifecycleFoodExperiment
    started, cpu = time.monotonic(), time.process_time()
    exp = cls(program, seed=seed, embodiment=body, condition='feedback', task='preference',
              mirror=mirror, max_steps=budget, opportunities_per_phase=20)
    first = None
    while exp.opportunity < 20:
        event = exp.tick()
        if event['outcome']['completed']:
            first = exp.time
            break
    return {'seed': seed, 'body': body, 'mirror': mirror, 'budget': budget,
            'control': 'gene7_frozen' if control else 'ordinary', 'completed': first is not None,
            'first_interaction_tick': first, 'ticks': exp.time, 'history': exp.history,
            'elapsed_seconds': time.monotonic() - started, 'cpu_seconds': time.process_time() - cpu,
            'worker_peak_rss_kib_cumulative': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--program', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--seeds', type=int, default=16, help='prefix of development seeds 0–15; fewer than 16 cannot qualify')
    a = p.parse_args()
    if not 1 <= a.seeds <= 16 or a.workers < 1:
        p.error('use 1–16 development seeds and at least one worker')
    program = a.program.resolve()
    jobs = [(str(program), seed, body, mirror, budget, control)
            for budget in BUDGETS for body in ('walking', 'swimming')
            for mirror in (False, True) for control in (False, True) for seed in range(a.seeds)]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    cases = a.output.with_suffix('.cases.jsonl')
    if a.output.exists() or cases.exists():
        raise FileExistsError('choose a new output; evidence is not overwritten')
    started, rows = time.monotonic(), []
    with cases.open('x') as f, ProcessPoolExecutor(max_workers=a.workers) as pool:
        for row in pool.map(trial, jobs, chunksize=1):
            rows.append(row)
            f.write(json.dumps(row, allow_nan=False) + '\n')
            f.flush()
            print(f"{len(rows)}/{len(jobs)} budget={row['budget']} body={row['body']} control={row['control']}", flush=True)
    metrics = {}
    for budget in BUDGETS:
        for body in ('walking', 'swimming'):
            for mirror in (False, True):
                for control in ('ordinary', 'gene7_frozen'):
                    subset = [r for r in rows if (r['budget'], r['body'], r['mirror'], r['control']) ==
                              (budget, body, mirror, control)]
                    completed = sum(r['completed'] for r in subset)
                    metrics[f'{budget}/{body}/{int(mirror)}/{control}'] = {
                        'completed': completed, 'total': len(subset),
                        'first_interaction_ticks': [r['first_interaction_tick'] for r in subset],
                        'censored_seeds': [r['seed'] for r in subset if not r['completed']]}
    eligible = [b for b in BUDGETS if all(metrics[f'{b}/{body}/{mirror}/{control}']['completed'] >= 13
                for body in ('walking', 'swimming') for mirror in (0, 1)
                for control in ('ordinary', 'gene7_frozen'))] if a.seeds == 16 else []
    root = Path(__file__).resolve().parents[1]
    files = ['scripts/calibrate_lifecycle_twenty_opportunities.py', 'src/creature_brain/benchmark/action_lifecycle.py',
             'src/creature_brain/benchmark/connection_freeze.py', 'src/creature_brain/benchmark/qualification.py',
             'src/creature_brain/benchmark/food.py', 'src/creature_brain/benchmark/contract.py',
             'src/creature_brain/benchmark/embodiment.py', 'src/creature_brain/neural.py',
             'src/creature_brain/svrule.py', 'src/creature_brain/genome.py', 'src/creature_brain/sensory.py']
    report = {'scope': 'development lifecycle contact timing; no native parity or preference claim',
              'seeds': list(range(a.seeds)), 'budgets': BUDGETS, 'opportunities_limit': 20,
              'qualification_rule': 'at least 13/16 seeds in each body/mirror/control cell',
              'full_development_sample': a.seeds == 16, 'selected_budget': min(eligible) if eligible else None,
              'program_sha256': hashlib.sha256(program.read_bytes()).hexdigest(),
              'source_sha256': {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in files},
              'metrics': metrics, 'cases': len(rows), 'wall_seconds': time.monotonic()-started,
              'cpu_seconds': sum(r['cpu_seconds'] for r in rows),
              'max_cumulative_worker_rss_kib': max(r['worker_peak_rss_kib_cumulative'] for r in rows)}
    a.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'output': str(a.output), 'selected_budget': report['selected_budget'], 'cases': len(rows)}))


if __name__ == '__main__':
    main()
