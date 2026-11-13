"""Research-only drive-to-combination migration ablation.

This suppresses only structural migration for this tract. It does not freeze
weights, reinforcement, consolidation, other tracts or learning generally.
The host must re-enter it after restoring a checkpoint. It never alters the
ordinary DefaultBrain class or native checkpoint format.
"""
from contextlib import contextmanager


@contextmanager
def suppress_drive_comb_migration(brain, on_entry=None):
    original = brain._migrate
    absent = object()
    previous = brain.__dict__.get('_migrate', absent)
    def wrapped(tract):
        if (tract.gene_id == 7 and tract.source_lobe == 'driv' and
                tract.destination_lobe == 'comb'):
            if on_entry is not None:
                on_entry(brain.to_dict())
            # Native/ordinary migration consumes the previous weak queue before
            # this tick rebuilds it. Keep the rebuild and all tract rules active.
            tract.weak.clear()
        else:
            original(tract)
    brain._migrate = wrapped
    try:
        yield
    finally:
        if previous is absent:
            del brain._migrate
        else:
            brain._migrate = previous
