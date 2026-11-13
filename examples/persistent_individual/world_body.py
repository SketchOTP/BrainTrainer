"""Persistent top-down digital body using the privately imported map/collision pack.

Pathfinding and initial curiosity are authored support. Only visited cells count
as experience; the planner's map knowledge is inherited, not learned geometry.
"""
from collections import deque
from pathlib import Path
from functools import lru_cache
from dataclasses import replace
import json,hashlib,math
from creature_brain.neural import DECISION_FROM_ACTION
PATH=Path(__file__).with_name('assets')/'world'/'maps.json'
MODEL='topdown-body-v1'
@lru_cache(maxsize=1)
def pack_hash():return hashlib.sha256(PATH.read_bytes()).hexdigest()
@lru_cache(maxsize=1)
def town_pack_hash():return hashlib.sha256(PATH.with_name('littleroot-v2.json').read_bytes()).hexdigest()
@lru_cache(maxsize=1)
def rural_pack_hash():return hashlib.sha256(PATH.with_name('rural-v3.json').read_bytes()).hexdigest()
@lru_cache(maxsize=1)
def visual_pack_hash():return hashlib.sha256(PATH.with_name('rural-v4.json').read_bytes()).hexdigest()
def pack_files():return {pack_hash():'maps.json',town_pack_hash():'littleroot-v2.json',rural_pack_hash():'rural-v3.json',visual_pack_hash():'rural-v4.json'}
def map_url(pack_id):return '/assets/world/'+pack_files()[pack_id]
@lru_cache(maxsize=4)
def pack(pack_id=None):
    if pack_id is None:pack_id=pack_hash()
    if pack_id not in pack_files():raise ValueError('unknown map pack')
    return json.loads(PATH.with_name(pack_files()[pack_id]).read_text())
def walkable(region,x,y,pack_id=None):
    m=pack(pack_id)['maps'][region]
    return (0<=x<m['width'] and 0<=y<m['height'] and
        (m['walkable'][y*m['width']+x] or any(p['x']==x and p['y']==y for p in m['portals'])))
def nearest(region,x,y,pack_id=None):
    m=pack(pack_id)['maps'][region]
    return min(((i,j) for j in range(m['height']) for i in range(m['width']) if walkable(region,i,j,pack_id)),key=lambda q:((q[0]-x)**2+(q[1]-y)**2,q))
def gateway(region,x,y,pack_id=None):
    m=pack(pack_id)['maps'][region]
    if any((p['x'],p['y'])==(x,y) for p in m['portals']):return True
    for c in m['connections']:
        other=pack(pack_id)['maps'][c['map']];offset=c['offset'];point=None
        if c['direction']=='up' and y==0:point=(x-offset,other['height']-1)
        elif c['direction']=='down' and y==m['height']-1:point=(x-offset,0)
        elif c['direction']=='left' and x==0:point=(other['width']-1,y-offset)
        elif c['direction']=='right' and x==m['width']-1:point=(0,y-offset)
        if point and walkable(c['map'],*point,pack_id):return True
    return False

def tree(region,start,pack_id=None):
    parents={start:None};queue=deque([start])
    while queue:
        x,y=queue.popleft()
        # Doors and map exits end a local route; never plan through a warp.
        if (x,y)!=start and gateway(region,x,y,pack_id):continue
        for node in ((x,y+1),(x-1,y),(x+1,y),(x,y-1)):
            if node not in parents and walkable(region,*node,pack_id):parents[node]=(x,y);queue.append(node)
    return parents

def enable(host):
    if getattr(host,'world',None) is not None:return
    region='MAP_OLDALE_TOWN';x,y=nearest(region,10,10)
    host.world={'model':MODEL,'pack_sha256':pack_hash(),'region':region,'y':float(y),'facing':'south',
        'visited':{},'goal':None,'route':[],'route_target':None,'transitions':0}
    host.position=float(x);host.velocity=0.;host.active_action=None
    for n,obj in enumerate(host.objects.values()):
        ox,oy=nearest(region,x+2+n,y+1)
        obj.update(x=float(ox),y=float(oy),region=region)
    visit(host)

def validate(world,x,objects=None):
    if not isinstance(world,dict) or world.get('model')!=MODEL or world.get('pack_sha256') not in pack_files():raise ValueError('unknown or changed world pack')
    pack_id=world['pack_sha256']
    if world.get('region') not in pack(pack_id)['maps'] or world.get('facing') not in ('north','south','east','west'):raise ValueError('invalid world location')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (x,world.get('y'))):raise ValueError('invalid world coordinates')
    if not walkable(world['region'],round(x),round(world['y']),pack_id):raise ValueError('world position is not traversable')
    if not isinstance(world.get('visited'),dict) or any(type(v) is not int or v<1 for v in world['visited'].values()):raise ValueError('invalid visited cells')
    region=world['region']
    if world.get('home_region') is not None and region not in home_regions(world):raise ValueError('body outside its home town')
    def cell(node):
        return isinstance(node,list) and len(node)==2 and all(type(v) is int for v in node) and walkable(region,*node,pack_id)
    route=world.get('route')
    if not isinstance(route,list) or any(not cell(n) for n in route):raise ValueError('invalid route')
    previous=(x,world['y'])
    for node in route:
        dx,dy=abs(node[0]-previous[0]),abs(node[1]-previous[1])
        if dx+dy>1.000001 or (dx>1e-6 and dy>1e-6):raise ValueError('route crosses a cell boundary')
        previous=node
    target=world.get('route_target')
    if target is not None and (not isinstance(target,list) or len(target)!=3 or target[0]!=region or not cell(target[1:])):raise ValueError('invalid route target')
    if route and (target is None or route[-1]!=target[1:]):raise ValueError('route does not reach target')
    goal=world.get('goal')
    if goal is not None and (not isinstance(goal,dict) or goal.get('region')!=region or
        not cell([goal.get('x'),goal.get('y')]) or not isinstance(goal.get('id'),str) or
        goal.get('origin')!='visited-cell-memory' or goal.get('map_knowledge')!='inherited-collision-map'):raise ValueError('invalid exploration goal')
    if type(world.get('transitions')) is not int or world['transitions']<0:raise ValueError('invalid transitions')
    for key in world['visited']:
        try:
            r,coordinates=key.split(':');cx,cy=map(int,coordinates.split(','))
            valid=r in pack(pack_id)['maps'] and any(r in pack(old)['maps'] and walkable(r,cx,cy,old) for old in historical_packs(pack_id)) and key==f'{r}:{cx},{cy}'
        except (ValueError,AttributeError):valid=False
        if not valid:raise ValueError('invalid visited cell')
    if world.get('last_cell') not in world['visited']:raise ValueError('last cell absent from memory')
    if objects is not None:
        for obj in objects.values():
            r=obj.get('region');ox,oy=obj.get('x'),obj.get('y')
            if r not in pack(pack_id)['maps'] or any(type(v) not in (int,float) or not math.isfinite(v) or v!=int(v) for v in (ox,oy)) or not walkable(r,int(ox),int(oy),pack_id):raise ValueError('invalid world object location')

def pose(host):return {'region':host.world['region'],'x':host.position,'y':host.world['y'],'facing':host.world['facing']}
def visit(host):
    w=host.world;key=f"{w['region']}:{round(host.position)},{round(w['y'])}"
    if key!=w.get('last_cell'):w['visited'][key]=w['visited'].get(key,0)+1;w['last_cell']=key

def exploration_pending(host):
    w=host.world;goal=w['goal']
    return bool(goal and goal['region']==w['region'] and
                math.hypot(goal['x']-host.position,goal['y']-w['y'])>=.01)

def review_exploration(host,event):
    goal=host.world['goal'];motion=event.get('world_motion')
    if goal is None or motion is None:return
    after=motion['after'];action=event['executed_action'];outcome=event['outcome']
    if (outcome['action_id']!=action['id'] or outcome['action']!=action['action'] or
        outcome['target']!=action['target']):return
    if after['region']==goal['region'] and math.hypot(after['x']-goal['x'],after['y']-goal['y'])<.01:
        motion['exploration_review']={'goal':dict(goal),'status':'reached-observed-position',
            'action_id':action['id'],'basis':'observed-body-position'}
        host.world['goal']=None

def exploration(host,proposed):
    w=host.world;r=w['region'];x,y=host.position,w['y'];goal=w['goal']
    if goal is None or goal['region']!=r or math.hypot(goal['x']-x,goal['y']-y)<.01:
        parents=tree(r,(round(x),round(y)),w['pack_sha256']);options=[]
        for node in parents:
            if node==(round(x),round(y)):continue
            key=f'{r}:{node[0]},{node[1]}';visits=w['visited'].get(key,0)
            options.append((visits,abs(node[0]-x)+abs(node[1]-y),node))
        if not options:return None
        _,_,point=min(options)
        goal={'id':f'world-explore:{host.time}','region':r,'x':point[0],'y':point[1],'origin':'visited-cell-memory','map_knowledge':'inherited-collision-map'};w['goal']=goal
    choice=replace(proposed,action=11,decision=DECISION_FROM_ACTION[11],target=None)
    return choice,{'model':'world-exploration-v1','reason':'explore-world','goal_id':goal['id'],'world_goal':dict(goal),'selected_action':11,'proposal_action':proposed.action}

def step(host,direction):
    w=host.world;choice=host._current_choice
    executing=host.active_action['choice'] if host.active_action else {'action':choice.action,'target':choice.target}
    target=host.objects.get(executing['target'])
    if executing['action'] in (4,12) and target and target.get('region')==w['region']:
        destination=nearest(w['region'],target['x'],target['y'],w['pack_sha256'])
    elif executing['action']==5 and target:
        dx=host.position-target['x'];dy=w['y']-target['y'];destination=nearest(w['region'],host.position+(1 if dx>=0 else -1)*2,w['y']+(1 if dy>=0 else -1)*2,w['pack_sha256'])
    elif w['goal'] and w['goal']['region']==w['region']:destination=(w['goal']['x'],w['goal']['y'])
    else:destination=nearest(w['region'],host.position+direction,w['y'],w['pack_sha256'])
    identity=[w['region'],*destination]
    if w['route_target']!=identity or not w['route']:
        parents=tree(w['region'],(round(host.position),round(w['y'])),w['pack_sha256'])
        if destination not in parents:return
        route=[];node=destination
        while node is not None:route.append(list(node));node=parents[node]
        route.reverse()
        if route and math.hypot(route[0][0]-host.position,route[0][1]-w['y'])<.01:route.pop(0)
        w['route']=route;w['route_target']=identity
    while w['route'] and math.hypot(w['route'][0][0]-host.position,w['route'][0][1]-w['y'])<1e-9:
        w['route'].pop(0)
    route_observation=None
    if getattr(host,'_route_review_enabled',False) and w['route']:
        points=[(host.position,w['y']),*w['route']]
        remaining=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(points,points[1:]))
        route_observation={'action_id':executing.get('id',choice.id),'target':executing['target'],
            'action':executing['action'],'region':w['region'],'destination':list(destination),
            'distance_before':remaining,'distance_after':remaining,
            'basis':'inherited-collision-map-route'}
        host._route_observation=route_observation
    if not w['route'] or host.reserve<.01 or host.obstacle_present:return
    tx,ty=w['route'][0];dx,dy=tx-host.position,ty-w['y'];distance=math.hypot(dx,dy)
    amount=min(distance,.35*host.body_strength)
    if amount<=0:return
    w['facing']=('east' if dx>0 else 'west') if abs(dx)>abs(dy) else ('south' if dy>0 else 'north')
    host.position+=dx/distance*amount;w['y']+=dy/distance*amount;host.reserve-=.01
    if math.hypot(tx-host.position,ty-w['y'])<1e-9:
        host.position=float(tx);w['y']=float(ty);w['route'].pop(0)
        transition(host)
    if route_observation is not None:
        route_observation['distance_after']=max(0.,remaining-amount) if w['region']==route_observation['region'] else None
    visit(host)

def transition(host):
    if host.world.get('home_region') is not None and host.world['pack_sha256']==pack_hash():return
    w=host.world;r=w['region'];m=pack(w['pack_sha256'])['maps'][r];x,y=round(host.position),round(w['y']);destination=None
    for p in m['portals']:
        if (p['x'],p['y'])==(x,y):
            for arrival in p['arrivals']:
                if walkable(p['destination'],*arrival,w['pack_sha256']):destination=(p['destination'],*arrival);break
    if destination is None:
        for c in m['connections']:
            other=pack(w['pack_sha256'])['maps'][c['map']];edge=c['direction'];offset=c['offset'];point=None
            if edge=='up' and y==0 and w['facing']=='north':point=(x-offset,other['height']-1)
            elif edge=='down' and y==m['height']-1 and w['facing']=='south':point=(x-offset,0)
            elif edge=='left' and x==0 and w['facing']=='west':point=(other['width']-1,y-offset)
            elif edge=='right' and x==m['width']-1 and w['facing']=='east':point=(0,y-offset)
            if point and walkable(c['map'],*point,w['pack_sha256']):destination=(c['map'],*point)
    if destination and (not w.get('home_region') or destination[0] in home_regions(w)):
        w['region'],host.position,w['y']=destination;host.position=float(host.position);w['y']=float(w['y']);w['route']=[];w['route_target']=None;w['goal']=None;w['transitions']+=1


def confine_home(host,region):
    if host.world is None or region not in pack()['maps']:raise ValueError('expected a known town and top-down body')
    x,y=nearest(region,10,10)
    host.world.update(home_region=region,region=region,y=float(y),facing='south',goal=None,route=[],route_target=None)
    host.position=float(x);host.velocity=0.;host.active_action=None
    for n,obj in enumerate(host.objects.values()):
        ox,oy=nearest(region,x+2+n,y+1)
        obj.update(x=float(ox),y=float(oy),region=region)
    visit(host)


def home_regions(world):
    if world['pack_sha256']!=pack_hash():return pack(world['pack_sha256'])['home_regions']
    return [world.get('home_region')]

def expand_home(host):
    w=host.world
    if w is None or w.get('home_region')!='MAP_LITTLEROOT_TOWN':raise ValueError('Littleroot home required')
    w['pack_sha256']=town_pack_hash();w['goal']=None;w['route']=[];w['route_target']=None
    if not walkable(w['region'],round(host.position),round(w['y']),w['pack_sha256']):
        host.position,w['y']=map(float,nearest(w['region'],host.position,w['y'],w['pack_sha256']))
    host.active_action=None
    for obj in host.objects.values():
        if not walkable(obj['region'],int(obj['x']),int(obj['y']),w['pack_sha256']):
            obj['x'],obj['y']=map(float,nearest(obj['region'],obj['x'],obj['y'],w['pack_sha256']))
    visit(host)


def historical_packs(pack_id):
    versions=list(pack_files())
    return versions[:versions.index(pack_id)+1]

def rural_home(host,target=None):
    target=target or rural_pack_hash()
    expected=town_pack_hash() if target==rural_pack_hash() else rural_pack_hash()
    if target not in (rural_pack_hash(),visual_pack_hash()):raise ValueError('invalid rural map target')
    w=host.world
    if w is None or w.get('home_region')!='MAP_LITTLEROOT_TOWN' or w['pack_sha256']!=expected:raise ValueError('expected previous Littleroot map required')
    w.update(pack_sha256=target,goal=None,route=[],route_target=None)
    allowed=home_regions(w)
    if w['region'] not in allowed:w.update(region='MAP_LITTLEROOT_TOWN',y=10.);host.position=10.
    if not walkable(w['region'],round(host.position),round(w['y']),w['pack_sha256']):
        host.position,w['y']=map(float,nearest(w['region'],host.position,w['y'],w['pack_sha256']))
    host.velocity=0.;host.active_action=None
    for obj in host.objects.values():
        if obj['region'] not in allowed:obj.update(region='MAP_LITTLEROOT_TOWN',x=10.,y=10.)
        if not walkable(obj['region'],int(obj['x']),int(obj['y']),w['pack_sha256']):
            obj['x'],obj['y']=map(float,nearest(obj['region'],obj['x'],obj['y'],w['pack_sha256']))
    visit(host)
