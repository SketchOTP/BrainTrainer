"""Pre-freeze and run the development-only in-contact tract-ablation protocol.

No evaluation can run until a complete matching lifecycle timing calibration has
qualified. This is not a whole-brain learning-disabled comparison.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import resource
import time

from creature_brain.benchmark.action_lifecycle import LifecycleFoodExperiment, LifecycleDriveCombFrozenExperiment
from creature_brain.benchmark.contract import ChosenAction, Outcome, attributed_adjustment
from creature_brain.benchmark.research_checkpoint import save_research_checkpoint, restore_research_checkpoint
from creature_brain.benchmark.retention_probe import probe_retained_choice

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = (2, 4, 8, 16, 32)
FILES = ('scripts/run_gene7_contact_development.py', 'scripts/calibrate_lifecycle_twenty_opportunities.py',
         'docs/FOOD_GENE7_CONTACT_PROTOCOL.md', 'src/creature_brain/benchmark/action_lifecycle.py',
         'src/creature_brain/benchmark/connection_freeze.py', 'src/creature_brain/benchmark/research_checkpoint.py',
         'src/creature_brain/benchmark/retention_probe.py',
         'src/creature_brain/benchmark/qualification.py', 'src/creature_brain/benchmark/food.py',
         'src/creature_brain/benchmark/contract.py', 'src/creature_brain/benchmark/embodiment.py',
         'src/creature_brain/neural.py', 'src/creature_brain/svrule.py',
         'src/creature_brain/genome.py', 'src/creature_brain/sensory.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def frozen_copy(value):
    return json.loads(json.dumps(value, allow_nan=False))


def source_digests():
    return {f: sha((ROOT / f).read_bytes()) for f in FILES}


def validate_calibration(cal, program):
    if (cal.get('seeds') != list(range(16)) or not cal.get('full_development_sample') or
            cal.get('budgets') != list(BUDGETS) or cal.get('opportunities_limit') != 20 or
            cal.get('program_sha256') != sha(program.read_bytes())):
        raise ValueError('calibration is incomplete or does not match the requested program')
    for name, digest in cal.get('source_sha256', {}).items():
        if not (ROOT / name).is_file() or sha((ROOT / name).read_bytes()) != digest:
            raise ValueError('calibration source differs: ' + name)
    required = {'scripts/calibrate_lifecycle_twenty_opportunities.py',
                'src/creature_brain/benchmark/action_lifecycle.py',
                'src/creature_brain/benchmark/connection_freeze.py'}
    if not required <= cal.get('source_sha256', {}).keys():
        raise ValueError('calibration is missing required source fingerprints')
    try:
        eligible = [budget for budget in BUDGETS if all(
            cal['metrics'][f'{budget}/{body}/{mirror}/{control}']['total'] == 16 and
            cal['metrics'][f'{budget}/{body}/{mirror}/{control}']['completed'] >= 13
            for body in ('walking', 'swimming') for mirror in (0, 1)
            for control in ('ordinary', 'gene7_frozen'))]
    except (KeyError, TypeError):
        raise ValueError('calibration cells are incomplete') from None
    if not eligible or cal.get('selected_budget') != min(eligible):
        raise ValueError('no qualified lifecycle budget')
    return min(eligible)


def freeze(program, calibration, destination):
    if destination.exists():
        raise FileExistsError('manifest already exists')
    program, calibration = program.resolve(), calibration.resolve()
    cal_bytes = calibration.read_bytes()
    budget = validate_calibration(json.loads(cal_bytes), program)
    manifest = {'schema': 'gene7-contact-development-v1', 'status': 'frozen',
                'scope': 'development-only gene-7 tract ablation; not global learning-disabled',
                'program': str(program), 'program_sha256': sha(program.read_bytes()),
                'calibration': str(calibration), 'calibration_sha256': sha(cal_bytes),
                'source_sha256': source_digests(), 'budget': budget, 'seeds': list(range(16)),
                'bodies': ['walking', 'swimming'], 'mirrors': [False, True], 'good_types': [0, 1],
                'controls': ['ordinary', 'gene7_frozen'], 'opportunities_per_phase': 20,
                'phases': ['experience', 'evaluation', 'reversal', 'reversal_evaluation'],
                'probe': {'energy': .5, 'hunger': .8, 'chemical_150': .8,
                          'pending_outcomes_cleared_in_probe_only': True},
                'checkpoint_after_opportunities': 40}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x') as f:
        json.dump(manifest, f, indent=2, allow_nan=False)
        f.write('\n')
    return manifest


def check_manifest(manifest):
    if manifest.get('schema') != 'gene7-contact-development-v1' or manifest.get('status') != 'frozen':
        raise ValueError('a frozen development manifest is required')
    program, calibration = Path(manifest['program']), Path(manifest['calibration'])
    if (manifest.get('source_sha256') != source_digests() or
            manifest.get('program_sha256') != sha(program.read_bytes()) or
            manifest.get('calibration_sha256') != sha(calibration.read_bytes())):
        raise ValueError('manifest inputs or source have changed')
    if (manifest.get('seeds') != list(range(16)) or manifest.get('bodies') != ['walking', 'swimming'] or
            manifest.get('mirrors') != [False, True] or manifest.get('good_types') != [0, 1] or
            manifest.get('controls') != ['ordinary', 'gene7_frozen'] or
            manifest.get('phases') != ['experience', 'evaluation', 'reversal', 'reversal_evaluation'] or
            manifest.get('opportunities_per_phase') != 20 or manifest.get('checkpoint_after_opportunities') != 40 or
            manifest.get('probe') != {'energy': .5, 'hunger': .8, 'chemical_150': .8,
                                      'pending_outcomes_cleared_in_probe_only': True}):
        raise ValueError('manifest parameters differ from the development protocol')
    if manifest.get('budget') != validate_calibration(json.loads(calibration.read_text()), program):
        raise ValueError('manifest budget does not match qualified calibration')


def tract_state(brain):
    return [{'gene_id': t.gene_id, 'source': t.source_lobe, 'destination': t.destination_lobe,
             'dendrites': [{'source': d.source, 'destination': d.destination, 'variables': d.variables.copy()}
                           for d in t.dendrites], 'weak': t.weak.copy(), 'helper': asdict(t.helper),
             'migrations': t.migrations} for t in brain.tracts]


def tract_delta(previous, current):
    result = []
    for old, new in zip(previous, current):
        changed = [{'index': i, 'value': v} for i, (before, v) in
                   enumerate(zip(old['dendrites'], new['dendrites'])) if before != v]
        meta = {k: new[k] for k in ('weak', 'helper', 'migrations') if old[k] != new[k]}
        if changed or meta:
            result.append({'gene_id': new['gene_id'], 'source': new['source'],
                           'destination': new['destination'], 'dendrites': changed, 'metadata': meta})
    return result


def probe_once(envelope, matched):
    exp = restore_research_checkpoint(frozen_copy(envelope))
    before = {'energy': exp.energy, 'hunger': exp.hunger, 'chemical_150': exp.brain.chemicals[150],
              'pending': frozen_copy(exp.pending)}
    result = probe_retained_choice(exp, match_needs=matched)
    result['brain_state_sha256'] = fingerprint(result.pop('brain_after'))
    result['prior_needs_and_pending'] = before
    return result


def attribution_checks():
    action = ChosenAction('a', 0, 12, 3, 4, 'object-0')
    return {'unrelated': attributed_adjustment(action, Outcome('b', 'object-0', 12, True, 'consumed', .2, -.25)) is None,
            'target_mismatch': attributed_adjustment(action, Outcome('a', 'object-1', 12, True, 'consumed', .2, -.25)) is None}


def case(args):
    manifest, seed, body, mirror, good, control = args
    cls = LifecycleDriveCombFrozenExperiment if control == 'gene7_frozen' else LifecycleFoodExperiment
    start, cpu = time.monotonic(), time.process_time()
    opportunities = manifest['opportunities_per_phase']
    exp = cls(manifest['program'], seed=seed, embodiment=body, condition='feedback', task='preference',
              mirror=mirror, max_steps=manifest['budget'], opportunities_per_phase=opportunities)
    exp.initial_good = good
    initial = frozen_copy(save_research_checkpoint(exp))
    initial_tracts = previous = tract_state(exp.brain)
    target_index = next(i for i, t in enumerate(initial_tracts) if (t['gene_id'], t['source'], t['destination']) == (7, 'driv', 'comb'))
    steps, probes, restored = [], {}, None
    checkpoint_equal = True
    while not exp.done:
        pending = frozen_copy(exp.pending)
        brain_inputs_before = {k: v.inputs.copy() for k, v in exp.brain.lobes.items()}
        event = exp.tick()
        current = tract_state(exp.brain)
        if control == 'gene7_frozen' and current[target_index] != initial_tracts[target_index]:
            raise RuntimeError('controlled gene-7 tract changed during a tick')
        steps.append({'event': event, 'pending_before': pending, 'queued_lobe_inputs_before': brain_inputs_before,
                      'chemicals_after': exp.brain.chemicals.copy(), 'rng_after': exp.brain._rng,
                      'tract_delta': tract_delta(previous, current)})
        previous = current
        if restored is not None:
            other = restored.tick()
            checkpoint_equal = checkpoint_equal and other == event
        if event['opportunity_end'] and exp.opportunity in (opportunities, 3 * opportunities):
            envelope = frozen_copy(save_research_checkpoint(exp))
            for matched in (False, True):
                first, second = probe_once(envelope, matched), probe_once(envelope, matched)
                if first != second:
                    raise RuntimeError('checkpointed probe did not reproduce')
                probes[f"{exp.opportunity}/{'matched' if matched else 'unmodified'}"] = first
            if frozen_copy(save_research_checkpoint(exp)) != envelope:
                raise RuntimeError('probe modified continuation')
        if event['opportunity_end'] and exp.opportunity == 2 * opportunities:
            restored = restore_research_checkpoint(frozen_copy(save_research_checkpoint(exp)))
    checkpoint_equal = checkpoint_equal and restored is not None and frozen_copy(exp.snapshot()) == frozen_copy(restored.snapshot())
    if not checkpoint_equal:
        raise RuntimeError('checkpoint continuation mismatch')
    fixed = initial_tracts[target_index] == previous[target_index]
    if control == 'gene7_frozen' and not fixed:
        raise RuntimeError('controlled gene-7 tract changed')
    return {'seed': seed, 'body': body, 'mirror': mirror, 'good': good, 'control': control,
            'initial_checkpoint': initial, 'initial_tracts': initial_tracts, 'steps': steps,
            'final_checkpoint': frozen_copy(save_research_checkpoint(exp)), 'probes': probes,
            'gene7_unchanged': fixed, 'checkpoint_continuation_equal': checkpoint_equal,
            'elapsed_seconds': time.monotonic()-start, 'cpu_seconds': time.process_time()-cpu,
            'worker_peak_rss_kib_cumulative': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def evaluate(manifest_path, output, workers):
    if workers < 1:
        raise ValueError('workers must be positive')
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    check_manifest(manifest)
    if not all(attribution_checks().values()):
        raise RuntimeError('outcome attribution checks failed')
    cases = output.with_suffix('.cases.jsonl')
    if output.exists() or cases.exists():
        raise FileExistsError('choose a new output')
    output.parent.mkdir(parents=True, exist_ok=True)
    jobs = [(manifest, seed, body, mirror, good, control)
            for seed in range(16) for body in manifest['bodies'] for mirror in manifest['mirrors']
            for good in manifest['good_types'] for control in manifest['controls']]
    pairs = defaultdict(dict)
    summaries = defaultdict(lambda: {'opportunities': 0, 'completed': 0, 'success': 0,
                                     'eat_ticks': 0, 'targets': Counter()})
    probe_summaries = defaultdict(Counter)
    seed_phase = defaultdict(lambda: defaultdict(list))
    started, count, cpu_total, peak = time.monotonic(), 0, 0.0, 0
    def aggregate(row):
        nonlocal count, cpu_total, peak
        count += 1
        cpu_total += row['cpu_seconds']
        peak = max(peak, row['worker_peak_rss_kib_cumulative'])
        key = (row['seed'], row['body'], row['mirror'], row['good'])
        pairs[key][row['control']] = {
            'brain': fingerprint(row['initial_checkpoint']['snapshot']['brain']),
            'observation': row['steps'][0]['event']['observation'], 'choice': row['steps'][0]['event']['choice']}
        phases = Counter()
        for name, probe in row['probes'].items():
            high = row['good'] ^ int(name.startswith('60/'))
            p = probe_summaries[f"{row['body']}/{row['control']}/{name}"]
            p['probes'] += 1
            p['eat'] += int(probe['action'] == 12)
            p['higher_target'] += int(probe['target'] == f'object-{high}')
            p['eat_and_higher_target'] += int(probe['action'] == 12 and probe['target'] == f'object-{high}')
        for step in row['steps']:
            e = step['event']
            s = summaries[f"{row['body']}/{row['control']}/{e['phase']}"]
            s['eat_ticks'] += int(e['choice']['action'] == 12)
            s['targets'][str(e['choice']['target'])] += 1
            if e['opportunity_end']:
                s['opportunities'] += 1
                s['completed'] += int(e['outcome']['completed'])
                s['success'] += int(e['success'])
                phases[e['phase']] += int(e['success'])
        for phase in manifest['phases']:
            seed_phase[(row['body'], row['seed'], phase)][row['control']].append(phases[phase]/20)
    with cases.open('x') as f, ProcessPoolExecutor(max_workers=workers) as pool:
        iterator = iter(jobs)
        pending = {pool.submit(case, job) for job in [next(iterator) for _ in range(min(workers, len(jobs)))]}
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                row = future.result()
                f.write(json.dumps(row, allow_nan=False) + '\n')
                f.flush()
                aggregate(row)
                print(f"{count}/{len(jobs)} {row['body']} {row['control']}", flush=True)
                try:
                    pending.add(pool.submit(case, next(iterator)))
                except StopIteration:
                    pass
    for key, pair in pairs.items():
        a, b = pair['ordinary'], pair['gene7_frozen']
        if a['brain'] != b['brain']:
            raise RuntimeError('paired initial brains differ')
        if a['observation'] != b['observation'] or a['choice'] != b['choice']:
            raise RuntimeError('paired initial observations or choices differ')
    differences = {f'{body}/{seed}/{phase}': sum(v['ordinary'])/4 - sum(v['gene7_frozen'])/4
                   for (body, seed, phase), v in seed_phase.items()}
    report = {'scope': manifest['scope'], 'manifest_sha256': sha(manifest_bytes), 'cases': count,
              'attribution_checks': attribution_checks(), 'all_paired_initial_states_match': True,
              'all_checkpoint_continuations_match': True, 'all_controlled_gene7_states_frozen': True,
              'summaries': dict(summaries), 'probe_summaries': dict(probe_summaries),
              'paired_seed_differences': differences,
              'wall_seconds': time.monotonic()-started, 'cpu_seconds': cpu_total,
              'max_cumulative_worker_rss_kib': peak}
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    f = commands.add_parser('freeze')
    f.add_argument('--program', required=True, type=Path)
    f.add_argument('--calibration', required=True, type=Path)
    f.add_argument('--manifest', required=True, type=Path)
    r = commands.add_parser('run')
    r.add_argument('--manifest', required=True, type=Path)
    r.add_argument('--output', required=True, type=Path)
    r.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.command == 'freeze':
        freeze(args.program, args.calibration, args.manifest)
    else:
        evaluate(args.manifest, args.output, args.workers)


if __name__ == '__main__':
    main()
