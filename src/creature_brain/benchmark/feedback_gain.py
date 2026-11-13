"""Optional worsening-signal gain for adaptation research, not native parity.

This experimental host interface changes only the routed brain training input
for an already-attributed positive hunger adjustment. It does not alter the
outcome, hunger, chemistry, target choice, or the baseline neural kernel.
"""
from creature_brain import route_sensory_adjustment
from .action_lifecycle import LifecycleFoodExperiment
from .food import TRACKED


class WorseningFeedbackGainExperiment(LifecycleFoodExperiment):
    EXTENSION = 'positive-hunger-feedback-gain-v1'

    def __init__(self, program, *, worsening_gain=2.0, **kwargs):
        if type(worsening_gain) not in (int, float) or worsening_gain not in (0.5, 1.0, 2.0):
            raise ValueError('research gain must be 0.5, 1 or 2')
        self.worsening_gain = float(worsening_gain)
        super().__init__(program, **kwargs)

    def _deliver_pending(self):
        if self.worsening_gain == 1.0:
            return super()._deliver_pending()
        pending, self.pending = self.pending, []
        for event in pending:
            adjustment = event['hunger_adjustment']
            route = route_sensory_adjustment(150, adjustment, TRACKED, training=True,
                source_valid=True, life_state=1, synchronous_learning=0)
            if self.config['condition'] == 'feedback':
                inputs = route.brain_inputs()
                if adjustment > 0 and route.lobe is not None:
                    inputs[route.lobe][route.neuron] = min(1.0, adjustment * self.worsening_gain)
                self.brain.queue_inputs(inputs)

    def snapshot(self):
        result = super().snapshot()
        result['feedback_extension'] = {'version': self.EXTENSION, 'worsening_gain': self.worsening_gain}
        return result

    @classmethod
    def restore(cls, snapshot):
        spec = snapshot.get('feedback_extension')
        if (not isinstance(spec, dict) or spec.get('version') != cls.EXTENSION or
                type(spec.get('worsening_gain')) not in (int, float) or spec.get('worsening_gain') not in (0.5, 1.0, 2.0)):
            raise ValueError('missing or incompatible feedback extension')
        obj = super().restore(snapshot)
        obj.worsening_gain = float(spec['worsening_gain'])
        return obj
