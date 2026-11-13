"""Authored curiosity with learned motion and persistent spatial goals.

Uses observed positions and actual displacement only, never host room limits.
No motion identifies an unresolved local limitation, not its physical cause.
"""
from copy import deepcopy
from dataclasses import replace
from .neural import DECISION_FROM_ACTION

class SpatialExploration:
    def __init__(self):
        self.low=None;self.high=None
        self.motion={};self.goals=[];self.blocked={};self.unmoving_until={}

    def active(self):return next((g for g in reversed(self.goals) if g['status']=='active'),None)

    def observe(self,record):
        if record['kind']!='experience':return
        e=record['payload']
        # Older unexecutive histories do not expose proprioceptive displacement.
        # Preserve that absence rather than inventing geometry or rejecting history.
        if 'body_motion' not in e:return
        body=e['body_motion'];before=body['before'];after=body['after']
        self.low=min(before,after) if self.low is None else min(self.low,before,after)
        self.high=max(before,after) if self.high is None else max(self.high,before,after)
        action=e['executed_action'];outcome=e['outcome'];decision=e.get('executive') or {}
        matched=(outcome['action_id']==action['id'] and outcome['action']==action['action'] and outcome['target']==action['target'])
        delta=after-before
        if matched and action['action'] in (10,11) and outcome['status']=='moving':
            row=self.motion.setdefault(action['action'],{'direction':None,'samples':[]})
            row['samples'].append({'event':record['sequence'],'delta':delta});del row['samples'][:-8]
            if abs(delta)>1e-9:row['direction']=1 if delta>0 else -1
        if decision.get('reason') in ('explore-unvisited-position','investigate-motion') and matched:
            spec=decision['exploration_goal'];goal=next((g for g in self.goals if g['id']==spec['id']),None)
            if goal is None:
                goal={**deepcopy(spec),'status':'active','evidence':[],'stalled':0};self.goals.append(goal)
            goal['evidence'].append(record['sequence'])
            goal['stalled']=goal['stalled']+1 if abs(delta)<1e-9 else 0
            if goal['objective']=='investigate-motion' and abs(delta)>1e-9:
                goal['status']='observed-motion'
            elif goal['target_position'] is not None and (after-goal['target_position'])*goal['direction']>=0:
                goal['status']='reached-new-position'
            elif goal['target_position'] is not None and delta*goal['direction']<0:
                goal['status']='motion-contradicted-expectation'
            elif goal['stalled']>=3:
                goal['status']='motion-blocked-cause-unknown'
                if goal['direction'] is None:self.unmoving_until[goal['action']]=e['time']+64
                else:self.blocked[goal['direction']]={'position':after,'retry_after':e['time']+128,'event':record['sequence']}
            goal['last_position']=after
        else:
            goal=self.active()
            if goal and goal['target_position'] is not None and (after-goal['target_position'])*goal['direction']>=0:
                goal.update(status='reached-during-other-activity',outcome_event=record['sequence'],last_position=after)

    def choose(self,proposed,position,intrinsic_actions):
        actions=[a for a in (10,11) if a in intrinsic_actions]
        if not actions:return None
        active=self.active()
        if active:
            spec={k:active[k] for k in ('id','objective','origin','action','direction','target_position','method')}
        else:
            unknown=[a for a in actions if self.motion.get(a,{}).get('direction') is None and proposed.time>=self.unmoving_until.get(a,0)]
            if unknown:
                spec={'id':f'explore:{proposed.time}','objective':'investigate-motion','origin':'unknown-available-movement',
                    'action':unknown[0],'direction':None,'target_position':None,'method':'observe-actual-motion'}
            else:
                options=[]
                for action in actions:
                    direction=self.motion.get(action,{}).get('direction')
                    if direction is None:continue
                    frontier=(self.low if direction<0 else self.high)
                    frontier=position if frontier is None else frontier
                    block=self.blocked.get(direction)
                    if block and abs(block['position']-frontier)<1e-8 and proposed.time<block['retry_after']:continue
                    target=frontier+direction
                    options.append((abs(target-position),action,direction,target))
                if not options:
                    if 8 not in intrinsic_actions:return None
                    return replace(proposed,action=8,decision=DECISION_FROM_ACTION[8],target=None),{
                        'reason':'quiet-after-unresolved-motion','goal_id':None,'proposal_action':proposed.action,
                        'selected_action':8,'uncertainty':'movement cause unknown; later probes remain possible'}
                _,action,direction,target=min(options)
                spec={'id':f'explore:{proposed.time}','objective':'explore-unvisited-position','origin':'observed-visited-range',
                    'action':action,'direction':direction,'target_position':target,'method':'extend-observed-range'}
        samples=self.motion.get(spec['action'],{}).get('samples',[])
        choice=replace(proposed,action=spec['action'],decision=DECISION_FROM_ACTION[spec['action']],target=None)
        return choice,{'reason':spec['objective'],'goal_id':spec['id'],'exploration_goal':spec,
            'proposal_action':proposed.action,'selected_action':spec['action'],
            'expected_displacement':sum(s['delta'] for s in samples)/len(samples) if samples else None,
            'prediction_evidence':[s['event'] for s in samples],
            'uncertainty':'current motion may differ; failed movement does not identify its cause'}

    def review(self):
        return {'exploration_goals':deepcopy(self.goals),'observed_position_range':[self.low,self.high],
            'motion_expectations':deepcopy(self.motion),'exploration_blocks':deepcopy(self.blocked)}
