"""Deterministic, bounded food benchmark with neutral host-side adapters.

The benchmark owns physics, chemistry and scoring, never a preferred-action
policy. Brain attention selects a category; an absent selection has no target.
"""
from __future__ import annotations
from dataclasses import asdict
import json
import random

from creature_brain import DefaultBrain, route_sensory_adjustment
from .contract import ChosenAction, Observation, Outcome, PerceivedObject, attributed_adjustment
from .embodiment import ADAPTERS

CATEGORIES = (3, 8)
TYPE_IDS = ('food-a', 'food-b')
PHASES = ('experience', 'evaluation', 'reversal', 'reversal_evaluation')
TRACKED = tuple(range(148, 163)) + tuple(range(199, 204))


def _tuple_tree(value):
    return tuple(_tuple_tree(x) for x in value) if isinstance(value, list) else value


class FoodExperiment:
    """One brain and its world, with explicitly limited feedback control.

    ``feedback_withheld`` still updates chemistry and all neural dynamics. It is
    NOT a learning-disabled control: genome rules may still change connections.
    """
    SCHEMA = 1

    def __init__(self, program, *, seed: int, embodiment: str, condition: str,
                 max_steps: int = 2, opportunities_per_phase: int = 20,
                 layout: str = 'training', appearance: str = 'training', novel_identity: bool = False):
        if embodiment not in ADAPTERS:
            raise ValueError('unknown embodiment')
        if condition not in ('feedback', 'feedback_withheld'):
            raise ValueError('unknown condition')
        if type(seed) is not int or seed < 0 or type(max_steps) is not int or max_steps < 1:
            raise ValueError('invalid seed or step limit')
        if type(opportunities_per_phase) is not int or opportunities_per_phase < 1:
            raise ValueError('invalid opportunity count')
        if layout not in ('training', 'heldout') or appearance not in ('training', 'heldout'):
            raise ValueError('unknown test variant')
        if type(novel_identity) is not bool:
            raise ValueError('novel_identity must be boolean')
        self.config = dict(seed=seed, embodiment=embodiment, condition=condition,
                           max_steps=max_steps, opportunities_per_phase=opportunities_per_phase,
                           layout=layout, appearance=appearance, novel_identity=novel_identity)
        self.brain = DefaultBrain.from_file(program, seed=seed, age_stage=1)
        self.rng = random.Random(seed)
        # Counterbalance exactly across consecutive seed pairs.
        self.initial_good = seed % 2
        self.time = 0
        self.opportunity = 0
        self.step_in_opportunity = 0
        self.energy = .5
        self.hunger = .8
        self.position = 0.0
        self.velocity = 0.0
        self.positions = [0., 0.]
        self.pending = []
        self.history = []
        self._reset_layout()

    @property
    def done(self):
        return self.opportunity >= len(PHASES)*self.config['opportunities_per_phase']

    @property
    def phase(self):
        return PHASES[self.opportunity // self.config['opportunities_per_phase']]

    def _reset_layout(self):
        # Balanced direction and equal distances: no outcome information is
        # placed in geometry or appearance. RNG state is checkpointed.
        sign = -1 if self.rng.randrange(2) else 1
        heldout = self.config['layout'] == 'heldout' and self.phase in ('evaluation', 'reversal_evaluation')
        distance = 1.0 if heldout else .8
        self.positions = [sign*distance, -sign*distance]
        self.position = self.velocity = 0.0
        self.step_in_opportunity = 0

    def observe(self):
        evaluate = self.phase in ('evaluation', 'reversal_evaluation')
        appearance = self.config['appearance'] if evaluate else 'training'
        novel = self.config['novel_identity'] and evaluate
        objects = tuple(PerceivedObject(identity=f'object-{i}', type_id=(f'novel-{i}' if novel else TYPE_IDS[i]),
                         category=((12, 17) if novel else CATEGORIES)[i], relative_position=x-self.position,
                         distance=abs(x-self.position), contact=abs(x-self.position) <= .85,
                         appearance=f'{appearance}-{i}', available_actions=(0, 4, 5, 10, 11, 12))
                        for i, x in enumerate(self.positions))
        return Observation(self.time, objects, self.energy, self.hunger)

    def _deliver_pending(self):
        pending, self.pending = self.pending, []
        for event in pending:
            route = route_sensory_adjustment(150, event['hunger_adjustment'], TRACKED,
                      training=True, source_valid=True, life_state=1, synchronous_learning=0)
            if self.config['condition'] == 'feedback':
                self.brain.queue_inputs(route.brain_inputs())

    def tick(self):
        if self.done:
            raise StopIteration('experiment complete')
        self._deliver_pending()
        obs = self.observe()
        # Both objects are encoded equally; never encode the hidden outcome.
        inputs = {'visn': {o.category: .5 for o in obs.objects}, 'driv': {2: obs.hunger}}
        chemicals = self.brain.chemicals.copy()
        chemicals[150] = self.hunger
        result = self.brain.tick(inputs, chemicals)
        target = next((o for o in obs.objects if o.category == result.attention), None)
        action = ChosenAction(f'{self.opportunity}:{self.step_in_opportunity}', self.time,
                              result.action, result.attention, result.decision,
                              target.identity if target else None)
        outcome = self._execute(action, target)
        self.time += 1
        self.step_in_opportunity += 1
        end = outcome.completed or self.step_in_opportunity >= self.config['max_steps']
        good_index = self.initial_good ^ int(self.phase in ('reversal', 'reversal_evaluation'))
        record = {'phase': self.phase, 'opportunity': self.opportunity,
                  'step': self.step_in_opportunity, 'observation': asdict(obs),
                  'choice': asdict(action), 'outcome': asdict(outcome),
                  'good_type_index': good_index,
                  'success': bool(outcome.completed and target and target.identity == f'object-{good_index}'),
                  'opportunity_end': end}
        self.history.append(record)
        if end:
            self.opportunity += 1
            if not self.done:
                self._reset_layout()
        return record

    def _execute(self, action, target):
        if target is not None and target.identity != action.target:
            return Outcome(action.id, target.identity, action.action, False,
                           'target-mismatch', 0.0, 0.0)
        if target is not None and action.action not in target.available_actions:
            return Outcome(action.id, target.identity, action.action, False,
                           'unavailable-action', 0.0, 0.0)
        status, completed, energy_delta, adjustment = 'no-target', False, 0.0, 0.0
        if action.action in (10, 11):
            self._move(-1 if action.action == 10 else 1)
            status = 'moving'
        if target is not None:
            if action.action not in (10, 11):
                status = 'not-completed'
            if action.action in (4, 5):
                direction = 1 if target.relative_position > 0 else -1
                self._move(direction if action.action == 4 else -direction)
                status = 'moving'
            elif action.action == 12 and target.contact:
                index = int(target.identity.split('-')[1])
                good = self.initial_good ^ int(self.phase in ('reversal', 'reversal_evaluation'))
                requested_energy = .2 if index == good else -.1
                adjustment = -.25 if index == good else .125
                prior_energy = self.energy
                self.energy = max(0., min(1., self.energy + requested_energy))
                energy_delta = self.energy - prior_energy
                self.hunger = max(0., min(1., self.hunger + adjustment))
                completed, status = True, 'consumed'
        outcome = Outcome(action.id, action.target, action.action, completed, status,
                          energy_delta, adjustment)
        credit = attributed_adjustment(action, outcome)
        if credit is not None:
            self.pending.append({'action_id': action.id, 'target': target.identity,
                                 'hunger_adjustment': credit})
        return outcome

    def _move(self, direction):
        self.position, self.velocity = ADAPTERS[self.config['embodiment']].advance(
            self.position, self.velocity, direction)

    def snapshot(self):
        """Return a JSON-compatible whole-experiment checkpoint."""
        return {'schema': self.SCHEMA, 'config': self.config.copy(),
                'brain': self.brain.to_dict(), 'rng': self.rng.getstate(),
                'initial_good': self.initial_good, 'time': self.time,
                'opportunity': self.opportunity, 'step_in_opportunity': self.step_in_opportunity,
                'energy': self.energy, 'hunger': self.hunger, 'position': self.position,
                'velocity': self.velocity, 'positions': self.positions.copy(),
                'pending': [p.copy() for p in self.pending], 'history': self.history.copy()}

    @classmethod
    def restore(cls, snapshot):
        if snapshot.get('schema') != cls.SCHEMA:
            raise ValueError('unsupported experiment checkpoint')
        obj = cls.__new__(cls)
        obj.config = snapshot['config'].copy()
        obj.brain = DefaultBrain.from_dict(snapshot['brain'])
        obj.rng = random.Random()
        obj.rng.setstate(_tuple_tree(snapshot['rng']))
        for key in ('initial_good', 'time', 'opportunity', 'step_in_opportunity',
                    'energy', 'hunger', 'position', 'velocity'):
            setattr(obj, key, snapshot[key])
        obj.positions = list(snapshot['positions'])
        obj.pending = [p.copy() for p in snapshot['pending']]
        obj.history = json.loads(json.dumps(snapshot['history']))
        return obj
