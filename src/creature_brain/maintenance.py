"""Initial maintenance drive with experience-derived recovery expectations.

Low/high reserve thresholds are authored instincts. Recovery evidence comes only
from attributed real rest outcomes; the drive does not know the body's rate.
"""
from copy import deepcopy
from dataclasses import replace
from .neural import DECISION_FROM_ACTION

class Maintenance:
    def __init__(self):
        self.goals=[]
        self.rest_evidence=[]
        self.requests=[]

    def choose(self,proposed,reserve, *, investigate=False):
        unresolved=next((g for g in reversed(self.goals) if g['status']=='recovery-needs-investigation'),None)
        if investigate and unresolved:
            # A targetless hold spends no movement reserve; it is not a claimed rest.
            probe=proposed.time>=unresolved.get('next_probe_tick',0)
            action=0 if probe else 8
            choice=replace(proposed,action=action,decision=DECISION_FROM_ACTION[action],target=None)
            return choice,{'reason':'probe-unresolved-recovery' if probe else 'conserve-before-recovery-probe',
                'goal_id':unresolved['id'],'selected_action':action,'proposal_action':proposed.action,
                'observed_reserve':reserve,'evidence':list(unresolved['evidence']),
                'uncertainty':'body recovery cause remains unknown',
                'origin':'own-observed-recovery-failure'}
        active=next((g for g in reversed(self.goals) if g['status']=='active'),None)
        if active is None:
            if reserve>=1 or (self.goals and self.goals[-1]['status']=='recovery-needs-investigation'):return None
            goal_id=f'maintenance:{proposed.time}'
        else:goal_id=active['id']
        recent=self.rest_evidence[-8:]
        expected=sum(e['gain'] for e in recent)/len(recent) if recent else None
        choice=replace(proposed,action=0,decision=DECISION_FROM_ACTION[0],target=None)
        return choice,{'reason':'restore-observed-body-reserve','goal_id':goal_id,
            'selected_action':0,'proposal_action':proposed.action,'observed_reserve':reserve,
            'expected_recovery':expected,'prediction_evidence':[e['event'] for e in recent],
            'uncertainty':'no experienced rest outcomes' if not recent else 'recent observed outcomes; changed body may differ',
            'origin':'authored maintenance drive informed by proprioception'}

    def observe(self,record):
        if record['kind']=='communication' and record['payload'].get('operation')=='request-recovery-help':
            self.requests.append({**deepcopy(record['payload']),'event':record['sequence']})
            return
        if record['kind']!='experience':return
        event=record['payload'];decision=event.get('executive') or {}
        if decision.get('reason') not in ('restore-observed-body-reserve','probe-unresolved-recovery'):return
        action=event['executed_action'];outcome=event['outcome'];resources=event.get('body_resources')
        if (not resources or action['action']!=0 or action['target'] is not None or
            outcome['action_id']!=action['id'] or outcome['action']!=0 or outcome['target'] is not None or
            outcome['status']!='rested' or not outcome['completed']):return
        gain=resources['after']-resources['before']
        self.rest_evidence.append({'event':record['sequence'],'gain':gain})
        goal=next((g for g in self.goals if g['id']==decision['goal_id']),None)
        if goal is None:
            goal={'id':decision['goal_id'],'objective':'restore-capacity-for-activity',
                'origin':decision['origin'],'status':'active','evidence':[],
                'start_reserve':resources['before'],'stalled':0,'rest_ticks':0}
            self.goals.append(goal)
        goal['evidence'].append(record['sequence']);goal['rest_ticks']+=1
        goal['stalled']=goal['stalled']+1 if gain<=0 else 0
        if resources['after']>=3:goal['status']='recovered-for-activity'
        elif goal['stalled']>=3:goal['status']='recovery-needs-investigation'
        elif gain>0:goal['status']='active'
        if goal['status']=='recovery-needs-investigation':
            goal['next_probe_tick']=event['time']+8
        if decision.get('reason')=='probe-unresolved-recovery':
            goal['probe_count']=goal.get('probe_count',0)+1
            if gain>0:goal['recovery_return_evidence']=record['sequence']
        goal['last_reserve']=resources['after']

    def assistance_request(self):
        requested={r['goal_id'] for r in self.requests}
        for goal in self.goals:
            if goal['status']=='recovery-needs-investigation' and goal['id'] not in requested:
                return {'operation':'request-recovery-help','goal_id':goal['id'],
                    'origin':'own-observed-recovery-failure','evidence':list(goal['evidence']),
                    'message':'Rest has not restored my capacity. Can you help investigate my recovery?',
                    'requested_help':'inspect the body recovery mechanism',
                    'unknowns':['whether the failure is temporary','whether the body implementation needs repair'],
                    'observed_rest_ticks':goal['rest_ticks']}
        return None

    def review(self):
        return {'recovery_requests':deepcopy(self.requests),'maintenance_goals':deepcopy(self.goals),'rest_evidence':deepcopy(self.rest_evidence[-8:]),
            'maintenance_uncertainty':'recovery mechanism is inferred only from observed reserve changes'}
