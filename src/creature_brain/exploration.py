"""Original, opt-in habitat curiosity: sensory intentions, never motors.

This is a host adaptation, not a recovered Docking Station brain component.
The genome still selects its attention and every action on every tick.
"""
import math

GOAL_SECONDS = 70.0
REST_BETWEEN_GOALS = 12.0
SUCCESS = {
    'water': {'drank', 'washed', 'splashed'},
    'shelter': {'entered'},
    'bush': {'foraged'},
    'path': {'explored'},
    'arch': {'explored', 'played'},
    'stairs': {'explored', 'played'},
    'cache': {'discovered', 'cache-empty'},
    'food': {'ate'},
}


def validate(state):
    if state is None:
        return None
    if not isinstance(state, dict) or not {'target','remaining','last'} <= set(state) or set(state)-{'target','remaining','last','pause'}:
        raise ValueError('invalid exploration state')
    target,remaining,last=state['target'],state['remaining'],state['last']
    if target is not None and (not isinstance(target,str) or not target):
        raise ValueError('invalid exploration target')
    if isinstance(remaining,bool) or not isinstance(remaining,(int,float)) or not math.isfinite(remaining) or remaining < 0:
        raise ValueError('invalid exploration duration')
    if not isinstance(last,dict) or any(not isinstance(k,str) or isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for k,v in last.items()):
        raise ValueError('invalid exploration memory')
    pause=state.get('pause',0.0)
    if isinstance(pause,bool) or not isinstance(pause,(int,float)) or not math.isfinite(pause) or pause<0:
        raise ValueError('invalid exploration pause')
    return {'target':target,'remaining':float(remaining),'last':dict(last),'pause':float(pause)}


def intention(world, creature, dt):
    """Choose a novel, useful visible place and provide noun/verb inputs."""
    if world.habitat is None or creature.command is not None or not creature.body.alive or creature.body.sleep_state != 'awake':
        return None
    state=creature.exploration
    if state is None:
        state=creature.exploration={'target':None,'remaining':0.0,'last':{},'pause':0.0}
    if state['pause']>0:
        state['pause']=max(0.0,state['pause']-dt)
        return None
    pose=world.agents[creature.creature_id]
    obj=world.objects.get(state['target'])
    if obj is None or not obj.enabled or (obj.kind=='food' and obj.quantity<=0) or state['remaining']<=0:
        if obj is not None:
            state['last'][obj.object_id]=world.time
            state['target']=None;state['remaining']=0.0;state['pause']=REST_BETWEEN_GOALS
            return None
        candidates=[]
        drives=creature.body.drives
        chemicals=creature.body.chemicals if hasattr(creature.body,'kernel') else None
        water=chemicals[33] if chemicals is not None else .5
        energy=chemicals[34] if chemicals is not None else creature.body.energy
        for feature in world.habitat['features']:
            item=world.objects.get(feature['id'])
            if item is None or not item.enabled or item.kind not in SUCCESS:continue
            if (item.kind=='cache' and item.discoveries) or (item.kind=='bush' and item.quantity<.5):continue
            distance=math.hypot(item.x-pose.x,item.y-pose.y)
            if distance>world.vision_radius:continue
            elapsed=max(0,world.time-state['last'].get(item.object_id,world.time-600))
            novelty=min(2.0,elapsed/300)
            need={'water':.5*(1-water),'shelter':.5*drives[7],
                  'bush':.35*max(drives[1:4]),'path':.25*drives[11]}.get(item.kind,0)
            score=novelty+need-.045*distance
            candidates.append((score,item.object_id,item))
        # Body needs can interrupt curiosity: select real accessible food,
        # but still rely on the genome to choose and carry out eating.
        hunger=max(drives[1:4])
        if hunger>.10 or energy<.4:
            for item in world.objects.values():
                if item.kind!='food' or not item.enabled or item.quantity<=0 or item.stored_in is not None or item.holder not in (None,pose.creature_id):continue
                distance=math.hypot(item.x-pose.x,item.y-pose.y)
                if distance<=world.vision_radius:
                    candidates.append((3+hunger-.045*distance,item.object_id,item))
        if not candidates:
            state['target']=None;state['remaining']=0;return None
        obj=max(candidates)[2]
        state['target']=obj.object_id;state['remaining']=GOAL_SECONDS
    distance=math.hypot(obj.x-pose.x,obj.y-pose.y)
    near=distance<=max(obj.radius,world.interaction_radius)
    # First approach the selected place, then suggest a context-specific use.
    if obj.kind=='food':action=12
    elif not near and not (obj.kind=='shelter' and pose.inside):action=4
    else:action={'water':12,'shelter':4,'bush':1,'path':4,'arch':1,'stairs':1,'cache':1}[obj.kind]
    return {'target':obj.object_id,'category':obj.category,'action':action,'strength':.5}


def observe(world, creature, intent, outcome, dt):
    if intent is None:return
    state=creature.exploration
    state['remaining']=max(0.0,state['remaining']-dt)
    obj=world.objects.get(intent['target'])
    if obj is not None and outcome.target==obj.object_id and outcome.status in SUCCESS[obj.kind]:
        state['last'][obj.object_id]=world.time
        state['target']=None;state['remaining']=0.0;state['pause']=REST_BETWEEN_GOALS
