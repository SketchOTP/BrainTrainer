"""Native rural berry plots with tick-based regrowth and conserved harvests."""
from creature_brain.benchmark.contract import Outcome,PerceivedObject
from world_body import pack,visual_pack_hash,interactive_pack_hash,path_aligned_pack_hash,town_canopy_pack_hash,scoped_town_pack_hash,natural_town_pack_hash,connected_town_pack_hash
MODEL='berry-garden-v1'  # retained for checkpoints and adoption events created before v9
GROWTH_MODEL='berry-garden-v2'
GROWTH_ART_MODEL='berry-tree-growth-v1'
REGROW_TICKS=80
TREE_STAGE_TICKS=24
BERRY_STAGE_TICKS=16
REGION='MAP_LITTLEROOT_TOWN'
NUTRITION_MODEL='stored-berry-nutrition-v1'
GARDEN_WORLD_PACKS=(visual_pack_hash(),interactive_pack_hash(),path_aligned_pack_hash(),town_canopy_pack_hash(),scoped_town_pack_hash(),natural_town_pack_hash(),connected_town_pack_hash())

def plots(pack_id=None):
    return {f'berry-{i}':p for i,p in enumerate(pack(pack_id or visual_pack_hash())['maps'][REGION]['berries'])}

def model_for_pack(pack_id):
    if pack_id not in GARDEN_WORLD_PACKS:raise ValueError('rural visual world required for garden')
    return GROWTH_MODEL if pack_id in (natural_town_pack_hash(),connected_town_pack_hash()) else MODEL

def enable(host):
    if host.world is None:raise ValueError('rural visual world required for garden')
    pack_id=host.world['pack_sha256'];model=model_for_pack(pack_id)
    if 'garden' in host.world:return
    host.world['garden']={'model':model,'inventory':{'oran':0,'pecha':0}}
    if model==GROWTH_MODEL:
        host.world['garden'].update(pack_sha256=pack_id,growth_model=GROWTH_ART_MODEL)
    initial_stages=(0,1,2,3,5,5)
    for index,(identity,p) in enumerate(plots(pack_id).items()):
        host.objects[identity]={'identity':identity,'type_id':f"berry:{p['kind']}",'category':2,
            'x':float(p['x']),'y':float(p['y']),'region':REGION,'visible':True,'food':False,
            'function':'berry-plot','kind':p['kind'],'state':1 if model==MODEL else 0,'harvests':0}
        if model==MODEL:
            host.objects[identity].update(state=1,growth_ticks=0)
        else:
            life_stage=initial_stages[index%len(initial_stages)]
            berry_stage=1 if index==len(initial_stages)-1 else 0
            host.objects[identity].update(life_stage=life_stage,
                life_stage_ticks=(index*5)%TREE_STAGE_TICKS if life_stage<5 else 0,
                berry_stage=berry_stage,berry_stage_ticks=0,
                state=0)
    # Checkpoint canonicalization orders object keys. Use that order before the
    # first perception as well, so same-category attention survives restoration.
    host.objects=dict(sorted(host.objects.items()))

def advance(host):
    if host.world is None or 'garden' not in host.world:return []
    grown=[]
    garden=host.world['garden'];pack_id=host.world['pack_sha256']
    for identity in plots(pack_id):
        obj=host.objects[identity]
        if garden['model']==MODEL and obj['state']==0:
            obj['growth_ticks']+=1
            if obj['growth_ticks']==REGROW_TICKS:
                obj.update(state=1,growth_ticks=0);grown.append(identity)
        elif garden['model']==GROWTH_MODEL:
            if obj['life_stage']<5:
                obj['life_stage_ticks']+=1
                if obj['life_stage_ticks']==TREE_STAGE_TICKS:
                    obj.update(life_stage=obj['life_stage']+1,life_stage_ticks=0,
                        berry_stage=0,berry_stage_ticks=0,state=0)
            elif obj['berry_stage']<2:
                obj['berry_stage_ticks']+=1
                if obj['berry_stage_ticks']==BERRY_STAGE_TICKS:
                    obj['berry_stage']+=1;obj['berry_stage_ticks']=0
                    if obj['berry_stage']==2:
                        obj['state']=1;grown.append(identity)
    return grown

def harvest(host,action,target):
    obj=host.objects[target.identity]
    if action.target!=target.identity:return Outcome(action.id,action.target,action.action,False,'target-mismatch',0.,0.)
    if not target.contact:return Outcome(action.id,action.target,action.action,False,'not-in-contact',0.,0.)
    if obj['state']!=1:return Outcome(action.id,action.target,action.action,False,'not-ripe',0.,0.)
    if host.world['garden']['model']==GROWTH_MODEL:
        # Picking only clears the fruit cycle. The mature tree stays mature.
        obj.update(state=0,berry_stage=0,berry_stage_ticks=0)
    else:
        obj.update(state=0,growth_ticks=0)
    obj['harvests']+=1
    host.world['garden']['inventory'][obj['kind']]+=1
    return Outcome(action.id,action.target,action.action,True,'harvested',0.,0.)

def migrate_to_growth_model(host,target_pack):
    garden=(host.world or {}).get('garden')
    if garden is None:return
    if target_pack!=natural_town_pack_hash() or host.world.get('pack_sha256')!=target_pack:
        raise ValueError('growth garden migration requires the v9 natural town pack')
    if garden.get('model')==GROWTH_MODEL and garden.get('pack_sha256')==target_pack:return
    if garden.get('model')!=MODEL:raise ValueError('unsupported prior garden model')
    for identity,p in plots(target_pack).items():
        obj=host.objects[identity]
        ripe=obj['state']==1
        obj.update(x=float(p['x']),y=float(p['y']),region=REGION,
            life_stage=5,life_stage_ticks=0,
            berry_stage=2 if ripe else 0,berry_stage_ticks=0)
        obj.pop('growth_ticks',None)
    garden.update(model=GROWTH_MODEL,pack_sha256=target_pack,growth_model=GROWTH_ART_MODEL)

def validate(host):
    garden=(host.world or {}).get('garden')
    if garden is None:return
    pack_id=host.world['pack_sha256']
    expected_model=model_for_pack(pack_id)
    if garden.get('model')!=expected_model:raise ValueError('invalid garden model')
    if expected_model==GROWTH_MODEL and (garden.get('pack_sha256')!=pack_id or garden.get('growth_model')!=GROWTH_ART_MODEL):
        raise ValueError('invalid berry tree growth model')
    totals={'oran':0,'pecha':0}
    for identity,p in plots(pack_id).items():
        obj=host.objects[identity]
        fixed={'identity':identity,'type_id':f"berry:{p['kind']}",'category':2,'x':p['x'],'y':p['y'],
            'region':REGION,'visible':True,'food':False,'function':'berry-plot','kind':p['kind']}
        if any(obj.get(k)!=v for k,v in fixed.items()):raise ValueError('garden plot differs from its native location')
        if type(obj.get('state')) is not int or obj['state'] not in (0,1):raise ValueError('invalid berry maturity')
        if expected_model==MODEL:
            if type(obj.get('growth_ticks')) is not int or not 0<=obj['growth_ticks']<REGROW_TICKS or (obj['state']==1 and obj['growth_ticks']!=0):raise ValueError('invalid berry growth clock')
        else:
            life=obj.get('life_stage');life_ticks=obj.get('life_stage_ticks')
            berry=obj.get('berry_stage');berry_ticks=obj.get('berry_stage_ticks')
            if type(life) is not int or not 0<=life<=5 or type(life_ticks) is not int or (life<5 and not 0<=life_ticks<TREE_STAGE_TICKS) or (life==5 and life_ticks!=0):
                raise ValueError('invalid tree growth stage')
            if type(berry) is not int or not 0<=berry<=2 or type(berry_ticks) is not int or (berry<2 and not 0<=berry_ticks<BERRY_STAGE_TICKS) or (berry==2 and berry_ticks!=0):
                raise ValueError('invalid berry growth stage')
            if ((life<5 and (berry!=0 or berry_ticks!=0 or obj['state']!=0)) or
                (life==5 and obj['state']!=(1 if berry==2 else 0))):
                raise ValueError('berry maturity differs from the tree stage')
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
    if 'life_stage' in obj:
        life=obj.get('life_stage');life_ticks=obj.get('life_stage_ticks')
        berry=obj.get('berry_stage');berry_ticks=obj.get('berry_stage_ticks')
        if (type(life) is not int or not 0<=life<=5 or type(life_ticks) is not int or
                (life<5 and not 0<=life_ticks<TREE_STAGE_TICKS) or (life==5 and life_ticks!=0) or
                type(berry) is not int or not 0<=berry<=2 or type(berry_ticks) is not int or
                (berry<2 and not 0<=berry_ticks<BERRY_STAGE_TICKS) or (berry==2 and berry_ticks!=0) or
                (life<5 and (berry!=0 or berry_ticks!=0 or obj['state']!=0)) or
                (life==5 and obj['state']!=(1 if berry==2 else 0))):
            raise ValueError('unknown berry tree growth stage')
        if life<5:
            row,frame=(0,life) if life<4 else (1,0)
            stage=('seed-mound','sprout','sapling','small-tree','medium-tree')[life]
            remaining=(5-life)*TREE_STAGE_TICKS-life_ticks+2*BERRY_STAGE_TICKS
        elif berry==0:
            row,frame=(1,1) if obj['kind']=='oran' else (2,0)
            stage='large-tree-no-berries'
            remaining=2*BERRY_STAGE_TICKS-berry_ticks
        elif berry==1:
            row,frame=(1,2) if obj['kind']=='oran' else (2,1)
            stage='small-berries'
            remaining=BERRY_STAGE_TICKS-berry_ticks
        else:
            row,frame=(1,3) if obj['kind']=='oran' else (2,2)
            stage='full-berries'
            remaining=0
        underlay=None
        if life>=2:
            variant=int(obj['identity'].rsplit('-',1)[-1])%4
            underlay={'atlas_url':'/assets/interactive-art/v1/garden-soil.png',
                'row':variant//2,'frame':variant%2,'frame_size':128,
                'source_rect':[4,36,120,56],
                'fixed_view':True,'render_size_cells':[2.1,.98]}
        visual={'model':'native-berry-tree-visual-v1','stage':stage,
            'atlas_url':'/assets/interactive-art/v1/berry-growth.png','frame_size':128,
            'row':row,'frame':frame,'fixed_view':True,'render_size_cells':[1.4,1.55],
            'harvest_available':obj['state']==1,'regrowth_world_ticks_remaining':remaining,
            'basis':'authoritative tree and berry stages; no visual-only transition'}
        if underlay:visual['underlay']=underlay
        return visual
    growth=obj.get('growth_ticks')
    if type(growth) is not int or not 0<=growth<REGROW_TICKS or (obj['state']==1 and growth):
        raise ValueError('invalid visual growth clock')
    ripe=obj['state']==1
    return {'model':'native-berry-visual-v2','stage':'fruiting' if ripe else 'recovering',
        'atlas_url':'/assets/interactive-art/v1/trees.png','frame_size':128,
        'row':2 if ripe else 3,'frame':{'oran':1,'pecha':2}[obj['kind']] if ripe else 2,
        'fixed_view':True,'render_size_cells':[1.2,1.55],
        'harvest_available':ripe,'regrowth_world_ticks_remaining':0 if ripe else REGROW_TICKS-growth,
        'basis':'authoritative garden state; no visual-only transition'}


def environment_contract(host):
    """Grounded object descriptions for environment authoring and display clients."""
    if not (host.world or {}).get('garden'):return []
    growth_model=host.world['garden'].get('model')==GROWTH_MODEL
    effects=(['advance seed mound through sprout, sapling, small tree, medium tree and large tree',
        'grow no berries into small berries and then full berries',
        'keep full berries until picked; picking clears only berries and leaves the large tree']
        if growth_model else ['remove ripe berries','add one berry to matching inventory','start world-tick regrowth'])
    return [{'identity':identity,'type_id':host.objects[identity]['type_id'],
        'position':{k:host.objects[identity][k] for k in ('region','x','y')},
        'visual':visual_state(host.objects[identity]),
        'interaction':{'action':1,'requires_contact':True,'success':'harvested',
            'effects':effects,
            'failure':'not-ripe or not-in-contact; no harvested berry added'},
        'regrowth':{'duration_world_ticks':BERRY_STAGE_TICKS*2 if growth_model else REGROW_TICKS,
            'tree_stage_duration_world_ticks':TREE_STAGE_TICKS if growth_model else None,
            'during_pause':False},
        'walkable_plot':True}
        for identity in plots(host.world['pack_sha256'])]
