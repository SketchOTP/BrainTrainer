"""Independent post-run audit of CB-04 source-bound starts, attempts and outcomes."""
import argparse,hashlib,json,collections
from pathlib import Path
from inherited_preparation import restore_prepared,clone_prepared_motor,prepared_snapshot
from prepared_development import digest


def main():
 p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('manifest',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
 manifest=json.loads(a.manifest.read_text())
 for path,want in manifest['sha256'].items():
  if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=want:raise ValueError('changed pinned input '+path)
 seeds=set();keys=set();attempts=0;events=0;completed=0;unsupported=0;failures=0;unknown=0;continuations=0
 geometry=collections.Counter();intent_distances=[];intent_wait_ticks=[]
 with a.raw.open() as stream:
  for line in stream:
   row=json.loads(line);seed=row['seed']
   if seed in seeds:raise ValueError('duplicate seed')
   seeds.add(seed);source=restore_prepared(row['prepared_checkpoint']);base=prepared_snapshot(source)
   if base['receipt']!=row['preparation'] or base['receipt']['processed_count']!=29:raise ValueError('bad profile receipt')
   bs=base['state'];bm=bs['model']
   for case in row['cases']:
    key=(seed,case['scenario'],case['condition'])
    if key in keys:raise ValueError('duplicate condition')
    keys.add(key);clone=clone_prepared_motor(source,case['condition']);cp=prepared_snapshot(clone);cs=cp['state'];cm=cs['model']
    if digest(cp)!=case['initial_checkpoint_sha256'] or cp['receipt']!=base['receipt'] or cs['individual']!=bs['individual']:
     raise ValueError('initial individual mismatch')
    if any(cs[k]!=bs[k] for k in ('reserve','body_strength','obstacle_present')) or any(cm[k]!=bm[k] for k in ('evidence','decisions','pending')):
     raise ValueError('initial body or model mismatch')
    if case['condition']=='candidate' and (cm['confirmations'] or cm['confirmation_attempts']):raise ValueError('unexpected confirmation')
    if not case['checkpoint_continuation_equal']:raise ValueError('continuation failure')
    final=restore_prepared(case['final_checkpoint'])
    if final._inherited_preparation!=base['receipt'] or final.brain.instinct_cursor!=29 or final.brain.instincts_processed!=29:
     raise ValueError('prepared final checkpoint receipt/cursor mismatch')
    continuations+=1
    if len(case['results'])!=24:raise ValueError('wrong number of opportunities')
    for i,op in enumerate(case['results']):
     if op['opportunity']!=i or op['phase']!=('healthy','impaired','recovery')[i//8]:raise ValueError('wrong phase')
     if op['ticks']!=len(op['events']) or not 1<=op['ticks']<=64:raise ValueError('wrong tick count')
     if op['completed']!=bool(op['completion']) or op['timed_out']==op['completed']:raise ValueError('wrong result classification')
     event_by_tick={v['event']['time']-1:v['event'] for v in op['events']};events+=len(event_by_tick)
     if len(event_by_tick)!=len(op['events']):raise ValueError('duplicate tick')
     first=op['events'][0]['event']['observation']; offered=[o for o in first['objects'] if o['identity']==op['offered']]
     if len(offered)!=1 or abs(offered[0]['distance']-2.0)>1e-8 or offered[0]['contact']:
      raise ValueError('initial offered geometry is not the declared 2.0 units')
     sign=1 if (i+int(case['mirror']))%2==0 else -1
     if offered[0]['relative_position']*sign<=0:raise ValueError('incorrect mirrored position')
     geometry['left' if offered[0]['relative_position']<0 else 'right']+=1
     for entry in op['events']:
      ev=entry['event'];choice=ev['choice']
      if choice['action']==12 and choice['target']==op['offered']:
       objects=[o for o in ev['observation']['objects'] if o['identity']==op['offered']]
       if len(objects)!=1:raise ValueError('eat target absent from recorded observation')
       intent_distances.append(objects[0]['distance']);intent_wait_ticks.append(ev['time']-op['start_tick']);break
     actual_completions=[v['event']['outcome'] for v in op['events'] if v['event']['outcome']['completed']]
     if len(actual_completions)!=int(op['completed']) or (actual_completions and actual_completions[0]!=op['completion']):raise ValueError('wrong completion')
     completed+=len(actual_completions)
     unsupported+=sum(v['event']['outcome']['status']=='unavailable-action' for v in op['events'])
     seen=set();spent=0.0
     for motor in op['motor']:
      ev=event_by_tick[motor['tick']];choice=ev['choice'];executed=ev['executed_action'];aid=motor['motor_attempt_id']
      if aid in seen:raise ValueError('duplicate attempt')
      seen.add(aid)
      if (motor['action_id']!=choice['id'] or motor['brain_action']!=choice['action'] or motor['brain_target']!=choice['target'] or
          motor['executing_action_id']!=executed['id'] or motor['executing_action']!=executed['action'] or motor['executing_target']!=executed['target']):raise ValueError('action attribution mismatch')
      if motor['prediction']!=motor['predictions'][motor['mode']]['success_probability']:raise ValueError('prediction mismatch')
      attempts+=1;spent+=motor['cost'];failures+=motor['motor_success'] is False;unknown+=motor['motor_success'] is None
     if abs(spent-op['reserve_cost'])>1e-8:raise ValueError('reserve expenditure mismatch')
 expected={(s,sc,c) for s in range(500,516) for sc in ('sustained','intermittent') for c in ('normal','effort','baseline','candidate')}
 if seeds!=set(range(500,516)) or keys!=expected:raise ValueError('missing cases')
 result={'raw_sha256':hashlib.sha256(a.raw.read_bytes()).hexdigest(),'seeds':len(seeds),'histories':len(keys),
         'matched_complete_starts':len(keys),'matched_in_process_continuations':continuations,'ticks':events,
         'motor_attempts':attempts,'completions':completed,'unsupported_choice_ticks':unsupported,
         'measured_motor_failures':failures,'unknown_motor_attempts':unknown,'pinned_inputs':len(manifest['sha256']),
         'initial_offered_geometry_counts':dict(geometry),'first_eat_intents':len(intent_distances),
         'first_intent_distance_min':min(intent_distances) if intent_distances else None,
         'first_intent_distance_max':max(intent_distances) if intent_distances else None,
         'first_intent_wait_ticks_min':min(intent_wait_ticks) if intent_wait_ticks else None,
         'first_intent_wait_ticks_max':max(intent_wait_ticks) if intent_wait_ticks else None}
 with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result,indent=2))

if __name__=='__main__':main()
