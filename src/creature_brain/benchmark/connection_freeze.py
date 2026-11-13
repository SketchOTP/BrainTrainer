"""Research-only gene-7 persistent tract-state freeze.

The tract update executes normally on isolated copies of its dendrites, weak
queue and helper. The resulting neuron writes and RNG advance remain live;
only that tract's persistent state is discarded at the tract boundary. This is
not a whole-brain learning-disabled mode, and it must be re-entered after a
checkpoint restore. The ordinary DefaultBrain class remains unchanged.
"""
from contextlib import contextmanager
from copy import deepcopy
from .qualification import QualificationExperiment


@contextmanager
def freeze_drive_comb_tract_state(brain, *, before=None, before_discard=None):
    original=brain._update_tract
    absent=object()
    previous=brain.__dict__.get('_update_tract',absent)
    def wrapped(tract):
        if (tract.gene_id,tract.source_lobe,tract.destination_lobe)!=(7,'driv','comb'):
            return original(tract)
        if before is not None: before(brain.to_dict())
        dendrites,weak,helper,migrations=tract.dendrites,tract.weak,tract.helper,tract.migrations
        try:
            tract.dendrites=deepcopy(dendrites)
            tract.weak=weak.copy()
            tract.helper=deepcopy(helper)
            result=original(tract)
            if before_discard is not None: before_discard(brain.to_dict())
            return result
        finally:
            tract.dendrites,tract.weak,tract.helper,tract.migrations=dendrites,weak,helper,migrations
    brain._update_tract=wrapped
    try:
        yield
    finally:
        if previous is absent:del brain._update_tract
        else:brain._update_tract=previous


class DriveCombFrozenExperiment(QualificationExperiment):
    """Qualification task with the explicitly scoped control on every tick."""
    CONTROL = 'drive-comb-tract-state-frozen-v1'

    def tick(self):
        with freeze_drive_comb_tract_state(self.brain):
            return super().tick()

    def snapshot(self):
        value=super().snapshot()
        value['qualification_control']=self.CONTROL
        return value

    @classmethod
    def restore(cls,snapshot):
        if snapshot.get('qualification_control') != cls.CONTROL:
            raise ValueError('missing or incompatible qualification control')
        return super().restore(snapshot)
