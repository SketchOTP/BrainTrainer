"""Deterministic simulated embodiment for the recovered neural circuit.

Distances are world units and time is simulated seconds. Categories and action
IDs come from the packaged catalogues; geometry, costs and affordances below
are explicit original simulation choices, rather than a CAOS/physics clone.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from copy import deepcopy
import math
from typing import Mapping
from .vision import validate as validate_visual


def finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


@dataclass
class Pose:
    creature_id: str
    x: float
    y: float
    heading: float = 0.0
    category: int = 36
    active: bool = True
    carrying: str | None = None
    wetness: float = 0.0
    water_intake: float = 0.0
    cleanliness: float = 0.75
    shelter: str | None = None
    inside: bool = False
    elevation: float = 0.0
    location: str = "clearing"
    route: list[list[float]] = field(default_factory=list)
    route_target: str | None = None

    def __post_init__(self):
        if not isinstance(self.creature_id, str) or not self.creature_id:
            raise ValueError("creature identity must be nonempty")
        self.x, self.y = finite(self.x, 'x'), finite(self.y, 'y')
        self.heading = finite(self.heading, 'heading')
        if type(self.category) is not int or not 0 <= self.category < 40:
            raise ValueError("category must be in0..39")
        for key in ("wetness", "cleanliness"):
            value=finite(getattr(self,key),key)
            if not 0<=value<=1: raise ValueError("invalid habitat state")
            setattr(self,key,value)
        self.water_intake=finite(self.water_intake,"water intake")
        self.elevation=finite(self.elevation,"elevation")
        if self.water_intake<0 or self.elevation<0 or type(self.inside) is not bool:
            raise ValueError("invalid habitat pose")
        if self.shelter is not None and not isinstance(self.shelter,str): raise ValueError("invalid shelter")
        if not isinstance(self.location,str) or not isinstance(self.route,list): raise ValueError("invalid route state")
        for point in self.route:
            if not isinstance(point,list) or len(point)!=3 or any(not math.isfinite(finite(v,"route point")) for v in point): raise ValueError("invalid route point")
        if type(self.active) is not bool:
            raise ValueError("active must be boolean")


@dataclass
class WorldObject:
    object_id: str
    category: int
    x: float
    y: float
    kind: str = 'food'
    quantity: float = 1.0
    protein: float = 0.0
    starch: float = 0.0
    fat: float = 0.0
    toxin: float = 0.0
    smell: float = 1.0
    portable: bool = True
    holder: str | None = None
    enabled: bool = True
    regeneration: float = 0.0
    initial_quantity: float | None = None
    radius: float = 0.0
    stored_in: str | None = None
    storage: list[str] = field(default_factory=list)
    decorations: list[str] = field(default_factory=list)
    discoveries: int = 0
    last_harvest: float = -1000.0
    percepts: list[str] = field(default_factory=list)
    visual: list[str] | None = None

    def __post_init__(self):
        if not isinstance(self.object_id, str) or not self.object_id:
            raise ValueError("object identity must be nonempty")
        if type(self.category) is not int or not 0 <= self.category < 40:
            raise ValueError("category must be in0..39")
        for name in ('x', 'y', 'quantity', 'protein', 'starch', 'fat', 'toxin', 'smell', 'regeneration'):
            setattr(self, name, finite(getattr(self, name), name))
        if min(self.quantity, self.protein, self.starch, self.fat, self.toxin,
               self.smell, self.regeneration) < 0:
            raise ValueError("resource properties must be nonnegative")
        if self.initial_quantity is None:
            self.initial_quantity = self.quantity
        self.initial_quantity = finite(self.initial_quantity, 'initial_quantity')
        if self.initial_quantity < self.quantity:
            raise ValueError("initial capacity must cover quantity")
        self.last_harvest=finite(self.last_harvest,"last harvest")
        self.radius=finite(self.radius,"radius")
        if self.radius<0 or type(self.discoveries) is not int or self.discoveries<0: raise ValueError("invalid habitat resource")
        if self.stored_in is not None and not isinstance(self.stored_in,str): raise ValueError("invalid storage owner")
        if (not isinstance(self.percepts,list) or len(self.percepts)>8
                or any(not isinstance(v,str) or not v or len(v)>32 for v in self.percepts)
                or len(set(self.percepts))!=len(self.percepts)):
            raise ValueError('invalid observable percepts')
        self.visual=validate_visual(self.visual)
        for values in (self.storage,self.decorations):
            if not isinstance(values,list) or any(not isinstance(v,str) for v in values) or len(values)!=len(set(values)): raise ValueError("invalid stored items")
        if type(self.portable) is not bool or type(self.enabled) is not bool:
            raise ValueError("object flags must be boolean")


@dataclass(frozen=True)
class Observation:
    inputs: dict[str, list[float]]
    representatives: dict[int, str]
    nearby_creatures: tuple[str, ...]
    visible_creatures: tuple[str, ...]
    ambient_temperature: float
    at_home: bool
    threat: float


@dataclass
class ActionOutcome:
    actor: str
    action: int
    target: str | None
    status: str = 'idle'
    effort: float = 0.0
    distance: float = 0.0
    protein: float = 0.0
    starch: float = 0.0
    fat: float = 0.0
    toxin: float = 0.0
    consumed: float = 0.0
    injury: float = 0.0
    stimulation: float = 0.0
    resting: bool = False
    request_sleep: bool = False
    feedback: float = 0.0
    social_events: list[dict] = field(default_factory=list)
    water: float = 0.0
    wetness: float = 0.0
    habitat_event: str | None = None
    spawned: list[str] = field(default_factory=list)

    @property
    def causal_outcome(self) -> bool:
        return self.status in ('ate', 'played', 'moved', 'resting', 'expressed', 'hit',
                               'injured', 'looked', 'picked-up', 'dropped', 'deactivated', 'drank',
                               'washed', 'splashed', 'entered', 'stored', 'decorated', 'foraged', 'explored','discovered')


class World:
    """A bounded2D arena with consumable resources and real action consequences."""

    MODEL = 'original-body-world-v1'

    def __init__(self, width: float = 20.0, height: float = 12.0,
                 temperature: float = 22.0, *, movement_speed: float = 1.0,
                 interaction_radius: float = 0.8, vision_radius: float = 14.0):
        self.width, self.height = finite(width, 'width'), finite(height, 'height')
        self.temperature = finite(temperature, 'temperature')
        self.movement_speed = finite(movement_speed, 'movement_speed')
        self.interaction_radius = finite(interaction_radius, 'interaction_radius')
        self.vision_radius = finite(vision_radius, 'vision_radius')
        if min(self.width, self.height, self.movement_speed, self.interaction_radius, self.vision_radius) <= 0:
            raise ValueError("world dimensions and action scales must be positive")
        self.time = 0.0
        self.objects: dict[str, WorldObject] = {}
        self.agents: dict[str, Pose] = {}
        self.habitat = None

    @staticmethod
    def _habitat_xy(px, py):
        u,v=.5,.5
        for _ in range(15):
            x=110+740*u-100*v+200*u*v; y=50+450*v+12*u*(1-v)
            a,b=740+200*v,-100+200*u; c,d=12*(1-v),450-12*u
            det=a*d-b*c; dx,dy=px-x,py-y
            u+=(d*dx-b*dy)/det;v+=(-c*dx+a*dy)/det
        return [max(0.0,min(20.0,20*u)),max(0.0,min(12.0,12*v))]

    def enable_pet_habitat(self):
        """Add the original interactive digital world without resetting state.

        This opt-in profile alone adds world-specific action scripts. Benchmarks
        retain their original environment. Geometry matches the pet artwork's
        declared perspective; routes contain physical XY and stair elevation.
        """
        if self.habitat is not None:
            # Stable object IDs preserve existing checkpoints while labels
            # follow the current digital-world presentation.
            labels={'habitat-water':'Data stream','habitat-hut':'Recharge shelter',
                    'habitat-west-bush':'Data-fruit cluster','habitat-east-bush':'Energy-fruit cluster',
                    'habitat-arch':'Gateway arch','habitat-stairs':'Data steps',
                    'habitat-trail':'Signal trail','habitat-cache':'Lost memory cache'}
            for feature in self.habitat.get('features',[]):
                if feature.get('id') in labels:feature['label']=labels[feature['id']]
            return self.habitat_snapshot()
        if self.width!=20 or self.height!=12: raise ValueError('digital habitat requires a20 by12 world')
        xy=self._habitat_xy;hub=xy(480,300)
        definitions=[
            ('water','Data stream','water',25,(400,500),1.1,[('drink','Drink data water',12),('wash','Wash',1),('splash','Play in the stream',2)]),
            ('hut','Recharge shelter','shelter',30,(780,178),.85,[('enter','Enter safe pod',4),('sleep','Rest inside',9),('store','Store carried item',7),('decorate','Decorate',1),('retrieve','Retrieve item',6)]),
            ('west-bush','Data-fruit cluster','bush',4,(115,258),.9,[('forage','Search data cluster',1),('walk','Pass through',4)]),
            ('east-bush','Energy-fruit cluster','bush',7,(861,344),.9,[('forage','Search energy nodes',1),('walk','Pass through',4)]),
            ('arch','Gateway arch','arch',21,(201,83),.75,[('play','Play at gateway',1),('explore','Explore gateway',4)]),
            ('stairs','Data steps','stairs',26,(238,168),.65,[('climb','Climb data steps',4),('play','Play on steps',1)]),
            ('trail','Signal trail','path',34,(632,58.465),.7,[('explore','Explore signal trail',4)]),
            ('cache','Lost memory cache','cache',33,(610,104),.65,[('search','Search memory cache',1),('look','Inspect cache',0)]),
        ]
        conflicts=['habitat-'+row[0] for row in definitions if 'habitat-'+row[0] in self.objects]
        if conflicts:raise ValueError('habitat identities conflict with existing objects')
        features=[];routes=[]
        for short,label,kind,category,pixel,radius,cues in definitions:
            key='habitat-'+short;x,y=xy(*pixel)
            if key in self.objects: raise ValueError('habitat identity conflicts with an existing object')
            self.add_object(WorldObject(key,category,x,y,kind=kind,portable=False,radius=radius,
                                        quantity=3 if kind=='bush' else 1,regeneration=.005 if kind=='bush' else 0))
            feature={'id':key,'label':label,'kind':kind,'x':x,'y':y,'radius':radius,
                     'cues':[{'id':cue,'label':text,'action':action,'category':category} for cue,text,action in cues]}
            if kind=='shelter':feature['interior']=xy(815,155)
            pixels={'arch':[(270,220),(238,168),(201,83)],'stairs':[(270,220),(238,168)],
                    'trail':[(580,190),(620,120),(632,58.465)],'cache':[(580,190),(610,104)],'hut':[(700,260),(780,178)],
                    'water':[(475,410),(400,500)],'west-bush':[(230,300),(115,258)],
                    'east-bush':[(740,350),(861,344)]}[short]
            points=[[hub[0],hub[1],0.0]]
            for j,pixelpoint in enumerate(pixels):
                a,b=xy(*pixelpoint);z=(j+1)/len(pixels) if short in ('arch','stairs') else 0.0
                points.append([a,b,z])
            routes.append({'id':key,'kind':kind,'points':points,'width':.8})
            features.append(feature)
        self.habitat={'profile':'forest-pet-v1','projection':'forest-perspective-v1','features':features,'routes':routes,
                      'adaptations':['Action IDs are interpreted by original habitat scripts; the genome remains the motor selector.',
                                     'Drinking doses native Water33; wetness, cooling, drying and shelter warmth are authored world physics.']}
        return self.habitat_snapshot()

    def habitat_snapshot(self,creature_id=None):
        if self.habitat is None:return None
        result=deepcopy(self.habitat)
        result['storage']={o.object_id:o.storage.copy() for o in self.objects.values() if o.kind=='shelter'}
        result['decor']={o.object_id:o.decorations.copy() for o in self.objects.values() if o.kind=='shelter'}
        result['forage']={o.object_id:{'quantity':o.quantity,'capacity':o.initial_quantity,'discoveries':o.discoveries} for o in self.objects.values() if o.kind=='bush'}
        if creature_id is not None:
            pose=self.agents[creature_id]
            result['creature']={key:deepcopy(getattr(pose,key)) for key in ('wetness','water_intake','cleanliness','shelter','inside','elevation','location','route','route_target')}
        return result

    def _feature(self,identifier):
        if self.habitat is None:return None
        return next((f for f in self.habitat['features'] if f['id']==identifier),None)

    def _near_shelter(self,pose):
        if self.habitat is None:return None
        return next((o for o in self.objects.values() if o.kind=='shelter' and
                     math.hypot(o.x-pose.x,o.y-pose.y)<=1.8),None)

    def _habitat_move(self,pose,obj,dt,*,interior=False):
        feature=self._feature(obj.object_id)
        if pose.route_target!=obj.object_id or not pose.route:
            route=next(r for r in self.habitat['routes'] if r['id']==obj.object_id)
            points=deepcopy(route['points'])
            previous=next((r for r in self.habitat['routes'] if r['id']==pose.route_target),None)
            if previous is not None and previous['id']!=obj.object_id and pose.location!='clearing':
                nearest=min(range(len(previous['points'])),key=lambda i:math.hypot(pose.x-previous['points'][i][0],pose.y-previous['points'][i][1]))
                points=list(reversed(deepcopy(previous['points'][:nearest+1])))+points[1:]
            else:
                nearest=min(range(len(points)),key=lambda i:math.hypot(pose.x-points[i][0],pose.y-points[i][1]))
                points=points[nearest:]
            pose.route=points;pose.route_target=obj.object_id
        if interior and feature.get('interior'):
            goal=[*feature['interior'],0.0]
            if not pose.route or pose.route[-1]!=goal:pose.route.append(goal)
        budget=self.movement_speed*dt;total=0.0
        while pose.route and budget>0:
            x,y,z=pose.route[0];distance=math.hypot(x-pose.x,y-pose.y)
            if distance<=1e-8:pose.elevation=z;pose.route.pop(0);continue
            amount=min(distance,budget);fraction=amount/distance
            pose.heading=math.atan2(y-pose.y,x-pose.x);pose.x+=(x-pose.x)*fraction;pose.y+=(y-pose.y)*fraction
            pose.elevation+=(z-pose.elevation)*fraction;budget-=amount;total+=amount
            if amount>=distance-1e-8:pose.route.pop(0)
        self._carry(pose)
        if not pose.route:pose.location=obj.kind
        return total

    def _store(self,pose,shelter,*,decorate=False):
        if pose.carrying is None:return False
        item=self.objects[pose.carrying];item.holder=None;item.stored_in=shelter.object_id
        item.x,item.y=shelter.x,shelter.y;pose.carrying=None;shelter.storage.append(item.object_id)
        if decorate:shelter.decorations.append(item.object_id)
        return True

    def _forage(self,pose,obj,out,dt):
        if self.time-obj.last_harvest<5:out.status='forage-wait';return
        if obj.quantity<.5:out.status='forage-empty';return
        obj.quantity-=.5;obj.discoveries+=1;obj.last_harvest=self.time
        pose.cleanliness=max(0,pose.cleanliness-.08)
        trinket=obj.discoveries%3==0
        key=f'{obj.object_id}-find-{obj.discoveries}'
        x=min(self.width,max(0,obj.x+.4));y=min(self.height,max(0,obj.y+.25))
        self.add_object(WorldObject(key,21 if trinket else 8,x,y,kind='trinket' if trinket else 'food',
                                    quantity=1 if trinket else .5,portable=True))
        out.status='foraged';out.stimulation=.35;out.spawned=[key];out.habitat_event='Found a memory shard' if trinket else 'Found a data-fruit packet'

    def _habitat_action(self,pose,obj,action,dt,out):
        feature=self._feature(obj.object_id)
        if feature is None:return False
        # Looking is a sensory action: it must not make the pet walk to a
        # distant landmark. Fixed landscape cannot be switched off like a toy.
        if action==0:
            out.status='looked';out.stimulation=.05;return True
        if action==3:
            out.status='unavailable-action';return True
        distance=0.0 if obj.kind=='shelter' and pose.inside and pose.shelter==obj.object_id else math.hypot(obj.x-pose.x,obj.y-pose.y)
        if action in (1,2,4,6,8,12,13) and distance>max(self.interaction_radius,obj.radius):
            out.distance=self._habitat_move(pose,obj,dt,interior=obj.kind=='shelter' and action==4);out.effort=.15;out.status='moved';
            if obj.kind=='shelter' and action==4 and not pose.route:pose.inside=True;pose.shelter=obj.object_id;pose.location='shelter';out.status='entered'
            return True
        if obj.kind=='water':
            if action==12:
                out.water=.15*dt;pose.water_intake+=out.water;out.status='drank';out.habitat_event='Drinking from the stream'
            elif action in (1,2,8,13):
                pose.wetness=min(1,pose.wetness+(.5 if action==1 else .3)*dt)
                if action==1:pose.cleanliness=min(1,pose.cleanliness+.3*dt)
                out.status='washed' if action==1 else 'splashed';out.stimulation=.6;out.habitat_event='Washing' if action==1 else 'Playing in the stream'
            elif action==4:
                out.distance=self._habitat_move(pose,obj,dt);out.status='moved' if out.distance else 'explored'
            else:return False
            out.wetness=pose.wetness;pose.location='water';return True
        if obj.kind=='shelter':
            if action==4 and pose.inside and pose.shelter==obj.object_id:
                out.status='entered';return True
            if action==4:
                out.distance=self._habitat_move(pose,obj,dt,interior=True);out.effort=.1
                if not pose.route:pose.inside=True;pose.shelter=obj.object_id;pose.location='shelter';out.status='entered';out.habitat_event='Entered the recharge shelter'
                else:out.status='moved'
            elif action==1:
                if self._store(pose,obj,decorate=True):out.status='decorated'
                elif obj.storage:
                    key=next((k for k in obj.storage if k not in obj.decorations),None)
                    if key is None:out.status='resting';out.resting=True
                    else:obj.decorations.append(key);out.status='decorated'
                else:out.status='resting';out.resting=True
            elif action==6:
                if not pose.carrying and obj.storage:
                    key=obj.storage.pop();item=self.objects[key];item.stored_in=None;item.holder=pose.creature_id;pose.carrying=key
                    if key in obj.decorations:obj.decorations.remove(key)
                    out.status='picked-up';self._carry(pose)
                else:out.status='storage-empty'
            elif action in (2,8):out.status='resting';out.resting=True
            else:return False
            return True
        if obj.kind=='bush':
            if action in (1,2,12):self._forage(pose,obj,out,dt)
            elif action==4:
                out.distance=self._habitat_move(pose,obj,dt);out.status='moved' if out.distance else 'explored';pose.location='bush'
                if not pose.route and self.time-obj.last_harvest>=20:self._forage(pose,obj,out,dt)
            else:return False
            return True
        if obj.kind=='cache':
            if action==1:
                if obj.discoveries:
                    out.status='cache-empty';return True
                obj.discoveries=1;obj.quantity=0
                key=obj.object_id+'-keepsake'
                self.add_object(WorldObject(key,21,obj.x,min(self.height,obj.y+.3),kind='trinket',portable=True))
                out.status='discovered';out.spawned=[key];out.habitat_event='Found a polished stone in the cache';return True
            return False
        if obj.kind in ('arch','stairs','path'):
            if action in (1,2,4,8):
                out.distance=self._habitat_move(pose,obj,dt);out.effort=.2 if obj.kind=='stairs' else .12
                out.status='moved' if out.distance else ('played' if action in (1,2,8) else 'explored')
                out.stimulation=.5 if out.status=='played' else .1;out.habitat_event='Exploring '+feature['label']
                return True
        return False

    def add_object(self, obj: WorldObject) -> None:
        if obj.object_id in self.objects or obj.object_id in self.agents:
            raise ValueError("duplicate world identity")
        self._inside(obj.x, obj.y)
        self.objects[obj.object_id] = obj

    def add_agent(self, pose: Pose) -> None:
        if pose.creature_id in self.agents or pose.creature_id in self.objects:
            raise ValueError("duplicate world identity")
        self._inside(pose.x, pose.y)
        self.agents[pose.creature_id] = pose

    def _inside(self, x, y):
        if not 0 <= x <= self.width or not 0 <= y <= self.height:
            raise ValueError("position outside world")

    def ambient_at(self, x: float, y: float) -> float:
        # A mild lateral gradient makes navigation thermally consequential.
        return self.temperature + 4.0 * (x / self.width - 0.5)

    def at_home(self, pose: Pose) -> bool:
        return any(o.enabled and o.kind in ('home', 'nest') and
                   math.hypot(o.x-pose.x, o.y-pose.y) <= 1.6
                   for o in self.objects.values())

    def contact_damage(self, x: float, y: float, dt: float) -> float:
        return sum(amount for _,amount in self.contact_events(x,y,dt))

    def contact_events(self, x: float, y: float, dt: float):
        """Actual contact sources and their damage, for causal attribution."""
        return [(obj,0.025*dt) for obj in self.objects.values()
                if obj.enabled and obj.kind=='danger' and
                math.hypot(obj.x-x,obj.y-y)<=self.interaction_radius]

    def _entities(self, observer: Pose):
        for obj in self.objects.values():
            if not obj.enabled or obj.stored_in is not None or (obj.kind == 'food' and obj.quantity <= 0):
                continue
            if obj.holder is not None and obj.holder != observer.creature_id:
                continue
            yield obj.object_id, obj.category, obj.x, obj.y, obj.smell, obj
        for pose in self.agents.values():
            if pose.creature_id != observer.creature_id and pose.active:
                yield pose.creature_id, pose.category, pose.x, pose.y, 0.7, pose

    def sense(self, creature_id: str, attention: int = 0, age_stage: int = 3, *, position=None, focus=None) -> Observation:
        pose = self.agents[creature_id]
        if position is not None:
            x,y=position
            self._inside(finite(x,'observer x'),finite(y,'observer y'))
            pose=Pose(pose.creature_id,x,y,pose.heading,pose.category,pose.active,pose.carrying)
        visual, smell, detail, situation = [0.0]*40, [0.0]*40, [0.0]*16, [0.0]*16
        representatives: dict[int, str] = {}
        distances: dict[int, tuple[float, str]] = {}
        visible, nearby = [], []
        threat = 0.0
        for identifier, category, x, y, strength, obj in self._entities(pose):
            distance = math.hypot(x-pose.x, y-pose.y)
            if isinstance(obj, Pose):
                if distance <= self.vision_radius:
                    visible.append(identifier)
                if distance <= 3.0:
                    nearby.append(identifier)
            smell[category] = max(smell[category], strength / (1.0 + 0.6*distance))
            if distance > self.vision_radius and identifier!=focus:
                continue
            key = (-1.0 if identifier==focus else distance, identifier)
            if category not in distances or key < distances[category]:
                distances[category] = key
                representatives[category] = identifier
                visual[category] = 1.0 / (1.0 + 0.12*distance)
            if isinstance(obj, WorldObject) and obj.kind == 'danger' and distance < 2.0:
                threat = max(threat, (2.0-distance)/2.0)
        target = representatives.get(attention)
        if target is not None:
            obj = self.objects.get(target) or self.agents.get(target)
            distance = math.hypot(obj.x-pose.x, obj.y-pose.y)
            detail[0] = float(pose.carrying == target)
            detail[1] = float(isinstance(obj, WorldObject) and obj.holder not in (None, creature_id))
            detail[2] = 1.0 / (1.0+distance)
            detail[3] = float(isinstance(obj, Pose))
            detail[8] = 1.0
            detail[9] = min(1.0, getattr(obj, 'smell', 0.7))
            detail[10] = 1.0
        situation[0] = min(1.0, age_stage/6.0)
        situation[2] = float(pose.carrying is not None)
        situation[5] = float(bool(nearby))
        situation[8] = 1.0
        ambient=self.ambient_at(pose.x,pose.y)
        if self.habitat is not None:
            shelter=self._near_shelter(pose)
            if shelter:ambient+=6.0
            ambient-=pose.wetness*4.0
        return Observation({'visn': visual, 'smel': smell, 'detl': detail, 'situ': situation},
                           representatives, tuple(sorted(nearby)), tuple(sorted(visible)),
                           ambient, self.at_home(pose) or (self.habitat is not None and self._near_shelter(pose) is not None), threat)

    def move_toward(self, pose: Pose, x: float, y: float, dt: float, *, retreat=False) -> float:
        dx, dy = x-pose.x, y-pose.y
        distance = math.hypot(dx, dy)
        if distance == 0:
            dx, dy, distance = math.cos(pose.heading), math.sin(pose.heading), 1.0
        length = min(self.movement_speed*dt, distance)
        factor = -1.0 if retreat else 1.0
        newx = min(self.width, max(0.0, pose.x + factor*dx/distance*length))
        newy = min(self.height, max(0.0, pose.y + factor*dy/distance*length))
        moved = math.hypot(newx-pose.x, newy-pose.y)
        pose.heading = math.atan2(factor*dy, factor*dx)
        pose.x, pose.y = newx, newy
        self._carry(pose)
        return moved

    def _carry(self, pose):
        if pose.carrying is not None:
            obj = self.objects[pose.carrying]
            obj.x, obj.y = pose.x, pose.y

    def act(self, actor: str, action: int, target: str | None, dt: float) -> ActionOutcome:
        dt = finite(dt, 'dt')
        if dt <= 0 or type(action) is not int or not 0 <= action <= 13:
            raise ValueError("positive dt and external action ID0..13 required")
        pose = self.agents[actor]
        out = ActionOutcome(actor, action, target)
        if not pose.active:
            out.status = 'inactive'
            return out
        obj = self.objects.get(target) or self.agents.get(target)
        if obj is not None and isinstance(obj, WorldObject) and not obj.enabled:
            obj = None
        if action in (10, 11):
            out.distance = self.move_toward(pose, pose.x + (-1 if action == 10 else 1), pose.y, dt)
            out.effort, out.status = 0.12, 'moved'
            return out
        if action == 9:
            if self.habitat is not None and isinstance(obj,WorldObject) and obj.kind=='shelter' and not (pose.inside and pose.shelter==obj.object_id):
                out.distance=self._habitat_move(pose,obj,dt,interior=True);out.status='moved';out.effort=.1
                if pose.route:return out
                pose.inside=True;pose.shelter=obj.object_id;pose.location='shelter'
            out.status, out.resting, out.request_sleep = 'resting', True, True
            return out
        if action == 7:
            if self.habitat is not None and isinstance(obj,WorldObject) and obj.kind=='shelter' and math.hypot(obj.x-pose.x,obj.y-pose.y)>1.8:
                out.distance=self._habitat_move(pose,obj,dt,interior=True);out.status='moved';out.effort=.1;return out
            shelter=self._near_shelter(pose) if self.habitat is not None else None
            if shelter is not None and self._store(pose,shelter):
                out.status='stored';out.target=shelter.object_id;out.habitat_event='Stored an item in the shelter';return out
            if pose.carrying is not None:
                held = self.objects[pose.carrying]
                held.holder = None
                self._carry(pose)
                pose.carrying = None
                out.status = 'dropped'
            return out
        if obj is None:
            out.status = 'no-target'
            return out
        if isinstance(obj,WorldObject) and (obj.holder not in (None,actor) or
                                            (obj.kind=='food' and obj.quantity<=0)):
            # Another actor may have taken/depleted a shared target since the
            # simultaneous perception phase. Recheck authority at actuation.
            out.status='unavailable-action'
            return out
        if self.habitat is not None and isinstance(obj,WorldObject) and self._habitat_action(pose,obj,action,dt,out):return out
        distance = math.hypot(obj.x-pose.x, obj.y-pose.y)
        if action == 5:
            out.distance = self.move_toward(pose, obj.x, obj.y, dt, retreat=True)
            out.effort, out.status = 0.15, 'moved'
        elif action == 4 or (action in (1, 2, 6, 8, 12, 13) and distance > self.interaction_radius):
            out.distance = self.move_toward(pose, obj.x, obj.y, dt)
            out.effort, out.status = 0.15, 'moved'
        elif action == 12 and isinstance(obj, WorldObject) and obj.kind == 'food' and obj.quantity > 0:
            amount = min(obj.quantity, 0.5*dt)
            obj.quantity -= amount
            out.consumed=amount
            out.protein, out.starch, out.fat, out.toxin = [amount*getattr(obj,k) for k in ('protein','starch','fat','toxin')]
            out.status, out.stimulation = 'ate', 0.1
            if obj.quantity <= 0 and pose.carrying == obj.object_id:
                pose.carrying, obj.holder = None, None
        elif action == 6 and isinstance(obj, WorldObject) and obj.portable and obj.holder is None and pose.carrying is None:
            pose.carrying, obj.holder = obj.object_id, actor
            self._carry(pose)
            out.status, out.effort = 'picked-up', 0.05
        elif action in (1, 2) and isinstance(obj, Pose):
            out.status, out.stimulation, out.effort = 'played', 0.6, 0.08
            out.social_events.append({'actor': actor, 'recipient': obj.creature_id,
                                      'positive': 0.05*dt, 'negative': 0.0, 'reason': 'play-contact'})
        elif action in (1, 2) and isinstance(obj, WorldObject):
            if obj.kind in ('toy','trinket'):
                out.status, out.stimulation, out.effort = 'played', 1.0, 0.08
            elif obj.kind in ('home','nest'):
                out.status, out.resting = 'resting', True
            elif obj.kind == 'dispenser':
                food = self.objects.get(obj.object_id+'-food')
                if food is not None:
                    food.quantity = food.initial_quantity
                out.status, out.stimulation = 'activated', 0.2
            else:
                out.status = 'unavailable-action'
        elif action == 8:
            out.status, out.stimulation = 'expressed', 0.4
            if isinstance(obj, Pose):
                out.social_events.append({'actor': actor, 'recipient': obj.creature_id,
                                          'positive': 0.08*dt, 'negative': 0.0, 'reason': 'friendly-expression'})
        elif action == 13:
            out.status, out.effort = 'hit', 0.25
            if isinstance(obj, Pose):
                out.social_events.append({'actor': actor, 'recipient': obj.creature_id,
                                          'positive': 0.0, 'negative': 0.10*dt, 'reason': 'attack'})
            else:
                out.stimulation = 0.1
        elif action == 0:
            out.status, out.stimulation = 'looked', 0.05
        elif action == 3:
            if isinstance(obj,WorldObject):
                obj.enabled=False
                out.status = 'deactivated'
            else:
                out.status='unavailable-action'
        else:
            out.status = 'unavailable-action'
        return out

    def step(self, dt: float) -> None:
        dt = finite(dt, 'dt')
        if dt <= 0:
            raise ValueError("dt must be positive")
        self.time += dt
        for obj in self.objects.values():
            if obj.regeneration:
                obj.quantity = min(obj.initial_quantity, obj.quantity+obj.regeneration*dt)
        for pose in self.agents.values():
            self._carry(pose)
            if self.habitat is not None:
                water=next((o for o in self.objects.values() if o.kind=='water' and math.hypot(o.x-pose.x,o.y-pose.y)<=o.radius),None)
                shelter=self._near_shelter(pose)
                pose.wetness=min(1,pose.wetness+.12*dt) if water else max(0,pose.wetness-(.04 if shelter else .015)*dt)
                if pose.inside and (shelter is None or shelter.object_id!=pose.shelter):pose.inside=False;pose.shelter=None
                # Location is a current observation, not a memory of the last
                # feature whose route happened to finish.
                if pose.location not in ('clearing','shelter') and not any(
                    o.enabled and o.kind==pose.location and
                    math.hypot(o.x-pose.x,o.y-pose.y)<=max(o.radius,self.interaction_radius)
                    for o in self.objects.values()):
                    pose.location='clearing'
                if pose.location=='shelter' and not pose.inside and shelter is None:
                    pose.location='clearing'
                if pose.location=='clearing' and not pose.route:
                    pose.elevation=0.0
                bush=next((o for o in self.objects.values() if o.kind=='bush' and math.hypot(o.x-pose.x,o.y-pose.y)<=o.radius),None)
                if not water and not pose.inside:pose.cleanliness=max(0,pose.cleanliness-(.01 if bush else .001)*dt)

    def to_dict(self) -> dict:
        return {'model':self.MODEL,'width':self.width,'height':self.height,
                'temperature':self.temperature,'movement_speed':self.movement_speed,
                'interaction_radius':self.interaction_radius,'vision_radius':self.vision_radius,
                'time':self.time,'habitat':deepcopy(self.habitat),'objects':[asdict(o) for o in sorted(self.objects.values(),key=lambda o:o.object_id)],
                'agents':[asdict(p) for p in sorted(self.agents.values(),key=lambda p:p.creature_id)]}

    @classmethod
    def from_dict(cls, data: Mapping) -> World:
        if data['model'] != cls.MODEL:
            raise ValueError("unsupported world checkpoint")
        world=cls(**{k:data[k] for k in ('width','height','temperature','movement_speed','interaction_radius','vision_radius')})
        world.habitat=deepcopy(data.get('habitat'))
        if world.habitat is not None and (not isinstance(world.habitat,dict) or world.habitat.get('profile')!='forest-pet-v1'):raise ValueError('unsupported habitat profile')
        world.time=finite(data['time'],'time')
        if world.time < 0:
            raise ValueError("negative world time")
        for row in data['objects']:
            world.add_object(WorldObject(**row))
        for row in data['agents']:
            world.add_agent(Pose(**row))
        for pose in world.agents.values():
            if pose.carrying is not None and (pose.carrying not in world.objects or world.objects[pose.carrying].holder != pose.creature_id):
                raise ValueError("inconsistent carried-object identity")
        for obj in world.objects.values():
            if obj.holder is not None and (obj.holder not in world.agents or world.agents[obj.holder].carrying != obj.object_id):
                raise ValueError("inconsistent object holder")
        for obj in world.objects.values():
            if obj.stored_in is not None and (obj.stored_in not in world.objects or obj.object_id not in world.objects[obj.stored_in].storage):raise ValueError('inconsistent stored object')
            for key in obj.storage:
                if key not in world.objects or world.objects[key].stored_in!=obj.object_id:raise ValueError('inconsistent storage identity')
            if any(key not in obj.storage for key in obj.decorations):raise ValueError('decoration is not stored')
        return world
