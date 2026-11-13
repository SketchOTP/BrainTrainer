"""Bounded development panel; see docs/OUTCOME_RECALL_DEVELOPMENT.md."""
import argparse
import json
from pathlib import Path
from continuing_companion import ContinuingCompanion, canonical


def run(seed, program, folder, *, good_type=0, mirror=False):
    case_id = f'seed-{seed}-good-{good_type}'
    c = ContinuingCompanion(program, seed=seed, good_type=good_type)
    sign = -1 if mirror else 1
    c.place('toy', 0, actor='development-runner', visible=False)
    acquisition = []
    for offer in range(6):
        target = f'object-{offer % 2}'
        c.place(f'object-{1-offer % 2}', 0, actor='development-runner', visible=False)
        c.place(target, c._host.position + sign * (.5 if offer % 2 == 0 else -.5),
                actor='companion-person' if offer % 2 == 0 else 'other-person')
        outcomes = []
        for _ in range(32):
            event = c.tick()
            outcomes.append(event['outcome'])
            if event['outcome']['completed']:
                break
        acquisition.append({'offer': offer, 'target': target, 'ticks': len(outcomes),
                            'completed': outcomes[-1]['completed'], 'outcome': outcomes[-1]})
    c.place('object-0', c._host.position + sign * .5, actor='evaluation-runner')
    c.place('object-1', c._host.position - sign * .5, actor='evaluation-runner')
    c.save(folder/f'{case_id}-acquired.json')
    before = {'hunger': c._host.hunger, 'reserve': c._host.reserve}
    branches = {}
    for name in ('passive', 'recall'):
        child = c.fork(purpose=f'{name} memory-path development comparison')
        if name == 'recall':
            child.enable_recall(actor='development-runner')
        initial = child.intention()
        events = [child.tick() for _ in range(24)]
        child.save(folder/f'{case_id}-{name}.json')
        branches[name] = {'initial_intention': initial, 'events': events,
                         'hunger_before': before['hunger'], 'hunger_after':child._host.hunger,
                         'reserve_spent': before['reserve'] - child._host.reserve,
                         'completed': sum(e['outcome']['completed'] for e in events),
                         'total_hunger_adjustment': sum(e['outcome']['hunger_adjustment'] for e in events)}
    different = [i for i,(a,b) in enumerate(zip(branches['passive']['events'], branches['recall']['events']))
                 if a['choice'] != b['choice']]
    return {'seed': seed, 'good_type': good_type, 'mirror':mirror, 'case_id':case_id, 'acquisition': acquisition, 'branches': branches,
            'different_choice_ticks': different,
            'scope': 'bounded paired memory-path comparison, not whole-brain learning-disabled control'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--prospective', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    program = Path(__file__).resolve().parents[2]/'research/docking-station-20261103/resources/chichi-brain-program.json'
    import hashlib, shutil
    root = Path(__file__).resolve().parents[2]
    sources = list((root/'examples/persistent_individual').glob('*.py')) + list((root/'src/creature_brain').rglob('*.py'))
    sources += [root/'docs/OUTCOME_RECALL_PROSPECTIVE.md', root/'docs/OUTCOME_RECALL_DEVELOPMENT.md']
    hashes = {}
    for source in sources:
        relative = source.relative_to(root)
        target = args.output/'source'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        hashes[str(relative)] = hashlib.sha256(target.read_bytes()).hexdigest()
    (args.output/'manifest.json').write_text(json.dumps({'prospective':args.prospective,
        'seeds':list(range(16,24)) if args.prospective else list(range(4)),
        'source_sha256':hashes,'program_sha256':hashlib.sha256(program.read_bytes()).hexdigest()},indent=2)+'\n')
    cases = [(seed, good, bool(seed % 2)) for seed in range(16,24) for good in (0,1)] if args.prospective else [(seed,0,False) for seed in range(4)]
    with (args.output/'cases.jsonl').open('x') as out:
        for seed, good, mirror in cases:
            result = run(seed, program, args.output, good_type=good, mirror=mirror)
            out.write(canonical(result)+'\n'); out.flush()
            print(json.dumps({'seed': seed, 'good_type': good, 'acquisition_completions':sum(x['completed'] for x in result['acquisition']),
                              'different_choice_ticks':len(result['different_choice_ticks']),
                              'initial_intention':result['branches']['recall']['initial_intention']}), flush=True)


if __name__ == '__main__':
    main()
