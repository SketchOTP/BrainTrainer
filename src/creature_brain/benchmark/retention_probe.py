"""One-tick observational retention probes on cloned experiment checkpoints."""
from contextlib import nullcontext
from dataclasses import asdict
import json

from .action_lifecycle import LifecycleFoodExperiment, LifecycleDriveCombFrozenExperiment
from .connection_freeze import freeze_drive_comb_tract_state
from .research_checkpoint import save_research_checkpoint, restore_research_checkpoint


def probe_retained_choice(experiment, *, match_needs):
    """Observe one choice on a clone; no outcome is executed or delivered.

    Both variants remove pending feedback and fix geometry. The matched-needs
    variant additionally sets energy, hunger and chemical 150 to .5, .8, .8.
    Neurons, tract state, RNG and other chemistry are not reset. The caller
    must separately pair the two training branches and interpret residual
    activity as a possible contributor to differences in choice.
    """
    if type(match_needs) is not bool:
        raise ValueError('match_needs must be boolean')
    if type(experiment) not in (LifecycleFoodExperiment, LifecycleDriveCombFrozenExperiment):
        raise ValueError('retention probe requires a lifecycle experiment')
    checkpoint = json.loads(json.dumps(save_research_checkpoint(experiment)))
    clone = restore_research_checkpoint(checkpoint)
    if clone.done or clone.active_action is not None:
        raise ValueError('probe requires an unfinished experiment at an action boundary')
    discarded_pending = len(clone.pending)
    clone.pending = []
    clone.position = clone.velocity = 0.0
    clone.positions = [.5, -.5]
    if match_needs:
        clone.energy, clone.hunger = .5, .8
        clone.brain.chemicals[150] = .8
    obs = clone.observe()
    inputs = {'visn': {o.category: .5 for o in obs.objects}, 'driv': {2: obs.hunger}}
    chemicals = clone.brain.chemicals.copy()
    chemicals[150] = clone.hunger
    control = freeze_drive_comb_tract_state(clone.brain) if type(clone) is LifecycleDriveCombFrozenExperiment else nullcontext()
    with control:
        output = clone.brain.tick(inputs, chemicals)
    target = next((o for o in obs.objects if o.category == output.attention), None)
    return {'match_needs': match_needs, 'discarded_pending_count': discarded_pending,
            'observation': asdict(obs), 'attention': output.attention, 'decision': output.decision,
            'action': output.action, 'target': target.identity if target else None,
            'brain_after': clone.brain.to_dict()}
