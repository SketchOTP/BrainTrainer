"""Explicit body selection and checkpoint ownership."""
from pathlib import Path
from .physiology import Physiology

RESOURCE_ROOT=Path(__file__).resolve().parents[2]/'research/docking-station-20261103/resources'
DEFAULT_GENOME=RESOURCE_ROOT/'chichi-genome.json'
DEFAULT_BRAIN=RESOURCE_ROOT/'chichi-brain-program.json'


def genome_body(path=DEFAULT_GENOME, *, age_stage=3, sex='female',tick_seconds=1.0):
    from .genome_physiology import GenomePhysiology
    return GenomePhysiology.from_file(path,age_stage=age_stage,sex=sex,tick_seconds=tick_seconds)


def body_from_dict(data):
    if data.get('model')=='simplified-physiology-v1':
        return Physiology.from_dict(data)
    if data.get('model')=='genome-physiology-v1':
        from .genome_physiology import GenomePhysiology
        return GenomePhysiology.from_dict(data)
    raise ValueError('unsupported body model checkpoint')


def clone_body(body):
    return body.clone() if hasattr(body,'clone') else body_from_dict(body.to_dict())
