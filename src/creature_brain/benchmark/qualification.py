"""Development-only qualification tasks for the recovered-brain benchmark.

No host policy supplies an action or target. These tasks add explicit task
geometry and optional observation of the existing brain tick; they do not
change native-informed neural semantics.
"""
from __future__ import annotations
from dataclasses import asdict
from copy import deepcopy

from .food import FoodExperiment

TASKS = ('single_contact', 'single_distance', 'preference', 'embodied')


class QualificationExperiment(FoodExperiment):
    def __init__(self, program, *, task, mirror=False, food_index=0, trace=False, **kwargs):
        if task not in TASKS or type(mirror) is not bool or food_index not in (0, 1):
            raise ValueError('invalid qualification task')
        self.task, self.mirror, self.food_index, self.trace = task, mirror, food_index, trace
        super().__init__(program, **kwargs)

    def _reset_layout(self):
        super()._reset_layout()
        distance = {'single_contact': .5, 'single_distance': 1.2,
                    'preference': .5, 'embodied': 1.2}[self.task]
        # Per-seed mirrored branches have identical category/outcome mapping.
        sign = -1 if self.mirror else 1
        self.positions = [sign*distance, -sign*distance]

    def observe(self):
        observation = super().observe()
        if self.task.startswith('single_'):
            from .contract import Observation
            return Observation(observation.time, (observation.objects[self.food_index],),
                               observation.energy, observation.hunger)
        return observation

    def tick(self):
        if not self.trace:
            return super().tick()
        original = self.brain.tick
        trace = {}
        def traced_tick(inputs=None, chemicals=None):
            tract = next(t for t in self.brain.tracts
                         if t.source_lobe == 'driv' and t.destination_lobe == 'comb')
            before = [(d.source, d.destination, d.variables.copy()) for d in tract.dendrites]
            trace['inputs'] = deepcopy(inputs)
            trace['chemical_150'] = chemicals[150] if chemicals is not None else None
            trace['pending_response'] = self.brain.lobes['resp'].inputs.copy()
            trace['weak_before'] = tract.weak.copy()
            trace['resp2_before'] = self.brain.lobes['resp'].neurons[2].copy()
            trace['drive2_before'] = self.brain.lobes['driv'].neurons[2].copy()
            out = original(inputs, chemicals)
            trace['resp2_after'] = self.brain.lobes['resp'].neurons[2].copy()
            trace['drive2_after'] = self.brain.lobes['driv'].neurons[2].copy()
            trace['weak_after'] = tract.weak.copy()
            trace['connection_changes'] = [
                {'index': i, 'before': old, 'after': (d.source, d.destination, d.variables.copy())}
                for i, (old, d) in enumerate(zip(before, tract.dendrites))
                if old != (d.source, d.destination, d.variables)]
            return out
        self.brain.tick = traced_tick
        try:
            event = super().tick()
        finally:
            self.brain.tick = original
        event['brain_trace'] = trace
        return event

    def snapshot(self):
        value = super().snapshot()
        value['qualification'] = {'task': self.task, 'mirror': self.mirror,
                                  'food_index': self.food_index, 'trace': self.trace}
        return value

    @classmethod
    def restore(cls, snapshot):
        result = super().restore(snapshot)
        spec = snapshot['qualification']
        result.task, result.mirror = spec['task'], spec['mirror']
        result.food_index, result.trace = spec['food_index'], spec['trace']
        return result
