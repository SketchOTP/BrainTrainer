"""Explicitly typed checkpoints for opt-in qualification experiments.

Existing snapshot formats remain unchanged.  This envelope records the class
whose behavior produced a snapshot, so callers using this loader cannot silently
drop an experimental body rule or persistent-state control on restore.
"""
from .approach_probe import EatApproachProbe
from .connection_freeze import DriveCombFrozenExperiment
from .qualification import QualificationExperiment
from .action_lifecycle import LifecycleFoodExperiment, LifecycleDriveCombFrozenExperiment

_TYPES = {
    'qualification-v1': QualificationExperiment,
    'eat-approach-probe-v1': EatApproachProbe,
    'drive-comb-frozen-v1': DriveCombFrozenExperiment,
    'action-lifecycle-v1': LifecycleFoodExperiment,
    'action-lifecycle-drive-comb-frozen-v1': LifecycleDriveCombFrozenExperiment,
}
_SCHEMA = 'creature-brain-research-checkpoint-v1'


def save_research_checkpoint(experiment):
    """Capture a supported exact experiment type; reject unknown subclasses."""
    kind = next((k for k, cls in _TYPES.items() if type(experiment) is cls), None)
    if kind is None:
        raise ValueError('unsupported research experiment type')
    return {'schema': _SCHEMA, 'experiment_type': kind, 'snapshot': experiment.snapshot()}


def restore_research_checkpoint(envelope):
    """Restore only an explicitly named supported type and matching control."""
    if not isinstance(envelope, dict) or envelope.get('schema') != _SCHEMA:
        raise ValueError('unsupported research checkpoint envelope')
    cls = _TYPES.get(envelope.get('experiment_type'))
    snapshot = envelope.get('snapshot')
    if cls is None or not isinstance(snapshot, dict):
        raise ValueError('unknown research experiment type or missing snapshot')
    marker = snapshot.get('qualification_control')
    expected = DriveCombFrozenExperiment.CONTROL if cls in (DriveCombFrozenExperiment, LifecycleDriveCombFrozenExperiment) else None
    if marker != expected:
        raise ValueError('checkpoint control does not match experiment type')
    has_lifecycle = 'action_lifecycle' in snapshot
    if has_lifecycle != (cls in (LifecycleFoodExperiment, LifecycleDriveCombFrozenExperiment)):
        raise ValueError('checkpoint lifecycle does not match experiment type')
    return cls.restore(snapshot)
