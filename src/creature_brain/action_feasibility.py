"""Experience-derived exclusions for currently unavailable action proposals.

Only attributed execution failures establish evidence. A changed current
availability observation overrides the exclusion; old failure is not incapability.
"""
from dataclasses import replace
from copy import deepcopy
from .neural import DECISION_FROM_ACTION

class ActionFeasibility:
    def __init__(self):self.failures={}

    def observe(self,record):
        if record['kind']!='experience':return
        event=record['payload'];action=event['executed_action'];outcome=event['outcome']
        if (outcome['action_id']!=action['id'] or outcome['action']!=action['action'] or
            outcome['target']!=action['target'] or outcome['completed']):return
        target=next((o for o in event['observation']['objects'] if o['identity']==action['target']),None)
        if outcome['status']=='unavailable-action' and target and action['action'] not in target['available_actions']:
            key=('unavailable-action',target['type_id'],action['action'])
        elif outcome['status']=='no-target' and action['target'] is None:
            key=('no-target',None,action['action'])
        else:return
        row=self.failures.setdefault(key,{'reason':key[0],'type_id':key[1],'action':key[2],'count':0,'evidence':[]})
        row['count']+=1;row['evidence'].append(record['sequence']);del row['evidence'][:-8]

    def alternative(self,proposed,observation, *, intrinsic_actions=()):
        if proposed.target is None and proposed.action in intrinsic_actions:return None
        target=next((o for o in observation.objects if o.identity==proposed.target),None)
        if target:
            if proposed.action in target.available_actions:return None
            key=('unavailable-action',target.type_id,proposed.action)
        elif proposed.target is None:key=('no-target',None,proposed.action)
        else:return None # A missing formerly selected target is a separate unresolved case.
        row=self.failures.get(key)
        if row is None or row['count']<2:return None
        selected=replace(proposed,action=8,decision=DECISION_FROM_ACTION[8],target=None)
        return selected,{'reason':'defer-repeatedly-unavailable-action','goal_id':None,
            'proposal_action':proposed.action,'selected_action':8,'proposal_target':proposed.target,
            'observed_failure':row['reason'],'evidence':list(row['evidence']),
            'failure_count':row['count'],'knowledge_scope':'observed failures; current availability may change',
            'alternative':'intrinsic quiet hold; ordinary activity selection continues next tick'}

    def review(self):
        return {'action_feasibility':deepcopy(list(self.failures.values())),
            'feasibility_scope':'attributed unavailable-action and no-target outcomes only; no inference from imagined attempts'}
