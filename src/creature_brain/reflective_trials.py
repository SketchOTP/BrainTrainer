"""Lived trials selected by reflection; success is derived only from experience."""
from copy import deepcopy
import math
from dataclasses import replace
from .neural import DECISION_FROM_ACTION

PLAN_FIELDS={'target','type_id','action','starting_appearance','expected_appearance','max_attempts','max_world_ticks'}

def validate_plan(plan):
    if not isinstance(plan,dict) or not PLAN_FIELDS<=set(plan) or set(plan)-PLAN_FIELDS-{'max_target_distance'}:raise ValueError('invalid embodied trial fields')
    for key in ('target','type_id'):
        if not isinstance(plan[key],str) or not plan[key]:raise ValueError('trial requires target identity and type')
    if type(plan['action']) is not int or plan['action'] not in (1,2,3,6,7,12,13):raise ValueError('unsupported trial interaction')
    for key in ('starting_appearance','expected_appearance'):
        if plan[key] is not None and (not isinstance(plan[key],str) or not plan[key]):raise ValueError('invalid appearance prediction')
    for key,maximum in (('max_attempts',32),('max_world_ticks',256)):
        if type(plan[key]) is not int or not 1<=plan[key]<=maximum:raise ValueError('trial exceeds bounded execution allowance')
    distance=plan.get('max_target_distance')
    if distance is not None and (type(distance) not in (int,float) or not math.isfinite(distance) or distance<0):
        raise ValueError('invalid target distance condition')
    return plan

class ReflectiveTrials:
    def __init__(self):self.trials=[];self.requests=[];self.reflections=[]
    def active(self):return next((t for t in self.trials if t['status']=='active'),None)
    def validate(self,payload):
        validate_plan(payload['plan'])
        if self.active():raise ValueError('a reflective trial is already active')
        if any(t['request_id']==payload['request_id'] for t in self.trials):raise ValueError('reflection already consumed')
        if not isinstance(payload['request_id'],str) or not payload['request_id']:raise ValueError('missing reflection identity')
    def observe(self,record):
        e=record['payload']
        if record['kind']=='hypothesis' and e.get('operation')=='request-reflection':
            self.requests.append({**deepcopy(e),'event':record['sequence'],'tick':record['tick']});return
        if record['kind']=='hypothesis' and e.get('operation')=='reflection-result':
            self.reflections.append({**deepcopy(e),'event':record['sequence']});return
        if record['kind']=='hypothesis' and e.get('operation')=='adopt-reflective-trial':
            self.validate(e)
            self.trials.append({**deepcopy(e),'id':f"reflection:{record['sequence']}",
                'adoption_event':record['sequence'],'started_tick':record['tick'],
                'status':'active','attempts':0,'evidence':[],'cause':'not-established'})
            return
        trial=self.active()
        if record['kind']!='experience' or trial is None:return
        decision=e.get('executive') or {};plan=trial['plan']
        if decision.get('reflective_trial_id')==trial['id']:
            trial['evidence'].append(record['sequence'])
            if decision.get('reason')=='reflective-trial-unavailable':
                trial.update(status='incomplete',reason=decision['unavailable_reason'],outcome_event=record['sequence']);return
            a=e['executed_action'];o=e['outcome']
            matched=(a['target']==plan['target'] and a['action']==plan['action'] and
                o['action_id']==a['id'] and o['target']==a['target'] and o['action']==a['action'])
            if matched and o['status'] not in ('approaching','contact','not-in-contact'):
                trial['attempts']+=1
                before=next((v for v in e['observation']['objects'] if v['identity']==plan['target']),None)
                after=next((v for v in e.get('observation_after',{}).get('objects',[]) if v['identity']==plan['target']),None)
                changed=bool(o['completed'] and before and 'observation_after' in e and
                    (after is None or before['appearance']!=after['appearance']))
                success=changed and (plan['expected_appearance'] is None or
                    (after is not None and after['appearance']==plan['expected_appearance']))
                trial['last_outcome']=deepcopy(o)
                if o.get('hunger_adjustment',0)>0:
                    trial.update(status='adverse-result-stop',prediction_matched=success,outcome_event=record['sequence'])
                elif success:trial.update(status='observed-success',outcome_event=record['sequence'])
                elif trial['attempts']>=plan['max_attempts']:
                    trial.update(status='prediction-not-observed',outcome_event=record['sequence'])
        if trial['status']=='active' and e['time']-trial['started_tick']>=plan['max_world_ticks']:
            trial.update(status='incomplete',reason='world-time-allowance-exhausted',outcome_event=record['sequence'])
    def choose(self,proposed,observation):
        t=self.active()
        if t is None:return None
        p=t['plan'];target=next((o for o in observation.objects if o.identity==p['target']),None)
        reason=None
        if target is None:reason='target-not-observed'
        elif target.type_id!=p['type_id']:reason='target-type-changed'
        elif p.get('max_target_distance') is not None and target.distance>p['max_target_distance']:reason='target-beyond-distance-condition'
        elif not t['attempts'] and p['starting_appearance'] is not None and target.appearance!=p['starting_appearance']:reason='starting-observation-changed'
        action=p['action'] if target and target.contact else 4
        if reason is None and action not in target.available_actions:reason='action-unavailable'
        info={'reflective_trial_id':t['id'],'request_id':t['request_id'],'selected_action':8 if reason else action,
            'reason':'reflective-trial-unavailable' if reason else 'reflective-trial-interaction' if target.contact else 'reflective-trial-approach'}
        if reason:
            info['unavailable_reason']=reason
            return replace(proposed,action=8,decision=DECISION_FROM_ACTION[8],target=None),info
        return replace(proposed,action=action,decision=DECISION_FROM_ACTION[action],target=target.identity,attention=target.category),info
    def request(self,goals,tick):
        if self.active():return None
        completed={r['request_id'] for r in self.reflections}
        if any(r['request_id'] not in completed for r in self.requests):return None
        if self.requests and tick-self.requests[-1]['tick']<128:return None
        reviewed={r['trigger_id'] for r in self.requests}
        for trial in reversed(self.trials):
            trigger=f"trial-outcome:{trial.get('outcome_event')}"
            if trial['status']!='active' and trigger not in reviewed:
                return {'trigger_id':trigger,'reason':'review-lived-trial','trial_id':trial['id'],'evidence_event':trial['outcome_event']}
        for goal in reversed(goals):
            trigger=f"unresolved:{goal['id']}:{goal['evidence'][-1]}"
            if goal['status']=='effect-unresolved-review-needed' and trigger not in reviewed:
                return {'trigger_id':trigger,'reason':'unresolved-activity','goal_id':goal['id'],'evidence_event':goal['evidence'][-1]}
        return None
    def review(self):return {'reflective_trials':deepcopy(self.trials),'reflection_requests':deepcopy(self.requests),'reflection_results':deepcopy(self.reflections)}
