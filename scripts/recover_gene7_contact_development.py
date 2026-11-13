"""Resume missing frozen development cases without changing original evidence."""
import argparse
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_gene7_contact_development import case, check_manifest, sha


def key_for(row):
    key = (row['seed'], row['body'], row['mirror'], row['good'], row['control'])
    if (type(key[0]) is not int or type(key[2]) is not bool or type(key[3]) is not int):
        raise ValueError('invalid case key types')
    return key


def expected_keys(manifest):
    return {(seed, body, mirror, good, control)
            for seed in manifest['seeds'] for body in manifest['bodies']
            for mirror in manifest['mirrors'] for good in manifest['good_types']
            for control in manifest['controls']}


def validate_row(row, manifest, allowed):
    key = key_for(row)
    if key not in allowed:
        raise ValueError(f'case key outside frozen manifest: {key}')
    seed, body, mirror, good, control = key
    initial, final = row['initial_checkpoint'], row['final_checkpoint']
    kind = 'action-lifecycle-drive-comb-frozen-v1' if control == 'gene7_frozen' else 'action-lifecycle-v1'
    if initial['experiment_type'] != kind or final['experiment_type'] != kind:
        raise ValueError(f'wrong checkpoint type for {key}')
    first, last = initial['snapshot'], final['snapshot']
    config = first['config']
    if (config['seed'] != seed or config['embodiment'] != body or config['condition'] != 'feedback' or
            config['max_steps'] != manifest['budget'] or config['opportunities_per_phase'] != 20 or
            first['qualification']['task'] != 'preference' or first['qualification']['mirror'] != mirror or
            first['initial_good'] != good or first['opportunity'] != 0 or last['opportunity'] != 80 or
            config != last['config'] or row['checkpoint_continuation_equal'] is not True):
        raise ValueError(f'invalid case configuration or continuation: {key}')
    steps = row['steps']
    if (not steps or len(steps) != last['time'] - first['time'] or
            sum(s['event']['opportunity_end'] for s in steps) != 80 or
            set(row['probes']) != {'20/unmodified', '20/matched', '60/unmodified', '60/matched'}):
        raise ValueError(f'incomplete history or probes: {key}')
    expected_opportunity = 0
    for step in steps:
        event = step['event']
        if event['opportunity'] != expected_opportunity:
            raise ValueError(f'out-of-order opportunity: {key}')
        if event['opportunity_end']:
            expected_opportunity += 1
        if control == 'gene7_frozen' and any(
                (d['gene_id'], d['source'], d['destination']) == (7, 'driv', 'comb')
                for d in step['tract_delta']):
            raise ValueError(f'controlled tract changed: {key}')
    if control == 'gene7_frozen':
        if row['gene7_unchanged'] is not True:
            raise ValueError(f'controlled tract not fixed: {key}')
        tract_index = next(i for i, t in enumerate(row['initial_tracts'])
                           if (t['gene_id'], t['source'], t['destination']) == (7, 'driv', 'comb'))
        if first['brain']['tracts'][tract_index] != last['brain']['tracts'][tract_index]:
            raise ValueError(f'controlled checkpoint tract mismatch: {key}')
    return key


def scan_original(path, manifest):
    expected = expected_keys(manifest)
    present, digest, count = set(), hashlib.sha256(), 0
    with path.open('rb') as f:
        for line in f:
            digest.update(line)
            count += 1
            if not line.endswith(b'\n'):
                raise ValueError(f'original row {count} is incomplete')
            try:
                row = json.loads(line)
                key = validate_row(row, manifest, expected)
            except (ValueError, KeyError, TypeError, IndexError) as error:
                raise ValueError(f'original row {count} invalid: {error}') from error
            if key in present:
                raise ValueError(f'duplicate original case: {key}')
            present.add(key)
    return present, digest.hexdigest()


def recover(manifest_path, original_path, output, workers, expected_missing):
    if workers < 1 or expected_missing < 1:
        raise ValueError('worker and expected-missing counts must be positive')
    cases = output.with_suffix('.cases.jsonl')
    if output.exists() or cases.exists():
        raise FileExistsError('choose new recovery files')
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    check_manifest(manifest)
    present, original_digest = scan_original(original_path, manifest)
    missing = sorted(expected_keys(manifest) - present)
    if len(missing) != expected_missing:
        raise ValueError(f'expected {expected_missing} missing cases, found {len(missing)}')
    print(f'Validated {len(present)} original cases; running {len(missing)} missing cases.', flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    recovered = set()
    cpu, peak = 0.0, 0
    with cases.open('x') as f, ProcessPoolExecutor(max_workers=workers) as pool:
        iterator = iter(missing)
        pending = {pool.submit(case, (manifest, *key)) for key in
                   [next(iterator) for _ in range(min(workers, len(missing)))]}
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                row = future.result()
                key = validate_row(row, manifest, set(missing))
                if key in recovered:
                    raise ValueError(f'duplicate recovered case: {key}')
                f.write(json.dumps(row, allow_nan=False) + '\n')
                f.flush()
                recovered.add(key)
                cpu += row['cpu_seconds']
                peak = max(peak, row['worker_peak_rss_kib_cumulative'])
                print(f'{len(recovered)}/{len(missing)} {key}', flush=True)
                try:
                    pending.add(pool.submit(case, (manifest, *next(iterator))))
                except StopIteration:
                    pass
    if recovered != set(missing):
        raise RuntimeError('recovery did not cover all missing cases')
    check_manifest(manifest)
    if sha(manifest_path.read_bytes()) != sha(manifest_bytes):
        raise RuntimeError('frozen manifest changed during recovery')
    result = {'scope': 'recovery of missing cases in frozen development-only gene-7 tract ablation',
              'manifest': str(manifest_path.resolve()), 'manifest_sha256': sha(manifest_bytes),
              'original_cases': str(original_path.resolve()), 'original_cases_sha256': original_digest,
              'original_cases_count': len(present), 'recovery_cases': str(cases.resolve()),
              'recovery_cases_sha256': file_sha(cases), 'recovered_count': len(recovered),
              'recovered_keys': [list(key) for key in sorted(recovered)],
              'recovery_script_sha256': file_sha(Path(__file__)),
              'wall_seconds': time.monotonic()-start, 'cpu_seconds': cpu,
              'max_cumulative_worker_rss_kib': peak,
              'parent_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    with output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')
    return result


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True, type=Path)
    p.add_argument('--original', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--expected-missing', required=True, type=int)
    p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    recover(a.manifest, a.original, a.output, a.workers, a.expected_missing)


if __name__ == '__main__':
    main()
