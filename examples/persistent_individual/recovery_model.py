"""Experimental self-model that probes unused execution modes more often.

This extension changes exploration frequency only. It receives no body-change
signal, does not alter the recovered brain or baseline SuccessModel, and uses
exactly the same matched-outcome and cancellation rules.
"""
from copy import deepcopy
from self_model import SuccessModel


class RecoveryProbeModel(SuccessModel):
    """Probe the least-sampled mode every fourth decision instead of eighth.

    The extra real attempts can accelerate recovery detection, but may cause
    additional failures or expense while a body remains impaired.
    """
    SCHEMA = 'creature-brain-action-success-recovery-probe-v1'
    EXPLORE_INTERVAL = 4

    @classmethod
    def from_baseline(cls, baseline):
        """Copy a baseline model's evidence and pending actions into this candidate."""
        if type(baseline) is not SuccessModel:
            raise ValueError('expected a baseline SuccessModel')
        data = deepcopy(baseline.to_dict())
        data['schema'] = cls.SCHEMA
        return cls.from_dict(data)


class ConfirmRecoveryModel(SuccessModel):
    """Confirm one surprising cheap-mode success with one real subsequent try.

    The ordinary eight-decision probe schedule remains intact. When normal
    succeeds despite earlier failure evidence and a lower predicted success
    than effort, one further normal attempt is scheduled for that action and
    context. This is an experiment, not proof of a body-regime change.
    """
    SCHEMA = 'creature-brain-action-success-confirm-recovery-v1'

    def __init__(self):
        super().__init__()
        self.confirmations = {}
        self.confirmation_attempts = set()

    def begin(self, action_id, action, context, modes):
        result = super().begin(action_id, action, context, modes)
        key = (action, context)
        confirmation = self.confirmations.pop(key, None)
        if confirmation is not None and confirmation in modes:
            result['mode'] = confirmation
            result['selection_reason'] = 'confirm-observed-success'
            self.pending[action_id]['mode'] = confirmation
            self.confirmation_attempts.add(action_id)
        return result

    def complete(self, action_id, action, mode, success, *, cost=0.):
        pending = self.pending.get(action_id)
        was_confirmation = action_id in self.confirmation_attempts
        before = self.predict(action, pending['context'], mode) if pending and mode == 'normal' else None
        effort = self.predict(action, pending['context'], 'effort') if before is not None else None
        evidence = self.evidence.get((action, pending['context'], mode), {}) if before is not None else {}
        completed = super().complete(action_id, action, mode, success, cost=cost)
        if completed:
            self.confirmation_attempts.discard(action_id)
            if (not was_confirmation and success and before is not None and
                    evidence.get('failure', 0.) > 0 and effort['observations'] > 0 and
                    before['success_probability'] < effort['success_probability']):
                self.confirmations[(action, pending['context'])] = mode
        return completed

    def cancel(self, action_id):
        cancelled = super().cancel(action_id)
        if cancelled:self.confirmation_attempts.discard(action_id)
        return cancelled

    def to_dict(self):
        result = super().to_dict()
        result['confirmations'] = [{'action':a,'context':c,'mode':m}
                                   for (a,c),m in sorted(self.confirmations.items())]
        result['confirmation_attempts'] = sorted(self.confirmation_attempts)
        return result

    @classmethod
    def from_dict(cls, data):
        result = super().from_dict(data)
        confirmations = data.get('confirmations')
        attempts = data.get('confirmation_attempts')
        if not isinstance(confirmations,list) or not isinstance(attempts,list):
            raise ValueError('invalid confirmation state')
        for item in confirmations:
            a,c,m = item['action'],item['context'],item['mode']
            cls._validate(a,c,(m,))
            if m!='normal' or (a,c) in result.confirmations:raise ValueError('invalid or duplicate confirmation')
            result.confirmations[(a,c)] = m
        if (any(not isinstance(item,str) or item not in result.pending for item in attempts)
                or len(set(attempts)) != len(attempts)):
            raise ValueError('invalid confirmation attempt')
        result.confirmation_attempts = set(attempts)
        return result

    @classmethod
    def from_baseline(cls, baseline):
        if type(baseline) is not SuccessModel:raise ValueError('expected a baseline SuccessModel')
        data = deepcopy(baseline.to_dict());data['schema'] = cls.SCHEMA
        data['confirmations'] = [];data['confirmation_attempts'] = []
        return cls.from_dict(data)
