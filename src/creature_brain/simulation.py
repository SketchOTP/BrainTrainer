"""Closed-loop genome brain, original physiology, identity memory and world.

All motor requests originate in the actual genome's decision lobe. Locomotion,
sensory encodings, body rates, action scripts and counterfactual feedback are
explicit simulation adaptations, not a reproduction of the proprietary engine.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path

from .neural import GenomeBrain, DECISION_FROM_ACTION
from .physiology import Physiology
from .body import DEFAULT_GENOME, DEFAULT_BRAIN, body_from_dict, clone_body, genome_body
from .social import SocialMemory
from .world import ActionOutcome, Pose, World, WorldObject, finite
from . import exploration
from .experience import ExperienceMemory
from . import vision


@dataclass
class Creature:
    creature_id: str
    brain: GenomeBrain
    body: object = None
    social: SocialMemory = field(default_factory=SocialMemory)
    response: list[float] = field(default_factory=lambda: [0.0]*20)
    slot_owners: list[str | None] = field(default_factory=lambda: [None]*35)
    command: dict | None = None
    exploration: dict | None = None
    experience: ExperienceMemory = field(default_factory=ExperienceMemory)
    action_reward: float = 0.0
    action_punishment: float = 0.0
    feedback_body: object = None
    feedback_origin: tuple[float,float] | None = None
    feedback_elapsed: float = 0.0
    feedback_previous: list[float] = field(default_factory=lambda:[0.0]*22)

    def __post_init__(self):
        if self.body is None:
            self.body=genome_body(age_stage=self.brain.age_stage,sex=self.brain.sex)
        if hasattr(self.body,'kernel'):
            kernel=self.body.kernel
            if kernel.source_sha256!=self.brain.definition.source_sha256:
                raise ValueError('brain and biochemical body require the same source genome')
            if (kernel.sex,kernel.age_stage)!=(self.brain.sex,self.brain.age_stage):
                raise ValueError('brain and biochemical body require matching age and sex expression')

    def to_dict(self):
        return {'id': self.creature_id, 'brain': self.brain.to_dict(),
                'body': self.body.to_dict(), 'social': self.social.to_dict(),
                'response': self.response.copy(), 'slot_owners': self.slot_owners.copy(),
                'command': None if self.command is None else dict(self.command),
                'exploration': exploration.validate(self.exploration),
                'experience': self.experience.to_dict(),
                'action_reward':self.action_reward,'action_punishment':self.action_punishment,
                'feedback_body':None if self.feedback_body is None else self.feedback_body.to_dict(),
                'feedback_origin':None if self.feedback_origin is None else list(self.feedback_origin),
                'feedback_elapsed':self.feedback_elapsed,'feedback_previous':self.feedback_previous.copy()}

    @classmethod
    def from_dict(cls, data):
        creature = cls(data['id'], GenomeBrain.from_dict(data['brain']),
                       body_from_dict(data['body']), SocialMemory.from_dict(data['social']))
        if (not isinstance(data['response'], list) or len(data['response']) != 20
                or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1 for v in data['response'])):
            raise ValueError('invalid drive-response vector')
        owners = data['slot_owners']
        if not isinstance(owners,list) or len(owners)!=35 or any(v is not None and (not isinstance(v,str) or not v) for v in owners):
            raise ValueError('invalid identity-slot owners')
        for identity in creature.social.identities:
            if owners[creature.social.slot(identity)] != identity:
                raise ValueError('social and neural identity slots disagree')
        creature.response = list(data['response']); creature.slot_owners = list(owners)
        creature.command = data['command']
        creature.exploration = exploration.validate(data.get('exploration'))
        creature.experience = ExperienceMemory.from_dict(data.get('experience'))
        for name in ('action_reward','action_punishment'):
            value=finite(data[name],name)
            if not 0<=value<=1: raise ValueError('invalid causal reinforcement')
            setattr(creature,name,value)
        saved=data.get('feedback_body')
        if saved is not None:
            creature.feedback_body=body_from_dict(saved)
            if type(creature.feedback_body) is not type(creature.body):
                raise ValueError('feedback control and actual body models disagree')
            if hasattr(creature.body,'kernel'):
                a,b=creature.body,creature.feedback_body
                if not a.same_definition(b):
                    raise ValueError('feedback control and actual body definitions disagree')
            origin=data['feedback_origin']
            if not isinstance(origin,list) or len(origin)!=2:
                raise ValueError('feedback requires a two-dimensional origin')
            creature.feedback_origin=tuple(finite(v,'feedback origin') for v in origin)
            creature.feedback_elapsed=finite(data['feedback_elapsed'],'feedback elapsed')
            previous=data['feedback_previous']
            if len(previous)!=22 or any(abs(finite(v,'feedback delta'))>1 for v in previous) or creature.feedback_elapsed<0:
                raise ValueError('invalid persistent feedback state')
            creature.feedback_previous=list(previous)
        return creature


class Simulation:
    """Deterministic phased, multi-creature simulation; timestep in seconds.

    Perception/decision is simultaneous. Actuation rotates the first actor each
    step to share contested resources. A resting/sleeping/dead body can inhibit
    motors; it never substitutes a different decision algorithm.
    """
    MODEL = 'genome-embodied-creature-v1'

    def __init__(self, world=None, *, dt=0.25,feedback_horizon=64.0):
        self.world = World() if world is None else world
        self.dt = finite(dt,'dt')
        if not 0 < self.dt <= 1:
            raise ValueError('simulation dt must be in (0,1] seconds')
        self.feedback_horizon=finite(feedback_horizon,'feedback horizon')
        if self.feedback_horizon<self.dt:
            raise ValueError('feedback horizon must cover at least one timestep')
        self.creatures: dict[str,Creature] = {}
        self.steps = 0
        self.actions = Counter()
        self.outcomes = Counter()
        self.sleep_counts = Counter()
        self.events = Counter()
        self.autonomy_mode = 'scripted'

    def add(self, creature: Creature, x: float, y: float, *, category=36):
        if creature.creature_id in self.creatures:
            raise ValueError('duplicate creature identity')
        self._validate_anatomy(creature)
        self.world.add_agent(Pose(creature.creature_id,x,y,category=category))
        self.creatures[creature.creature_id] = creature

    @staticmethod
    def _validate_anatomy(creature):
        expected={'driv':20,'resp':20,'visn':40,'smel':40,'noun':40,
                  'verb':13,'decn':13,'attn':40,'detl':16,'situ':16,'forf':36}
        if any(name not in creature.brain.lobes or len(creature.brain.lobes[name].neurons)!=count
               for name,count in expected.items()):
            raise ValueError('body/world adapter requires the supplied adult Chichi-compatible anatomy')

    def command(self, creature_id, *, action: int, category: int, seconds=5.0, strength=1.0, target=None):
        """Teacher noun/verb stimulus, never a direct motor override."""
        if type(action) is not int or action not in DECISION_FROM_ACTION or DECISION_FROM_ACTION[action]>=13:
            raise ValueError('unsupported spoken action')
        if type(category) is not int or not 0<=category<40:
            raise ValueError('noun category must be0..39')
        seconds, strength = finite(seconds,'seconds'),finite(strength,'strength')
        if seconds<=0 or not 0<strength<=1:
            raise ValueError('positive duration and normalized command strength required')
        if target is not None:
            obj=self.world.objects.get(target)
            if obj is None or not obj.enabled or obj.category!=category:raise ValueError('sensory target must be an available object of the named category')
        self.creatures[creature_id].command = {'action':action,'category':category,
                                              'remaining':seconds,'strength':strength}
        if target is not None:self.creatures[creature_id].command['target']=target

    def offer_feature(self,creature_id,feature_id,cue_id):
        """Point to a feature and speak a noun/verb cue; never issue motors."""
        feature=self.world._feature(feature_id)
        if feature is None:raise ValueError('unknown habitat feature')
        cue=next((c for c in feature['cues'] if c['id']==cue_id),None)
        if cue is None:raise ValueError('unknown feature cue')
        if not self.creatures[creature_id].body.alive:raise ValueError('creature is not alive')
        self.command(creature_id,action=cue['action'],category=cue['category'],seconds=30,strength=1,target=feature_id)
        return {'feature':feature_id,'cue':cue_id,'motor_override':False}

    def _environment(self, creature, observation):
        return {'ambient_temperature':observation.ambient_temperature,
                'nearby_creatures':len(observation.nearby_creatures),
                'at_home':observation.at_home,
                'threat':max(observation.threat,creature.social.nearby_threat(observation.nearby_creatures)),
                'separation':creature.social.separation_distress(observation.visible_creatures)}

    @staticmethod
    def _neural_context(creature):
        if not hasattr(creature.body,'neural_receptor_outputs'):
            return {}
        loci={};neurons={}
        # Native locus binding retains the LAST lobe for a duplicate tissue.
        # Build that selection first: earlier large lobes must not leak slots
        # past the end of a later small lobe with the same tissue ID.
        selected={lobe.tissue:lobe for lobe in creature.brain.lobes.values()}
        for lobe in selected.values():
            for index,state in enumerate(lobe.neurons):
                neurons[lobe.tissue,index]=state[0]
                for variable in range(4):
                    loci[0,lobe.tissue,index*4+variable]=state[variable]
        return {'neural_loci':loci,'neuronal_values':neurons}

    @staticmethod
    def _apply_neural_receptors(creature):
        if not creature.body.alive or not hasattr(creature.body,'neural_receptor_outputs'):
            return
        tissues={lobe.tissue:lobe for lobe in creature.brain.lobes.values()}
        for (organ,tissue,locus),value in creature.body.neural_receptor_outputs().items():
            if organ!=0:raise ValueError('body returned a non-neural receptor binding')
            lobe=tissues.get(tissue);index,variable=divmod(locus,4)
            if lobe is None or index>=len(lobe.neurons):
                raise ValueError('biochemical receptor addresses an unavailable brain locus')
            creature.brain.set_neuron_state(lobe.name,index,variable,value)

    def _identities(self, creature, observation):
        creature.social.advance(self.dt,observation.visible_creatures)
        for identity in observation.visible_creatures:
            creature.social.observe(identity,dt=self.dt)
        self._sync_slots(creature)

    @staticmethod
    def _sync_slots(creature):
        for slot in range(creature.social.capacity):
            creature.brain.set_neuron_state('forf',slot,5,0)
            creature.brain.set_neuron_state('forf',slot,7,0)
        for identity in creature.social.identities:
            slot = creature.social.slot(identity)
            if creature.slot_owners[slot] != identity:
                for variable in range(8):
                    creature.brain.set_neuron_state('forf',slot,variable,0)
                # Explicit unrelated-identity initialization; kinship is unmodeled.
                creature.brain.set_neuron_state('forf',slot,4,-1)
                creature.brain.set_neuron_state('forf',slot,7,1)
                creature.slot_owners[slot] = identity
            if creature.social.opinion(identity)['present']:
                creature.brain.set_neuron_state('forf',slot,5,1)

    def step(self):
        identifiers = sorted(self.creatures)
        for identity in identifiers:
            self.world.agents[identity].active=self.creatures[identity].body.alive
        decisions, observations, controls, commands, previous_states, previous_positions, intentions, experience_context = {}, {}, {}, {}, {}, {}, {}, {}
        for identity in identifiers:
            c = self.creatures[identity]
            if self.autonomy_mode == 'scripted':
                intent=exploration.intention(self.world,c,self.dt)
            elif self.autonomy_mode == 'learned':
                intent=c.experience.intention(self.world,c)
            elif self.autonomy_mode == 'observe':
                intent=None
            else:raise ValueError('invalid autonomy mode')
            intentions[identity]=intent
            focus=c.command.get('target') if c.command else (intent['target'] if intent else None)
            obs = self.world.sense(identity,c.brain.output().attention,c.brain.age_stage,focus=focus)
            observations[identity] = obs
            if c.body.alive: self._identities(c,obs)
            environment = self._environment(c,obs)
            neural_context=self._neural_context(c)
            c.body.step(0,**environment,**neural_context)
            self._apply_neural_receptors(c)
            if c.body.sleep_state!='awake' and environment['threat']>.4:
                c.body.wake('threat')
            previous_states[identity] = c.body.sleep_state
            pose=self.world.agents[identity]
            if hasattr(c.body,'kernel'):
                if c.feedback_body is None or c.feedback_elapsed>=self.feedback_horizon:
                    c.feedback_body=clone_body(c.body)
                    c.feedback_origin=(pose.x,pose.y)
                    c.feedback_elapsed=0.0;c.feedback_previous=[0.0]*22
                controls[identity]=c.feedback_body
                previous_positions[identity]=c.feedback_origin
            else:
                controls[identity] = clone_body(c.body)
                previous_positions[identity]=(pose.x,pose.y)
            inputs = dict(obs.inputs)
            inputs.update(driv=c.body.drives,resp=c.response)
            commands[identity] = c.command is not None
            chemicals=c.body.chemicals
            # Global body distress still reaches needs/social circuitry. General
            # action reinforcement uses this actor's attributable chemical pulse.
            chemicals[204],chemicals[205]=c.action_reward,c.action_punishment
            cue=c.command if c.command is not None else intent
            if cue is not None:
                inputs['noun'] = {cue['category']:cue['strength']}
                inputs['verb'] = {DECISION_FROM_ACTION[cue['action']]:cue['strength']}
            if not c.body.alive:
                decisions[identity] = c.brain.output()
            elif c.body.sleep_state=='rem':
                c.brain.chemicals[:] = chemicals
                decisions[identity] = c.brain.rehearse_next_instinct()
            else:
                if c.body.sleep_state!='awake':
                    inputs = {'driv':c.body.drives,'resp':[0.0]*20}
                decisions[identity] = c.brain.tick(inputs,chemicals)

        results = {}
        offset = self.steps % len(identifiers) if identifiers else 0
        for identity in identifiers[offset:] + identifiers[:offset]:
            c = self.creatures[identity]; output = decisions[identity]
            target = observations[identity].representatives.get(output.attention)
            entity=self.world.objects.get(target) or self.world.agents.get(target)
            experience_context[identity]=(getattr(entity,'category',None),c.body.drives,
                                          c.body.chemicals[33] if hasattr(c.body,'kernel') else .5)
            if not c.body.alive or c.body.sleep_state!='awake':
                result = ActionOutcome(identity,output.action,target,
                                       status='dead' if not c.body.alive else 'sleeping')
            else:
                result = self.world.act(identity,output.action,target,self.dt)
            results[identity] = result
            if self.autonomy_mode == 'scripted':exploration.observe(self.world,c,intentions[identity],result,self.dt)
            c.body.set_resting(result.resting)
            if result.request_sleep and c.body.drives[7]>=.6:
                c.body.request_sleep()
            if result.water>0 and hasattr(c.body,'kernel'):
                # Water33 is the actual genotype chemical; intake amount is an
                # explicit world-script dose, not an invented thirst formula.
                c.body.kernel.inject(33,min(1.0,result.water))
            if result.consumed>0:
                if hasattr(c.body,'kernel'):
                    category=self.world.objects[result.target].category
                    c.body.ingest(toxin=result.toxin,
                                  stimulus_id={3:77,8:78}.get(category,79),
                                  stimulus_strength=result.consumed)
                else:
                    c.body.ingest(result.protein,result.starch,result.fat,result.toxin)
            if hasattr(c.body,'kernel') and result.status in ('played','hit','splashed'):
                target_object=self.world.objects.get(result.target)
                if target_object is not None and target_object.kind in ('toy','trinket','water','arch','stairs'):
                    c.body.stimulate(97,self.dt)

        # External harm/social reception is applied to actual AND control bodies.
        # Thus a victim's unrelated concurrent decision never receives its blame.
        for identity in identifiers:
            c = self.creatures[identity]; pose = self.world.agents[identity]
            contacts=self.world.contact_events(pose.x,pose.y,self.dt)
            damage = min(1.0,sum(amount for _,amount in contacts))
            control_damage=min(1.0,self.world.contact_damage(*previous_positions[identity],self.dt))
            if damage and c.body.alive:
                c.body.hurt(damage)
                _,drives_before,water_before=experience_context[identity]
                for hazard,amount in contacts:
                    injury=ActionOutcome(identity,decisions[identity].action,hazard.object_id,status='injured',injury=amount)
                    c.experience.observe(now=self.world.time+self.dt,target=hazard.object_id,category=hazard.category,
                                         action=injury.action,result=injury,drives=drives_before,water_before=water_before,
                                         position=(pose.x,pose.y),percepts=hazard.percepts,visual=vision.pixels_for(hazard))
            if control_damage: controls[identity].hurt(control_damage)
            for event in results[identity].social_events:
                recipient = self.creatures[event['recipient']]
                if not recipient.body.alive: continue
                positive, negative = event['positive'],event['negative']
                recipient.body.interact(positive,negative)
                controls[event['recipient']].interact(positive,negative)
                if negative:
                    recipient.body.hurt(negative); controls[event['recipient']].hurt(negative)
                recipient.social.observe(identity,positive,negative,dt=0)
                self._sync_slots(recipient)
                slot = recipient.social.slot(identity)
                recipient.brain.set_neuron_state('forf',slot,3,1)
                # Initiating friendly contact has an explicit self-side comfort.
                if positive:
                    c.body.interact(positive,0)
                    c.social.observe(recipient.creature_id,positive,0,dt=0)
                self.events[event['reason']] += 1

        self.world.step(self.dt)
        frames = []
        for identity in identifiers:
            c = self.creatures[identity]; result = results[identity]
            obs = self.world.sense(identity,decisions[identity].attention,c.brain.age_stage)
            environment = self._environment(c,obs)
            neural_context=self._neural_context(c)
            stimulation=0.0 if hasattr(c.body,'kernel') else result.stimulation
            c.body.step(self.dt,effort=result.effort,stimulation=stimulation,**environment,**neural_context)
            # Keep the prior location without this actor's navigation or effects.
            control_observation=self.world.sense(identity,position=previous_positions[identity])
            controls[identity].step(self.dt,**self._environment(c,control_observation),**neural_context)
            self._apply_neural_receptors(c)
            delta=[a-b for a,b in zip(c.body.drives+[c.body.reward,c.body.punishment],
                                     controls[identity].drives+[controls[identity].reward,controls[identity].punishment])]
            if hasattr(c.body,'kernel'):
                change=[max(-1.0,min(1.0,a-b)) for a,b in zip(delta,c.feedback_previous)]
                c.response=change[:20]
                c.action_reward=max(0.0,change[20]);c.action_punishment=max(0.0,change[21])
                c.feedback_previous=delta;c.feedback_elapsed+=self.dt
            else:
                c.response=delta[:20] if result.causal_outcome else [0.0]*20
                c.action_reward=max(0.0,delta[20]) if result.causal_outcome else 0.0
                c.action_punishment=max(0.0,delta[21]) if result.causal_outcome else 0.0
                change=delta
            _,drives_before,water_before=experience_context[identity]
            remembered_target=self.world.objects.get(result.target) or self.world.agents.get(result.target)
            category=getattr(remembered_target,'category',None)
            remembered_pose=self.world.agents[identity]
            c.experience.note_action(now=self.world.time,target=result.target,category=category,action=result.action,status=result.status,dt=self.dt)
            c.experience.observe(now=self.world.time,target=result.target,category=category,action=result.action,
                                 result=result,drives=drives_before,water_before=water_before,
                                 position=(remembered_pose.x,remembered_pose.y),
                                 percepts=getattr(remembered_target,'percepts',()),
                                 visual=vision.pixels_for(remembered_target) if isinstance(remembered_target,WorldObject) else None)
            if c.command is not None:
                c.command['remaining'] -= self.dt
                if c.command['remaining']<=0: c.command=None
            pose = self.world.agents[identity]
            pose.active = c.body.alive
            self.actions[str(result.action)] += 1
            self.outcomes[result.status] += 1
            self.sleep_counts[c.body.sleep_state] += 1
            if c.body.sleep_state != previous_states[identity]:
                self.events['sleep:'+previous_states[identity]+'->'+c.body.sleep_state] += 1
            output = decisions[identity]
            frames.append({'id':identity,'x':pose.x,'y':pose.y,'carrying':pose.carrying,
                           'attention':output.attention,'decision':output.decision,'action':output.action,
                           'target':result.target,'outcome':result.status,'commanded':commands[identity],
                           'intention':intentions[identity],
                           'habitat':self.world.habitat_snapshot(identity),
                           'habitat_event':result.habitat_event,'water_intake':result.water,'spawned':result.spawned,
                           'sleep':c.body.sleep_state,'alive':c.body.alive,'health':c.body.health,
                           'energy':c.body.energy,'drives':c.body.drives,'response':c.response,
                           'body_model':c.body.to_dict()['model'] if not hasattr(c.body,'MODEL') else c.body.MODEL,
                           'nutrients':{'protein':c.body.protein,'starch':c.body.starch,'fat':c.body.fat},
                           'biochemistry':self._biochemical_metrics(c),
                           'reward':c.body.reward,'punishment':c.body.punishment,
                           'action_reward':c.action_reward,'action_punishment':c.action_punishment,
                           'instincts_processed':c.brain.instincts_processed,
                           'migrations':sum(t.migrations for t in c.brain.tracts),
                           'social':[dict(c.social.opinion(other),
                                          neural_opinion=[c.brain.lobes['forf'].neurons[c.social.slot(other)][v] for v in (0,2)])
                                     for other in c.social.identities]})
        self.steps += 1
        return {'step':self.steps,'time':self.world.time,'creatures':frames,
                'objects':[{'id':o.object_id,'category':o.category,'x':o.x,'y':o.y,
                            'kind':o.kind,'quantity':o.quantity,'holder':o.holder}
                           for o in sorted(self.world.objects.values(),key=lambda o:o.object_id)]}

    def summary(self):
        return {'model':self.MODEL,'steps':self.steps,'simulated_seconds':self.world.time,
                'dt':self.dt,'action_counts':dict(self.actions),'outcome_counts':dict(self.outcomes),
                'sleep_counts':dict(self.sleep_counts),'event_counts':dict(self.events),
                'creatures':{identity:{'alive':c.body.alive,'health':c.body.health,
                                      'sleep':c.body.sleep_state,'drives':c.body.drives,
                                      'death_reason':c.body.death_reason,
                                      'body_model':c.body.to_dict()['model'] if not hasattr(c.body,'MODEL') else c.body.MODEL,
                                      'biochemical_tick_seconds':c.body.kernel.tick_seconds if hasattr(c.body,'kernel') else None,
                                      'biochemistry':self._biochemical_metrics(c),
                                      'lobes':len(c.brain.lobes),'tracts':len(c.brain.tracts),
                                      'neurons':sum(len(l.neurons) for l in c.brain.lobes.values()),
                                      'dendrites':sum(len(t.dendrites) for t in c.brain.tracts),
                                      'instincts_processed':c.brain.instincts_processed,
                                      'migrations':sum(t.migrations for t in c.brain.tracts)}
                             for identity,c in self.creatures.items()}}

    @staticmethod
    def _biochemical_metrics(creature):
        body=creature.body
        if not hasattr(body,'kernel'):return None
        chemicals=body.chemicals
        return {'chemicals':{str(i):chemicals[i] for i in (2,3,4,5,9,10,11,12,29,30,33,34,35,125,127,148,149,150,151,204,205,212,213)},
                'organs':len(body.kernel.organs),
                'organ_health':[organ.health for organ in body.kernel.organs]}

    def to_dict(self):
        return {'schema':3,'model':self.MODEL,'dt':self.dt,'steps':self.steps,'feedback_horizon':self.feedback_horizon,'autonomy_mode':self.autonomy_mode,
                'world':self.world.to_dict(),'creatures':[c.to_dict() for c in self.creatures.values()],
                'actions':dict(self.actions),'outcomes':dict(self.outcomes),
                'sleep_counts':dict(self.sleep_counts),'events':dict(self.events)}

    @classmethod
    def from_dict(cls,data):
        if data.get('schema') not in (2,3) or data.get('model')!=cls.MODEL:
            raise ValueError('unsupported simulation checkpoint')
        sim = cls(World.from_dict(data['world']),dt=data['dt'],feedback_horizon=data.get('feedback_horizon',64))
        sim.autonomy_mode=data.get('autonomy_mode','scripted')
        if sim.autonomy_mode not in ('scripted','observe','learned'):raise ValueError('invalid autonomy mode')
        if type(data['steps']) is not int or data['steps']<0:
            raise ValueError('invalid simulation step')
        sim.steps = data['steps']
        for row in data['creatures']:
            creature = Creature.from_dict(row)
            sim._validate_anatomy(creature)
            if creature.creature_id in sim.creatures or creature.creature_id not in sim.world.agents:
                raise ValueError('checkpoint creature identity mismatch')
            if creature.feedback_origin is not None:
                sim.world._inside(*creature.feedback_origin)
                if creature.feedback_elapsed>sim.feedback_horizon+sim.dt:
                    raise ValueError('feedback control exceeds its declared horizon')
            sim.creatures[creature.creature_id] = creature
            if creature.exploration is not None:
                features = {f['id'] for f in sim.world.habitat['features']} if sim.world.habitat else set()
                if sim.world.habitat:
                    features.update(o.object_id for o in sim.world.objects.values() if o.kind=='food')
                target = creature.exploration['target']
                if (target is not None and target not in features) or not set(creature.exploration['last']) <= features:
                    raise ValueError('exploration memory references an unknown habitat feature')
            if creature.command is not None:
                command = dict(creature.command)
                sim.command(creature.creature_id,action=command['action'],category=command['category'],
                            seconds=command['remaining'],strength=command['strength'],target=command.get('target'))
        if sim.creatures.keys()!=sim.world.agents.keys():
            raise ValueError('world and body identities disagree')
        if not math.isclose(sim.world.time,sim.steps*sim.dt,abs_tol=1e-7):
            raise ValueError('simulation and world clocks disagree')
        for key,attribute in [('actions','actions'),('outcomes','outcomes'),('sleep_counts','sleep_counts'),('events','events')]:
            if any(type(v) is not int or v<0 for v in data[key].values()):
                raise ValueError('invalid simulation counters')
            setattr(sim,attribute,Counter(data[key]))
        return sim

    def save(self,path):
        path = Path(path); temporary = path.with_suffix(path.suffix+'.tmp')
        temporary.write_text(json.dumps(self.to_dict(),allow_nan=False)+'\n')
        temporary.replace(path)

    @classmethod
    def load(cls,path):
        return cls.from_dict(json.loads(Path(path).read_text()))


def make_demo(genome_path, *, seed=7, count=2, dt=.2, rehearse=True,
              body_model='genome',physiology_genome=None,timing_profile='docking-nominal'):
    if type(count) is not int or not 1<=count<=8:
        raise ValueError('demo supports one to eight creatures')
    if timing_profile not in ('docking-nominal','legacy'):
        raise ValueError('unknown timing profile')
    if body_model=='genome' and timing_profile=='docking-nominal' and not math.isclose(dt,.2,abs_tol=1e-12):
        raise ValueError('docking-nominal requires dt=0.2 for one brain and biochemical update per creature tick')
    sim = Simulation(dt=dt)
    for obj in [WorldObject('balanced-food',11,5,5,quantity=8,protein=.7,starch=.8,fat=.5,regeneration=.01),
                WorldObject('fruit',8,15,8,quantity=6,starch=.9,fat=.1,regeneration=.005),
                WorldObject('toy',21,10,6,kind='toy',portable=True),
                WorldObject('home',30,3,3,kind='home',portable=False),
                WorldObject('danger',20,18,2,kind='danger',portable=False),
                WorldObject('toxic-food',9,17,3,quantity=3,starch=.3,toxin=.8)]:
        sim.world.add_object(obj)
    for i in range(count):
        brain = GenomeBrain.from_file(genome_path,seed=seed+i,sex='female' if i%2==0 else 'male')
        if rehearse:
            # Declared boot rehearsal with REM consolidation, before embodiment.
            brain.chemicals[213]=1.0
            brain.train_instincts()
            brain.chemicals[213]=0.0
            brain.clear_activity()
        if body_model=='genome':
            full_genome=physiology_genome
            if full_genome is None:
                full_genome=DEFAULT_GENOME if Path(genome_path).resolve()==DEFAULT_BRAIN.resolve() else genome_path
            body=genome_body(full_genome,age_stage=brain.age_stage,sex=brain.sex,
                             tick_seconds=.2 if timing_profile=='docking-nominal' else 1.0)
        elif body_model=='simplified':body=Physiology()
        else:raise ValueError('body_model must be genome or simplified')
        creature = Creature('creature-'+str(i+1),brain,body)
        sim.add(creature,6+i*.7,5+i*.2)
    return sim
