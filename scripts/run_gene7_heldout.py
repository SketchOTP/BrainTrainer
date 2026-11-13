"""Freeze and execute resumable shards of the held-out gene-7 comparison.

No held-out branch can run before the developer manifest, protocol and selected
diagnostic artifacts have been explicitly frozen with their digests. This uses
the exact development case function, including per-tick traces and checkpoint
continuation. Every shard covers a fixed five-seed range and writes separate
append-only case data, avoiding the prior long-process deadline.
"""
import argparse
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_gene7_contact_development as dev
from recover_gene7_contact_development import expected_keys, validate_row

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'docs/FOOD_GENE7_HELDOUT_PROTOCOL.md'
SOURCES = (PROTOCOL, 'scripts/run_gene7_heldout.py', 'scripts/analyze_gene7_heldout.py',
           'src/creature_brain/__init__.py', 'src/creature_brain/benchmark/approach_probe.py',
           'scripts/recover_gene7_contact_development.py', *dev.FILES)
SEEDS = list(range(56, 96))


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def source_digests():
    return {name: digest_file(ROOT / name) for name in SOURCES}


def freeze(dev_manifest, diagnostics, output, supporting=()):
    if output.exists():
        raise FileExistsError('manifest already exists')
    base = json.loads(dev_manifest.read_text())
    dev.check_manifest(base)
    if set(diagnostics) != {'transfer', 'reversal', 'replay'}:
        raise ValueError('transfer, reversal and replay diagnostic artifacts are required')
    paths = {role: path.resolve() for role, path in diagnostics.items()}
    if len(set(paths.values())) != 3:
        raise ValueError('diagnostic artifacts must be distinct')
    evidence = {role: json.loads(path.read_text()) for role, path in paths.items()}
    if (evidence['transfer'].get('summaries', {}).get('20', {}).get('pairs') != 24 or
            evidence['transfer'].get('summaries', {}).get('60', {}).get('pairs') != 24 or
            len(evidence['reversal'].get('cases', [])) != 256 or
            len(evidence['replay'].get('samples', [])) != 4 or
            not all(s.get('captured_events_pending_inputs_chemistry_rng_and_weak_queues_match') is True and
                    s.get('independent_midpoint_checkpoint_continuation_and_final_match') is True
                    for s in evidence['replay']['samples'])):
        raise ValueError('development diagnostics are incomplete or replay failed')
    diagnostic_digests = {role: {'path': str(path), 'sha256': digest_file(path)} for role, path in paths.items()}
    supporting_digests = {str(path.resolve()): digest_file(path) for path in supporting}
    if len(supporting_digests) != len(supporting):
        raise ValueError('supporting evidence must be distinct')
    manifest = {**base, 'schema': 'gene7-contact-heldout-v1', 'scope': 'held-out scoped gene-7 tract ablation',
                'seeds': SEEDS, 'base_manifest': str(dev_manifest.resolve()),
                'base_manifest_sha256': digest_file(dev_manifest), 'source_sha256': source_digests(),
                'diagnostic_sha256': diagnostic_digests, 'supporting_sha256': supporting_digests,
                'scoring': {'paired_unit': 'seed_mean_of_four_mirror_assignment_branches',
                            'min_difference': .1, 'interval': 'paired_percentile_bootstrap_95',
                            'bootstrap_samples': 10000, 'bootstrap_seed': 20261106,
                            'requires_both_evaluations_and_bodies': True},
                'shard_size': 5}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return manifest


def check_manifest(manifest):
    if manifest.get('schema') != 'gene7-contact-heldout-v1' or manifest.get('status') != 'frozen':
        raise ValueError('frozen held-out manifest required')
    base_path = Path(manifest['base_manifest'])
    if digest_file(base_path) != manifest['base_manifest_sha256']:
        raise ValueError('base manifest changed')
    base = json.loads(base_path.read_text())
    dev.check_manifest(base)
    if manifest.get('source_sha256') != source_digests():
        raise ValueError('held-out source changed')
    diagnostics = manifest.get('diagnostic_sha256', {})
    if set(diagnostics) != {'transfer', 'reversal', 'replay'} or any(
            digest_file(item['path']) != item['sha256'] for item in diagnostics.values()):
        raise ValueError('diagnostic evidence changed')
    if any(digest_file(path) != h for path, h in manifest.get('supporting_sha256', {}).items()):
        raise ValueError('supporting evidence changed')
    for key in ('budget', 'program', 'program_sha256', 'calibration', 'calibration_sha256', 'bodies',
                'mirrors', 'good_types', 'controls', 'opportunities_per_phase', 'phases', 'probe',
                'checkpoint_after_opportunities'):
        if manifest.get(key) != base.get(key):
            raise ValueError(f'held-out condition differs: {key}')
    if (manifest.get('seeds') != SEEDS or manifest.get('shard_size') != 5 or
            manifest.get('scoring') != {'paired_unit': 'seed_mean_of_four_mirror_assignment_branches',
                'min_difference': .1, 'interval': 'paired_percentile_bootstrap_95', 'bootstrap_samples': 10000,
                'bootstrap_seed': 20261106, 'requires_both_evaluations_and_bodies': True}):
        raise ValueError('held-out schedule or scoring differs')


def shard(manifest_path, shard_index, output, workers, resume=False):
    if type(shard_index) is not int or not 0 <= shard_index < 8 or not 1 <= workers <= 16:
        raise ValueError('invalid shard or worker count')
    manifest_bytes = manifest_path.read_bytes()
    initial_manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes)
    check_manifest(manifest)
    cases = output.with_suffix('.cases.jsonl')
    start_receipt = output.with_suffix('.start.json')
    if output.exists() or ((cases.exists() or start_receipt.exists()) and not resume):
        raise FileExistsError('shard exists; use resume only for an incomplete case file')
    subset = manifest['seeds'][shard_index * 5:(shard_index + 1) * 5]
    allowed = {key for key in expected_keys(manifest) if key[0] in subset}
    expected_start = {'schema': 'gene7-heldout-shard-start-v1', 'manifest_sha256': initial_manifest_hash,
                      'shard': shard_index, 'seeds': subset}
    output.parent.mkdir(parents=True, exist_ok=True)
    if resume:
        if not start_receipt.exists() or json.loads(start_receipt.read_text()) != expected_start:
            raise ValueError('shard start receipt does not match frozen manifest')
        if not cases.exists():
            cases.touch(exist_ok=False)
    else:
        with start_receipt.open('x') as stream:
            json.dump(expected_start, stream, indent=2, allow_nan=False)
            stream.write('\n')
    start_receipt_hash = digest_file(start_receipt)
    start = time.monotonic()
    cpu, peak, seen = 0.0, 0, set()
    resumed_count, pre_resume_sha256 = 0, None
    if resume:
        pre_resume_sha256 = digest_file(cases)
        with cases.open('rb') as stream:
            for line in stream:
                if not line.endswith(b'\n'):
                    raise ValueError('partial case line; preserve file and repair separately')
                row = json.loads(line)
                key = validate_row(row, manifest, allowed)
                if key in seen:
                    raise ValueError('duplicate retained case')
                seen.add(key)
                cpu += row['cpu_seconds']
                peak = max(peak, row['worker_peak_rss_kib_cumulative'])
        resumed_count = len(seen)
    jobs = [(manifest, *key) for key in sorted(allowed - seen)]
    with cases.open('a' if resume else 'x') as stream, ProcessPoolExecutor(max_workers=workers) as pool:
        iterator = iter(jobs)
        pending = {pool.submit(dev.case, next(iterator)) for _ in range(min(workers, len(jobs)))}
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                row = future.result()
                key = validate_row(row, manifest, allowed)
                if key in seen:
                    raise ValueError('duplicate result')
                stream.write(json.dumps(row, allow_nan=False) + '\n')
                stream.flush()
                seen.add(key)
                cpu += row['cpu_seconds']
                peak = max(peak, row['worker_peak_rss_kib_cumulative'])
                print(f'shard {shard_index}: {len(seen)}/{len(allowed)}', flush=True)
                try:
                    pending.add(pool.submit(dev.case, next(iterator)))
                except StopIteration:
                    pass
    if seen != allowed:
        raise ValueError('shard incomplete')
    check_manifest(manifest)
    if digest_file(manifest_path) != initial_manifest_hash:
        raise ValueError('manifest changed during shard')
    if digest_file(start_receipt) != start_receipt_hash:
        raise ValueError('shard start receipt changed')
    report = {'schema': 'gene7-heldout-shard-v1', 'manifest_sha256': initial_manifest_hash,
              'shard': shard_index, 'seeds': subset, 'cases': len(seen), 'case_file': str(cases.resolve()),
              'case_sha256': digest_file(cases), 'wall_seconds': time.monotonic()-start,
              'start_receipt': str(start_receipt.resolve()), 'start_receipt_sha256': start_receipt_hash,
              'resumed_existing_count': resumed_count, 'pre_resume_sha256': pre_resume_sha256,
              'summed_case_cpu_seconds': cpu, 'max_cumulative_worker_rss_kib': peak,
              'memory_scope': 'largest cumulative worker RSS; not process-family peak'}
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    f = commands.add_parser('freeze')
    f.add_argument('--development-manifest', required=True, type=Path)
    f.add_argument('--transfer', required=True, type=Path)
    f.add_argument('--reversal', required=True, type=Path)
    f.add_argument('--replay', required=True, type=Path)
    f.add_argument('--supporting-evidence', action='append', default=[], type=Path)
    f.add_argument('--output', required=True, type=Path)
    r = commands.add_parser('shard')
    r.add_argument('--manifest', required=True, type=Path)
    r.add_argument('--shard', required=True, type=int)
    r.add_argument('--output', required=True, type=Path)
    r.add_argument('--workers', type=int, default=12)
    r.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'freeze':
        freeze(args.development_manifest, {'transfer': args.transfer, 'reversal': args.reversal, 'replay': args.replay}, args.output,
               args.supporting_evidence)
    else:
        shard(args.manifest, args.shard, args.output, args.workers, args.resume)


if __name__ == '__main__':
    main()
