"""Reversal development diagnostics from the preserved/recovered raw cases.

Descriptive temporal co-occurrence, not proof that a signal caused a weight
change or that a connection stores value. Reads one case at a time.
"""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / 'runs/food-qualification/gene7-contact-development-v1-recovered-analysis.json'
OUTPUT = ROOT / 'runs/food-qualification/gene7-reversal-diagnostics-v1.json'


def snapshot(tract, old_comb, new_comb):
    d = tract['dendrites']
    def group(target):
        selected = [x for x in d if x['source'] == 2 and x['destination'] == target]
        return {'count': len(selected), 'weight0_sum': sum(x['variables'][0] for x in selected),
                'weight1_sum': sum(x['variables'][1] for x in selected)}
    return {'old_food_eat': group(old_comb), 'new_food_eat': group(new_comb)}


def analyze_case(row):
    old, new = row['good'], 1-row['good']
    old_target, new_target = f'object-{old}', f'object-{new}'
    attention = next(t for t in row['initial_tracts'] if (t['source'], t['destination']) == ('comb', 'attn'))
    decision = next(t for t in row['initial_tracts'] if (t['source'], t['destination']) == ('comb', 'decn'))
    eat_comb = {d['source'] for d in decision['dendrites'] if d['destination'] == 4}
    by_category = {category: {d['source'] for d in attention['dendrites'] if d['destination'] == category} & eat_comb
                   for category in (3, 8)}
    if any(len(x) != 1 for x in by_category.values()):
        raise ValueError('food/eat combination mapping is ambiguous')
    targets = [next(iter(by_category[3])), next(iter(by_category[8]))]
    tract = next(t for t in row['initial_tracts'] if (t['gene_id'],t['source'],t['destination']) == (7,'driv','comb'))
    tract = json.loads(json.dumps(tract))
    r = {'seed': row['seed'], 'body': row['body'], 'mirror': row['mirror'], 'good': old,
         'control': row['control'], 'first_new_eat_opportunity': None,
         'first_new_consumption_opportunity': None, 'first_new_feedback_opportunity': None,
         'first_success_after_new_feedback_opportunity': None,
         'reversal_opportunities': 0, 'new_eat_requests': 0, 'old_eat_requests': 0,
         'new_consumptions': 0, 'old_consumptions': 0, 'new_feedback_events': 0, 'old_feedback_events': 0,
         'new_feedback_ticks_gene7_delta': 0, 'old_feedback_ticks_gene7_delta': 0,
         'new_feedback_ticks_dendrite_delta': 0, 'old_feedback_ticks_dendrite_delta': 0,
         'migration_events': 0, 'weight0_increases': 0, 'weight0_decreases': 0,
         'ticks_with_gene7_delta': 0, 'snapshots': {}, 'first_reversal_success': False}
    feedback_occured = False
    for step in row['steps']:
        event = step['event']; op = event['opportunity']; phase = event['phase']
        reversal = phase == 'reversal'
        gene7 = next((v for v in step['tract_delta'] if (v['gene_id'],v['source'],v['destination']) ==
                      (7,'driv','comb')), None)
        if reversal:
            choice, outcome = event['choice'], event['outcome']
            if choice['action'] == 12 and choice['target'] == new_target:
                r['new_eat_requests'] += 1
                if r['first_new_eat_opportunity'] is None:r['first_new_eat_opportunity'] = op-40
            if choice['action'] == 12 and choice['target'] == old_target:r['old_eat_requests'] += 1
            if outcome['completed']:
                if outcome['target'] == new_target:
                    r['new_consumptions'] += 1
                    if r['first_new_consumption_opportunity'] is None:r['first_new_consumption_opportunity'] = op-40
                elif outcome['target'] == old_target:r['old_consumptions'] += 1
            for pending in step['pending_before']:
                # Target and outcome source are explicit; the adapter routes this
                # pending response in this tick. Its neuron effect is not recorded.
                if pending['target'] == new_target and pending['hunger_adjustment'] < 0:
                    r['new_feedback_events'] += 1
                    if gene7 is not None:r['new_feedback_ticks_gene7_delta'] += 1
                    if gene7 is not None and gene7['dendrites']:r['new_feedback_ticks_dendrite_delta'] += 1
                    if r['first_new_feedback_opportunity'] is None:r['first_new_feedback_opportunity'] = op-40
                    feedback_occured = True
                elif pending['target'] == old_target and pending['hunger_adjustment'] > 0:
                    r['old_feedback_events'] += 1
                    if gene7 is not None:r['old_feedback_ticks_gene7_delta'] += 1
                    if gene7 is not None and gene7['dendrites']:r['old_feedback_ticks_dendrite_delta'] += 1
            if event['opportunity_end']:
                r['reversal_opportunities'] += 1
                if op == 40:r['first_reversal_success'] = bool(event['success'])
                if feedback_occured and event['success'] and r['first_new_feedback_opportunity'] is not None and op-40 > r['first_new_feedback_opportunity']:
                    if r['first_success_after_new_feedback_opportunity'] is None:r['first_success_after_new_feedback_opportunity'] = op-40
            if gene7 is not None:r['ticks_with_gene7_delta'] += 1
        if gene7:
            for item in gene7['dendrites']:
                previous=tract['dendrites'][item['index']]; current=item['value']
                if reversal:
                    r['migration_events'] += int((previous['source'],previous['destination']) != (current['source'],current['destination']))
                    if previous['variables'][0] < current['variables'][0]:r['weight0_increases'] += 1
                    elif previous['variables'][0] > current['variables'][0]:r['weight0_decreases'] += 1
                tract['dendrites'][item['index']] = current
            tract.update(gene7['metadata'])
        if event['opportunity_end'] and op in (39,59,79):
            r['snapshots'][str(op+1)] = snapshot(tract,targets[old],targets[new])
    if r['reversal_opportunities'] != 20 or set(r['snapshots']) != {'40','60','80'}:
        raise ValueError('incomplete reversal or missing snapshots')
    return r


def main():
    if OUTPUT.exists():raise FileExistsError(OUTPUT)
    reference=json.loads(ANALYSIS.read_text());cases=[];keys=set();source_hashes=[]
    for source in reference['case_sources']:
        path=ROOT/source['path']; sha=hashlib.sha256();count=0
        with path.open('rb') as stream:
            for line in stream:
                sha.update(line);row=json.loads(line);item=analyze_case(row)
                key=tuple(item[k] for k in ('seed','body','mirror','good','control'))
                if key in keys:raise ValueError('duplicate case')
                keys.add(key);cases.append(item);count+=1
        if sha.hexdigest()!=source['sha256'] or count!=source['cases']:raise ValueError('case source mismatch')
        source_hashes.append({'path':source['path'],'sha256':sha.hexdigest(),'cases':count})
    if len(cases)!=256:raise ValueError('expected 256 cases')
    groups={}
    for body in ('walking','swimming'):
      for control in ('ordinary','gene7_frozen'):
        rs=[r for r in cases if r['body']==body and r['control']==control]
        sums=Counter()
        for r in rs:
            sums['cases']+=1
            for field in ('new_eat_requests','old_eat_requests','new_consumptions','old_consumptions',
                          'new_feedback_events','old_feedback_events','new_feedback_ticks_gene7_delta',
                          'old_feedback_ticks_gene7_delta','new_feedback_ticks_dendrite_delta',
                          'old_feedback_ticks_dendrite_delta','migration_events','weight0_increases','weight0_decreases',
                          'ticks_with_gene7_delta'):
                sums[field]+=r[field]
            for field in ('first_new_eat_opportunity','first_new_consumption_opportunity',
                          'first_new_feedback_opportunity','first_success_after_new_feedback_opportunity'):
                sums['cases_with_'+field]+=int(r[field] is not None)
            sums['first_reversal_success']+=int(r['first_reversal_success'])
            before,after=r['snapshots']['40'],r['snapshots']['60']
            sums['cases_old_count_decreased']+=int(after['old_food_eat']['count'] < before['old_food_eat']['count'])
            sums['cases_new_count_increased']+=int(after['new_food_eat']['count'] > before['new_food_eat']['count'])
            sums['cases_old_weight0_decreased']+=int(after['old_food_eat']['weight0_sum'] < before['old_food_eat']['weight0_sum']-1e-12)
            sums['cases_new_weight0_increased']+=int(after['new_food_eat']['weight0_sum'] > before['new_food_eat']['weight0_sum']+1e-12)
        groups[f'{body}/{control}']=dict(sums)
    OUTPUT.write_text(json.dumps({'scope':'exploratory reconstructed development reversal only; no causal learning claim',
       'analysis_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'source_hashes':source_hashes,'food_eat_mapping':'derived from comb->attn and comb->decn fixed tracts; categories 3 and 8, decision 4',
       'timing':'opportunity offsets 0..19 from start of reversal; events on pending-delivery tick only',
       'limitations':['Requests count ticks, not independent attempts.', 'Pending events show planned delivery; response neuron effects are not captured in this trace.',
         'Same-tick state changes and later choices are observational and do not establish signal causation.',
         'Dendrite weight sums omit inhibitory semantics and other states; endpoints can migrate.',
         'Four counterbalanced cases per seed are not independent seeds.',
         'Opposite condition trajectories differ; no native-engine or held-out claim.'],
       'groups':groups,'cases':cases},indent=2,allow_nan=False)+'\n')
    print(json.dumps(groups,indent=2))

if __name__=='__main__':main()
