"""Optional interaction counterfactual, not native action-script emulation.

When the brain requests eat at an out-of-contact target, the body advances one
movement step toward that same target instead of immediately failing. A later
brain decision still controls the next action; there is no automatic consumption,
target substitution, or persistent motor-script simulation.
"""
from .contract import Outcome
from .qualification import QualificationExperiment


class EatApproachProbe(QualificationExperiment):
    def _execute(self, action, target):
        if (action.action==12 and target is not None and
                target.identity==action.target and 12 in target.available_actions and not target.contact):
            self._move(1 if target.relative_position>0 else -1)
            return Outcome(action.id,target.identity,action.action,False,'eat-approaching',0.0,0.0)
        return super()._execute(action,target)
