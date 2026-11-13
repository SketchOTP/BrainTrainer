"""Relate a narrow weight-order proxy to later reversal choices, descriptively."""
import hashlib,json
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/'runs/food-qualification/gene7-contact-development-v1-recovered-analysis.json'
OUTPUT=ROOT/'runs/food-qualification/gene7-reversal-lag-v1.json'


def analyze_case(row):
    tracts=row['initial_tracts']; old=row['good'];new=1-old
    attention=next(t for t in tracts if (t['source'],t['destination'])==('comb','attn'))
    decision=next(t for t in tracts if (t['source'],t['destination'])==('comb','decn'))
    eat={d['source'] for d in decision['dendrites'] if d['destination']==4}
    mapping=[next(iter(eat & {d['source'] for d in attention['dendrites'] if d['destination']==cat})) for cat in (3,8)]
    tract=next(t for t in tracts if (t['gene_id'],t['source'],t['destination'])==(7,'driv','comb'))
    records=[d.copy() for d in tract['dendrites']]
    def contribution(d,target):return d['variables'][0] if d['source']==2 and d['destination']==target else 0.
    oldsum=sum(contribution(d,mapping[old]) for d in records)
    newsum=sum(contribution(d,mapping[new]) for d in records)
    baseline=None;cross=None;first_success=None;later_success=None;first_request=None;later_request=None
    for step in row['steps']:
        event=step['event']; op=event['opportunity']
        if op==40 and baseline is None:baseline=(oldsum,newsum)
        if event['phase']=='reversal':
            if event['choice']['action']==12 and event['choice']['target']==f'object-{new}':
                if first_request is None:first_request=op-40
                if cross is not None and later_request is None:later_request=op-40
            if event['opportunity_end'] and event['success']:
                if first_success is None:first_success=op-40
                if cross is not None and later_success is None:later_success=op-40
        delta=next((d for d in step['tract_delta'] if (d['gene_id'],d['source'],d['destination'])==(7,'driv','comb')),None)
        if delta:
            for item in delta['dendrites']:
                index=item['index'];prior=records[index];current=item['value']
                oldsum+=contribution(current,mapping[old])-contribution(prior,mapping[old])
                newsum+=contribution(current,mapping[new])-contribution(prior,mapping[new])
                records[index]=current
        if event['phase']=='reversal' and baseline is not None and baseline[1]<=baseline[0] and cross is None and newsum>oldsum+1e-12:
            cross=op-40
    return {'seed':row['seed'],'body':row['body'],'mirror':row['mirror'],'good':old,'control':row['control'],
            'start_old_sum':baseline[0], 'start_new_sum':baseline[1],
            'first_crossing_opportunity':cross, 'first_new_eat_request_opportunity':first_request,
            'first_new_success_opportunity':first_success, 'first_request_after_crossing_opportunity':later_request,
            'first_success_after_crossing_opportunity':later_success}


def main():
    if OUTPUT.exists():raise FileExistsError(OUTPUT)
    ref=json.loads(REFERENCE.read_text());cases=[]; keys=set()
    for source in ref['case_sources']:
        sha=hashlib.sha256(); count=0
        with (ROOT/source['path']).open('rb') as f:
            for line in f:
                sha.update(line); row=json.loads(line); r=analyze_case(row)
                key=tuple(r[k] for k in ('seed','body','mirror','good','control'))
                if key in keys:raise ValueError('duplicate case')
                keys.add(key);cases.append(r);count+=1
        if sha.hexdigest()!=source['sha256'] or count!=source['cases']:raise ValueError('source mismatch')
    if len(cases)!=256:raise ValueError('incomplete cases')
    groups={}
    for body in ('walking','swimming'):
      for control in ('ordinary','gene7_frozen'):
        rs=[r for r in cases if r['body']==body and r['control']==control];c=Counter()
        for r in rs:
            c['cases']+=1
            c['already_new_greater_at_start']+=int(r['start_new_sum']>r['start_old_sum'])
            if r['first_crossing_opportunity'] is not None:
                c['crossed_during_reversal']+=1
                c['new_eat_after_crossing']+=int(r['first_request_after_crossing_opportunity'] is not None)
                c['new_success_after_crossing']+=int(r['first_success_after_crossing_opportunity'] is not None)
                c['new_success_before_or_same_opportunity_as_crossing']+=int(r['first_new_success_opportunity'] is not None and
                    r['first_new_success_opportunity']<=r['first_crossing_opportunity'])
        groups[f'{body}/{control}']=dict(c)
    OUTPUT.write_text(json.dumps({'scope':'descriptive order of drive-2 old/new food-eat state0 sums and choices, not a learned-value readout',
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limitations':['Crossing is a numerical proxy; native meaning and influence of summed weights are not established.',
          'A request or consumption after a crossing is not proof of causation.',
          'Choices are read before the tract update in the same tick; counts allow later ticks within the same opportunity.',
          '64 branches per cell share 16 seeds; do not treat them as independent.',
          'Pairs with no crossing or no subsequent response are censored.'],
        'groups':groups,'cases':cases},indent=2)+'\n')
    print(json.dumps(groups,indent=2))

if __name__=='__main__':main()
