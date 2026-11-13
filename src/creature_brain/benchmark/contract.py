"""Structured, embodiment-neutral host/brain contract for benchmark experiments."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PerceivedObject:
    identity: str
    type_id: str
    category: int
    relative_position: float
    distance: float
    contact: bool
    appearance: str
    available_actions: tuple[int, ...]


@dataclass(frozen=True)
class Observation:
    time: int
    objects: tuple[PerceivedObject, ...]
    energy: float
    hunger: float


@dataclass(frozen=True)
class ChosenAction:
    id: str
    time: int
    action: int
    attention: int
    decision: int
    target: str | None


@dataclass(frozen=True)
class Outcome:
    action_id: str
    target: str | None
    action: int
    completed: bool
    status: str
    energy_delta: float
    hunger_adjustment: float


def attributed_adjustment(action: ChosenAction, outcome: Outcome) -> float | None:
    """Credit only a completed outcome explicitly linked to the same action/target."""
    if (not outcome.completed or action.target is None or
            outcome.action_id != action.id or outcome.target != action.target or
            outcome.action != action.action):
        return None
    return outcome.hunger_adjustment
