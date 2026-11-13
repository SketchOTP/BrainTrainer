"""Original experience memory and learned sensory recall for the pet.

This is a bounded host-side associative learner, not a claim about native
Creatures cognition. It learns category/action values from observed effects;
it never directly selects a motor action.
"""
from collections import deque
from copy import deepcopy
import math
from . import vision

MODEL='experience-memory-v1'
MAX_EPISODES=96
MAX_ASSOCIATIONS=560  # 40 categories * 14 actions
MAX_RISKS=128
MAX_PERCEPTS=64
MAX_VISUAL_EXAMPLES=128


class ExperienceMemory:
    def __init__(self):
        self.episodes=deque(maxlen=MAX_EPISODES)
        self.associations={}
        self.last_recorded={}
        self.total_observations=0
        self.risks={}
        self.percept_history={}
        self.visual_examples=[]
        self._visual_cache={}
        self.repetition={'target':None,'action':None,'elapsed':0.0,'until':0.0,'cooldown':0.0,'category':None,'cue_target':None,'cue_category':None,'cue_action':None,'blocked_action':None}
        self.aversion={'target':None,'started':0.0,'cooldown':0.0,'cooldown_target':None}

    def observe(self, *, now, target, category, action, result, drives, water_before, position=None, percepts=(), visual=None):
        """Record experienced consequences, rate-limited per object/action.

        The scalar valuation is an explicit host design. It rewards observed
        intake in proportion to need and stimulation in proportion to boredom,
        and penalizes observed toxin/injury. Delayed chemistry is not assigned
        to an arbitrary current action.
        It does not map any category to an action.
        """
        if target is None or category is None or result.status in ('moved','idle','sleeping','dead','no-target','unavailable-action','forage-wait','forage-empty','cache-empty','resting','dropped'):
            return
        harm=2.0*result.toxin+result.injury
        key=f'{target}|{action}'
        # A newly harmful outcome must not be hidden by the sampling limit.
        if now-self.last_recorded.get(key,-1e12)<1.0 and not (harm>0 and target not in self.risks):return
        self.last_recorded[key]=now
        if len(self.last_recorded)>256:
            oldest=min(self.last_recorded,key=self.last_recorded.get);del self.last_recorded[oldest]
        hunger=max(drives[1:4]);boredom=drives[11]
        positive=(result.consumed*(.25+.75*hunger)
                  +result.water*max(0.0,1-water_before)
                  +result.stimulation*.04*(.1+boredom))
        if harm>0:
            self.risks[target]={'action':action,'category':category,'harm':harm,'last':now,'safe':0}
            if len(self.risks)>MAX_RISKS:
                del self.risks[min(self.risks,key=lambda k:self.risks[k]['last'])]
        elif target in self.risks and self.risks[target]['action']==action and result.consumed>0:
            # A previously harmful object may change; clear its warning only
            # after repeated observed safe outcomes for the same action.
            self.risks[target]['safe']+=1
            if self.risks[target]['safe']>=5:del self.risks[target]
        # Percepts are explicit observable labels, never derived from the
        # hidden toxin field. Count distinct objects, not repeated ticks.
        if result.consumed>0 or harm>0:
            if visual is not None:
                pixels=vision.validate(visual)
                # One prototype per object/action; repeated frames do not
                # masquerade as independent examples.
                existing=next((x for x in self.visual_examples if x['target']==target and x['action']==action),None)
                label='harmful' if target in self.risks else 'safe'
                record={'target':target,'category':category,'action':action,'pixels':pixels,'label':label,'time':now}
                if existing is not None:self.visual_examples.remove(existing)
                self.visual_examples.append(record)
                if len(self.visual_examples)>MAX_VISUAL_EXAMPLES:self.visual_examples.pop(0)
                self._visual_cache.clear()
            for percept in percepts:
                if percept not in self.percept_history and len(self.percept_history)>=MAX_PERCEPTS:continue
                entry=self.percept_history.setdefault(percept,{})
                group=entry.setdefault(str(action),{'harmful':[],'safe':[]})
                positive_id='harmful' if harm>0 else 'safe';opposite='safe' if harm>0 else 'harmful'
                if target in group[opposite]:group[opposite].remove(target)
                if target not in group[positive_id]:
                    group[positive_id].append(target)
                    del group[positive_id][:-16]
        # Delayed biochemical changes can originate in an earlier action;
        # do not attach those pulses to whichever action happens to be current.
        value=max(-1.0,min(1.0,positive-harm))
        assoc_key=f'{category}:{action}'
        row=self.associations.setdefault(assoc_key,{'count':0,'mean':0.0,'consumed':0.0,'water':0.0,'toxin':0.0,'stimulation':0.0})
        row['count']+=1
        # Bounded recency weighting permits adaptation when outcomes reverse.
        alpha=max(.05,1.0/min(row['count'],20))
        row['mean']+=alpha*(value-row['mean'])
        for name in ('consumed','water','toxin','stimulation'):
            row[name]+=alpha*(getattr(result,name)-row[name])
        self.total_observations+=1
        self.episodes.append({'time':now,'target':target,'category':category,'action':action,
                              'outcome':result.status,'value':value,'consumed':result.consumed,
                              'water':result.water,'toxin':result.toxin,'stimulation':result.stimulation,
                              'position':list(position) if position is not None else None,
                              'hunger':hunger,'water_before':water_before,'percepts':list(percepts)})

    def note_action(self, *, now, target, category, action, status, dt):
        """Remember sustained, non-locomotor actions; never actuate motors."""
        state=self.repetition
        eligible=target is not None and category is not None and action not in (9,10,11) and status not in ('moved','idle','sleeping','dead','no-target','unavailable-action','resting')
        if not eligible:
            state['target']=None;state['action']=None;state['category']=None;state['elapsed']=0.0
            return
        if state['target']==target and state['action']==action:
            state['elapsed']+=dt
        else:
            state.update(target=target,action=action,category=category,elapsed=dt)
        if state['elapsed']>=4.0 and now>=state['cooldown'] and now>=state['until']:
            state['until']=now+12.0;state['cooldown']=now+26.0
            state['cue_target']=target;state['cue_category']=category
            state['cue_action']=5 if action==0 else 0
            state['blocked_action']=action

    def _learned_hazard(self,item):
        if item.object_id in self.risks:return True
        return self.classify_visual(vision.pixels_for(item))=='harmful'

    def classify_visual(self,pixels):
        """Nearest visual prototypes; abstain with insufficient or ambiguous evidence."""
        if pixels is None:return 'unknown'
        pixels=vision.validate(pixels)
        key=tuple(pixels)
        if key in self._visual_cache:return self._visual_cache[key]
        latest={}
        for example in self.visual_examples:
            # One object cannot independently count as both safe and harmful.
            old=latest.get(example['target'])
            if old is None or example['label']=='harmful' or old['label']!='harmful':latest[example['target']]=example
        groups={'safe':{},'harmful':{}}
        for example in latest.values():groups[example['label']][example['target']]=example['pixels']
        if any(len(group)<2 for group in groups.values()):return 'unknown'
        d={label:min(vision.distance(pixels,p) for p in group.values()) for label,group in groups.items()}
        result='unknown' if min(d.values())>.12 or abs(d['safe']-d['harmful'])<.005 else min(d,key=d.get)
        if len(self._visual_cache)>=256:self._visual_cache.clear()
        self._visual_cache[key]=result
        return result

    def intention(self,world,creature):
        """Learned recall plus original generic aversion/habituation cues."""
        if creature.command is not None or not creature.body.alive or creature.body.sleep_state!='awake':return None
        pose=world.agents[creature.creature_id];now=world.time
        danger=[]
        for item in world.objects.values():
            if not item.enabled or item.stored_in is not None or (item.kind=='food' and item.quantity<=0) or item.holder not in (None,pose.creature_id):continue
            distance=math.hypot(item.x-pose.x,item.y-pose.y)
            if distance<4 and self._learned_hazard(item):danger.append((distance,item.object_id,item))
        a=self.aversion
        eligible=[entry for entry in danger if now>=a['cooldown'] or entry[1]!=a['cooldown_target']]
        item=min(eligible)[2] if eligible else None
        if item is not None:
            if a['target']!=item.object_id:a['target']=item.object_id;a['started']=now
            if now-a['started']<12:
                return {'target':item.object_id,'category':item.category,'action':5,'strength':.7,'source':'aversion'}
            a.update(target=None,started=now,cooldown=now+8,cooldown_target=item.object_id)
        elif not danger:a['target']=None
        r=self.repetition
        if now<r['until'] and r['cue_target'] in world.objects:
            item=world.objects[r['cue_target']]
            if item.enabled:return {'target':item.object_id,'category':item.category,'action':r['cue_action'],'strength':.7,'source':'habituation'}
        return self._survival_cue(world,creature) or self.recall(world,creature)

    def _survival_cue(self,world,creature):
        """Point the genome brain toward an available resource when a body signal is high.

        This is an original digital-world affordance adapter: it supplies a
        target and sensory cue, but the genome brain still selects the motor
        action. It does not create food, heal the body, or override behavior.
        """
        body=creature.body;pose=world.agents[creature.creature_id]
        drives=body.drives;chemicals=body.chemicals if hasattr(body,'kernel') else None
        if chemicals is None:return None
        available=[]
        hunger=max(drives[1:4]);energy=chemicals[34]
        if hunger>=.55 or energy<.45:
            for item in world.objects.values():
                if (not item.enabled or item.kind!='food' or item.quantity<=0
                        or item.stored_in is not None or item.holder not in (None,pose.creature_id)
                        or self._learned_hazard(item)):
                    continue
                distance=math.hypot(item.x-pose.x,item.y-pose.y)
                if distance<=world.vision_radius:
                    available.append((distance,item.object_id,item.category,'food',item))
            for item in world.objects.values():
                if not item.enabled or item.kind!='bush' or item.quantity<=0:continue
                distance=math.hypot(item.x-pose.x,item.y-pose.y)
                if distance<=world.vision_radius:
                    available.append((distance,item.object_id,item.category,'bush',item))
            if available:
                distance,identifier,category,kind,item=min(available)
                action=(4 if distance>max(world.interaction_radius,item.radius)
                        else 12 if kind=='food' else 1)
                return {'target':identifier,'category':category,'action':action,
                        'strength':.45,'source':'survival-affordance','need':'food'}

        water_level=chemicals[33]
        if water_level<.55 and world.habitat is not None:
            feature=next((f for f in world.habitat['features'] if f['kind']=='water'),None)
            if feature is not None:
                distance=math.hypot(feature['x']-pose.x,feature['y']-pose.y)
                cue=next((c for c in feature['cues'] if c['id']=='drink'),None)
                if cue:
                    return {'target':feature['id'],'category':cue['category'],
                            'action':4 if distance>feature['radius'] else cue['action'],
                            'strength':.45,'source':'survival-affordance','need':'water'}

        tired=max(drives[6],drives[7])
        if tired>=.65 and world.habitat is not None:
            feature=next((f for f in world.habitat['features'] if f['kind']=='shelter'),None)
            if feature is not None:
                distance=math.hypot(feature['x']-pose.x,feature['y']-pose.y)
                cue=next((c for c in feature['cues'] if c['id']=='sleep'),None)
                if cue:
                    return {'target':feature['id'],'category':cue['category'],
                            'action':cue['action'] if distance<=feature['radius']+1 else 4,
                            'strength':.45,'source':'survival-affordance','need':'rest'}

        lonely=drives[8]
        companions=[other for key,other in world.agents.items()
                    if key!=pose.creature_id and other.active]
        if lonely>=.65 and companions:
            other=min(companions,key=lambda row:math.hypot(row.x-pose.x,row.y-pose.y))
            distance=math.hypot(other.x-pose.x,other.y-pose.y)
            return {'target':other.creature_id,'category':other.category,
                    'action':4 if distance>world.interaction_radius else 8,
                    'strength':.45,'source':'survival-affordance','need':'company'}
        return None

    def recall(self, world, creature):
        """Offer a learned category/action association for a visible entity."""
        if creature.command is not None or not creature.body.alive or creature.body.sleep_state!='awake':return None
        pose=world.agents[creature.creature_id]; candidates=[];specifics={}
        drives=creature.body.drives
        chemicals=creature.body.chemicals if hasattr(creature.body,'kernel') else None
        hunger=max(max(drives[1:4])-.05, max(0,.4-chemicals[34]) if chemicals is not None else 0, 0)
        thirst=max(0,.9-chemicals[33]) if chemicals is not None else 0
        boredom=max(0,drives[11]-.1)
        for episode in self.episodes:
            k=(episode['target'],episode['action']);specifics.setdefault(k,[]).append(episode)
        for item in world.objects.values():
            if not item.enabled or item.stored_in is not None or (item.kind=='food' and item.quantity<=0) or item.holder not in (None,pose.creature_id):continue
            distance=math.hypot(item.x-pose.x,item.y-pose.y)
            if distance>world.vision_radius:continue
            if item.object_id in self.risks:continue
            pixels=vision.pixels_for(item)
            visual_class=self.classify_visual(pixels)
            if visual_class=='harmful':continue
            options=[]
            for key,row in self.associations.items():
                category,action=map(int,key.split(':'))
                if category==item.category and row['count']>=4:options.append((action,row))
            if visual_class=='safe':
                safe=[e for e in self.visual_examples if e['label']=='safe' and e['category'] is not None]
                if safe:
                    exemplar=min(safe,key=lambda e:vision.distance(pixels,e['pixels']))
                    row=self.associations.get(f"{exemplar['category']}:{exemplar['action']}")
                    if row is not None and row['count']>=2:options.append((exemplar['action'],row))
            for action,row in options:
                r=self.repetition
                if world.time<r['cooldown'] and item.object_id==r['cue_target'] and action==r['blocked_action']:continue
                # Specific experiences take precedence when this individual
                # object has been tried; category knowledge covers new IDs.
                specific=specifics.get((item.object_id,action),[])
                if len(specific)>=2:
                    effects={name:sum(e[name] for e in specific)/len(specific) for name in ('consumed','water','toxin','stimulation')}
                else:effects=row
                estimate=(effects['consumed']*hunger+effects['water']*thirst
                          +effects['stimulation']*.04*boredom-2*effects['toxin'])
                if estimate<=.002:continue
                score=estimate*min(1.0,row['count']/12)/(1+.08*distance)
                candidates.append((score,item.object_id,item.category,action))
        if not candidates:return None
        score,target,category,action=max(candidates)
        return {'target':target,'category':category,'action':action,'strength':.35,'source':'experience','predicted_value':score}

    def to_dict(self):
        return {'model':MODEL,'episodes':deepcopy(list(self.episodes)),'associations':deepcopy(self.associations),
                'last_recorded':dict(self.last_recorded),'total_observations':self.total_observations,
                'risks':deepcopy(self.risks),'percept_history':deepcopy(self.percept_history),
                'visual_examples':deepcopy(self.visual_examples),
                'repetition':deepcopy(self.repetition),'aversion':deepcopy(self.aversion)}

    @classmethod
    def from_dict(cls,data):
        if data is None:return cls()
        if not isinstance(data,dict) or data.get('model')!=MODEL:raise ValueError('unsupported experience memory')
        obj=cls();episodes=deepcopy(data.get('episodes'));associations=deepcopy(data.get('associations'));last=data.get('last_recorded');total=data.get('total_observations')
        if not isinstance(episodes,list) or len(episodes)>MAX_EPISODES or not isinstance(associations,dict) or len(associations)>MAX_ASSOCIATIONS or not isinstance(last,dict) or len(last)>256 or type(total) is not int or total<len(episodes):raise ValueError('invalid experience memory')
        for key,row in associations.items():
            try: cat,action=map(int,key.split(':'))
            except (ValueError,AttributeError):raise ValueError('invalid experience association') from None
            if not isinstance(row,dict) or not {'count','mean'}<=set(row) or set(row)-{'count','mean','consumed','water','toxin','stimulation'}:raise ValueError('invalid experience association')
            for name in ('consumed','water','toxin','stimulation'):row.setdefault(name,0.0)
            if not 0<=cat<40 or not 0<=action<14 or type(row['count']) is not int or row['count']<1 or isinstance(row['mean'],bool) or not isinstance(row['mean'],(int,float)) or not math.isfinite(row['mean']) or abs(row['mean'])>1:raise ValueError('invalid experience association')
            if any(isinstance(row[n],bool) or not isinstance(row[n],(int,float)) or not math.isfinite(row[n]) or row[n]<0 for n in ('consumed','water','toxin','stimulation')):raise ValueError('invalid experience effects')
        if any(not isinstance(k,str) or isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for k,v in last.items()):raise ValueError('invalid experience timestamps')
        for e in episodes:
            if not isinstance(e,dict) or not {'time','target','category','action','outcome','value','consumed','water','toxin'}<=set(e) or set(e)-{'time','target','category','action','outcome','value','consumed','water','toxin','stimulation','position','hunger','water_before','percepts'}:raise ValueError('invalid experience episode')
            e.setdefault('stimulation',0.0)
            e.setdefault('position',None);e.setdefault('hunger',0.0);e.setdefault('water_before',.5);e.setdefault('percepts',[])
            if not isinstance(e['target'],str) or not isinstance(e['outcome'],str) or type(e['category']) is not int or not 0<=e['category']<40 or type(e['action']) is not int or not 0<=e['action']<14:raise ValueError('invalid experience episode')
            if not isinstance(e['percepts'],list) or len(e['percepts'])>8 or any(not isinstance(v,str) or not v or len(v)>32 for v in e['percepts']) or len(set(e['percepts']))!=len(e['percepts']):raise ValueError('invalid experience percepts')
            if e['position'] is not None and (not isinstance(e['position'],list) or len(e['position'])!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in e['position'])):raise ValueError('invalid experience location')
            for name in ('time','value','consumed','water','toxin','stimulation','hunger','water_before'):
                if isinstance(e[name],bool) or not isinstance(e[name],(int,float)) or not math.isfinite(e[name]) or (name!='value' and e[name]<0) or (name=='value' and abs(e[name])>1):raise ValueError('invalid experience episode')
        risks=deepcopy(data.get('risks',{}));percepts=deepcopy(data.get('percept_history',{}))
        visual_examples=deepcopy(data.get('visual_examples',[]))
        if not isinstance(visual_examples,list) or len(visual_examples)>MAX_VISUAL_EXAMPLES:raise ValueError('invalid visual memory')
        seen=set()
        for example in visual_examples:
            if not isinstance(example,dict) or not {'target','action','pixels','label','time'}<=set(example) or set(example)-{'target','category','action','pixels','label','time'}:raise ValueError('invalid visual example')
            example.setdefault('category',None)
            if not isinstance(example['target'],str) or not example['target'] or type(example['action']) is not int or not 0<=example['action']<14 or (example['category'] is not None and (type(example['category']) is not int or not 0<=example['category']<40)) or example['label'] not in ('safe','harmful') or isinstance(example['time'],bool) or not isinstance(example['time'],(int,float)) or not math.isfinite(example['time']) or example['time']<0:raise ValueError('invalid visual example')
            vision.validate(example['pixels']);key=(example['target'],example['action'])
            if key in seen:raise ValueError('duplicate visual example')
            seen.add(key)
        if not isinstance(risks,dict) or len(risks)>MAX_RISKS or not isinstance(percepts,dict) or len(percepts)>MAX_PERCEPTS:raise ValueError('invalid learned hazards')
        for key,row in risks.items():
            if not isinstance(key,str) or not key or not isinstance(row,dict) or not {'action','category','harm','last'}<=set(row) or set(row)-{'action','category','harm','last','safe'} or type(row['action']) is not int or not 0<=row['action']<14 or type(row['category']) is not int or not 0<=row['category']<40:raise ValueError('invalid learned hazard')
            row.setdefault('safe',0)
            if type(row['safe']) is not int or not 0<=row['safe']<5:raise ValueError('invalid safe evidence')
            if any(isinstance(row[k],bool) or not isinstance(row[k],(int,float)) or not math.isfinite(row[k]) or row[k]<0 for k in ('harm','last')):raise ValueError('invalid learned hazard')
        for token,actions in percepts.items():
            if not isinstance(token,str) or not token or len(token)>32 or not isinstance(actions,dict) or len(actions)>14:raise ValueError('invalid percept history')
            for action,group in actions.items():
                if not isinstance(action,str) or not action.isdigit() or not 0<=int(action)<14 or not isinstance(group,dict) or set(group)!={'harmful','safe'}:raise ValueError('invalid percept history')
                for values in group.values():
                    if not isinstance(values,list) or len(values)>16 or any(not isinstance(v,str) or not v for v in values) or len(set(values))!=len(values):raise ValueError('invalid percept evidence')
                if set(group['harmful']) & set(group['safe']):raise ValueError('conflicting percept evidence')
        repetition=deepcopy(data.get('repetition',obj.repetition));aversion=deepcopy(data.get('aversion',obj.aversion))
        if isinstance(repetition,dict):
            repetition.setdefault('cue_action',0 if repetition.get('cue_target') else None)
            repetition.setdefault('blocked_action',None)
        if isinstance(aversion,dict):aversion.setdefault('cooldown_target',None)
        if not isinstance(repetition,dict) or set(repetition)!=set(obj.repetition) or not isinstance(aversion,dict) or set(aversion)!=set(obj.aversion):raise ValueError('invalid behavior memory')
        for row,names in ((repetition,('elapsed','until','cooldown')),(aversion,('started','cooldown'))):
            if any(isinstance(row[k],bool) or not isinstance(row[k],(int,float)) or not math.isfinite(row[k]) or row[k]<0 for k in names):raise ValueError('invalid behavior clock')
        for row,names in ((repetition,('target','cue_target')),(aversion,('target','cooldown_target'))):
            if any(row[k] is not None and (not isinstance(row[k],str) or not row[k]) for k in names):raise ValueError('invalid behavior target')
        for name,limit in (('action',14),('cue_action',14),('blocked_action',14),('category',40),('cue_category',40)):
            if repetition[name] is not None and (type(repetition[name]) is not int or not 0<=repetition[name]<limit):raise ValueError('invalid behavior category')
        obj.episodes=deque(deepcopy(episodes),maxlen=MAX_EPISODES);obj.associations=deepcopy(associations);obj.last_recorded=dict(last);obj.total_observations=total
        obj.risks=risks;obj.percept_history=percepts;obj.repetition=repetition;obj.aversion=aversion
        obj.visual_examples=visual_examples
        return obj
