"""Review actual world exploration motion without diagnosing hidden body causes."""
from copy import deepcopy
from dataclasses import replace
from .neural import DECISION_FROM_ACTION

class WorldMotionReview:
    def __init__(self):
        self.goals={}
        self.requests=[]

    def observe(self,record):
        e=record['payload']
        if record['kind']=='communication' and e.get('operation')=='request-world-motion-help':
            self.requests.append({**deepcopy(e),'event':record['sequence']});return
        if record['kind']!='experience':return
        d=e.get('executive') or {};motion=e.get('world_motion')
        if not motion:return
        a=e['executed_action'];o=e['outcome'];spec=d.get('world_goal')
        matched=o['action_id']==a['id'] and o['action']==a['action'] and o['target']==a['target']
        arrival=motion.get('exploration_review')
        if matched and arrival and arrival['status']=='reached-observed-position':
            prior=self.goals.get(arrival['goal']['id'])
            if prior:prior.update(status='reached-observed-position',completion_event=record['sequence'])
        if d.get('reason') not in ('explore-world','probe-world-motion'):return
        if (not spec or a['action']!=11 or a['target'] is not None or
            o['action_id']!=a['id'] or o['action']!=11 or o['target'] is not None):return
        before,after=motion['before'],motion['after']
        moved=(before['region']!=after['region'] or abs(before['x']-after['x'])>1e-9 or abs(before['y']-after['y'])>1e-9)
        goal=self.goals.setdefault(spec['id'],{'id':spec['id'],'destination':deepcopy(spec),
            'status':'active','stalled':0,'evidence':[]})
        goal['evidence'].append(record['sequence']);goal['stalled']=0 if moved else goal['stalled']+1
        if moved:
            goal['status']='active';goal['motion_return_event']=record['sequence']
        elif goal['stalled']>=3:
            goal.update(status='motion-unresolved',next_probe_tick=e['time']+8)
        review=motion.get('exploration_review')
        if review and review['goal']['id']==spec['id'] and review['status']=='reached-observed-position':goal['status']='reached-observed-position'

    def choose(self,proposed,decision):
        goal=self.goals.get(decision['goal_id'])
        if not goal or goal['status']!='motion-unresolved':return proposed,decision
        probe=proposed.time>=goal['next_probe_tick'];action=11 if probe else 8
        return replace(proposed,action=action,decision=DECISION_FROM_ACTION[action],target=None),{
            **decision,'reason':'probe-world-motion' if probe else 'wait-before-world-motion-probe',
            'selected_action':action,'evidence':list(goal['evidence']),
            'uncertainty':'movement failed; body and environment causes remain unknown'}

    def assistance_request(self):
        requested={r['goal_id'] for r in self.requests}
        for goal in self.goals.values():
            if goal['status']=='motion-unresolved' and goal['id'] not in requested:
                return {'operation':'request-world-motion-help','goal_id':goal['id'],
                    'origin':'own-observed-world-motion-failure','evidence':list(goal['evidence']),
                    'observed_motion_attempts':len(goal['evidence']),
                    'message':'I tried to move but my position did not change. Can you help investigate?',
                    'requested_help':'investigate movement in this situation',
                    'unknowns':['whether the body or surroundings prevented movement','whether the limitation is temporary']}
        return None

    def review(self):
        return {'world_motion_reviews':deepcopy(list(self.goals.values())),
                'world_motion_requests':deepcopy(self.requests)}
