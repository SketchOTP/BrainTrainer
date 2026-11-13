"""Host-side routing of a chemical adjustment into native-informed learning.

The host owns chemical state, agent identity, action execution and timing. This
module does not manufacture those facts or mutate a brain. The route mirrors
the recovered sensory-training branch; it is not a whole stimulus or body model.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Sequence


@dataclass(frozen=True)
class SensoryRoute:
    """A requested chemical adjustment and, when eligible, a brain input.

    ``adjustment`` is the requested signed adjustment, not a measured change
    after the host's chemistry has applied its own limits. ``status`` records
    why training was or was not selected. ``unresolved`` means missing host
    facts prevented a decision; it must not be treated as a negative finding.
    """
    chemical: int
    adjustment: float
    status: str
    lobe: str | None = None
    neuron: int | None = None

    def brain_inputs(self) -> dict[str, dict[int, float]]:
        """Return a single sparse input frame; unresolved routes must be fixed."""
        if self.status == 'unresolved':
            raise ValueError('cannot apply unresolved sensory attribution')
        if self.lobe is None:
            return {}
        return {self.lobe: {self.neuron: self.adjustment}}


def route_sensory_adjustment(
    chemical: int,
    adjustment: float,
    tracked_chemicals: Sequence[int],
    *,
    training: bool,
    source_valid: bool | None = None,
    life_state: int | None = None,
    synchronous_learning: int | None = None,
    source_is_self: bool | None = None,
    source_is_pointer: bool | None = None,
    source_is_it: bool | None = None,
    expected_script: int | None = None,
    stimulus_script: int | None = None,
) -> SensoryRoute:
    """Route one already-decoded chemical signal using the native training gates.

    ``training`` is selected by the caller after decoding stimulus flags; a
    plain chemical-only path never enters native sensory training. Tracked
    chemical order is program/host data, not a universal chemical mapping.
    For the synchronous action check scripts are engine script IDs, not brain
    decision indexes. The ``-1`` script sentinel fails that check.

    Facts may be None when unknown; only facts needed by the selected path are
    required. The caller should apply ``adjustment`` to its chemistry even when
    training is rejected, and deliver routed inputs on the appropriate brain
    update. This function doesn't assert the selected lobe exists in a program.
    """
    if type(chemical) is not int or not 0 <= chemical <= 255:
        raise ValueError('chemical must be an integer in 0..255')
    if isinstance(adjustment, bool) or not isinstance(adjustment, (int, float)):
        raise ValueError('adjustment must be a finite number in -1..1')
    try:
        adjustment = float(adjustment)
    except OverflowError as error:
        raise ValueError('adjustment must be a finite number in -1..1') from error
    if not math.isfinite(adjustment) or not -1 <= adjustment <= 1:
        raise ValueError('adjustment must be a finite number in -1..1')
    if not isinstance(tracked_chemicals, Sequence) or isinstance(tracked_chemicals, (str, bytes)):
        raise ValueError('tracked chemicals must be a sequence')
    if any(type(item) is not int or not 0 <= item <= 255 for item in tracked_chemicals):
        raise ValueError('tracked chemicals must contain integers in 0..255')
    if type(training) is not bool:
        raise ValueError('training must be bool')
    for name, value in (('source_valid', source_valid), ('source_is_self', source_is_self),
                        ('source_is_pointer', source_is_pointer), ('source_is_it', source_is_it)):
        if value is not None and type(value) is not bool:
            raise ValueError(f'{name} must be bool or None')
    for name, value in (('life_state', life_state), ('synchronous_learning', synchronous_learning),
                        ('expected_script', expected_script), ('stimulus_script', stimulus_script)):
        if value is not None and type(value) is not int:
            raise ValueError(f'{name} must be an integer or None')

    def result(status, lobe=None, neuron=None):
        return SensoryRoute(chemical, adjustment, status, lobe, neuron)

    if not training:
        return result('chemical_only')
    try:
        neuron = tracked_chemicals.index(chemical)
    except ValueError:
        return result('untracked')
    if source_valid is None:
        return result('unresolved')
    if not source_valid:
        return result('invalid_source')
    if life_state is None:
        return result('unresolved')
    if life_state != 1:
        return result('routed', 'prox', neuron)
    if synchronous_learning is None:
        return result('unresolved')
    if synchronous_learning != 1:
        return result('routed', 'resp', neuron)
    if source_is_self is True or source_is_pointer is True:
        return result('routed', 'resp', neuron)
    if source_is_self is None or source_is_pointer is None:
        return result('unresolved')
    if expected_script == -1 or stimulus_script == -1 or source_is_it is False:
        return result('action_or_target_mismatch')
    if expected_script is not None and stimulus_script is not None and expected_script != stimulus_script:
        return result('action_or_target_mismatch')
    if expected_script is None or stimulus_script is None or source_is_it is None:
        return result('unresolved')
    return result('routed', 'resp', neuron)
