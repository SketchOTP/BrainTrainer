"""Bounded plumbing diagnostic, not the proposed preference evaluation."""
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

from creature_brain.benchmark.action_lifecycle import LifecycleFoodExperiment, LifecycleDriveCombFrozenExperiment
from creature_brain.benchmark.retention_probe import probe_retained_choice


def run(job):
    program, seed, body, mirror, good, frozen = job
    cls = LifecycleDriveCombFrozenExperiment if frozen else LifecycleFoodExperiment
    start, cpu = time.monotonic(), time.process_time()
    exp = cls(program, seed=seed, embodiment=body, condition='feedback', task='preference',
              mirror=mirror, max_steps=8, opportunities_per_phase=2)
    exp.initial_good = good
    initial = exp.brain.to_dict()['tracts'][5]
    probes = {}
    while not exp.done:
        exp.tick()
        if exp.opportunity in (2, 6) and exp.step_in_opportunity == 0 and str(exp.opportunity) not in probes:
            probes[str(exp.opportunity)] = {str(match): probe_retained_choice(exp, match_needs=match)
                                            for match in (False, True)}
    return {'seed': seed, 'body': body, 'mirror': mirror, 'good': good, 'frozen': frozen,
            'history': exp.history, 'probes': probes, 'initial_tract': initial,
            'final_tract': exp.brain.to_dict()['tracts'][5],
            'elapsed_seconds': time.monotonic()-start, 'cpu_seconds': time.process_time()-cpu,
            'worker_max_rss_kib_cumulative': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main(program, dest):
    output = Path(dest)
    raw = output.with_suffix('.cases.jsonl')
    if output.exists() or raw.exists():
        raise FileExistsError('choose new output')
    jobs = [(program, 0, body, mirror, good, frozen) for body in ('walking', 'swimming')
            for mirror in (False, True) for good in (0, 1) for frozen in (False, True)]
    rows = []
    start = time.monotonic()
    with raw.open('x') as stream, ProcessPoolExecutor(max_workers=4) as pool:
        for row in pool.map(run, jobs):
            rows.append(row)
            stream.write(json.dumps(row, allow_nan=False)+'\n')
            stream.flush()
    root = Path(__file__).resolve().parents[1]
    files = ['scripts/smoke_lifecycle_gene7_preference.py', 'src/creature_brain/benchmark/action_lifecycle.py',
             'src/creature_brain/benchmark/retention_probe.py', 'src/creature_brain/benchmark/research_checkpoint.py',
             'src/creature_brain/benchmark/connection_freeze.py', 'src/creature_brain/benchmark/food.py',
             'src/creature_brain/benchmark/qualification.py', 'src/creature_brain/neural.py',
             'src/creature_brain/svrule.py']
    groups = {}
    for row in rows:
        key = f"{row['body']}/{'gene7_frozen' if row['frozen'] else 'ordinary'}"
        group = groups.setdefault(key, {'cases': 0, 'completed': 0, 'successful': 0,
                                        'probe_pairs': 0, 'frozen_tract_unchanged': 0})
        group['cases'] += 1
        group['completed'] += sum(e['outcome']['completed'] for e in row['history'])
        group['successful'] += sum(e['success'] for e in row['history'])
        group['probe_pairs'] += len(row['probes'])
        group['frozen_tract_unchanged'] += int(row['frozen'] and row['initial_tract'] == row['final_tract'])
    output.write_text(json.dumps({'scope': 'one-seed execution/retention-probe smoke; not learning evidence',
       'program_sha256': hashlib.sha256(Path(program).read_bytes()).hexdigest(),
       'source_sha256': {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
       'cases': len(rows), 'groups': groups, 'wall_seconds': time.monotonic()-start,
       'cpu_seconds': sum(row['cpu_seconds'] for row in rows),
       'max_cumulative_worker_rss_kib': max(row['worker_max_rss_kib_cumulative'] for row in rows)}, indent=2)+'\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
