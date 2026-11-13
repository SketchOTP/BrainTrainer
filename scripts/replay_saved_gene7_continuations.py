"""Independent reconstruction and continuation of predeclared saved cases.

The producer saved initial and final checkpoints, not midpoint checkpoints.
Reconstruct the midpoint from each saved initial checkpoint and compare every
captured event along the way, then checkpoint, restore, and replay to the end.
"""
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

from creature_brain.benchmark.research_checkpoint import restore_research_checkpoint, save_research_checkpoint

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = (
    (0, 'walking', False, 0, 'ordinary'),
    (0, 'walking', False, 0, 'gene7_frozen'),
    (15, 'swimming', True, 1, 'ordinary'),
    (15, 'swimming', True, 1, 'gene7_frozen'),
)


def normalized(value):
    return json.loads(json.dumps(value, allow_nan=False))


def extract(paths, expected_digests):
    selected = {}
    for path in paths:
        sha = hashlib.sha256()
        with path.open('rb') as stream:
            for raw in stream:
                sha.update(raw)
                prefix = raw[:180]
                if not any(f'"seed": {k[0]}, "body": "{k[1]}", "mirror": {str(k[2]).lower()}, '
                           f'"good": {k[3]}, "control": "{k[4]}"'.encode() in prefix for k in SAMPLES):
                    continue
                row = json.loads(raw)
                key = tuple(row[k] for k in ('seed', 'body', 'mirror', 'good', 'control'))
                if key in selected:
                    raise ValueError(f'duplicate selected case {key}')
                selected[key] = row
        if sha.hexdigest() != expected_digests[str(path.relative_to(ROOT))]:
            raise ValueError(f'case file digest differs from combined analysis: {path}')
    if selected.keys() != set(SAMPLES):
        raise ValueError(f'missing cases: {set(SAMPLES) - selected.keys()}')
    return selected


def replay(row):
    start, cpu = time.monotonic(), time.process_time()
    key = tuple(row[k] for k in ('seed', 'body', 'mirror', 'good', 'control'))
    experiment = restore_research_checkpoint(row['initial_checkpoint'])
    weak = { (t['gene_id'], t['source'], t['destination']): t['weak'].copy()
             for t in row['initial_tracts'] }
    restored = None
    midpoint_index = None
    for index, step in enumerate(row['steps']):
        if experiment.pending != step['pending_before']:
            raise AssertionError(f'{key}: pending inputs differ at step {index}')
        inputs = {name: l.inputs.copy() for name, l in experiment.brain.lobes.items()}
        if inputs != step['queued_lobe_inputs_before']:
            raise AssertionError(f'{key}: queued lobe inputs differ at step {index}')
        event = experiment.tick()
        if normalized(event) != step['event']:
            raise AssertionError(f'{key}: recorded choice/outcome differs at step {index}')
        if experiment.brain.chemicals != step['chemicals_after'] or experiment.brain._rng != step['rng_after']:
            raise AssertionError(f'{key}: recorded chemistry or RNG differs at step {index}')
        for tract in step['tract_delta']:
            tkey = (tract['gene_id'], tract['source'], tract['destination'])
            if 'weak' in tract['metadata']:
                weak[tkey] = tract['metadata']['weak']
        for tract in experiment.brain.tracts:
            if tract.weak != weak[(tract.gene_id, tract.source_lobe, tract.destination_lobe)]:
                raise AssertionError(f'{key}: weak queue differs at step {index}')
        if restored is not None and normalized(restored.tick()) != normalized(event):
            raise AssertionError(f'{key}: restored continuation differs at step {index}')
        if event['opportunity_end'] and experiment.opportunity == 40:
            if restored is not None:
                raise AssertionError('duplicate midpoint')
            midpoint_index = index
            restored = restore_research_checkpoint(normalized(save_research_checkpoint(experiment)))
    if restored is None:
        raise AssertionError(f'{key}: missing midpoint')
    actual = normalized(save_research_checkpoint(experiment))
    replayed = normalized(save_research_checkpoint(restored))
    if actual != row['final_checkpoint'] or replayed != row['final_checkpoint']:
        raise AssertionError(f'{key}: final checkpoint mismatch')
    return {'case': list(key), 'steps': len(row['steps']), 'midpoint_step': midpoint_index + 1,
            'post_midpoint_steps': len(row['steps']) - midpoint_index - 1,
            'captured_events_pending_inputs_chemistry_rng_and_weak_queues_match': True,
            'independent_midpoint_checkpoint_continuation_and_final_match': True,
            'elapsed_seconds': time.monotonic()-start, 'cpu_seconds': time.process_time()-cpu,
            'worker_peak_rss_kib_cumulative': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main(output):
    out = Path(output)
    if out.exists():
        raise FileExistsError('choose a new output')
    analysis = ROOT/'runs/food-qualification/gene7-contact-development-v1-recovered-analysis.json'
    result = json.loads(analysis.read_text())
    digests = {x['path']: x['sha256'] for x in result['case_sources']}
    paths = [ROOT/x['path'] for x in result['case_sources']]
    started = time.monotonic()
    selected = extract(paths, digests)
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(replay, (selected[k] for k in SAMPLES)))
    data = {'scope': 'four predetermined development cases; reconstructed midpoint, not original saved midpoint',
            'samples': rows, 'source_case_digests': digests,
            'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'wall_seconds': time.monotonic()-started,
            'cpu_seconds': sum(x['cpu_seconds'] for x in rows),
            'max_cumulative_worker_rss_kib': max(x['worker_peak_rss_kib_cumulative'] for x in rows)}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main(sys.argv[1])
