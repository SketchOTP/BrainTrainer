"""Experimental body execution for brain-selected actions, not native parity.

The brain still selects on every tick. A selected eat may approach, register
contact, and consume on successive ticks. A different action interrupts it;
a new explicit eat target replaces it; absent attention alone does not.
"""
from dataclasses import asdict

from .contract import ChosenAction, Outcome
from .qualification import QualificationExperiment
from .connection_freeze import freeze_drive_comb_tract_state


class LifecycleFoodExperiment(QualificationExperiment):
    LIFECYCLE = 'eat-approach-contact-consume-v1'

    def __init__(self, program, **kwargs):
        if kwargs.get('trace', False):
            raise ValueError('lifecycle experiment does not support qualification trace')
        self.active_action = None
        super().__init__(program, **kwargs)

    def _execute_lifecycle(self, choice, objects):
        events = []
        old = self.active_action
        if old is not None and (choice.action != 12 or
                (choice.target is not None and choice.target != old['choice']['target'])):
            events.append({'event': 'interrupted', 'action_id': old['choice']['id'],
                           'target': old['choice']['target']})
            self.active_action = old = None
        if old is None and choice.action == 12 and choice.target is not None:
            self.active_action = old = {'choice': asdict(choice), 'stage': 'approach'}
            events.append({'event': 'started', 'action_id': choice.id, 'target': choice.target})
        if old is None:
            target = next((o for o in objects if o.identity == choice.target), None)
            return choice, target, self._execute(choice, target), events

        selected = ChosenAction(**old['choice'])
        target = next((o for o in objects if o.identity == selected.target), None)
        if target is None or 12 not in target.available_actions:
            self.active_action = None
            status = 'target-lost' if target is None else 'unavailable-action'
            events.append({'event': 'failed', 'reason': status, 'action_id': selected.id,
                           'target': selected.target})
            return selected, target, Outcome(selected.id, selected.target, 12, False, status, 0., 0.), events
        if not target.contact:
            old['stage'] = 'approach'
            self._move(1 if target.relative_position > 0 else -1)
            return selected, target, Outcome(selected.id, selected.target, 12, False,
                                             'approaching', 0., 0.), events
        if old['stage'] == 'approach':
            old['stage'] = 'contact'
            events.append({'event': 'contact', 'action_id': selected.id, 'target': selected.target})
            return selected, target, Outcome(selected.id, selected.target, 12, False,
                                             'contact', 0., 0.), events
        outcome = self._execute(selected, target)
        self.active_action = None
        events.append({'event': 'completed' if outcome.completed else 'failed',
                       'action_id': selected.id, 'target': selected.target, 'reason': outcome.status})
        return selected, target, outcome, events

    def tick(self):
        if self.done:
            raise StopIteration('experiment complete')
        self._deliver_pending()
        obs = self.observe()
        inputs = {'visn': {o.category: .5 for o in obs.objects}, 'driv': {2: obs.hunger}}
        chemicals = self.brain.chemicals.copy()
        chemicals[150] = self.hunger
        result = self.brain.tick(inputs, chemicals)
        chosen_target = next((o for o in obs.objects if o.category == result.attention), None)
        choice = ChosenAction(f'{self.opportunity}:{self.step_in_opportunity}', self.time,
                              result.action, result.attention, result.decision,
                              chosen_target.identity if chosen_target else None)
        selected, target, outcome, events = self._execute_lifecycle(choice, obs.objects)
        self.time += 1
        self.step_in_opportunity += 1
        end = outcome.completed or self.step_in_opportunity >= self.config['max_steps']
        if end and self.active_action is not None:
            events.append({'event': 'cancelled', 'reason': 'opportunity-timeout',
                           'action_id': self.active_action['choice']['id'],
                           'target': self.active_action['choice']['target']})
            self.active_action = None
        good_index = self.initial_good ^ int(self.phase in ('reversal', 'reversal_evaluation'))
        record = {'phase': self.phase, 'opportunity': self.opportunity,
                  'step': self.step_in_opportunity, 'observation': asdict(obs),
                  'choice': asdict(choice), 'executed_action': asdict(selected),
                  'outcome': asdict(outcome), 'lifecycle_events': events,
                  'good_type_index': good_index,
                  'success': bool(outcome.completed and target and target.identity == f'object-{good_index}'),
                  'opportunity_end': end}
        self.history.append(record)
        if end:
            self.opportunity += 1
            if not self.done:
                self._reset_layout()
        return record

    def snapshot(self):
        value = super().snapshot()
        value['action_lifecycle'] = {'version': self.LIFECYCLE,
                                     'active_action': None if self.active_action is None else
                                     {'choice': self.active_action['choice'].copy(), 'stage': self.active_action['stage']}}
        return value

    @classmethod
    def restore(cls, snapshot):
        spec = snapshot.get('action_lifecycle')
        if not isinstance(spec, dict) or spec.get('version') != cls.LIFECYCLE:
            raise ValueError('missing or incompatible action lifecycle')
        action = spec.get('active_action')
        if action is not None:
            if not isinstance(action, dict) or action.get('stage') not in ('approach', 'contact'):
                raise ValueError('invalid active action')
            choice = ChosenAction(**action['choice'])
            if choice.action != 12 or choice.target is None:
                raise ValueError('invalid active eat target')
            action = {'choice': asdict(choice), 'stage': action['stage']}
        obj = super().restore(snapshot)
        obj.active_action = action
        return obj


class LifecycleDriveCombFrozenExperiment(LifecycleFoodExperiment):
    """Same body lifecycle with gene-7 persistent tract state frozen."""
    CONTROL = 'drive-comb-tract-state-frozen-v1'

    def tick(self):
        with freeze_drive_comb_tract_state(self.brain):
            return super().tick()

    def snapshot(self):
        value = super().snapshot()
        value['qualification_control'] = self.CONTROL
        return value

    @classmethod
    def restore(cls, snapshot):
        if snapshot.get('qualification_control') != cls.CONTROL:
            raise ValueError('missing or incompatible qualification control')
        return super().restore(snapshot)
