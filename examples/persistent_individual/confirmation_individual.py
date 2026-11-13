"""Optional confirmation-based motor individual; recovered brain stays unchanged."""
from copy import deepcopy
from motor_benchmark import MotorIndividual
from recovery_model import ConfirmRecoveryModel
from self_model import SuccessModel


class ConfirmationMotorIndividual(MotorIndividual):
    """Adaptive motor host with separately owned confirmation-model checkpoints."""
    CONFIRMATION_SCHEMA='creature-brain-confirmation-motor-example-v1'

    def __init__(self, program, *, seed, identity=None, good_type=0):
        super().__init__(program,seed=seed,condition='adaptive',identity=identity,good_type=good_type)
        self.model=ConfirmRecoveryModel()

    def motor_snapshot(self):
        snapshot=super().motor_snapshot()
        snapshot['schema']=self.CONFIRMATION_SCHEMA
        return snapshot

    @classmethod
    def restore_motor(cls,data):
        if not isinstance(data,dict) or data.get('schema')!=cls.CONFIRMATION_SCHEMA or data.get('condition')!='adaptive':
            raise ValueError('invalid confirmation motor checkpoint')
        old=deepcopy(data);model=old['model'];old['schema']='creature-brain-motor-example-v1'
        old['model']=SuccessModel().to_dict()
        obj=super().restore_motor(old)
        obj.model=ConfirmRecoveryModel.from_dict(model)
        return obj

    @classmethod
    def from_baseline(cls,baseline):
        """Copy an existing adaptive motor state without mutating the source."""
        if type(baseline) is not MotorIndividual or baseline.condition!='adaptive' or type(baseline.model) is not SuccessModel:
            raise ValueError('expected an adaptive baseline motor individual')
        converted=deepcopy(baseline.motor_snapshot())
        converted['schema']=cls.CONFIRMATION_SCHEMA
        converted['model']=ConfirmRecoveryModel.from_baseline(baseline.model).to_dict()
        return cls.restore_motor(converted)
