"""Independent arithmetic and retained-record audit for the frozen recall panel."""
import argparse
from collections import defaultdict
import hashlib
import json
from math import comb
from pathlib import Path


def analyze(folder):
    manifest = json.loads((folder/'manifest.json').read_text())
    for name, expected in manifest['source_sha256'].items():
        assert hashlib.sha256((folder/'source'/name).read_bytes()).hexdigest() == expected, name
    records = [json.loads(line) for line in (folder/'cases.jsonl').read_text().splitlines()]
    assert {(r['seed'],r['good_type']) for r in records} == {(s,g) for s in range(16,24) for g in (0,1)}
    assert len(records) == 16
    seeds = defaultdict(list)
    successes = defaultdict(int)
    harmful = defaultdict(int)
    hunger_changes = defaultdict(list)
    costs = defaultdict(list)
    case_results = []
    for case in records:
        assert case['mirror'] == bool(case['seed'] % 2)
        acquired = json.loads((folder/f"{case['case_id']}-acquired.json").read_text())
        acquired_host = acquired['host']['state']
        start_hunger = acquired_host['individual']['hunger']
        start_reserve = acquired_host['reserve']
        per_case = {}
        for name, branch in case['branches'].items():
            events = branch['events']
            assert len(events) == 24
            final = json.loads((folder/f"{case['case_id']}-{name}.json").read_text())
            assert final['events'][:len(acquired['events'])] == acquired['events']
            experiences = [e['payload'] for e in final['events'][len(acquired['events']):] if e['kind']=='experience']
            assert [{k:v for k,v in e.items() if k!='intention'} for e in experiences] == events
            first = next((e['outcome'] for e in events if e['outcome']['completed']), None)
            good = f"object-{case['good_type']}"
            score = int(first is not None and first['target'] == good)
            successes[name] += score
            per_case[name] = score
            bad = sum(e['outcome']['completed'] and e['outcome']['target'] != good for e in events)
            harmful[name] += bad
            finish = final['host']['state']
            actual_change = finish['individual']['hunger'] - start_hunger
            actual_cost = start_reserve - finish['reserve']
            assert branch['hunger_before'] == start_hunger
            assert branch['hunger_after'] == finish['individual']['hunger']
            assert abs(branch['reserve_spent'] - actual_cost) < 1e-12
            hunger_changes[name].append(actual_change)
            costs[name].append(actual_cost)
            for e in events:
                if e['outcome']['completed']:
                    a,o=e['executed_action'],e['outcome']
                    assert (a['id'],a['target'],a['action']) == (o['action_id'],o['target'],o['action'])
            cue = branch['initial_intention']
            if name == 'recall' and cue is not None:
                evidence = acquired['events'][cue['evidence_event']]
                assert evidence['kind'] == 'experience'
                assert evidence['payload']['outcome']['completed']
                assert evidence['payload']['outcome']['hunger_adjustment'] < 0
        delta=per_case['recall']-per_case['passive']
        seeds[case['seed']].append(delta)
        case_results.append({'seed':case['seed'],'good_type':case['good_type'],
                             'first_helpful':per_case,'paired_difference':delta})
    means = {s:sum(values)/len(values) for s,values in seeds.items()}
    positive = sum(v > 0 for v in means.values())
    negative = sum(v < 0 for v in means.values())
    n = positive + negative
    p = sum(comb(n,k) for k in range(positive,n+1))/2**n if n else 1.
    mean_difference = sum(means.values())/len(means)
    return {'cases':len(records),'seeds':len(seeds),'first_helpful':dict(successes),
            'mean_paired_difference':mean_difference,'positive_seeds':positive,'negative_seeds':negative,
            'tied_seeds':len(seeds)-n,'one_sided_sign_probability':p,
            'gate_passed':successes['recall']>=12 and mean_difference>0 and p<=.05,
            'harmful_consumptions':dict(harmful),
            'mean_actual_hunger_change':{k:sum(v)/len(v) for k,v in hunger_changes.items()},
            'mean_reserve_spent':{k:sum(v)/len(v) for k,v in costs.items()},
            'acquisition_completed':sum(a['completed'] for c in records for a in c['acquisition']),
            'acquisition_offers':sum(len(c['acquisition']) for c in records),
            'case_results':case_results,
            'cases_sha256':hashlib.sha256((folder/'cases.jsonl').read_bytes()).hexdigest(),
            'scope':'bounded first-helpful-interaction endpoint; not general learning or harm avoidance'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    args=parser.parse_args()
    result=analyze(args.folder)
    with (args.folder/'independent-audit.json').open('x') as out:
        json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='case_results'},indent=2))


if __name__=='__main__':main()
