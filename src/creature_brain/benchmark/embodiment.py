"""Small reusable movement adapters; host owns body state and direction."""
from typing import Protocol


class MovementAdapter(Protocol):
    def advance(self, position: float, velocity: float, direction: int) -> tuple[float, float]: ...


class WalkingAdapter:
    def advance(self, position, velocity, direction):
        return position + direction*.35, velocity


class SwimmingAdapter:
    def advance(self, position, velocity, direction):
        velocity = .5*velocity + direction*.2
        return position + velocity, velocity


ADAPTERS = {'walking': WalkingAdapter(), 'swimming': SwimmingAdapter()}
