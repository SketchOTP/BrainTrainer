"""Analyze a *completed* frozen gene-7 development run, without modifying it.

Pairs are seed-level averages of the four mirror/assignment branches. This is
an exploratory tract ablation, not a whole-brain learning-disabled estimate.
"""
import argparse
from collections import Counter, defaultdict
import fileinput
import hashlib
import json
from pathlib import Path
import random


PHASES = ('experience', 'evaluation', 'reversal', 'reversal_evaluation')
BODIES = ('walking', 'swimming')
CONTROLS = ('ordinary', 'gene7_frozen')


def bootstrap(values, rng, count):
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(count))
    return [means[int((count - 1) * .025)], means[int((count - 1) * .975)]]


def analyze(manifest_path, report_path, cases_path, samples=10000, bootstrap_seed=20261106, recovery_report_path=None):
    if samples < 100:
        raise ValueError('bootstrap requires at least 100 resamples')
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    paths = [cases_path] if isinstance(cases_path, Path) else list(cases_path)
    report = json.loads(report_path.read_text()) if report_path else None
    if report is not None and (report.get('manifest_sha256') != hashlib.sha256(manifest_bytes).hexdigest()
            or report.get('cases') != 256 or not report.get('all_paired_initial_states_match')
            or not report.get('all_checkpoint_continuations_match') or not report.get('all_controlled_gene7_states_frozen')):
        raise ValueError('complete matching development report required')
    if report is None and (len(paths) != 2 or recovery_report_path is None):
        raise ValueError('recovery analysis requires original and recovery case files and recovery report')
    recovery = json.loads(recovery_report_path.read_text()) if recovery_report_path else None
    if recovery is not None and recovery.get('manifest_sha256') != hashlib.sha256(manifest_bytes).hexdigest():
        raise ValueError('recovery manifest digest mismatch')
    if (manifest.get('schema') != 'gene7-contact-development-v1'
            or manifest.get('seeds') != list(range(16))
            or manifest.get('opportunities_per_phase') != 20
            or manifest.get('phases') != list(PHASES)):
        raise ValueError('unsupported manifest protocol')
    expected = {(s, b, m, g, c) for s in range(16) for b in BODIES
                for m in (False, True) for g in (0, 1) for c in CONTROLS}
    seen = set()
    values = defaultdict(list)
    initial_pairs = defaultdict(dict)
    digests = {str(path): hashlib.sha256() for path in paths}
    counts = Counter()
    source_keys = defaultdict(set)
    probe_counts, totals = defaultdict(Counter), defaultdict(Counter)
    cpu_seconds, peak_worker_rss = 0.0, 0
    with fileinput.input(files=[str(path) for path in paths], mode='rb') as stream:
        for line in stream:
            name = stream.filename()
            digests[name].update(line)
            counts[name] += 1
            if not line.endswith(b'\n'):
                raise ValueError('incomplete source line')
            row = json.loads(line)
            cpu_seconds += row['cpu_seconds']
            peak_worker_rss = max(peak_worker_rss, row['worker_peak_rss_kib_cumulative'])
            key = (row['seed'], row['body'], row['mirror'], row['good'], row['control'])
            if key not in expected or key in seen or not row.get('checkpoint_continuation_equal'):
                raise ValueError('unexpected, duplicated or invalid case: ' + repr(key))
            if row['control'] == 'gene7_frozen' and not row.get('gene7_unchanged'):
                raise ValueError('gene-7 control did not remain frozen')
            seen.add(key)
            source_keys[name].add(key)
            tract_indices = [i for i, t in enumerate(row['initial_tracts'])
                             if (t['gene_id'], t['source'], t['destination']) == (7, 'driv', 'comb')]
            if len(tract_indices) != 1:
                raise ValueError('cannot identify unique gene-7 tract')
            idx = tract_indices[0]
            original = row['initial_tracts'][idx]
            initial = row['initial_checkpoint']['snapshot']['brain']['tracts'][idx]
            final = row['final_checkpoint']['snapshot']['brain']['tracts'][idx]
            if initial['gene_id'] != 7 or final['gene_id'] != 7:
                raise ValueError('final tract identity changed')
            if any(original[k] != initial[k] for k in ('dendrites','weak','helper','migrations')):
                raise ValueError('initial tract inventory does not match checkpoint')
            if row['control'] == 'gene7_frozen' and any(original[k] != final[k] for k in ('dendrites','weak','helper','migrations')):
                raise ValueError('gene-7 initial and final tract state differ')
            for name_, probe in row['probes'].items():
                high = row['good'] ^ int(name_.startswith('60/'))
                p = probe_counts[f"{row['body']}/{row['control']}/{name_}"]
                p['probes'] += 1
                p['eat'] += int(probe['action'] == 12)
                p['higher_target'] += int(probe['target'] == f'object-{high}')
                p['eat_and_higher_target'] += int(probe['action'] == 12 and probe['target'] == f'object-{high}')
            snapshot = row['initial_checkpoint']['snapshot'].copy()
            marker = snapshot.pop('qualification_control', None)
            if marker != ('drive-comb-tract-state-frozen-v1' if row['control'] == 'gene7_frozen' else None):
                raise ValueError('initial control marker mismatch')
            canonical = json.dumps(snapshot, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
            initial_pairs[key[:-1]][row['control']] = hashlib.sha256(canonical).hexdigest()
            ended = set()
            for step in row['steps']:
                e = step['event']
                if row['control'] == 'gene7_frozen' and any((v['gene_id'], v['source'], v['destination']) == (7,'driv','comb') for v in step['tract_delta']):
                    raise ValueError('recorded gene-7 state changed during frozen case')
                t = totals[f"{row['body']}/{row['control']}/{e['phase']}"]
                t['steps'] += 1
                t['eat_ticks'] += int(e['choice']['action'] == 12)
                if not e['opportunity_end']:
                    continue
                t['opportunities'] += 1
                t['completed'] += int(e['outcome']['completed'])
                t['success'] += int(e['success'])
                op = e['opportunity']
                phase = PHASES[op // 20] if type(op) is int and 0 <= op < 80 else None
                if phase != e['phase'] or op in ended:
                    raise ValueError('invalid phase or duplicate opportunity')
                ended.add(op)
                k = (row['body'], row['seed'], row['control'], phase, op % 20)
                values[k].append((int(bool(e['success'])), int(bool(e['outcome']['completed']))))
            if ended != set(range(80)):
                raise ValueError('incomplete opportunities: ' + repr(key))
    if seen != expected:
        raise ValueError(f'incomplete cases: found {len(seen)} of {len(expected)}')
    if report is None and [counts[str(p)] for p in paths] != [237,19]:
        raise ValueError('recovery input counts differ from recorded interruption')
    if recovery is not None and (len(paths) != 2 or recovery.get('original_cases_count') != counts[str(paths[0])]
            or recovery.get('recovered_count') != counts[str(paths[1])]
            or recovery.get('original_cases_sha256') != digests[str(paths[0])].hexdigest()
            or recovery.get('recovery_cases_sha256') != digests[str(paths[1])].hexdigest()
            or {tuple(key) for key in recovery.get('recovered_keys', [])} != source_keys[str(paths[1])]):
        raise ValueError('recovery metadata does not match case files')
    if any(pair.get('ordinary') != pair.get('gene7_frozen') for pair in initial_pairs.values()):
        raise ValueError('paired complete initial snapshots differ beyond the control marker')
    rng = random.Random(bootstrap_seed)
    curves, phases = {}, {}
    for body in BODIES:
        for phase in PHASES:
            differences, ordinary, frozen = [], [], []
            success_by_seed = {s: [] for s in range(16)}
            for i in range(20):
                cell = {}
                for metric_index, metric in enumerate(('success', 'completion')):
                    estimates = {}
                    for control in CONTROLS:
                        by_seed = []
                        for seed in range(16):
                            branch_values = values[(body, seed, control, phase, i)]
                            if len(branch_values) != 4:
                                raise ValueError('missing counterbalanced branch')
                            by_seed.append(sum(v[metric_index] for v in branch_values) / 4)
                        estimates[control] = by_seed
                    diff = [x-y for x, y in zip(estimates['ordinary'], estimates['gene7_frozen'])]
                    cell[metric] = {'ordinary': sum(estimates['ordinary']) / 16,
                                    'gene7_frozen': sum(estimates['gene7_frozen']) / 16,
                                    'paired_difference': sum(diff) / 16,
                                    'paired_95pct_bootstrap_interval': bootstrap(diff, rng, samples)}
                    if metric == 'success':
                        for seed in range(16):
                            success_by_seed[seed].append((estimates['ordinary'][seed], estimates['gene7_frozen'][seed]))
                curves[f'{body}/{phase}/{i + 1}'] = cell
            for seed in range(16):
                a = sum(x for x, _ in success_by_seed[seed]) / 20
                b = sum(y for _, y in success_by_seed[seed]) / 20
                ordinary.append(a); frozen.append(b); differences.append(a-b)
            phases[f'{body}/{phase}'] = {'ordinary_success': sum(ordinary)/16,
                'gene7_frozen_success': sum(frozen)/16, 'paired_difference': sum(differences)/16,
                'paired_95pct_bootstrap_interval': bootstrap(differences, rng, samples),
                'seed_differences': differences, 'min_seed_difference': min(differences),
                'max_seed_difference': max(differences)}
    return {'scope': 'exploratory development gene-7 tract ablation; not a global learning-disabled control or causal proof of preference',
            'cases': len(seen), 'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
            'case_sources': [{'path': str(p), 'cases': counts[str(p)], 'sha256': digests[str(p)].hexdigest()} for p in paths],
            'recovered_after_interruption': report is None,
            'recovery_report_sha256': hashlib.sha256(recovery_report_path.read_bytes()).hexdigest() if recovery else None,
            'initial_checkpoint_comparison': 'complete initial snapshot excluding expected control marker',
            'gene7_check': 'recorded per-step deltas and initial/final tract state independently checked',
            'checkpoint_continuation': 'all producer per-case continuation checks passed; not independently replayed',
            'resources': {'summed_case_cpu_seconds': cpu_seconds, 'max_cumulative_worker_peak_rss_kib': peak_worker_rss,
                          'wall_seconds': None, 'memory_scope': 'maximum cumulative per-worker RSS; not process-family peak'},
            'totals': dict(totals), 'probe_summaries': dict(probe_counts),
            'bootstrap': {'unit': 'paired seed, after averaging four mirror/assignment branches',
                          'samples': samples, 'random_seed': bootstrap_seed, 'interval': 'percentile 95%'},
            'curves': curves, 'phase_summaries': phases,
            'limitations': ['Development seeds informed the design; intervals are descriptive.',
                'Ordinary and frozen conditions can differ in retained neuron and other tract state.',
                'The interrupted producer had no completed report binding its original raw cases; recovery metadata records post-interruption original and recovery digests.',
                'Later observations and outcomes diverge; this does not isolate preference from transient feedback or initial bias.',
                'Success includes all non-completions in the denominator.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--report', type=Path)
    p.add_argument('--recovery-report', type=Path)
    p.add_argument('--cases', type=Path, required=True, action='append', help='repeat for original and recovery cases')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--samples', type=int, default=10000)
    p.add_argument('--seed', type=int, default=20261106)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError('choose a new output')
    result = analyze(a.manifest, a.report, a.cases, a.samples, a.seed, a.recovery_report)
    with a.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')


if __name__ == '__main__':
    main()
