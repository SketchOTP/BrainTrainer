"""Genome-driven biochemistry from preserved local REA native evidence.

Native Update has no elapsed-time argument. The host selects a biochemical tick
duration and retains fractional seconds; Python arithmetic remains an explicit
adaptation, not x87 parity. Organ/receptor ownership, sequential
reaction order and the unusual 2.2-based kinetics follow the recovered engine.
No game data is bundled in this module.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import struct

from .genome import _HEADER, _SIZES, codon, expressed


class BiochemistryError(ValueError):
    """Unsupported or malformed supplied biochemical definition/state."""


def _number(value, name, lower=0.0, upper=1.0):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise BiochemistryError(f'{name} must be finite numeric data')
    try: value = float(value)
    except OverflowError as error: raise BiochemistryError(f'{name} exceeds numeric range') from error
    if not math.isfinite(value) or not lower <= value <= upper:
        raise BiochemistryError(f'{name} must be finite in {lower}..{upper}')
    return value


def _integer(value, name, lower=0, upper=255):
    if type(value) is not int or not lower <= value <= upper:
        raise BiochemistryError(f'{name} must be an integer in {lower}..{upper}')
    return value


def _clamp(value): return min(1.0, max(0.0, value))


def _f32(value): return struct.unpack('<f', struct.pack('<f', value))[0]


_BYTE_SCALE = _f32(1/255)
_POW_BASE = 2.200000047683716


def _unit(byte): return _f32(byte*_BYTE_SCALE)
_FIELDS = {
    'organ': ('clock_rate','damage_rate','life_force','biotick_start','atp_damage_coefficient'),
    'brain_organ': ('clock_rate','damage_rate','life_force','biotick_start','atp_damage_coefficient'),
    'receptor': ('organ','tissue','locus','chemical','threshold','nominal','gain','flags'),
    'emitter': ('organ','tissue','locus','chemical','threshold','rate','gain','flags'),
    'reaction': ('reactant1_amount','reactant1_chemical','reactant2_amount','reactant2_chemical',
                 'product1_amount','product1_chemical','product2_amount','product2_chemical','rate'),
    'initial_concentration': ('chemical','amount'),
    'neuroemitter': ('lobe0','neuron0','lobe1','neuron1','lobe2','neuron2','rate',
                     'chemical0','amount0','chemical1','amount1','chemical2','amount2','chemical3','amount3'),
    'halflives': tuple(f'chemical_{i}' for i in range(256)),
    'stimulus': ('stimulus','significance','input','intensity','features',
                 'chemical0','amount0','chemical1','amount1','chemical2','amount2','chemical3','amount3'),
}
_TYPES = {(3,0):'organ',(0,1):'brain_organ',(1,0):'receptor',(1,1):'emitter',
          (1,2):'reaction',(1,3):'halflives',(1,4):'initial_concentration',(1,5):'neuroemitter',
          (2,0):'stimulus'}


def _load(path):
    path = Path(path)
    if path.stat().st_size > 16*1024*1024: raise BiochemistryError('supplied genome exceeds 16 MiB')
    raw = path.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
    if raw[:4] != b'dna3':
        try: data = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as error: raise BiochemistryError('invalid genome JSON') from error
        return data
    records=[]; pos=4
    while raw[pos:pos+4] != b'gend':
        if raw[pos:pos+4] != b'gene' or pos+12>len(raw): raise BiochemistryError(f'invalid gene header at byte {pos}')
        offset=pos; header=dict(zip(_HEADER,raw[pos+4:pos+12])); pos+=12
        pair=header['type'],header['subtype']; size=_SIZES.get(pair)
        if size is None or pos+size>len(raw): raise BiochemistryError(f'unknown or truncated gene at byte {pos}')
        if pair in _TYPES:
            kind=_TYPES[pair]
            records.append({'kind':kind,'header':header,'offset':offset,'fields':dict(zip(_FIELDS[kind],raw[pos:pos+size]))})
        pos+=size
    if any(raw[pos+4:]): raise BiochemistryError('nonzero bytes after genome end')
    return {'records':records,'source_sha256':digest}


def _canonical(data):
    if not isinstance(data,dict) or not isinstance(data.get('records'),list) or len(data['records'])>100_000:
        raise BiochemistryError('biochemistry requires a bounded records array')
    records=[]
    for record in data['records']:
        if not isinstance(record,dict): raise BiochemistryError('gene records must be objects')
        kind=record.get('kind')
        if kind not in _FIELDS: continue
        h=record.get('header'); f=record.get('fields')
        if not isinstance(h,dict) or not isinstance(f,dict): raise BiochemistryError('gene requires header and fields')
        header={k:_integer(h.get(k),'gene header') for k in _HEADER}
        if _TYPES.get((header['type'],header['subtype']))!=kind:
            raise BiochemistryError('gene kind disagrees with its type/subtype header')
        fields={k:_integer(f.get(k),f'{kind}.{k}') for k in _FIELDS[kind]}
        records.append({'kind':kind,'header':header,'fields':fields,'offset':record.get('offset')})
    if not records: raise BiochemistryError('no biochemical genes supplied')
    source=data.get('source_sha256',data.get('sha256'))
    if not isinstance(source,str) or len(source)!=64 or any(c not in '0123456789abcdef' for c in source):
        raise BiochemistryError('definition requires underlying genome SHA-256')
    return {'source_sha256':source,'records':records}


@dataclass(frozen=True)
class Receptor:
    key: tuple[int,int,int]
    chemical: int
    threshold: float
    nominal: float
    gain: float
    flags: int
    gene_id: int


@dataclass(frozen=True)
class Emitter:
    key: tuple[int,int,int]
    chemical: int
    threshold: float
    rate: float
    gain: float
    flags: int
    gene_id: int


@dataclass(frozen=True)
class Reaction:
    reactants: tuple[tuple[int,int],tuple[int,int]]
    products: tuple[tuple[int,int],tuple[int,int]]
    rate: float
    gene_id: int


@dataclass(frozen=True)
class NeuroEmitter:
    neurons: tuple[tuple[int,int],...]
    rate: float
    products: tuple[tuple[int,float],...]
    gene_id: int


@dataclass(frozen=True)
class OrganDefinition:
    gene_id: int
    clock_rate: float
    repair_decay: float
    initial_life_force: float
    phase: float
    starvation_damage: float
    receptors: tuple[tuple[tuple[int,int,int],tuple[Receptor,...]],...]
    emitters: tuple[Emitter,...]
    reactions: tuple[Reaction,...]
    default: bool = False

    @property
    def receptor_count(self): return sum(len(group) for _,group in self.receptors)

    @property
    def energy_cost(self):
        return .0078+(self.receptor_count+len(self.emitters)+len(self.reactions))*_f32(.00039215686)


@dataclass(frozen=True)
class Definition:
    canonical_json: str
    source_sha256: str
    counts: tuple[tuple[str,int],...]
    organs: tuple[OrganDefinition,...]
    retention: tuple[float,...]
    initial: tuple[float,...]
    neuroemitters: tuple[NeuroEmitter,...]
    brain_organs: tuple[tuple[int,...],...]


def _compile(data, age_stage, sex):
    data=_canonical(data); records=data['records']; groups=[]; current=None
    initial=[0.0]*256; retention=[0.0]*256; neuro={}; brains=[]
    # The native constructor creates an unencoded default organ before scanning
    # explicit organ genes. Genes before the first organ belong to that owner.
    groups.append((None,[])); current=groups[-1]
    for record in records:
        kind=record['kind']; h=record['header']; f=record['fields']
        active=expressed(h,age_stage,sex)
        if kind=='organ':
            # Native FindGene applies expression filters BEFORE checking stop
            # boundaries. An inactive organ does not delimit the preceding
            # active owner's otherwise expressed receptors/emitters/reactions.
            if active:
                current=(record,[]); groups.append(current)
            continue
        if kind=='brain_organ':
            if active: brains.append(tuple(f[k] for k in _FIELDS[kind]))
            continue
        if not active: continue
        if kind in ('receptor','emitter','reaction'):
            if current[0] is not False: current[1].append(record)
        elif kind=='initial_concentration': initial[f['chemical']]=_unit(f['amount'])
        elif kind=='halflives':
            for i in range(256):
                b=f[f'chemical_{i}']
                retention[i]=0.0 if not b else _f32(.5 ** (1/_f32(_POW_BASE ** _f32(b*_f32(32/255)))))
        elif kind=='neuroemitter':
            neurons=tuple((f[f'lobe{i}'],f[f'neuron{i}']) for i in range(3))
            neuro[neurons]=NeuroEmitter(neurons,_unit(f['rate']),
                                       tuple((f[f'chemical{i}'],_unit(f[f'amount{i}'])) for i in range(4)),h['id'])
    # Native scans expressed organ generations 0,1,... and stops at the first
    # missing generation; each generation retains its physical source order.
    admitted=[groups[0]]
    generation=0
    while True:
        found=[g for g in groups[1:] if g[0] is not False and g[0]['header']['generation']==generation]
        if not found: break
        admitted.extend(found);generation+=1
    organs=[]
    for source,children in admitted:
        if source is False: continue
        receptors={}; emitters={}; reactions=[]
        for r in children:
            f=r['fields']; gene_id=r['header']['id']
            if r['kind']=='reaction':
                terms=lambda prefix:tuple((f[f'{prefix}{i}_chemical'],codon(f[f'{prefix}{i}_amount'],1,16)) for i in (1,2))
                reactions.append(Reaction(terms('reactant'),terms('product'),_f32(1-_unit(f['rate'])),gene_id))
            elif r['kind']=='receptor':
                organ=codon(f['organ'],0,3)
                tissue=len(reactions)-1 if organ==3 else f['tissue']
                key=organ,tissue,f['locus']
                receptor=Receptor(key,f['chemical'],_unit(f['threshold']),_unit(f['nominal']),
                                  _unit(f['gain']),f['flags'],gene_id)
                receptors.setdefault(key,[]).append(receptor)
            else:
                key=codon(f['organ'],0,2),f['tissue'],f['locus']
                emitters[(key,f['chemical'])]=Emitter(key,f['chemical'],_unit(f['threshold']),
                                                    1/codon(f['rate'],1,255),_unit(f['gain']),f['flags'],gene_id)
        if source is None:
            gene_id=-1; clock=.5; decay=struct.unpack('<f',bytes.fromhex('a1a0203d'))[0]
            initial_life=500000.0; phase=0.0; damage=initial_life*.0078125
        else:
            f=source['fields'];gene_id=source['header']['id'];clock=_unit(f['clock_rate'])
            decay=_unit(f['damage_rate']);initial_life=max(1.0,_unit(f['life_force']))*1_000_000
            phase=_unit(f['biotick_start']);damage=min(1.0,_unit(f['atp_damage_coefficient']))*initial_life*_BYTE_SCALE
        organs.append(OrganDefinition(gene_id,clock,decay,initial_life,phase,damage,
                                     tuple((key,tuple(value)) for key,value in receptors.items()),
                                     tuple(emitters.values()),tuple(reactions),source is None))
    return Definition(json.dumps(data,sort_keys=True,separators=(',',':')),data['source_sha256'],
                      tuple(sorted(Counter(r['kind'] for r in records).items())),tuple(organs),
                      tuple(retention),tuple(initial),tuple(neuro.values()),tuple(brains))


@dataclass
class Organ:
    definition: OrganDefinition
    index: int
    clock_rate: float
    phase: float
    initial_life_force: float
    life_force: float
    reserve_life_force: float
    repair_rate: float=0.0
    injury_input: float=0.0
    updates: int=0
    emitter_phases: list[float]=field(default_factory=list)
    reaction_rates: list[float]=field(default_factory=list)
    loci: dict=field(default_factory=dict)
    health_value: float=1.0

    @classmethod
    def create(cls,definition,index):
        return cls(definition,index,definition.clock_rate,definition.phase,definition.initial_life_force,
                   definition.initial_life_force,definition.initial_life_force,
                   emitter_phases=[0.0]*len(definition.emitters),reaction_rates=[r.rate for r in definition.reactions],
                   health_value=.5 if definition.default else 1.0)

    @property
    def gene_id(self): return self.definition.gene_id

    @property
    def health(self): return self.health_value

    @property
    def alive(self): return self.reserve_life_force>.5

    def clone(self):
        result=object.__new__(type(self));result.__dict__=self.__dict__.copy()
        result.emitter_phases=self.emitter_phases.copy();result.reaction_rates=self.reaction_rates.copy();result.loci=self.loci.copy()
        return result

    def to_dict(self):
        return {k:deepcopy(v) for k,v in self.__dict__.items() if k not in ('definition','loci')} | {'loci':[[*k,v] for k,v in self.loci.items()]}


class Biochemistry:
    """Stateful native-informed kernel with configurable biochemical cadence.

    Loci0/1 are creature-wide inputs/latched outputs. Organ2/3 addresses remain
    scoped to their owning organ. Chemical0 is the absent-reagent sentinel.
    Initial receptor readout is a pure projection; subsequent readouts are latched
    at native organ schedule points. clone shares the immutable compiled genome.
    """
    tick_seconds=1.0
    limitations=('host-selected mapping from native biochemical updates to seconds',
                 'Python arithmetic does not establish x87/float32 execution parity',
                 'brain-organ gene is retained as metadata; separate neural energy behavior is unmodeled',
                 'creature and neural scheduling are owned by the host adapter')

    def __init__(self,data,*,age_stage=3,sex='female',tick_seconds=1.0):
        self.tick_seconds=_number(tick_seconds,'biochemical tick seconds',0.001,60.0)
        self.age_stage=_integer(age_stage,'age stage',0,7)
        if sex not in ('female','male'): raise BiochemistryError('sex must be female or male')
        self.sex=sex;self.definition=_compile(data,age_stage,sex);self.source_sha256=self.definition.source_sha256
        self.chemicals=list(self.definition.initial);self.chemicals[0]=0.0
        self.organs=[Organ.create(d,i) for i,d in enumerate(self.definition.organs)]
        self.neuro_phases=[0.0]*len(self.definition.neuroemitters)
        self.pending_seconds=0.0;self.ticks=0;self._inputs={};self._outputs={};self._neurons={}
        self._project_initial_receptors()

    @classmethod
    def from_file(cls,path,*,age_stage=3,sex='female',tick_seconds=1.0):
        return cls(_load(path),age_stage=age_stage,sex=sex,tick_seconds=tick_seconds)

    @property
    def gene_counts(self): return dict(self.definition.counts)

    def clone(self):
        result=object.__new__(type(self));result.__dict__=self.__dict__.copy()
        result.chemicals=self.chemicals.copy();result.organs=[o.clone() for o in self.organs]
        result.neuro_phases=self.neuro_phases.copy();result._inputs=self._inputs.copy()
        result._outputs=self._outputs.copy();result._neurons=self._neurons.copy()
        return result

    def inject(self,chemical,amount):
        chemical=_integer(chemical,'chemical');amount=_number(amount,'injected amount',-1.0,1.0)
        if chemical:
            concentration=_number(self.chemicals[chemical],'chemical')
            self.chemicals[chemical]=_clamp(concentration+amount)

    def receptors(self):
        """Latched creature-locus writes, including emitter flag1 clear writes."""
        return self._outputs.copy()

    @staticmethod
    def _mapping(values, length, name):
        if not isinstance(values,Mapping): raise BiochemistryError(f'{name} must be a locus mapping')
        result={}
        for key,value in values.items():
            if not isinstance(key,tuple) or len(key)!=length: raise BiochemistryError(f'{name} requires {length}-element tuple keys')
            result[tuple(_integer(i,name,0,65535) for i in key)]=_number(value,name,-1.0,1.0)
        return result

    def set_neural_inputs(self,values): self._neurons=self._mapping(values,2,'neural inputs')

    @staticmethod
    def _receptor_alias(key):
        """Map an emitter address to a proven shared receptor-mode pointer.

        Native Creature forwards to different faculties for the two modes.
        Identical displayed organ/tissue/locus triples need not share storage.
        Life, Motor, Skeletal and Reproductive GetLocusAddress bodies establish
        these exact same- and cross-locus aliases; other inputs stay separate.
        """
        domain,tissue,locus=key
        if domain==0: return key
        if domain!=1: return None
        if tissue==1 and locus<32: return key
        if tissue==5 and locus<20: return key
        if tissue==3 and locus==0: return key
        if tissue==2 and 2<=locus<=5: return domain,tissue,locus-2
        if tissue==4 and 14<=locus<=37: return domain,tissue,locus-14
        return None

    def _read_locus(self,organ,key):
        domain,tissue,locus=key
        if domain==2:
            return {0:organ.clock_rate,1:organ.repair_rate,2:organ.health}.get(locus,0.0)
        if domain==3: return organ.reaction_rates[tissue] if 0<=tissue<len(organ.reaction_rates) else 0.0
        alias=self._receptor_alias(key)
        if alias is not None and alias in self._outputs: return self._outputs[alias]
        return self._inputs.get(key,0.0)

    def _write_locus(self,organ,key,value):
        domain,tissue,locus=key
        if domain==2:
            if locus==0: organ.clock_rate=value
            elif locus==1: organ.repair_rate=value
            elif locus==2: organ.injury_input=value
            organ.loci[key]=value
        elif domain==3:
            if 0<=tissue<len(organ.reaction_rates):
                organ.reaction_rates[tissue]=value;organ.loci[key]=value
        else:
            self._outputs[key]=value

    def _group_value(self,key,group):
        usable=[r for r in group if r.chemical]
        if not usable: return 0.0,False
        nominal=sum(r.nominal for r in usable)/len(usable);positive=[];negative=[]
        for r in usable:
            signal=max(0.0,self.chemicals[r.chemical]-r.threshold)
            signal=r.gain if signal>0 and r.flags&2 else signal*r.gain
            (negative if r.flags&1 else positive).append(signal)
        if key==(1,3,0):
            return float(sum(r.nominal for r in usable)+sum(positive)-sum(negative)>0),True
        value=nominal
        if positive: value=min(1.0,value+sum(positive)/len(positive))
        if negative: value=max(0.0,value-sum(negative)/len(negative))
        return value,True

    def _project_initial_receptors(self):
        for organ in self.organs:
            for key,group in organ.definition.receptors:
                if key[0] in (0,1): self._outputs[key]=self._group_value(key,group)[0]

    def _process_receptors(self,organ,selective=False):
        activity=False
        for key,group in organ.definition.receptors:
            if selective and not (key[0]==2 and key[2]==0): continue
            value,active=self._group_value(key,group);self._write_locus(organ,key,value);activity|=active
        return activity

    def _injure(self,organ,damage):
        organ.life_force=max(0.0,organ.life_force-damage)
        organ.health_value=_clamp(organ.life_force/organ.initial_life_force)
        self.inject(127,min(1.0,damage/organ.initial_life_force))

    def _process_all(self,organ):
        active=False
        for i,emitter in enumerate(organ.definition.emitters):
            value=self._read_locus(organ,emitter.key)
            if emitter.flags&4: value=1-value
            organ.emitter_phases[i]+=emitter.rate
            if organ.emitter_phases[i]<=1: continue
            organ.emitter_phases[i]-=1
            if value==0 or value<=emitter.threshold: continue
            amount=emitter.gain if emitter.flags&2 else (value-emitter.threshold)*emitter.gain
            self.inject(emitter.chemical,_clamp(amount));active=True
            if emitter.flags&1:
                if emitter.key[0] in (0,1):
                    self._inputs[emitter.key]=0.0
                    alias=self._receptor_alias(emitter.key)
                    if alias is not None: self._outputs[alias]=0.0
                elif emitter.key[0]==2:
                    # Emitter-mode locus2 refers to health, not injuryinput.
                    if emitter.key[2]==2: organ.health_value=0.0
                    else: self._write_locus(organ,emitter.key,0.0)
        for index,reaction in enumerate(organ.definition.reactions):
            ratios=[self.chemicals[c]/n if c else 1.0 for c,n in reaction.reactants]
            available=min(ratios)
            if available==0: continue
            rate=organ.reaction_rates[index]
            retention=.5**(1/(_POW_BASE**((1-rate)*32)))
            extent=(1-retention)*available
            for chemical,coefficient in reaction.reactants:
                if chemical: self.chemicals[chemical]=_clamp(self.chemicals[chemical]-extent*coefficient)
            for chemical,coefficient in reaction.products:
                if chemical: self.chemicals[chemical]=_clamp(self.chemicals[chemical]+extent*coefficient)
            active=True
        return active

    def _update_organ(self,organ):
        if not organ.alive: return
        organ.phase+=organ.clock_rate;active=False
        if organ.phase<1:
            active=self._process_receptors(organ,True)
        else:
            organ.phase-=1;organ.updates+=1
            cost=organ.definition.energy_cost;paid=self.chemicals[35]>=cost
            if paid:
                self.chemicals[35]=_clamp(self.chemicals[35]-cost);self.chemicals[36]=_clamp(self.chemicals[36]+cost)
                self._process_all(organ)
                # Native00417880 ORs the activity result with1 after successful
                # ATP consumption, including empty or substrate-starved organs.
                active=True
            else: self._injure(organ,organ.definition.starvation_damage)
            gap=organ.reserve_life_force-organ.life_force
            organ.reserve_life_force-=gap*organ.definition.repair_decay
            if paid:
                restored=gap*organ.repair_rate;organ.life_force+=restored
                self.inject(127,-min(1.0,restored/organ.initial_life_force))
                active|=gap>.5
            organ.health_value=_clamp(organ.life_force/organ.initial_life_force)
            if organ.injury_input!=0:
                self._injure(organ,organ.injury_input*organ.initial_life_force*.1);organ.injury_input=0.0
            active=self._process_receptors(organ) or active
        if active:
            organ.life_force*=1-1e-5;organ.reserve_life_force*=1-1e-5
            organ.health_value=_clamp(organ.life_force/organ.initial_life_force)

    def _tick(self):
        for i,emitter in enumerate(self.definition.neuroemitters):
            self.neuro_phases[i]+=emitter.rate
            if self.neuro_phases[i]>1:
                self.neuro_phases[i]-=1
                amount=1.0
                for binding in emitter.neurons:
                    # Tissue255 is a real binding (last matching lobe), not an
                    # unused-input sentinel. Unbound/invalid cells read zero.
                    amount*=self._neurons.get(binding,0.0)
                for chemical,gain in emitter.products:
                    self.inject(chemical,max(-1.0,min(1.0,amount*gain)))
        for organ in self.organs: self._update_organ(organ)
        self.chemicals[:]=[value*factor for value,factor in zip(self.chemicals,self.definition.retention)]
        self.chemicals[0]=0.0;self.ticks+=1

    def step(self,dt,loci=None,*,neuronal_values=None):
        dt=_number(dt,'dt',0.0,3600.0)
        if not isinstance(self.chemicals,list) or len(self.chemicals)!=256: raise BiochemistryError('chemicals must contain 256 values')
        concentrations=[_number(v,'chemical') for v in self.chemicals]
        if concentrations[0]!=0: raise BiochemistryError('chemical zero must remain absent')
        inputs=None if loci is None else self._mapping(loci,3,'loci')
        neurons=None if neuronal_values is None else self._mapping(neuronal_values,2,'neural inputs')
        self.chemicals[:]=concentrations
        if inputs is not None:
            self._inputs.update(inputs)
            for key,value in inputs.items():
                alias=self._receptor_alias(key)
                if alias is not None and alias in self._outputs: self._outputs[alias]=value
        if neurons is not None: self._neurons=neurons
        self.pending_seconds+=dt
        while self.pending_seconds>=self.tick_seconds-1e-12:
            self.pending_seconds-=self.tick_seconds
            if abs(self.pending_seconds)<1e-12: self.pending_seconds=0.0
            self._tick()
        return self.receptors()

    def to_dict(self):
        return {'schema':1,'source_sha256':self.source_sha256,'definition':json.loads(self.definition.canonical_json),'tick_seconds':self.tick_seconds,
                'age_stage':self.age_stage,'sex':self.sex,'chemicals':self.chemicals.copy(),'ticks':self.ticks,
                'pending_seconds':self.pending_seconds,'organs':[o.to_dict() for o in self.organs],
                'neuro_phases':self.neuro_phases.copy(),'inputs':[[*k,v] for k,v in self._inputs.items()],
                'outputs':[[*k,v] for k,v in self._outputs.items()],'neurons':[[*k,v] for k,v in self._neurons.items()]}

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict) or data.get('schema')!=1: raise BiochemistryError('unsupported biochemical checkpoint')
        try:
            result=cls(data['definition'],age_stage=data['age_stage'],sex=data['sex'],tick_seconds=data.get('tick_seconds',1.0))
            if data['source_sha256']!=result.source_sha256: raise BiochemistryError('genome identity mismatch')
            if not isinstance(data['chemicals'],list) or len(data['chemicals'])!=256: raise BiochemistryError('invalid chemical count')
            result.chemicals=[_number(v,'chemical') for v in data['chemicals']]
            if result.chemicals[0]!=0: raise BiochemistryError('chemical zero must remain absent')
            result.ticks=_integer(data['ticks'],'ticks',0,2**53)
            result.pending_seconds=_number(data['pending_seconds'],'pending seconds',0.0,result.tick_seconds-1e-15)
            if not isinstance(data['organs'],list) or len(data['organs'])!=len(result.organs): raise BiochemistryError('organ count mismatch')
            for organ,saved in zip(result.organs,data['organs']):
                if saved['index']!=organ.index or saved['initial_life_force']!=organ.initial_life_force: raise BiochemistryError('organ identity mismatch')
                for key in ('clock_rate','repair_rate','injury_input'): setattr(organ,key,_number(saved[key],key))
                organ.health_value=_number(saved['health_value'],'organ health')
                organ.phase=_number(saved['phase'],'organ phase',0.0,1.0)
                for key in ('life_force','reserve_life_force'):setattr(organ,key,_number(saved[key],key,0.0,organ.initial_life_force))
                organ.updates=_integer(saved['updates'],'organ updates',0,2**53)
                for key,count in (('emitter_phases',len(organ.definition.emitters)),('reaction_rates',len(organ.definition.reactions))):
                    if not isinstance(saved[key],list) or len(saved[key])!=count: raise BiochemistryError(f'invalid {key}')
                    setattr(organ,key,[_number(v,key) for v in saved[key]])
                organ.loci=result._decode_mapping(saved['loci'],3,'organ loci')
            if len(data['neuro_phases'])!=len(result.neuro_phases): raise BiochemistryError('neuroemitter count mismatch')
            result.neuro_phases=[_number(v,'neuroemitter phase') for v in data['neuro_phases']]
            result._inputs=result._decode_mapping(data['inputs'],3,'inputs')
            result._outputs=result._decode_mapping(data['outputs'],3,'outputs')
            result._neurons=result._decode_mapping(data['neurons'],2,'neurons')
            return result
        except (KeyError,TypeError,IndexError,OverflowError) as error: raise BiochemistryError('malformed biochemical checkpoint') from error

    @classmethod
    def _decode_mapping(cls,rows,length,name):
        if not isinstance(rows,list): raise BiochemistryError(f'invalid {name}')
        result={}
        for row in rows:
            if not isinstance(row,list) or len(row)!=length+1: raise BiochemistryError(f'invalid {name}')
            key=tuple(row[:length])
            if key in result: raise BiochemistryError(f'duplicate {name} key')
            result.update(cls._mapping({key:row[-1]},length,name))
        return result
