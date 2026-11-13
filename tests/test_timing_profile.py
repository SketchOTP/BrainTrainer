"""Nominal tick cadence and legacy checkpoint compatibility."""
import json
import unittest
from creature_brain.body import DEFAULT_GENOME
from creature_brain.biochemistry import Biochemistry


class TimingProfileTests(unittest.TestCase):
    def test_five_nominal_ticks_execute_the_same_gene_program_as_five_legacy_ticks(self):
        nominal=Biochemistry.from_file(DEFAULT_GENOME,tick_seconds=.2)
        legacy=Biochemistry.from_file(DEFAULT_GENOME,tick_seconds=1)
        inputs={(1,4,0):1,(1,0,0):.15,(1,4,9):1}
        nominal.step(1,inputs)
        legacy.step(5,inputs)
        self.assertEqual(nominal.ticks,5)
        self.assertEqual(nominal.chemicals,legacy.chemicals)
        self.assertEqual([o.to_dict() for o in nominal.organs],
                         [o.to_dict() for o in legacy.organs])

    def test_fractional_tick_and_checkpoint_resume(self):
        b=Biochemistry.from_file(DEFAULT_GENOME,tick_seconds=.2)
        b.step(.1);self.assertEqual(b.ticks,0)
        restored=Biochemistry.from_dict(json.loads(json.dumps(b.to_dict())))
        b.step(.1);restored.step(.1)
        self.assertEqual(b.ticks,1)
        self.assertEqual(b.to_dict(),restored.to_dict())


if __name__=='__main__': unittest.main()
