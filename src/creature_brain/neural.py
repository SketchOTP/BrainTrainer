"""Genome-driven fifteen-lobe neural runtime, informed by local native REA evidence.

Runs supplied SVRules in one shared component-priority schedule; actions come
only from the decision lobe. Python finite arithmetic is not x87 parity. Equal
priority components use stable insertion order (native sorting ties unqualified).
Migration selects a bounded set of highest-valued sources using the recovered
native finite-value ordering. Native numerical and runtime parity remain open.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from collections.abc import Mapping, Sequence
from copy import deepcopy
import math
from pathlib import Path

from .genome import GenomeDefinition, GenomeError, codon, definition_from_dict, expressed, load_genome
from .svrule import Context, Program, TractState, execute_trusted, native_random_index, reinforced_weight

# Local Docking Station.catalogue, ARRAY Action Script To Neuron Mappings;
# native00406750 indexes this array. The final unused action has no default cell.
ACTION_FROM_DECISION = (0, 1, 6, 7, 12, 2, 4, 13, 5, 8, 9, 10, 11, 3)
DECISION_FROM_ACTION = {action: neuron for neuron, action in enumerate(ACTION_FROM_DECISION)}


class NeuralError(ValueError):
    """Invalid normalized neural input, anatomy, or checkpoint."""


def _int(value, name, lower=0, upper=2**31-1):
    if type(value) is not int or not lower <= value <= upper:
        raise NeuralError(f'{name} must be an integer in {lower}..{upper}')
    return value


def _float(value, name, lower=-1.0, upper=1.0):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise NeuralError(f'{name} must be finite normalized numeric data')
    try: value = float(value)
    except OverflowError as error: raise NeuralError(f'{name} exceeds numeric range') from error
    if not math.isfinite(value) or not lower <= value <= upper:
        raise NeuralError(f'{name} must be finite in {lower}..{upper}')
    return value


def _vector(value, count, name, lower=-1.0):
    if not isinstance(value, (list, tuple)) or len(value) != count:
        raise NeuralError(f'{name} requires {count} values')
    return [_float(x, name, lower) for x in value]


@dataclass
class Lobe:
    name: str
    gene_id: int
    width: int
    height: int
    tissue: int
    order: int
    init_always: bool
    init_rule: Program
    update_rule: Program
    neurons: list[list[float]]
    winner: int = 0
    inputs: list[float] = field(default_factory=list)


@dataclass
class Dendrite:
    source: int
    destination: int
    variables: list[float] = field(default_factory=lambda: [0.0]*8)

    @property
    def states(self):
        return self.variables


@dataclass
class Tract:
    gene_id: int
    source_lobe: str
    destination_lobe: str
    order: int
    init_always: bool
    init_rule: Program
    update_rule: Program
    source_indices: tuple[int, ...]
    destination_indices: tuple[int, ...]
    source_connections: int
    destination_connections: int
    migrates: bool
    random_connections: bool
    source_variable: int
    destination_variable: int
    dendrites: list[Dendrite] = field(default_factory=list)
    helper: TractState = field(default_factory=TractState)
    weak: list[int] = field(default_factory=list)
    migrations: int = 0


@dataclass(frozen=True)
class BrainOutput:
    attention: int
    decision: int
    action: int
    tick: int


class GenomeBrain:
    """Stateful actual-genome neural controller; no high-level action fallback.

    tick consumes one normalized external-input frame. Neuron/tract state,
    migration queues, the shared native LCG and rehearsal cursors are checkpointed.
    Invalid public inputs are rejected before changing state. Unexpected trusted
    kernel failures abort the simulation and are not hidden by another controller.
    """
    def __init__(self, definition: GenomeDefinition, *, seed=1, age_stage=3, sex='female'):
        self.seed = _int(seed, 'seed', 0, 0xffffffff)
        self._rng = self.seed
        self.age_stage = _int(age_stage, 'age stage', 0, 7)
        if sex not in ('female', 'male'): raise NeuralError('sex must be female or male')
        self.sex = sex
        self.definition = definition
        self.chemicals = [0.0]*256
        self._dummy = [0.0]*8
        self.lobes = {}
        self.tracts = []
        self.components = []
        self.instincts = []
        self.instinct_cursor = 0
        self.instincts_processed = 0
        self.knowledge_cursor = 0
        self.knowledge = [None]*20
        self.last_rehearsal = None
        self.tick_count = 0
        records = [r for r in definition.records if expressed(r['header'], age_stage, sex)]
        for r in records:
            if r['kind'] != 'brain_lobe': continue
            f = r['fields']; name = f.get('lobe')
            if not isinstance(name, str) or len(name) != 4 or name in self.lobes:
                raise NeuralError('lobes require unique four-character tokens')
            w = _int(f.get('width'), 'lobe width', 1, 255)
            h = _int(f.get('height'), 'lobe height', 1, 255)
            if sum(len(l.neurons) for l in self.lobes.values()) + w*h > 1_000_000:
                raise NeuralError('brain exceeds reference neuron capacity')
            lobe = Lobe(name, r['header']['id'], w, h, codon(f['tissue'],0,255),
                        _int(f.get('update_time'), 'component order',0,65535),
                        bool(codon(f['init_rule_always'],0,1)), self._program(f,'init_rule'),
                        self._program(f,'update_rule'), [[0.0]*8 for _ in range(w*h)],
                        inputs=[0.0]*(w*h))
            self.lobes[name] = lobe; self.components.append(lobe)
        if not {'attn','decn','verb','driv','resp'} <= self.lobes.keys():
            raise NeuralError('required creature-control lobes are missing')
        for r in records:
            if r['kind'] == 'brain_tract':
                tract = self._make_tract(r); self.tracts.append(tract); self.components.append(tract)
            elif r['kind'] == 'instinct': self.instincts.append(deepcopy(r))
        self.components.sort(key=lambda component: component.order)
        self._validate_bindings()
        # Native ReadFromGenome initializes the same sorted component collection.
        for component in self.components:
            if isinstance(component, Lobe):
                if not component.init_always:
                    for i, state in enumerate(component.neurons):
                        self._run(component.init_rule, self._dummy, self._dummy, state,
                                  self._dummy, i, i, None)
            elif not component.init_always:
                for d in component.dendrites: self._init_dendrite(component,d)

    @staticmethod
    def _program(fields, name):
        try: return Program.from_bytes(bytes.fromhex(fields[name]['raw_hex']))
        except (KeyError, TypeError, ValueError) as error:
            raise NeuralError(f'invalid {name} program') from error

    @classmethod
    def from_file(cls, path: str | Path, *, seed=1, age_stage=3, sex='female'):
        return cls(load_genome(path), seed=seed, age_stage=age_stage, sex=sex)

    def _random(self, count):
        self._rng, result = native_random_index(self._rng, count)
        return result

    def _make_tract(self, record):
        f = record['fields']; source = self.lobes.get(f.get('source_lobe'))
        destination = self.lobes.get(f.get('destination_lobe'))
        if source is None or destination is None: raise NeuralError('tract has missing expressed lobe')
        def indices(prefix, lobe):
            lo = _int(f[prefix+'_lower'], prefix+' lower',0,65535)
            hi = _int(f[prefix+'_upper'], prefix+' upper',0,65535)
            result = tuple(range(lo,min(hi+1,len(lobe.neurons))))
            if not result: raise NeuralError('tract selects no neurons')
            return result
        t = Tract(record['header']['id'], source.name, destination.name,
                  _int(f['update_time'],'tract order',0,65535),
                  bool(codon(f['init_rule_always'],0,1)),self._program(f,'init_rule'),
                  self._program(f,'update_rule'),indices('source',source),indices('destination',destination),
                  _int(f['source_connections'],'source connections',0,65535),
                  _int(f['destination_connections'],'destination connections',0,65535),
                  bool(codon(f['migrates'],0,255)),bool(codon(f['random_connections'],0,255)),
                  codon(f['source_variable'],0,7),codon(f['destination_variable'],0,7))
        sc,dc = t.source_connections,t.destination_connections
        if not sc and not dc: raise NeuralError('tract has no connectivity')
        if not t.migrates:
            if not sc or not dc: raise NeuralError('fixed tract needs both connection counts')
            si=di=0
            for i in range(1,65026):
                t.dendrites.append(Dendrite(t.source_indices[si],t.destination_indices[di]))
                if i % sc == 0: di=(di+1)%len(t.destination_indices)
                if i % dc == 0: si=(si+1)%len(t.source_indices)
                if si==0 and di==0: break
        else:
            if sc and dc: raise NeuralError('migrating tract needs exactly one connection count')
            if sc:
                maximum=min(sc,len(destination.neurons)); side=t.source_indices; other=t.destination_indices
            else:
                maximum=min(dc,len(source.neurons)); side=t.destination_indices; other=t.source_indices
            if maximum > len(other): raise NeuralError('unique random fanout exceeds selected range')
            for fixed in side:
                count=self._random(maximum)+1 if t.random_connections else maximum
                chosen=set()
                while len(chosen)<count:
                    candidate=other[self._random(len(other))]
                    if candidate in chosen: continue
                    chosen.add(candidate)
                    t.dendrites.append(Dendrite(fixed,candidate) if sc else Dendrite(candidate,fixed))
        return t

    def _run(self, program, source, dendrite, neuron, spare, source_id, destination_id, tract):
        # Banks are admitted at construction/checkpoint load, then rebound only
        # to those same banks. Public setters and input frames validate writes;
        # the trusted VM checks its computed writes without rescanning the brain.
        context=Context(source=source,dendrite=dendrite,neuron=neuron,spare=spare,
                        chemicals=self.chemicals,source_id=source_id,destination_id=destination_id,
                        random_state=self._rng,tract=tract)
        result=execute_trusted(program,context)
        self._rng=context.random_state
        return result

    def _validate_bindings(self):
        """Validate owned banks once before using the shared trusted kernel."""
        Context(chemicals=self.chemicals, random_state=self._rng).validate()
        for lobe in self.lobes.values():
            for index, state in enumerate(lobe.neurons):
                Context(source=self._dummy, dendrite=self._dummy, neuron=state,
                        spare=self._dummy, source_id=index, destination_id=index).validate()
        for tract in self.tracts:
            source=self.lobes[tract.source_lobe]
            destination=self.lobes[tract.destination_lobe]
            for d in tract.dendrites:
                Context(source=source.neurons[d.source], dendrite=d.variables,
                        neuron=destination.neurons[d.destination], spare=source.neurons[source.winner],
                        source_id=d.source, destination_id=d.destination, tract=tract.helper).validate()

    def _init_dendrite(self, tract, dendrite):
        if tract.init_always:
            dendrite.variables[:]=[0.0]*8
        else:
            # Native00406de0 uses the shared scratch for source/current/spare.
            self._run(tract.init_rule,self._dummy,dendrite.variables,self._dummy,
                      self._dummy,dendrite.source,dendrite.destination,tract.helper)

    def _update_lobe(self, lobe):
        if lobe.order == 0: return
        spare=[0.0]*8; lobe.winner=0
        for i,state in enumerate(lobe.neurons):
            self._dummy[0]=lobe.inputs[i]; lobe.inputs[i]=0.0
            registered=False
            if lobe.init_always:
                registered=self._run(lobe.init_rule,self._dummy,self._dummy,state,spare,i,i,None).registered_as_spare
            registered=self._run(lobe.update_rule,self._dummy,self._dummy,state,spare,i,i,None).registered_as_spare or registered
            if registered: spare=state; lobe.winner=i

    def _migrate(self, tract):
        if not tract.weak: return
        source=self.lobes[tract.source_lobe]; destination=self.lobes[tract.destination_lobe]
        best=max(tract.destination_indices,key=lambda i: destination.neurons[i][tract.destination_variable])
        if destination.neurons[best][tract.destination_variable] > 0.0:
            # Native selects at most the original weak-queue size before checking
            # existing connections; ties preserve source-vector order.
            candidates=sorted(tract.source_indices,
                              key=lambda i:-source.neurons[i][tract.source_variable])[:len(tract.weak)]
            existing={(d.source,d.destination) for d in tract.dendrites}
            for si in candidates:
                strength=source.neurons[si][tract.source_variable]
                if strength <= 0.0: break
                if (si,best) in existing: continue
                for k,di in enumerate(tract.weak):
                    d=tract.dendrites[di]
                    if d.variables[7] < strength:
                        existing.discard((d.source,d.destination))
                        d.source,d.destination=si,best
                        existing.add((si,best))
                        self._init_dendrite(tract,d)
                        tract.weak.pop(k); tract.migrations+=1
                        break
        tract.weak.clear()

    def _update_tract(self, tract):
        if tract.order == 0: return
        if tract.migrates: self._migrate(tract)
        source=self.lobes[tract.source_lobe]; destination=self.lobes[tract.destination_lobe]
        for index,d in enumerate(tract.dendrites):
            src=source.neurons[d.source]; dst=destination.neurons[d.destination]
            spare=source.neurons[source.winner]
            if tract.init_always:
                self._run(tract.init_rule,src,d.variables,dst,spare,d.source,d.destination,tract.helper)
            self._run(tract.update_rule,src,d.variables,dst,spare,d.source,d.destination,tract.helper)
            if dst[2] != 0.0:
                h=tract.helper
                if h.reward_chemical is not None:
                    d.variables[0]=reinforced_weight(d.variables[0],self.chemicals[h.reward_chemical],h.reward_threshold,h.reward_rate)
                if h.punishment_chemical is not None:
                    d.variables[0]=reinforced_weight(d.variables[0],self.chemicals[h.punishment_chemical],h.punishment_threshold,h.punishment_rate)
            if tract.migrates:
                # Native catalogue Migration Parameters: capacity5, weak state7.
                insert=next((i for i,old in enumerate(tract.weak) if d.variables[7]<tract.dendrites[old].variables[7]),len(tract.weak))
                if insert<5:
                    tract.weak.insert(insert,index)
                    del tract.weak[5:]

    def _prepare_inputs(self, inputs):
        prepared=[]
        if inputs is not None:
            if not isinstance(inputs, Mapping): raise NeuralError('inputs must map lobe tokens to vectors')
            for name,values in inputs.items():
                if name not in self.lobes: raise NeuralError(f'unknown input lobe{name}')
                lobe=self.lobes[name]
                if isinstance(values,Mapping): items=values.items()
                elif isinstance(values,Sequence) and not isinstance(values,(str,bytes)):
                    if len(values)!=len(lobe.neurons): raise NeuralError('input vector has wrong length')
                    items=enumerate(values)
                else: raise NeuralError('lobe inputs must be a mapping or full vector')
                for index,value in items:
                    index=_int(index,'neuron index',0,len(lobe.neurons)-1)
                    value=_float(value,'neuron input')
                    total=lobe.inputs[index]+value
                    if not math.isfinite(total): raise NeuralError('queued neuron input exceeds numeric range')
                    prepared.append((lobe,index,total))
        return prepared

    def queue_inputs(self, inputs):
        """Add one input frame to pending inputs without advancing the brain.

        Individual values are normalized. Multiple events accumulate until the
        lobe updates, as in the native input buffer; their sum can exceed one.
        """
        prepared=self._prepare_inputs(inputs)
        for lobe,index,total in prepared: lobe.inputs[index]=total

    def tick(self, inputs=None, chemicals=None) -> BrainOutput:
        prepared=self._prepare_inputs(inputs)
        concentrations=_vector(self.chemicals if chemicals is None else chemicals,256,'chemicals',0.0)
        # All input validation precedes the first mutation.
        self.chemicals[:]=concentrations
        for lobe,index,total in prepared: lobe.inputs[index]=total
        for component in self.components:
            if isinstance(component,Lobe): self._update_lobe(component)
            else: self._update_tract(component)
        self.tick_count+=1
        return self.output()

    def output(self):
        decision=self.lobes['decn'].winner
        if decision>=len(ACTION_FROM_DECISION): raise NeuralError('no external action for decision neuron')
        return BrainOutput(self.lobes['attn'].winner,decision,ACTION_FROM_DECISION[decision],self.tick_count)

    def set_neuron_state(self,lobe,index,var,value):
        if lobe not in self.lobes: raise NeuralError('unknown lobe')
        target=self.lobes[lobe]
        index=_int(index,'neuron index',0,len(target.neurons)-1)
        var=_int(var,'neuron variable',0,7)
        value=_float(value,'neuron state')
        target.neurons[index][var]=value

    def clear_activity(self):
        """Native00408ca0 clears only var0, preserving memory/eligibility fields."""
        for lobe in self.lobes.values():
            for neuron in lobe.neurons: neuron[0]=0.0

    def _rehearse(self, record):
        f=record['fields']; self.clear_activity(); inputs={}
        for i in range(3):
            tissue=f['lobe'+str(i)]-1
            name=next((l.name for l in self.lobes.values() if l.tissue==tissue),None)
            if name is None: continue
            if name=='decn': name='verb'
            elif name=='attn': name='noun'
            index=f['cell'+str(i)]
            if name=='verb': index=DECISION_FROM_ACTION.get(index,-1)
            if not 0<=index<len(self.lobes[name].neurons): continue
            inputs.setdefault(name,{})[index]=1.0
            if name=='noun':
                inputs.setdefault('visn',{})[index]=0.1
                if 'smel' in self.lobes: inputs.setdefault('smel',{})[index]=1.0
        action=f['action']; expected=DECISION_FROM_ACTION.get(action)
        if expected is None or expected>=len(self.lobes['verb'].neurons):
            raise NeuralError('instinct action is unsupported by this anatomy')
        inputs.setdefault('verb',{})[expected]=1.0
        output=self.tick(inputs)
        reinforced=False
        drive=f.get('reinforcement_drive_index',f.get('reinforcement_chemical'))
        if not 0<=drive<len(self.lobes['resp'].neurons): raise NeuralError('instinct drive outside response lobe')
        if output.decision==expected:
            level=codon(f['reinforcement_amount'],0,248)/124.0-1.0
            output=self.tick({'resp':{drive:level*0.5}}); reinforced=True
        self.last_rehearsal={'kind':'instinct','gene_id':record['header']['id'],
                             'action':action,'drive':drive,'matched_decision':reinforced}
        self.instincts_processed+=1
        return output

    def rehearse_next_instinct(self):
        """Consume one inherited instinct, then cycle native drive-knowledge probes.

        Native Brain::Update takes inherited instincts from the end of its list.
        Its subsequent knowledge pass supplies one drive, noun0.5 and vision0.1,
        records the selected category/action, and clears var0 afterward.
        """
        if self.instinct_cursor<len(self.instincts):
            record=self.instincts[-1-self.instinct_cursor]
            output=self._rehearse(record); self.instinct_cursor+=1
            return output
        drive=self.knowledge_cursor
        self.clear_activity()
        inputs={'driv':{drive:1.0},'noun':[0.5]*len(self.lobes['noun'].neurons),
                'visn':[0.1]*len(self.lobes['visn'].neurons)}
        output=self.tick(inputs)
        self.knowledge[drive]={'attention':output.attention,'decision':output.decision,
                               'strength':self.lobes['decn'].neurons[output.decision][0]}
        self.knowledge_cursor=(drive+1)%len(self.lobes['driv'].neurons)
        self.last_rehearsal={'kind':'knowledge','drive':drive}
        self.clear_activity()
        return output

    def train_instincts(self,passes=1,max_instincts=None):
        passes=_int(passes,'training passes',0,1000)
        maximum=len(self.instincts) if max_instincts is None else _int(max_instincts,'max instincts',0,len(self.instincts))
        outcomes=[]
        for _ in range(passes):
            for record in reversed(self.instincts[-maximum:] if maximum else []):
                outcomes.append(self._rehearse(record))
            self.instinct_cursor=max(self.instinct_cursor,maximum)
        return outcomes

    def to_dict(self):
        return {'schema_version':1,'definition':deepcopy(self.definition.to_dict()),'seed':self.seed,
                'age_stage':self.age_stage,'sex':self.sex,'rng':self._rng,'tick':self.tick_count,
                'chemicals':self.chemicals.copy(),'dummy':self._dummy.copy(),
                'lobes':{name:{'neurons':deepcopy(l.neurons),'winner':l.winner,'inputs':l.inputs.copy()} for name,l in self.lobes.items()},
                'tracts':[{'gene_id':t.gene_id,'dendrites':[{'source':d.source,'destination':d.destination,'variables':d.variables.copy()} for d in t.dendrites],
                           'helper':asdict(t.helper),'weak':t.weak.copy(),'migrations':t.migrations} for t in self.tracts],
                'instinct_cursor':self.instinct_cursor,'instincts_processed':self.instincts_processed,
                'knowledge_cursor':self.knowledge_cursor,'knowledge':deepcopy(self.knowledge),
                'last_rehearsal':deepcopy(self.last_rehearsal)}

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict) or data.get('schema_version')!=1: raise NeuralError('unsupported neural checkpoint')
        brain=cls(definition_from_dict(data['definition']),seed=data['seed'],age_stage=data['age_stage'],sex=data['sex'])
        brain._rng=_int(data['rng'],'RNG',0,0xffffffff)
        brain.tick_count=_int(data['tick'],'tick')
        brain.chemicals[:]=_vector(data['chemicals'],256,'chemicals',0.0)
        if not isinstance(data['dummy'],list) or len(data['dummy'])!=8: raise NeuralError('dummy requires 8 values')
        brain._dummy[:]=[_float(v,'dummy',-math.inf,math.inf) for v in data['dummy']]
        if not isinstance(data['lobes'],dict) or data['lobes'].keys()!=brain.lobes.keys(): raise NeuralError('checkpoint lobe mismatch')
        for name,lobe in brain.lobes.items():
            saved=data['lobes'][name]
            if not isinstance(saved['neurons'],list) or len(saved['neurons'])!=len(lobe.neurons): raise NeuralError('checkpoint neuron count mismatch')
            lobe.neurons[:]=[_vector(row,8,'neuron') for row in saved['neurons']]
            lobe.winner=_int(saved['winner'],'winner',0,len(lobe.neurons)-1)
            if not isinstance(saved['inputs'],list) or len(saved['inputs'])!=len(lobe.neurons): raise NeuralError('queued input count mismatch')
            lobe.inputs[:]=[_float(v,'queued input',-math.inf,math.inf) for v in saved['inputs']]
        if not isinstance(data['tracts'],list) or len(data['tracts'])!=len(brain.tracts): raise NeuralError('checkpoint tract mismatch')
        for tract,saved in zip(brain.tracts,data['tracts']):
            if saved['gene_id']!=tract.gene_id or len(saved['dendrites'])!=len(tract.dendrites): raise NeuralError('checkpoint dendrite count mismatch')
            for d,item in zip(tract.dendrites,saved['dendrites']):
                if type(item['source']) is not int or item['source'] not in tract.source_indices or type(item['destination']) is not int or item['destination'] not in tract.destination_indices: raise NeuralError('checkpoint endpoint outside selected lobe range')
                d.source=item['source']; d.destination=item['destination']; d.variables[:]=_vector(item['variables'],8,'dendrite')
            try:
                tract.helper=TractState(**saved['helper']); tract.helper.validate()
            except (ValueError,TypeError) as error: raise NeuralError('invalid tract helper') from error
            if not isinstance(saved['weak'],list) or len(saved['weak'])>5 or len(set(saved['weak']))!=len(saved['weak']): raise NeuralError('invalid weak dendrite queue')
            tract.weak=[_int(x,'weak index',0,len(tract.dendrites)-1) for x in saved['weak']]
            tract.migrations=_int(saved['migrations'],'migration count')
        brain.instinct_cursor=_int(data['instinct_cursor'],'instinct cursor',0,len(brain.instincts))
        brain.instincts_processed=_int(data['instincts_processed'],'instinct count')
        brain.knowledge_cursor=_int(data['knowledge_cursor'],'knowledge cursor',0,len(brain.lobes['driv'].neurons)-1)
        if not isinstance(data['knowledge'],list) or len(data['knowledge'])!=len(brain.knowledge): raise NeuralError('invalid knowledge collection')
        for record in data['knowledge']:
            if record is None: continue
            _int(record['attention'],'knowledge attention',0,len(brain.lobes['attn'].neurons)-1)
            _int(record['decision'],'knowledge decision',0,len(brain.lobes['decn'].neurons)-1)
            _float(record['strength'],'knowledge strength')
        brain.knowledge=deepcopy(data['knowledge'])
        if data['last_rehearsal'] is not None and not isinstance(data['last_rehearsal'],dict): raise NeuralError('invalid rehearsal metadata')
        brain.last_rehearsal=deepcopy(data['last_rehearsal'])
        brain._validate_bindings()
        return brain
