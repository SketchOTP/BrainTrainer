"""Passive, pre-execution forecasts for the existing brain-selected eat lifecycle.

No policy action, target, effort, world input, or food outcome is supplied here.
A host can execute unchanged through ``tick`` and report its own external
opportunity timeout through ``record_timeout``. These forecasts concern this
example host, not native Docking Station action prediction.
"""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile


class CompleteActionObserver:
    SCHEMA = 'creature-brain-complete-action-observer-v2'
    CHECKPOINT_SCHEMA = 'creature-brain-observed-individual-v2'
    PRIOR_PROBABILITY = .5
    PRIOR_COST = .5
    PRIOR_MASS = 2.0
    CONTEXT_MASS = 4.0
    INSUFFICIENT_EVIDENCE_COUNT = 5
    TERMINAL_LEDGER_LIMIT = 512

    def __init__(self):
        self.baseline = {}
        self.contextual = {}
        self.pending = {}
        self.latest_forecast = None
        self.latest_terminal = None
        self.terminal_count = 0
        self.terminal_watermark = -1
        self.terminal_ids = []

    @staticmethod
    def _key(*values):
        return json.dumps(values,separators=(',',':'),allow_nan=False)

    @staticmethod
    def _state(table, key):
        return table.get(key, {'observed':0,'completed':0,'cost_count':0,'cost_sum':0.,'unknown':0})

    def _forecasts(self, host, choice, objects, deadline):
        target=next((o for o in objects if o.identity==choice.target),None)
        if target is None: # target will be reported unknown by the executor
            distance=None;contact=None
        else:
            distance=float(target.distance);contact=bool(target.contact)
        if distance is None:dbin='unknown'
        elif distance<=.85:dbin='contact'
        elif distance<=2.:dbin='near'
        else:dbin='far'
        normal=host.model.predict(choice.action,'walking','normal') if hasattr(host,'model') else None
        effort=host.model.predict(choice.action,'walking','effort') if hasattr(host,'model') else None
        # Only prior motor estimates, never true body strength, future selected
        # mode, seed, task phase, or object value, enter the forecast context.
        if normal is None or normal['observations']==0:mbin='unobserved'
        elif normal['success_probability']<.4:mbin='low'
        elif normal['success_probability']<.7:mbin='medium'
        else:mbin='high'
        policy=getattr(host,'condition','walking')
        remaining=max(0,deadline-host.time)
        horizon='short' if remaining<=8 else 'medium' if remaining<=16 else 'long'
        bkey=self._key(choice.action,policy)
        ckey=self._key(choice.action,policy,dbin,mbin,horizon)
        b=self._state(self.baseline,bkey);c=self._state(self.contextual,ckey)
        p=(self.PRIOR_MASS*self.PRIOR_PROBABILITY+b['completed'])/(self.PRIOR_MASS+b['observed'])
        cost=(self.PRIOR_MASS*self.PRIOR_COST+b['cost_sum'])/(self.PRIOR_MASS+b['cost_count'])
        cp=(self.CONTEXT_MASS*p+c['completed'])/(self.CONTEXT_MASS+c['observed'])
        cc=(self.CONTEXT_MASS*cost+c['cost_sum'])/(self.CONTEXT_MASS+c['cost_count'])
        context={'distance':distance,'contact':contact,'distance_bin':dbin,'hunger':float(host.hunger),
                 'energy':float(host.energy),'reserve':float(host.reserve),
                 'time_remaining':remaining,'horizon_bin':horizon,'motor_normal':deepcopy(normal),
                 'motor_effort':deepcopy(effort),'motor_bin':mbin,'policy':policy}
        return {'kind':'forecast','action_id':choice.id,'action':choice.action,'target':choice.target,
                'start_tick':host.time,'deadline':deadline,'context':context,
                'baseline':{'model':'historical-action-policy','schema':self.SCHEMA,
                            'completion_probability':p,'expected_reserve_cost':cost,
                            'evidence_count':b['observed'],'cost_evidence_count':b['cost_count'],
                            'prior_only':b['observed']==0,
                            'insufficient_evidence':b['observed']<self.INSUFFICIENT_EVIDENCE_COUNT},
                'candidate':{'model':'contextual-motor-action','schema':self.SCHEMA,
                             'completion_probability':cp,'expected_reserve_cost':cc,
                             'evidence_count':c['observed'],'cost_evidence_count':c['cost_count'],
                             'shared_evidence_count':b['observed'],
                             'prior_only':b['observed']==0 and c['observed']==0,
                             'insufficient_evidence':c['observed']<self.INSUFFICIENT_EVIDENCE_COUNT},
                '_baseline_key':bkey,'_context_key':ckey}

    def _start(self, host, choice, objects, opportunity_deadline):
        # This host owns monotonic numeric tick IDs. A watermark preserves
        # idempotency even after old entries leave the bounded ledger.
        if choice.id!=str(host.time) or int(choice.id)<=self.terminal_watermark or choice.id in self.pending:
            raise ValueError('duplicate or invalid host action id')
        own_deadline=host.time+host.ACTION_TICKS
        deadline=own_deadline if opportunity_deadline is None else min(own_deadline,opportunity_deadline)
        if not isinstance(deadline,int) or isinstance(deadline,bool) or deadline<=host.time:
            raise ValueError('deadline must be after the action starts')
        forecast=self._forecasts(host,choice,objects,deadline)
        self.pending[choice.id]={'forecast':deepcopy(forecast),'cost':0.,'motor_attempts':0,
                                 'motor_failures':0,'motor_unknowns':0}
        public={k:deepcopy(v) for k,v in forecast.items() if not k.startswith('_')}
        self.latest_forecast=deepcopy(public)
        return public

    def _finish(self, action_id, target, terminal, tick, reason=None):
        pending=self.pending.get(action_id)
        if pending is None or pending['forecast']['target']!=target:return None
        if terminal not in ('completed','interrupted','timeout','unknown'):
            raise ValueError('invalid terminal outcome')
        forecast=pending['forecast'];cost=pending['cost']
        # Unknown/unobserved execution is censored for completion and cost.
        for table,key in ((self.baseline,forecast['_baseline_key']),(self.contextual,forecast['_context_key'])):
            item=table.setdefault(key,{'observed':0,'completed':0,'cost_count':0,'cost_sum':0.,'unknown':0})
            if terminal=='unknown':item['unknown']+=1
            else:
                item['observed']+=1;item['completed']+=int(terminal=='completed')
                item['cost_count']+=1;item['cost_sum']+=cost
        del self.pending[action_id]
        self.terminal_count+=1
        self.terminal_watermark=max(self.terminal_watermark,int(action_id))
        self.terminal_ids.append({'action_id':action_id,'target':target,'terminal':terminal})
        if len(self.terminal_ids)>self.TERMINAL_LEDGER_LIMIT:self.terminal_ids.pop(0)
        result={'kind':'terminal','action_id':action_id,'target':target,'terminal':terminal,
                'reason':reason,'end_tick':tick,'observed_cost':cost,
                'motor_attempts':pending['motor_attempts'],'motor_failures':pending['motor_failures'],
                'motor_unknowns':pending['motor_unknowns'],
                'forecast':{k:deepcopy(v) for k,v in forecast.items() if not k.startswith('_')}}
        self.latest_terminal=deepcopy(result)
        return result

    def tick(self, host, *, opportunity_deadline=None):
        """Execute exactly one original host tick and emit separate observer records."""
        original=host._execute_lifecycle
        previous=host.__dict__.get('_execute_lifecycle',None)
        had_previous='_execute_lifecycle' in host.__dict__
        records=[]
        def observe(choice,objects):
            old=host.active_action
            interrupted=old is not None and (choice.action!=12 or
                (choice.target is not None and choice.target!=old['choice']['target']))
            if choice.action==12 and choice.target is not None and (old is None or interrupted):
                records.append(self._start(host,choice,objects,opportunity_deadline))
            motor_start=len(host.motor_records)
            executed,target,outcome,events=original(choice,objects)
            for m in host.motor_records[motor_start:]:
                pending=self.pending.get(m['executing_action_id'])
                if pending is not None and pending['forecast']['target']==m['executing_target']:
                    pending['cost']+=m['cost'];pending['motor_attempts']+=1
                    pending['motor_failures']+=m['motor_success'] is False
                    pending['motor_unknowns']+=m['motor_success'] is None
            for event in events:
                event_type=event['event']
                if event_type=='interrupted':kind='interrupted'
                elif event_type=='failed':kind='unknown'
                elif event_type=='completed':kind='completed' if outcome.completed else 'unknown'
                else:continue
                item=self._finish(event['action_id'],event['target'],kind,host.time+1,event.get('reason'))
                if item:records.append(item)
            return executed,target,outcome,events
        host._execute_lifecycle=observe
        try:event=host.tick()
        finally:
            if had_previous:host._execute_lifecycle=previous
            else:del host._execute_lifecycle
        for lifecycle in event['lifecycle_events']:
            if lifecycle['event']=='cancelled':
                item=self._finish(lifecycle['action_id'],lifecycle['target'],'timeout',host.time,lifecycle.get('reason'))
                if item:records.append(item)
        return {'host_event':event,'action_prediction_events':records}

    def record_timeout(self, *, action_id, target, tick, reason='opportunity-timeout'):
        """Record an actual external host timeout after its action was cancelled."""
        return self._finish(action_id,target,'timeout',tick,reason)

    def to_dict(self):
        return {'schema':self.SCHEMA,'baseline':deepcopy(self.baseline),'contextual':deepcopy(self.contextual),
                'pending':deepcopy(self.pending),'latest_forecast':deepcopy(self.latest_forecast),
                'latest_terminal':deepcopy(self.latest_terminal),'terminal_count':self.terminal_count,
                'terminal_watermark':self.terminal_watermark,'terminal_ids':deepcopy(self.terminal_ids)}

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict) or data.get('schema')!=cls.SCHEMA:raise ValueError('invalid observer checkpoint')
        result=cls()
        for key in ('baseline','contextual','pending'):
            if not isinstance(data.get(key),dict):raise ValueError('invalid observer field')
            setattr(result,key,deepcopy(data[key]))
        result.latest_forecast=deepcopy(data['latest_forecast']);result.latest_terminal=deepcopy(data['latest_terminal'])
        result.terminal_count=data['terminal_count']
        result.terminal_watermark=data['terminal_watermark'];result.terminal_ids=deepcopy(data['terminal_ids'])
        if type(result.terminal_count) is not int or result.terminal_count<0:raise ValueError('invalid terminal count')
        if (type(result.terminal_watermark) is not int or result.terminal_watermark < -1 or
                not isinstance(result.terminal_ids,list) or len(result.terminal_ids)>cls.TERMINAL_LEDGER_LIMIT or
                len(result.terminal_ids)>result.terminal_count):raise ValueError('invalid terminal ledger')
        seen=set()
        for item in result.terminal_ids:
            if (not isinstance(item,dict) or not isinstance(item.get('action_id'),str) or
                    not item['action_id'].isdigit() or int(item['action_id'])>result.terminal_watermark or
                    item['action_id'] in seen or item.get('terminal') not in ('completed','interrupted','timeout','unknown')):
                raise ValueError('invalid terminal ledger entry')
            seen.add(item['action_id'])
        for table in (result.baseline,result.contextual):
            for key,item in table.items():
                if not isinstance(key,str) or not isinstance(item,dict):raise ValueError('invalid evidence entry')
                for field in ('observed','completed','cost_count','unknown'):
                    if type(item.get(field)) is not int or item[field]<0:raise ValueError('invalid evidence count')
                if item['completed']>item['observed'] or item['cost_count']>item['observed']:
                    raise ValueError('inconsistent evidence counts')
                value=item.get('cost_sum')
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                    raise ValueError('invalid cost evidence')
        for aid,pending in result.pending.items():
            if (not isinstance(aid,str) or not aid.isdigit() or int(aid)<=result.terminal_watermark or
                    not isinstance(pending,dict) or not isinstance(pending.get('forecast'),dict) or
                    pending['forecast'].get('action_id')!=aid):raise ValueError('invalid pending forecast')
            cost=pending.get('cost')
            if isinstance(cost,bool) or not isinstance(cost,(int,float)) or not math.isfinite(cost) or cost<0:
                raise ValueError('invalid pending cost')
            for field in ('motor_attempts','motor_failures','motor_unknowns'):
                if type(pending.get(field)) is not int or pending[field]<0:raise ValueError('invalid pending counts')
            if pending['motor_failures']+pending['motor_unknowns']>pending['motor_attempts']:
                raise ValueError('inconsistent pending counts')
        return result


def observed_snapshot(host,observer):
    from inherited_preparation import prepared_snapshot
    return {'schema':CompleteActionObserver.CHECKPOINT_SCHEMA,'host':prepared_snapshot(host),'observer':observer.to_dict()}


def restore_observed(data):
    from inherited_preparation import restore_prepared
    if not isinstance(data,dict) or data.get('schema')!=CompleteActionObserver.CHECKPOINT_SCHEMA:
        raise ValueError('invalid observed checkpoint')
    return restore_prepared(data['host']),CompleteActionObserver.from_dict(data['observer'])


def save_observed(host,observer,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(observed_snapshot(host,observer),f,allow_nan=False);f.flush();os.fsync(f.fileno())
        os.replace(name,path);directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(name):os.unlink(name)


def load_observed(path):
    with Path(path).open() as f:return restore_observed(json.load(f))
