"""Optional, exactly-once inherited-instinct preparation and portable receipt.

This is a declared research host profile, not a native sleep reconstruction.
It does not alter DefaultBrain construction or the ordinary checkpoint schemas.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile

from creature_brain import DefaultBrain
from creature_brain.genome import load_genome
from individual import Individual
from motor_benchmark import MotorIndividual
from confirmation_individual import ConfirmationMotorIndividual

PROFILE='cb04-inherited-instincts-age1-one-pass-v1'
SCHEMA='creature-brain-prepared-checkpoint-v1'


class _NoUntypedCheckpoint:
    """Do not silently discard a prepared individual's profile and receipt."""
    @staticmethod
    def _typed_required(*args,**kwargs):
        raise ValueError('prepared individuals require prepared_snapshot/save_prepared')
    snapshot=_typed_required
    motor_snapshot=_typed_required
    save=_typed_required
    save_motor=_typed_required


class _PreparedIndividual(_NoUntypedCheckpoint,Individual):pass
class _PreparedMotor(_NoUntypedCheckpoint,MotorIndividual):pass
class _PreparedConfirmation(_NoUntypedCheckpoint,ConfirmationMotorIndividual):pass


def _guard(individual):
    mapping={Individual:_PreparedIndividual,MotorIndividual:_PreparedMotor,ConfirmationMotorIndividual:_PreparedConfirmation}
    if type(individual) not in mapping:raise ValueError('unsupported individual type')
    individual.__class__=mapping[type(individual)]
    return individual


def _raw_motor(individual):
    # Invoke the original owner implementation directly; it calls the original
    # parent snapshot. The public legacy methods remain fail-closed.
    if type(individual) is _PreparedConfirmation:return ConfirmationMotorIndividual.motor_snapshot(individual)
    if type(individual) is _PreparedMotor:return MotorIndividual.motor_snapshot(individual)
    raise ValueError('expected prepared motor individual')


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def prepare_inherited(individual, program_path):
    """Apply the declared one-pass procedure once to a fresh, age-1 brain.

    A cloned brain is prepared before commit, so errors do not partially mutate
    the caller. The receipt records inherited preparation, not food experience.
    """
    if getattr(individual,'_inherited_preparation',None) is not None:raise ValueError('already prepared')
    if type(individual) not in (Individual,MotorIndividual,ConfirmationMotorIndividual):
        raise TypeError('expected an unprepared supported individual')
    b=individual.brain
    if (individual.time!=0 or individual.pending or individual.active_action is not None or
        b.age_stage!=1 or b.tick_count!=0 or b.instinct_cursor!=0 or b.instincts_processed!=0 or
        b.last_rehearsal is not None or any(b.chemicals) or any(any(l.inputs) for l in b.lobes.values())):
        raise ValueError('preparation requires a pristine age-1 individual')
    if len(b.instincts)!=29:raise ValueError('this profile requires exactly 29 expressed instincts')
    program_path=Path(program_path)
    if load_genome(program_path).to_dict()!=b.definition.to_dict():raise ValueError('brain does not match program')
    program_sha=hashlib.sha256(program_path.read_bytes()).hexdigest()
    before=b.to_dict();prepared=DefaultBrain.from_dict(before);records=[]
    original=prepared._rehearse
    def record(gene):
        result=original(gene);records.append(deepcopy(prepared.last_rehearsal));return result
    prepared._rehearse=record
    try:
        prepared.chemicals[213]=1.0
        prepared.train_instincts(passes=1)
        prepared.chemicals[213]=0.0
        prepared.clear_activity()
    finally:
        del prepared._rehearse
    if prepared.instincts_processed!=29 or prepared.instinct_cursor!=29 or len(records)!=29:
        raise RuntimeError('incomplete inherited preparation')
    after=prepared.to_dict()
    receipt={'profile':PROFILE,'complete':True,'classification':'inherited-preparation-not-experience',
             'program_sha256':program_sha,'definition_sha256':_digest(before['definition']),
             'identity':individual.identity,'seed':b.seed,'age_stage':b.age_stage,'sex':b.sex,
             'expressed_count':29,'processed_count':prepared.instincts_processed,
             'matched_decision_count':sum(bool(r['matched_decision']) for r in records),
             'brain_tick_before':before['tick'],'brain_tick_after':after['tick'],
             'rng_before':before['rng'],'rng_after':after['rng'],
             'before_brain_sha256':_digest(before),'prepared_brain_sha256':_digest(after),
             'chemicals_before':before['chemicals'],'chemicals_after':after['chemicals'],
             'pending_inputs_before':{n:v['inputs'] for n,v in before['lobes'].items()},
             'pending_inputs_after':{n:v['inputs'] for n,v in after['lobes'].items()},
             'rehearsals':records}
    individual.brain=prepared
    individual._inherited_preparation=receipt
    _guard(individual)
    return deepcopy(receipt)


def clone_prepared_motor(prepared, condition):
    """Fork a matched freshly prepared motor state into one experimental arm."""
    if type(prepared) is not _PreparedMotor or prepared.condition!='adaptive':
        raise ValueError('expected a prepared adaptive motor individual')
    receipt=getattr(prepared,'_inherited_preparation',None)
    if not receipt or prepared.time!=0 or _digest(prepared.brain.to_dict())!=receipt['prepared_brain_sha256']:
        raise ValueError('expected the unchanged post-preparation state')
    if condition not in ('normal','effort','baseline','candidate'):raise ValueError('invalid condition')
    if condition=='candidate':
        baseline=MotorIndividual.restore_motor(_raw_motor(prepared))
        clone=ConfirmationMotorIndividual.from_baseline(baseline)
    else:
        data=deepcopy(_raw_motor(prepared));data['condition']='adaptive' if condition=='baseline' else condition
        clone=MotorIndividual.restore_motor(data)
    clone._inherited_preparation=deepcopy(receipt)
    return _guard(clone)


def prepared_snapshot(individual):
    receipt=getattr(individual,'_inherited_preparation',None)
    if not isinstance(receipt,dict) or receipt.get('profile')!=PROFILE or receipt.get('complete') is not True:
        raise ValueError('individual lacks a complete preparation receipt')
    if type(individual) is _PreparedConfirmation:kind='confirmation';state=_raw_motor(individual)
    elif type(individual) is _PreparedMotor:kind='motor';state=_raw_motor(individual)
    elif type(individual) is _PreparedIndividual:kind='individual';state=Individual.snapshot(individual)
    else:raise ValueError('unsupported individual type')
    return {'schema':SCHEMA,'profile':PROFILE,'receipt':deepcopy(receipt),'kind':kind,'state':state}


def restore_prepared(data):
    if not isinstance(data,dict) or data.get('schema')!=SCHEMA or data.get('profile')!=PROFILE:
        raise ValueError('invalid prepared checkpoint')
    receipt=data.get('receipt')
    if not isinstance(receipt,dict) or receipt.get('profile')!=PROFILE or receipt.get('complete') is not True or receipt.get('processed_count')!=29:
        raise ValueError('invalid preparation receipt')
    kind=data.get('kind');state=data.get('state')
    if kind=='confirmation':obj=ConfirmationMotorIndividual.restore_motor(state)
    elif kind=='motor':obj=MotorIndividual.restore_motor(state)
    elif kind=='individual':obj=Individual.restore(state)
    else:raise ValueError('unknown prepared individual kind')
    b=obj.brain
    if (obj.identity!=receipt.get('identity') or b.seed!=receipt.get('seed') or b.age_stage!=1 or
        b.sex!=receipt.get('sex') or _digest(b.definition.to_dict())!=receipt.get('definition_sha256') or
        b.tick_count<receipt.get('brain_tick_after',0) or b.instincts_processed<29 or b.instinct_cursor<29):
        raise ValueError('checkpoint conflicts with preparation receipt')
    obj._inherited_preparation=deepcopy(receipt)
    return _guard(obj)


def save_prepared(individual,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as out:
            json.dump(prepared_snapshot(individual),out,allow_nan=False);out.write('\n');out.flush();os.fsync(out.fileno())
        os.replace(tmp,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def load_prepared(path):
    with Path(path).open() as stream:return restore_prepared(json.load(stream))
