"""Controlled food-preference experiment; independent of world/pet adapters."""
from .contract import ChosenAction, Observation, Outcome, PerceivedObject
from .embodiment import MovementAdapter, WalkingAdapter, SwimmingAdapter

__all__ = ['ChosenAction', 'Observation', 'Outcome', 'PerceivedObject',
           'MovementAdapter', 'WalkingAdapter', 'SwimmingAdapter']
