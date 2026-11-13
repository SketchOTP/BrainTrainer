"""Post-run independent audit of CB-05 raw forecasts, attribution and contexts."""
from collections import Counter
import argparse
import hashlib
import json
import math
from pathlib import Path


def approx(a,b):return math.isclose(a,b,abs_tol=1e-9,rel_tol=1e-9)


def main():
    p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('manifest',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    manifest=json.loads(args.manifest.read_text())
    for name,sha in manifest['sha256'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha:raise ValueError('pinned source changed: '+name)
    table=json.loads(Path('runs/self-model/cb05-prospective/condition-table.json').read_text())['rows']
    expected={(x['seed'],x['opportunity']):x for x in table};counts=Counter();seen_seed=set()
    allowed={'distance','contact','distance_bin','hunger','energy','reserve','time_remaining','horizon_bin','motor_normal','motor_effort','motor_bin','policy'}
    with args.raw.open() as f:
      for line in f:
        case=json.loads(line);seed=case['seed']
        if seed in seen_seed:raise ValueError('duplicate seed')
        seen_seed.add(seed);base={};contextual={};all_ids=set()
        if case['preparation']['processed_count']!=29 or case['preparation']['brain_tick_after']!=58:raise ValueError('bad inherited preparation')
        state=case['initial_checkpoint']['state']['individual']
        if state['initial_good']!=(seed//2)%2:raise ValueError('incorrect value assignment')
        for o in case['opportunities']:
            cfg=o['config'];key=(seed,cfg['opportunity'])
            if expected.pop(key,None)!=cfg:raise ValueError('unmatched condition row')
            counts['opportunities']+=1;events=o['events'];motors=o['motor'];preds=o['predictions']
            if len(events)!=o['end_tick']-o['start_tick']:raise ValueError('noncontinuous ticks')
            first=events[0]['observation'];objects=first['objects']
            if len(objects)!=1 or objects[0]['identity']!=o['offered'] or not approx(objects[0]['relative_position'],cfg['side']*2) or not approx(first['hunger'],cfg['hunger']):raise ValueError('initial scene/need mismatch')
            choices=[ev['choice'] for ev in events];eat=[v for v in choices if v['action']==12]
            counts['no_brain_eat_intent']+=not eat
            counts['eat_choice_without_target_opportunities']+=any(v['target'] is None for v in eat)
            counts['no_accepted_eat_action']+=not any(p['kind']=='forecast' for p in preds)
            counts['unsupported_choice_ticks']+=sum(ev['outcome']['status']=='unavailable-action' for ev in events)
            if o['no_eat_request'] != (not any(p['kind']=='forecast' for p in preds)):raise ValueError('request flag mismatch')
            if o['completed']!=any(ev['outcome']['completed'] for ev in events):raise ValueError('completion flag mismatch')
            if not approx(sum(m['cost'] for m in motors),o['total_opportunity_cost']):raise ValueError('total opportunity cost mismatch')
            bytime={ev['choice']['time']:ev for ev in events}
            attempts=set()
            for m in motors:
                if m['motor_attempt_id'] in attempts:raise ValueError('duplicate motor attempt')
                attempts.add(m['motor_attempt_id']);counts['motor_attempts']+=1
                counts['motor_failures']+=m['motor_success'] is False;counts['motor_unknowns']+=m['motor_success'] is None
            forecasts={};closed=set()
            for item in preds:
                aid=item['action_id']
                if item['kind']=='forecast':
                    if aid in all_ids:raise ValueError('duplicate action identity')
                    all_ids.add(aid);forecasts[aid]=item;counts['forecasts']+=1
                    t=item['start_tick'];ev=bytime[t];choice=ev['choice'];ctx=item['context']
                    if (choice['id']!=aid or choice['action']!=12 or choice['target']!=item['target'] or
                        not any(z['event']=='started' and z['action_id']==aid and z['target']==item['target'] for z in ev['lifecycle_events'])):
                        raise ValueError('forecast does not match lifecycle start')
                    if set(ctx)!=allowed:raise ValueError('unexpected forecast context field')
                    target=next((z for z in ev['observation']['objects'] if z['identity']==item['target']),None)
                    if target is None or not approx(target['distance'],ctx['distance']) or target['contact']!=ctx['contact']:
                        raise ValueError('geometry context mismatch')
                    if not approx(ev['observation']['hunger'],ctx['hunger']) or not approx(ev['observation']['energy'],ctx['energy']):raise ValueError('needs context mismatch')
                    prior_spend=sum(m['cost'] for m in motors if m['tick']<t)
                    if not approx(ctx['reserve'],o['start_reserve']-prior_spend):raise ValueError('reserve context mismatch')
                    first_motors=[m for m in motors if m['tick']==t and m['executing_action_id']==aid]
                    if first_motors:
                        motor=first_motors[0]
                        if motor['predictions'].get('normal')!=ctx['motor_normal'] or motor['predictions'].get('effort')!=ctx['motor_effort']:raise ValueError('motor prior feature mismatch')
                    if item['deadline']!=min(t+32,o['deadline']) or ctx['time_remaining']!=item['deadline']-t or ctx['policy']!='adaptive':raise ValueError('deadline/policy mismatch')
                    normal=ctx['motor_normal'];mbin='unobserved' if normal is None or normal['observations']==0 else 'low' if normal['success_probability']<.4 else 'medium' if normal['success_probability']<.7 else 'high'
                    dbin='contact' if ctx['distance']<=.85 else 'near' if ctx['distance']<=2. else 'far'
                    remaining=ctx['time_remaining'];hbin='short' if remaining<=8 else 'medium' if remaining<=16 else 'long'
                    if (ctx['motor_bin'],ctx['distance_bin'],ctx['horizon_bin'])!=(mbin,dbin,hbin):raise ValueError('feature bin mismatch')
                    bk=(12,'adaptive');ck=(12,'adaptive',dbin,mbin,hbin)
                    b=base.get(bk,{'observed':0,'completed':0,'cost_count':0,'cost_sum':0})
                    c=contextual.get(ck,{'observed':0,'completed':0,'cost_count':0,'cost_sum':0})
                    prob=(1+b['completed'])/(2+b['observed']);cost=(1+b['cost_sum'])/(2+b['cost_count'])
                    cp=(4*prob+c['completed'])/(4+c['observed']);cc=(4*cost+c['cost_sum'])/(4+c['cost_count'])
                    if not all(approx(a,b) for a,b in ((item['baseline']['completion_probability'],prob),(item['baseline']['expected_reserve_cost'],cost),(item['candidate']['completion_probability'],cp),(item['candidate']['expected_reserve_cost'],cc))):raise ValueError('pre-outcome prediction mismatch')
                    if item['baseline']['evidence_count']!=b['observed'] or item['candidate']['evidence_count']!=c['observed']:raise ValueError('evidence count mismatch')
                    forecasts[aid]=(item,bk,ck)
                elif item['kind']=='terminal':
                    if aid not in forecasts or aid in closed:raise ValueError('unmatched/repeated terminal')
                    forecast,bk,ck=forecasts[aid];closed.add(aid)
                    if item['forecast']!=forecast or item['target']!=forecast['target']:raise ValueError('terminal forecast mismatch')
                    matching=[m for m in motors if m['executing_action_id']==aid and m['executing_target']==item['target']]
                    if any(not forecast['start_tick']<=m['tick']<item['end_tick'] for m in matching):raise ValueError('motor attempt outside action')
                    if not approx(sum(m['cost'] for m in matching),item['observed_cost']):raise ValueError('action cost mismatch')
                    if (len(matching),sum(m['motor_success'] is False for m in matching),sum(m['motor_success'] is None for m in matching))!=(item['motor_attempts'],item['motor_failures'],item['motor_unknowns']):raise ValueError('action attempt counts mismatch')
                    kind=item['terminal'];counts['terminal_'+kind]+=1
                    event_matches=[ev for ev in events if any(z['action_id']==aid and z['target']==item['target'] for z in ev['lifecycle_events'])]
                    if kind=='completed':ok=any(ev['outcome']['completed'] and ev['outcome']['action_id']==aid for ev in event_matches)
                    elif kind=='interrupted':ok=any(any(z['event']=='interrupted' and z['action_id']==aid for z in ev['lifecycle_events']) for ev in event_matches)
                    elif kind=='unknown':ok=any(any(z['event']=='failed' and z['action_id']==aid for z in ev['lifecycle_events']) for ev in event_matches)
                    elif kind=='timeout':ok=(o['timeout_action'] is not None and o['timeout_action']['choice']['id']==aid) or any(any(z['event']=='cancelled' and z['action_id']==aid for z in ev['lifecycle_events']) for ev in event_matches)
                    else:raise ValueError('invalid terminal kind')
                    if not ok:raise ValueError('terminal lacks actual lifecycle event')
                    for storage,k in ((base,bk),(contextual,ck)):
                        rec=storage.setdefault(k,{'observed':0,'completed':0,'cost_count':0,'cost_sum':0})
                        if kind!='unknown':rec['observed']+=1;rec['completed']+=kind=='completed';rec['cost_count']+=1;rec['cost_sum']+=item['observed_cost']
                else:raise ValueError('unknown event kind')
            if set(forecasts)!=closed:raise ValueError('unreconciled forecasts')
        if case['final_checkpoint']['observer']['pending']:raise ValueError('pending forecast after history')
    if seen_seed!=set(range(700,716)) or expected:raise ValueError('incomplete panel')
    result={'schema':'cb05-independent-audit-v1','seeds':len(seen_seed),'counts':dict(counts),'pinned_sources':len(manifest['sha256']),
            'raw_sha256':hashlib.sha256(args.raw.read_bytes()).hexdigest(),
            'limits':'Runtime actual strength is determined by frozen source and recorded condition, not separately sampled in raw per tick; forecast visibility and cost/terminal matching were checked against recorded events.'}
    with args.output.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__':main()
