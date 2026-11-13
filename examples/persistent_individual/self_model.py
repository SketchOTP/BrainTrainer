"""Optional, outcome-trained competence model for a body's execution modes.

This module does not choose a neural action or target.  A host may ask which
execution mode to use for an already selected action, and must later report an
explicitly matched action outcome and actual cost.  An interrupted/unknown
outcome is cancelled, not recorded as failure.  No hidden body regime or food
value is an input.
"""
from copy import deepcopy
import math


class SuccessModel:
    """Discounted empirical action-success estimates with bounded exploration.

    Evidence is exponentially discounted *on a new outcome for the same mode*.
    Each observable (action, context, mode) has a Beta(1, 1) prior.  Selection
    first tries each candidate twice, then periodically explores the least-tried
    mode (every eighth decision); otherwise it maximizes estimated success
    probability minus 0.25 times observed mean resource cost. This is a small
    heuristic, not a calibrated model of arbitrary tasks or a neural policy.
    """
    SCHEMA = 'creature-brain-action-success-model-v1'
    DISCOUNT = .8
    COST_WEIGHT = .25
    EXPLORE_INTERVAL = 8
    INITIAL_TRIALS = 2

    def __init__(self):
        self.evidence = {}
        self.decisions = {}
        self.pending = {}

    @staticmethod
    def _validate(action, context, modes):
        if type(action) is not int or not isinstance(context, str) or not context:
            raise ValueError('expected integer action and nonempty observable context')
        if (not isinstance(modes, (tuple, list)) or not modes or
                any(not isinstance(m, str) or not m for m in modes) or len(set(modes)) != len(modes)):
            raise ValueError('modes must be distinct nonempty strings')

    def predict(self, action, context, mode):
        self._validate(action, context, (mode,))
        item = self.evidence.get((action, context, mode), {})
        success = item.get('success', 0.)
        failure = item.get('failure', 0.)
        mass = success + failure
        return {'success_probability': (1. + success) / (2. + mass),
                'mean_cost': item.get('cost', 0.) / mass if mass else None,
                'observations': item.get('count', 0)}

    def begin(self, action_id, action, context, modes):
        if not isinstance(action_id, str) or not action_id or action_id in self.pending:
            raise ValueError('action ID must be a new nonempty string')
        self._validate(action, context, modes)
        estimates = {mode: self.predict(action, context, mode) for mode in modes}
        counts = {mode: estimates[mode]['observations'] for mode in modes}
        key = (action, context)
        number = self.decisions.get(key, 0)
        # Candidate order is a deterministic tie break, not a target preference.
        under_sampled = [m for m in modes if counts[m] < self.INITIAL_TRIALS]
        if under_sampled:
            selected = min(under_sampled, key=lambda m: counts[m])
            reason = 'initial-exploration'
        elif number % self.EXPLORE_INTERVAL == 0:
            selected = min(modes, key=lambda m: counts[m])
            reason = 'periodic-exploration'
        else:
            selected = max(modes, key=lambda m: estimates[m]['success_probability'] -
                           self.COST_WEIGHT * (estimates[m]['mean_cost'] or 0.))
            reason = 'estimated-utility'
        self.decisions[key] = number + 1
        self.pending[action_id] = {'action': action, 'context': context, 'mode': selected}
        return {'action_id': action_id, 'action': action, 'context': context, 'mode': selected,
                'predictions': estimates, 'selection_reason': reason}

    def complete(self, action_id, action, mode, success, *, cost=0.):
        """Train only on a matching explicit action result; unmatched reports are ignored."""
        if type(success) is not bool or isinstance(cost, bool) or not isinstance(cost, (int, float)):
            raise ValueError('success must be boolean and cost a nonnegative number')
        if not math.isfinite(cost) or cost < 0:
            raise ValueError('invalid observed cost')
        pending = self.pending.get(action_id)
        if pending is None or pending['action'] != action or pending['mode'] != mode:
            return False
        key = (action, pending['context'], mode)
        item = self.evidence.setdefault(key, {'success': 0., 'failure': 0., 'cost': 0., 'count': 0})
        item['success'] = self.DISCOUNT * item['success'] + int(success)
        item['failure'] = self.DISCOUNT * item['failure'] + int(not success)
        item['cost'] = self.DISCOUNT * item['cost'] + float(cost)
        item['count'] += 1
        del self.pending[action_id]
        return True

    def cancel(self, action_id):
        return self.pending.pop(action_id, None) is not None

    def to_dict(self):
        return {'schema': self.SCHEMA,
                'evidence': [{'action': a, 'context': c, 'mode': m, **deepcopy(v)}
                             for (a, c, m), v in sorted(self.evidence.items())],
                'decisions': [{'action': a, 'context': c, 'count': n}
                              for (a, c), n in sorted(self.decisions.items())],
                'pending': deepcopy(self.pending)}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get('schema') != cls.SCHEMA:
            raise ValueError('invalid success model checkpoint')
        result = cls()
        if not isinstance(data.get('evidence'), list) or not isinstance(data.get('decisions'), list) or not isinstance(data.get('pending'), dict):
            raise ValueError('invalid success model fields')
        for item in data['evidence']:
            a, c, mode = item['action'], item['context'], item['mode']
            cls._validate(a, c, (mode,))
            key = (a, c, mode)
            if key in result.evidence or type(item['count']) is not int or item['count'] < 0:
                raise ValueError('duplicate or invalid evidence')
            values = {field: item[field] for field in ('success', 'failure', 'cost')}
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values.values()):
                raise ValueError('invalid evidence value')
            result.evidence[key] = {**values, 'count': item['count']}
        for item in data['decisions']:
            a, c, n = item['action'], item['context'], item['count']
            cls._validate(a, c, ('mode',))
            if (a, c) in result.decisions or type(n) is not int or n < 0:
                raise ValueError('duplicate or invalid decisions')
            result.decisions[(a, c)] = n
        for action_id, item in data['pending'].items():
            if not isinstance(action_id, str) or not action_id or not isinstance(item, dict):
                raise ValueError('invalid pending action')
            cls._validate(item['action'], item['context'], (item['mode'],))
            result.pending[action_id] = {'action': item['action'], 'context': item['context'], 'mode': item['mode']}
        return result
