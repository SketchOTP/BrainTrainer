"""Analyze all frozen held-out shards with the predeclared seed-level test."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_gene7_heldout as heldout
from recover_gene7_contact_development import expected_keys, validate_row


def bootstrap(values, rng, count):
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(count))
    return [means[int((count - 1)*.025)], means[int((count - 1)*.975)]]


def analyze(manifest_path, reports, output):
    if output.exists():
        raise FileExistsError('choose new analysis output')
    manifest = json.loads(manifest_path.read_text())
    heldout.check_manifest(manifest)
    if len(reports) != 8:
        raise ValueError('all eight completed shards required')
    allowed, seen, shards = expected_keys(manifest), set(), set()
    pairs, values = defaultdict(dict), defaultdict(dict)
    totals, probes = defaultdict(Counter), defaultdict(Counter)
    cpu, peak = 0.0, 0
    sources = []
    for report_path in reports:
        report = json.loads(report_path.read_text())
        index = report['shard']
        if (report['schema'] != 'gene7-heldout-shard-v1' or index in shards or index not in range(8) or
                report['manifest_sha256'] != heldout.digest_file(manifest_path) or
                report['seeds'] != manifest['seeds'][index*5:(index+1)*5] or report['cases'] != 80):
            raise ValueError('invalid or duplicate shard')
        shards.add(index)
        start_path = Path(report['start_receipt'])
        start = json.loads(start_path.read_text())
        if (heldout.digest_file(start_path) != report['start_receipt_sha256'] or
                start != {'schema': 'gene7-heldout-shard-start-v1',
                          'manifest_sha256': report['manifest_sha256'],
                          'shard': index, 'seeds': report['seeds']}):
            raise ValueError('shard start receipt mismatch')
        path = Path(report['case_file'])
        if heldout.digest_file(path) != report['case_sha256']:
            raise ValueError('shard case digest mismatch')
        source_count = 0
        with path.open('rb') as stream:
            for line in stream:
                if not line.endswith(b'\n'):
                    raise ValueError('incomplete case line')
                row = json.loads(line)
                key = validate_row(row, manifest, allowed)
                if key in seen or key[0] not in report['seeds']:
                    raise ValueError('duplicate or misplaced case')
                seen.add(key)
                source_count += 1
                cpu += row['cpu_seconds']
                peak = max(peak, row['worker_peak_rss_kib_cumulative'])
                initial = row['initial_checkpoint']['snapshot'].copy()
                marker = initial.pop('qualification_control', None)
                if marker != ('drive-comb-tract-state-frozen-v1' if row['control'] == 'gene7_frozen' else None):
                    raise ValueError('control marker mismatch')
                encoded = json.dumps(initial, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
                pairs[key[:-1]][row['control']] = hashlib.sha256(encoded).hexdigest()
                for name, probe in row['probes'].items():
                    higher = row['good'] ^ int(name.startswith('60/'))
                    p = probes[f"{row['body']}/{row['control']}/{name}"]
                    p['probes'] += 1
                    p['higher_target'] += int(probe['target'] == f'object-{higher}')
                    p['eat_and_higher_target'] += int(probe['action'] == 12 and probe['target'] == f'object-{higher}')
                ended = set()
                for step in row['steps']:
                    event = step['event']
                    op = event['opportunity']
                    if type(op) is not int or not 0 <= op < 80 or event['phase'] != manifest['phases'][op // 20]:
                        raise ValueError('opportunity phase does not match manifest')
                    cell = totals[f"{row['body']}/{row['control']}/{event['phase']}"]
                    cell['steps'] += 1
                    cell['eat_ticks'] += int(event['choice']['action'] == 12)
                    cell['action_' + str(event['choice']['action'])] += 1
                    cell['attention_' + str(event['choice']['attention'])] += 1
                    cell['target_' + str(event['choice']['target'])] += 1
                    if event['opportunity_end']:
                        if op in ended:
                            raise ValueError('duplicate completed opportunity')
                        ended.add(op)
                        cell['opportunities'] += 1
                        cell['completed'] += int(event['outcome']['completed'])
                        cell['success'] += int(event['success'])
                        cell['higher_completed'] += int(event['success'])
                        k = (row['body'], row['seed'], row['control'], event['phase'], event['opportunity'] % 20)
                        branch = (row['mirror'], row['good'])
                        if branch in values[k]:
                            raise ValueError('duplicate opportunity')
                        values[k][branch] = (int(event['success']), int(event['outcome']['completed']))
                if ended != set(range(80)):
                    raise ValueError('incomplete opportunity history')
        if source_count != 80:
            raise ValueError('wrong shard case count')
        sources.append({'report': str(report_path), 'report_sha256': heldout.digest_file(report_path),
                        'case_file': str(path), 'case_sha256': report['case_sha256']})
    if seen != allowed or shards != set(range(8)):
        raise ValueError('incomplete held-out set')
    if any(set(pair) != {'ordinary', 'gene7_frozen'} or pair['ordinary'] != pair['gene7_frozen'] for pair in pairs.values()):
        raise ValueError('paired complete initial states differ')
    rng = random.Random(manifest['scoring']['bootstrap_seed'])
    curves, phases = {}, {}
    for body in manifest['bodies']:
        for phase in manifest['phases']:
            estimates = {control: [] for control in manifest['controls']}
            for seed in manifest['seeds']:
                for control in manifest['controls']:
                    nums = []
                    for opportunity in range(20):
                        branch = values[(body, seed, control, phase, opportunity)]
                        if set(branch) != {(m, g) for m in (False, True) for g in (0, 1)}:
                            raise ValueError('missing counterbalanced opportunity')
                        nums.append(Fraction(sum(v[0] for v in branch.values()), 4))
                    estimates[control].append(sum(nums)/20)
            differences = [a-b for a, b in zip(estimates['ordinary'], estimates['gene7_frozen'])]
            interval = bootstrap([float(v) for v in differences], rng, manifest['scoring']['bootstrap_samples'])
            difference = sum(differences)/len(differences)
            phases[f'{body}/{phase}'] = {'ordinary_success': float(sum(estimates['ordinary'])/40),
                'gene7_frozen_success': float(sum(estimates['gene7_frozen'])/40),
                'paired_difference': float(difference), 'paired_95pct_bootstrap_interval': interval,
                'seed_differences': [float(v) for v in differences],
                'meets_target': difference >= Fraction(1, 10) and interval[0] > 0}
            for i in range(20):
                curves[f'{body}/{phase}/{i+1}'] = {control: sum(
                    sum(x[0] for x in values[(body, seed, control, phase, i)].values())/4
                    for seed in manifest['seeds'])/40 for control in manifest['controls']}
    for cell in totals.values():
        cell['non_completion'] = cell['opportunities'] - cell['completed']
        cell['conditional_higher_value_rate'] = cell['success'] / cell['completed'] if cell['completed'] else None
    result = {'schema': 'gene7-heldout-analysis-v1', 'manifest_sha256': heldout.digest_file(manifest_path),
              'cases': len(seen), 'sources': sources, 'all_full_initial_pairs_match': True,
              'producer_checkpoint_continuations_match': True, 'recorded_gene7_state_fixed': True,
              'totals': dict(totals), 'probe_summaries': dict(probes), 'phase_summaries': phases,
              'learning_curves': curves,
              'overall_target_met': all(phases[f'{body}/{phase}']['meets_target']
                  for body in manifest['bodies'] for phase in ('evaluation', 'reversal_evaluation')),
              'summed_case_cpu_seconds': cpu, 'max_cumulative_worker_rss_kib': peak,
              'memory_scope': 'largest cumulative worker RSS; not process-family peak',
              'limitations': ['Scoped persistent tract ablation, not global learning-disabled.',
                  'Experimental interruption rule is not verified against native brain-selected action changes.',
                  'Checkpoint continuation is checked by the producer; not independently replayed for every held-out case.',
                  'Matched-needs probes leave other retained neural activity intact.']}
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--shard-report', action='append', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    analyze(args.manifest, args.shard_report, args.output)


if __name__ == '__main__':
    main()
