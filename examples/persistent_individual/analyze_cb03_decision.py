"""Derive CB-03 decision/dispatch and lifecycle diagnostics from frozen CB-02 data.

This is a projection of recorded events, not new simulation or native evidence.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'runs/self-model/complete-action/calibration.jsonl'


def summarize(row):
    result = row['result']; events = result['events']; budget = 64
    attention=Counter(); targets=Counter(); winners=Counter(); dispatch=Counter(); episodes={}
    for item in events:
        e=item['event']; c=e['choice']; t=c['time']; attention[str(c['attention'])]+=1
        targets[c['target'] if c['target'] is not None else '<none>']+=1
        winners[(c['decision'],c['action'])]+=1
        dispatch[(c['decision'],c['action'],e['outcome']['status'])]+=1
        for entry in e['lifecycle_events']:
            if entry['event']=='started':
                obj=next((o for o in e['observation']['objects'] if o['identity']==entry['target']),None)
                episodes[entry['action_id']]={'original_action_id':entry['action_id'],'target':entry['target'],
                    'start_clock':t,'start_step':t-result['start_tick']+1,'ticks_remaining_inclusive':budget-(t-result['start_tick']),
                    'start_distance':obj['distance'] if obj else None,'steps':[], 'termination':None}
            if entry['event'] in ('interrupted','failed','completed') and entry['action_id'] in episodes:
                episodes[entry['action_id']]['termination']={'event':entry['event'],'clock':t,'competing_choice':c,
                                                               'reason':entry.get('reason')}
        executed=e['executed_action']; key=executed['id']
        if key in episodes and executed['action']==12:
            obj=next((o for o in e['observation']['objects'] if o['identity']==executed['target']),None)
            episodes[key]['steps'].append({'clock':t,'current_choice_id':c['id'],'decision':c['decision'],
                'mapped_action':c['action'],'current_target':c['target'],'executing_action_id':key,
                'executing_target':executed['target'],'distance':obj['distance'] if obj else None,
                'contact':obj['contact'] if obj else None,'outcome':e['outcome']['status'],
                'obstacle_present':item['obstacle_present']})
    requested=bool(result['requested_eat'])
    return {'seed':row['seed'],'mirror':row['mirror'],'condition':row['condition'],'distance':row['distance'],
            'recorded_steps':len(events),'opportunity_budget':budget,'attention_counts':dict(attention),'target_counts':dict(targets),
            'decision_action_counts':[{'decision':d,'action':a,'ticks':n} for (d,a),n in sorted(winners.items())],
            'dispatch_counts':[{'decision':d,'action':a,'status':s,'ticks':n} for (d,a,s),n in sorted(dispatch.items())],
            'requested_eat':requested,'completed':result['completed'],'contact':result['contact'],
            'first_missing_transition':None if requested else 'decision winner never equals eat neuron 4',
            'timeout_canceled_action':result['timeout_canceled_action'], 'episodes':list(episodes.values())}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    rows=[json.loads(line) for line in SOURCE.open()]
    focus=[r for r in rows if r['distance']==2.0]
    assert len(focus)==32 and len({(r['seed'],r['mirror'],r['condition']) for r in focus})==32
    summaries=[summarize(r) for r in focus]
    baseline=[r for r in focus if r['condition']=='baseline' and r['seed']==0]
    false=next(r for r in baseline if not r['mirror']);true=next(r for r in baseline if r['mirror'])
    def choices(r):return [(v['event']['choice']['decision'],v['event']['choice']['action']) for v in r['result']['events']]
    left,right=choices(false),choices(true);common=min(len(left),len(right))
    mismatch=[i for i in range(common) if left[i]!=right[i]]
    out={'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
         'analysis_source':str(Path(__file__).resolve().relative_to(ROOT)),
         'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'scope':'32 paired-controller branches, four seeds and two mirrors at 2.0 units, no new replays',
         'decision_to_action_mapping_note':'recorded decision 4 maps to action 12; no inference about biological cause',
         'mirror_comparison':{'seed':0,'condition':'baseline','common_ticks':common,'same_winners_and_actions':not mismatch,
                              'mismatch_ticks':mismatch},'branches':summaries}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(out,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print('recorded',len(summaries),'branches; same mirror decisions on',common,'common ticks:',not mismatch)

if __name__=='__main__':main()
