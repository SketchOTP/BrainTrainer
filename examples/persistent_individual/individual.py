"""Continuous, local-only example body for the recovered creature brain.

This is an example host, not a neural kernel or Docking Station archive.
No food value or preferred action is supplied to the brain before interaction.
"""
BASE_OBJECTS=frozenset(('object-0','object-1','toy'))

from contextlib import nullcontext
from copy import deepcopy
from dataclasses import asdict
import json
import os
from pathlib import Path
import random
import tempfile
import uuid

from creature_brain import DefaultBrain
from creature_brain.neural import DECISION_FROM_ACTION
from creature_brain.benchmark.action_lifecycle import LifecycleFoodExperiment
from creature_brain.benchmark.connection_freeze import freeze_drive_comb_tract_state
from creature_brain.benchmark.contract import ChosenAction, Observation, Outcome, PerceivedObject
from creature_brain.benchmark.food import _tuple_tree


class Individual(LifecycleFoodExperiment):
    SCHEMA = 'creature-brain-continuous-individual-v1'
    ACTION_TICKS = 32

    def __init__(self, program, *, seed=0, good_type=0, freeze_tract=False, identity=None):
        if good_type not in (0, 1) or type(freeze_tract) is not bool:
            raise ValueError('invalid world configuration')
        self.identity = identity or str(uuid.uuid4())
        self.freeze_tract = freeze_tract
        self.objects = {}
        self.last_event = None
        self.world = None
        super().__init__(program, seed=seed, embodiment='walking', condition='feedback',
                         task='preference', max_steps=32, opportunities_per_phase=20)
        self.initial_good = good_type

    @property
    def done(self):
        return False

    @property
    def phase(self):
        # The live world has fixed effects, not benchmark phase changes.
        return 'experience'

    def _reset_layout(self):
        # Called only at construction; ticks never reset the body or the world.
        self.position = self.velocity = 0.0
        self.positions = [0.5, -0.5]
        self.step_in_opportunity = 0
        self.objects = {
            'object-0': {'identity':'object-0','type_id':'food-a','category':3,'x':.5,'visible':True,'food':True},
            'object-1': {'identity':'object-1','type_id':'food-b','category':8,'x':-.5,'visible':True,'food':True},
            'toy': {'identity':'toy','type_id':'toy','category':12,'x':1.4,'visible':True,'food':False},
        }

    def place(self, identity, x, visible=True):
        if self.objects.get(identity,{}).get('function')=='berry-plot':raise ValueError('garden plots have fixed native locations')
        if identity not in self.objects or type(visible) is not bool or isinstance(x,bool) or not isinstance(x,(int,float)):
            raise ValueError('invalid object placement')
        import math
        if not math.isfinite(x) or not -50 <= x <= 50: raise ValueError('position outside world')
        if self.world is not None:
            from world_body import nearest
            x,y=nearest(self.world['region'],x,self.world['y'],self.world['pack_sha256'])
            self.objects[identity].update(y=float(y),region=self.world['region'])
        self.objects[identity]['x'] = float(x)
        self.objects[identity]['visible'] = visible

    def observe(self):
        values=[]
        for obj in self.objects.values():
            if not obj['visible']: continue
            if self.world is not None and obj.get('region')!=self.world['region']:continue
            distance=abs(obj['x']-self.position) if self.world is None else ((obj['x']-self.position)**2+(obj['y']-self.world['y'])**2)**.5
            actions=(0,1,4,5,10,11) if obj.get('function') else (0,4,5,10,11,12) if obj['food'] else (0,4,5,10,11)
            if obj.get('function')=='berry-plot' and obj['state']==0:actions=(0,4,5,10,11)
            values.append(PerceivedObject(obj['identity'],obj['type_id'],obj['category'],
                obj['x']-self.position,distance,distance<=.85,
                f"{obj['type_id']}:state={obj['state']}" if obj.get('function') else obj['type_id'],actions))
        from garden import stored_food
        values.extend(stored_food(self))
        return Observation(self.time,tuple(values),self.energy,self.hunger)

    @staticmethod
    def device_state(*, function, type_id, delay):
        if function not in ('switch','counter','delayed-switch','inert') or not isinstance(type_id,str) or not type_id.strip():
            raise ValueError('device requires a function and percept type')
        if type(delay) is not int or not 1<=delay<=8:raise ValueError('invalid device delay')
        return dict(function=function,type_id=type_id,food=False,state=0,delay=delay,pending_activation=0)

    def configure_device(self, identity, *, function, type_id, delay=2):
        if self.objects.get(identity,{}).get('function')=='berry-plot':raise ValueError('garden plots cannot be reconfigured as devices')
        if identity not in self.objects:raise ValueError('device requires an existing object')
        state=self.device_state(function=function,type_id=type_id,delay=delay)
        self.objects[identity].update(state)

    def add_world_device(self, identity, *, label, function, type_id, delay, region, x, y):
        from world_body import pack,walkable
        if (not isinstance(identity,str) or not identity.strip() or identity in self.objects or
            identity.startswith(('basket-','berry-')) or not isinstance(label,str) or not label.strip()):
            raise ValueError('new device requires a unique identity and label')
        if (self.world is None or not isinstance(region,str) or region not in pack(self.world['pack_sha256'])['maps'] or
            type(x) is not int or type(y) is not int or not walkable(region,x,y,self.world['pack_sha256'])):
            raise ValueError('new device requires a traversable world cell')
        if any(o.get('region')==region and o['x']==x and o.get('y')==y for o in self.objects.values()):
            raise ValueError('world cell already contains an object')
        state=self.device_state(function=function,type_id=type_id,delay=delay)
        self.objects[identity]=dict(identity=identity,label=label,category=12,x=float(x),y=float(y),
            region=region,visible=True,**state)
        self.objects=dict(sorted(self.objects.items()))

    def _execute(self, action, target):
        if target is not None and target.identity in ('basket-oran','basket-pecha'):
            from garden import eat_stored
            return eat_stored(self,action,target)
        obj=self.objects.get(target.identity) if target is not None else None
        if obj is not None and obj.get('function')=='berry-plot' and action.action==1:
            from garden import harvest
            return harvest(self,action,target)
        if obj is not None and obj.get('function') and action.action==1:
            if action.target!=target.identity:
                return Outcome(action.id,action.target,action.action,False,'target-mismatch',0.,0.)
            if not target.contact:
                return Outcome(action.id,action.target,action.action,False,'not-in-contact',0.,0.)
            if obj['function']=='switch':obj['state']=1-obj['state']
            elif obj['function']=='counter':obj['state']+=1
            elif obj['function']=='delayed-switch':
                obj['pending_activation']+=1
                if obj['pending_activation']>=obj['delay']:
                    obj['state']=1-obj['state'];obj['pending_activation']=0
            return Outcome(action.id,action.target,action.action,True,'activated',0.,0.)
        return super()._execute(action,target)

    def _move(self, direction):
        # The example has a finite one-dimensional room; movement itself is
        # still performed by the existing walking adapter.
        super()._move(direction)
        if self.world is None:
            self.position=max(-20.0,min(20.0,self.position))

    def intrinsic_actions(self):
        return (10,11)+((0,) if getattr(self,'rest_enabled',False) else ())+((8,) if getattr(self,'hold_enabled',False) else ())

    def tick(self, *, recall=None, executive=None):
        self._route_observation=None
        from garden import advance
        garden_growth=advance(self)
        obs=self.observe()
        if recall is not None:
            import math
            if (not isinstance(recall,dict) or
                type(recall.get('category')) is not int or
                type(recall.get('action')) is not int or
                recall['action'] not in DECISION_FROM_ACTION or
                DECISION_FROM_ACTION[recall['action']] >= 13 or
                isinstance(recall.get('strength'),bool) or
                not isinstance(recall.get('strength'),(int,float)) or
                not math.isfinite(recall['strength']) or not 0 < recall['strength'] <= 1 or
                not any(o.identity==recall.get('target') and o.category==recall['category']
                        and recall['action'] in o.available_actions for o in obs.objects)):
                raise ValueError('recall must refer to a visible, available sensory cue')
        self._deliver_pending()
        inputs={'visn':{o.category:.5 for o in obs.objects},'driv':{2:obs.hunger}}
        if recall is not None:
            inputs['noun']={recall['category']:recall['strength']}
            inputs['verb']={DECISION_FROM_ACTION[recall['action']]:recall['strength']}
        chemistry=self.brain.chemicals.copy();chemistry[150]=self.hunger
        with freeze_drive_comb_tract_state(self.brain) if self.freeze_tract else nullcontext():
            result=self.brain.tick(inputs,chemistry)
        selected=next((o for o in obs.objects if o.category==result.attention),None)
        choice=ChosenAction(f'{self.time}',self.time,result.action,result.attention,result.decision,
                            selected.identity if selected else None)
        proposal=choice
        position_before=self.position
        world_before=None
        if self.world is not None:
            from world_body import pose
            world_before=pose(self)
        if executive is not None:
            choice=executive(choice,obs)
            if (not isinstance(choice,ChosenAction) or choice.id!=proposal.id or choice.time!=proposal.time or
                not (any(o.identity==choice.target and choice.action in o.available_actions for o in obs.objects) or
                     (choice.target is None and choice.action in self.intrinsic_actions()))):
                if choice!=proposal:
                    raise ValueError('executive selected an invalid action or target')
        executed,target,outcome,events=self._execute_lifecycle(choice,obs.objects)
        if outcome.completed and outcome.status=='consumed' and target is not None:
            self.objects[target.identity]['visible']=False
        if self.active_action is not None and self.time-self.active_action['choice']['time']+1>=self.ACTION_TICKS:
            events.append({'event':'cancelled','reason':'action-timeout','action_id':self.active_action['choice']['id'],
                           'target':self.active_action['choice']['target']})
            self.active_action=None
        self.time+=1
        self.last_event={'time':self.time,'observation':asdict(obs),'choice':asdict(choice),
                         'executed_action':asdict(executed),'outcome':asdict(outcome),
                         'lifecycle_events':events,'pending_count':len(self.pending)}
        if executive is not None:
            self.last_event['observation_after']=asdict(self.observe())
            self.last_event['substrate_proposal']=asdict(proposal)
            self.last_event['body_motion']={'before':position_before,'after':self.position}
        if self.world is not None:
            self.last_event['world_motion']={'before':world_before,'after':pose(self)}
            if self._route_observation is not None:
                self.last_event['world_motion']['route_progress']=self._route_observation
        if self.world is not None and 'garden' in self.world:
            self.last_event['garden_growth']={'ripened':garden_growth,'basis':'world-tick-regrowth'}
        return deepcopy(self.last_event)

    def snapshot(self):
        return {'schema':self.SCHEMA,'identity':self.identity,'freeze_tract':self.freeze_tract,
                'config':deepcopy(self.config),'brain':self.brain.to_dict(),'rng':self.rng.getstate(),
                'initial_good':self.initial_good,'time':self.time,'energy':self.energy,'hunger':self.hunger,
                'position':self.position,'velocity':self.velocity,'objects':deepcopy(self.objects),
                'pending':deepcopy(self.pending),'active_action':deepcopy(self.active_action),
                'last_event':deepcopy(self.last_event),**({'world':deepcopy(self.world)} if self.world is not None else {})}

    @classmethod
    def restore(cls, data):
        if not isinstance(data,dict) or data.get('schema')!=cls.SCHEMA: raise ValueError('invalid individual checkpoint')
        obj=cls.__new__(cls)
        obj.identity=data['identity'];obj.freeze_tract=data['freeze_tract'];obj.config=deepcopy(data['config'])
        if not isinstance(obj.identity,str) or not obj.identity or type(obj.freeze_tract) is not bool:
            raise ValueError('invalid identity or control')
        obj.brain=DefaultBrain.from_dict(data['brain']);obj.rng=random.Random();obj.rng.setstate(_tuple_tree(data['rng']))
        obj.initial_good=data['initial_good'];obj.time=data['time'];obj.energy=data['energy'];obj.hunger=data['hunger']
        obj.position=data['position'];obj.velocity=data['velocity'];obj.objects=deepcopy(data['objects'])
        obj.world=deepcopy(data.get('world'))
        if obj.world is not None:
            from world_body import validate
            validate(obj.world,obj.position,obj.objects)
        obj.pending=deepcopy(data['pending']);obj.active_action=deepcopy(data['active_action']);obj.last_event=deepcopy(data['last_event'])
        if obj.initial_good not in (0,1) or type(obj.time) is not int or obj.time<0:
            raise ValueError('invalid world state')
        from garden import validate as validate_garden, plots
        garden_pack=(obj.world or {}).get('pack_sha256')
        required=BASE_OBJECTS|(set(plots(garden_pack)) if (obj.world or {}).get('garden') is not None else set())
        if not required<=set(obj.objects):raise ValueError('missing world objects')
        for key in set(obj.objects)-required:
            item=obj.objects[key]
            if (obj.world is None or not isinstance(key,str) or not key.strip() or key.startswith(('basket-','berry-')) or
                item.get('identity')!=key or not isinstance(item.get('label'),str) or not item['label'].strip() or
                type(item.get('category')) is not int or item['category']!=12 or type(item.get('visible')) is not bool):
                raise ValueError('invalid added device identity')
            obj.device_state(function=item.get('function'),type_id=item.get('type_id'),delay=item.get('delay'))
        validate_garden(obj)
        for item in obj.objects.values():
            if item.get('function')=='berry-plot':continue
            if 'function' in item and (item['function'] not in ('switch','counter','delayed-switch','inert') or
                type(item.get('state')) is not int or item['state']<0 or
                (item['function'] in ('switch','delayed-switch') and item['state'] not in (0,1)) or item.get('food') is not False):
                raise ValueError('invalid device state')
            if item.get('function')=='delayed-switch' and (type(item.get('delay')) is not int or not 1<=item['delay']<=8 or type(item.get('pending_activation')) is not int or not 0<=item['pending_activation']<item['delay']):
                raise ValueError('invalid delayed device state')
        obj.task='preference';obj.mirror=False;obj.food_index=0;obj.trace=False
        obj.positions=[obj.objects['object-0']['x'],obj.objects['object-1']['x']]
        obj.opportunity=0;obj.step_in_opportunity=0;obj.history=[]
        return obj

    def save(self,path):
        """Atomically replace a local portable checkpoint."""
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
        try:
            with os.fdopen(fd,'w') as stream:
                json.dump(self.snapshot(),stream,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            os.replace(name,path)
        finally:
            if os.path.exists(name):os.unlink(name)

    @classmethod
    def load(cls,path):
        with Path(path).open() as stream:return cls.restore(json.load(stream))
