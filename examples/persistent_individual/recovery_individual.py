"""Optional recovery-aware motor individual with explicit checkpoint ownership."""
from copy import deepcopy
from motor_benchmark import MotorIndividual
from recovery_model import RecoveryProbeModel
from self_model import SuccessModel


class RecoveryMotorIndividual(MotorIndividual):
    """Same recovered brain and host; only mode probing frequency differs."""
    RECOVERY_SCHEMA='creature-brain-recovery-motor-example-v1'

    def __init__(self, program, *, seed, identity=None):
        super().__init__(program,seed=seed,condition='adaptive',identity=identity)
        self.model=RecoveryProbeModel()

    def motor_snapshot(self):
        snapshot=super().motor_snapshot()
        snapshot['schema']=self.RECOVERY_SCHEMA
        return snapshot

    @classmethod
    def restore_motor(cls,data):
        if not isinstance(data,dict) or data.get('schema')!=cls.RECOVERY_SCHEMA or data.get('condition')!='adaptive':
            raise ValueError('invalid recovery motor checkpoint')
        old=deepcopy(data);model=old['model'];old['schema']='creature-brain-motor-example-v1'
        old['model']=SuccessModel().to_dict()
        obj=super().restore_motor(old)
        obj.model=RecoveryProbeModel.from_dict(model)
        return obj

    @classmethod
    def from_baseline(cls,baseline):
        """Copy an existing adaptive motor state; never mutate the source."""
        if type(baseline) is not MotorIndividual or baseline.condition!='adaptive' or type(baseline.model) is not SuccessModel:
            raise ValueError('expected an adaptive baseline motor individual')
        converted=deepcopy(baseline.motor_snapshot())
        converted['schema']=cls.RECOVERY_SCHEMA
        converted['model']=RecoveryProbeModel.from_baseline(baseline.model).to_dict()
        return cls.restore_motor(converted)
