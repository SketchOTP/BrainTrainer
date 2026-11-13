"""Native rural berry plots with tick-based regrowth and conserved harvests."""
from creature_brain.benchmark.contract import Outcome,PerceivedObject
from world_body import pack,visual_pack_hash
MODEL='berry-garden-v1'
REGROW_TICKS=80
REGION='MAP_LITTLEROOT_TOWN'
NUTRITION_MODEL='stored-berry-nutrition-v1'

def plots():
    return {f'berry-{i}':p for i,p in enumerate(pack(visual_pack_hash())['maps'][REGION]['berries'])}

def enable(host):
    if host.world is None or host.world['pack_sha256']!=visual_pack_hash():raise ValueError('rural visual world required for garden')
    if 'garden' in host.world:return
    host.world['garden']={'model':MODEL,'inventory':{'oran':0,'pecha':0}}
    for identity,p in plots().items():
        host.objects[identity]={'identity':identity,'type_id':f"berry:{p['kind']}",'category':2,
            'x':float(p['x']),'y':float(p['y']),'region':REGION,'visible':True,'food':False,
            'function':'berry-plot','kind':p['kind'],'state':1,'growth_ticks':0,'harvests':0}
    # Checkpoint canonicalization orders object keys. Use that order before the
    # first perception as well, so same-category attention survives restoration.
    host.objects=dict(sorted(host.objects.items()))

def advance(host):
    if host.world is None or 'garden' not in host.world:return []
    grown=[]
    for identity in plots():
        obj=host.objects[identity]
        if obj['state']==0:
            obj['growth_ticks']+=1
            if obj['growth_ticks']==REGROW_TICKS:
                obj.update(state=1,growth_ticks=0);grown.append(identity)
    return grown

def harvest(host,action,target):
    obj=host.objects[target.identity]
    if action.target!=target.identity:return Outcome(action.id,action.target,action.action,False,'target-mismatch',0.,0.)
    if not target.contact:return Outcome(action.id,action.target,action.action,False,'not-in-contact',0.,0.)
    if obj['state']!=1:return Outcome(action.id,action.target,action.action,False,'not-ripe',0.,0.)
    obj.update(state=0,growth_ticks=0);obj['harvests']+=1
    host.world['garden']['inventory'][obj['kind']]+=1
    return Outcome(action.id,action.target,action.action,True,'harvested',0.,0.)

def validate(host):
    garden=(host.world or {}).get('garden')
    if garden is None:return
    if host.world['pack_sha256']!=visual_pack_hash() or garden.get('model')!=MODEL:raise ValueError('invalid garden model')
    totals={'oran':0,'pecha':0}
    for identity,p in plots().items():
        obj=host.objects[identity]
        fixed={'identity':identity,'type_id':f"berry:{p['kind']}",'category':2,'x':p['x'],'y':p['y'],
            'region':REGION,'visible':True,'food':False,'function':'berry-plot','kind':p['kind']}
        if any(obj.get(k)!=v for k,v in fixed.items()):raise ValueError('garden plot differs from its native location')
        if type(obj.get('state')) is not int or obj['state'] not in (0,1):raise ValueError('invalid berry maturity')
        if type(obj.get('growth_ticks')) is not int or not 0<=obj['growth_ticks']<REGROW_TICKS or (obj['state']==1 and obj['growth_ticks']!=0):raise ValueError('invalid berry growth clock')
        if type(obj.get('harvests')) is not int or obj['harvests']<0:raise ValueError('invalid berry harvest count')
        totals[obj['kind']]+=obj['harvests']
    consumed={'oran':0,'pecha':0}
    if 'nutrition' in garden:
        nutrition=garden['nutrition']
        if not isinstance(nutrition,dict):raise ValueError('invalid nutrition state')
        consumed=nutrition.get('consumed')
        relief=nutrition.get('relief',{'oran':.2,'pecha':.2})
        if not isinstance(relief,dict) or set(relief)!={'oran','pecha'} or any(type(v) not in (int,float) or not 0<=v<=.2 for v in relief.values()):raise ValueError('invalid berry effectiveness')
        if nutrition.get('model')!=NUTRITION_MODEL or not isinstance(consumed,dict) or set(consumed)!=set(totals) or any(type(v) is not int or v<0 for v in consumed.values()):raise ValueError('invalid berry consumption state')
    inv=garden.get('inventory')
    if not isinstance(inv,dict) or set(inv)!=set(totals) or any(type(v) is not int or v<0 for v in inv.values()) or any(inv[k]+consumed[k]!=totals[k] for k in totals):raise ValueError('berry inventory and consumption do not match harvests')


def enable_nutrition(host):
    garden=(host.world or {}).get('garden')
    if garden is None:raise ValueError('berry garden required for stored food')
    if 'nutrition' not in garden:
        garden['nutrition']={'model':NUTRITION_MODEL,'consumed':{'oran':0,'pecha':0}}

def stored_food(host):
    garden=(host.world or {}).get('garden',{})
    if 'nutrition' not in garden:return []
    return [PerceivedObject(f'basket-{kind}',f'stored-berry:{kind}',category,0.,0.,True,
            f'stored-berry:{kind}:count={garden["inventory"][kind]}',(12,))
        for kind,category in (('oran',3),('pecha',8)) if garden['inventory'][kind]>0]

def eat_stored(host,action,target):
    kind=target.identity.removeprefix('basket-');garden=(host.world or {}).get('garden',{})
    if (action.action!=12 or action.target!=target.identity or not target.contact or
        'nutrition' not in garden or kind not in garden['inventory'] or garden['inventory'][kind]<=0):
        return Outcome(action.id,action.target,action.action,False,'stored-food-unavailable',0.,0.)
    prior_hunger,prior_energy=host.hunger,host.energy
    garden['inventory'][kind]-=1;garden['nutrition']['consumed'][kind]+=1
    host.hunger=max(0.,host.hunger-garden['nutrition'].get('relief',{'oran':.2,'pecha':.2})[kind]);host.energy=min(1.,host.energy+.05)
    adjustment=host.hunger-prior_hunger
    host.pending.append({'action_id':action.id,'target':target.identity,'hunger_adjustment':adjustment})
    return Outcome(action.id,action.target,12,True,'ate-stored-berry',host.energy-prior_energy,adjustment)


def visual_state(obj):
    """Project actual garden state into its native artwork, without advancing it.

    This is a display contract, not an additional source of creature knowledge.
    Generated environment assets must implement the same observable states.
    """
    if obj.get('function')!='berry-plot':return None
    if obj.get('kind') not in ('oran','pecha') or type(obj.get('state')) is not int or obj['state'] not in (0,1):
        raise ValueError('unknown berry visual state')
    growth=obj.get('growth_ticks')
    if type(growth) is not int or not 0<=growth<REGROW_TICKS or (obj['state']==1 and growth):
        raise ValueError('invalid visual growth clock')
    ripe=obj['state']==1
    return {'model':'native-berry-visual-v1','stage':'fruiting' if ripe else 'recovering',
        'asset':f"/assets/world/berry-{obj['kind']}.png",'frame':5 if ripe else 3,
        'frame_width':16,'frame_height':32,'anchor_y':16,
        'harvest_available':ripe,'regrowth_world_ticks_remaining':0 if ripe else REGROW_TICKS-growth,
        'basis':'authoritative garden state; no visual-only transition'}


def environment_contract(host):
    """Grounded object descriptions for environment authoring and display clients."""
    if not (host.world or {}).get('garden'):return []
    return [{'identity':identity,'type_id':host.objects[identity]['type_id'],
        'position':{k:host.objects[identity][k] for k in ('region','x','y')},
        'visual':visual_state(host.objects[identity]),
        'interaction':{'action':1,'requires_contact':True,'success':'harvested',
            'effects':['remove ripe berries','add one berry to matching inventory','start world-tick regrowth'],
            'failure':'not-ripe or not-in-contact; no harvested berry added'},
        'regrowth':{'duration_world_ticks':REGROW_TICKS,'during_pause':False},
        'walkable_plot':True}
        for identity in plots()]
