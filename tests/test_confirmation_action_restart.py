"""Real process restarts across one brain-chosen food action and its feedback."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from confirmation_restart_probe import run
from motor_benchmark import PROGRAM

@unittest.skipUnless(PROGRAM.is_file(),'requires owner-provided brain program')
class ConfirmationActionRestartTests(unittest.TestCase):
    def test_brain_chosen_eat_and_pending_confirmation_then_feedback(self):
        evidence=run()
        self.assertTrue(evidence['matched_full_state_and_events'])
        self.assertEqual(evidence['child_exit_codes'],[0,0,0])
        self.assertEqual(evidence['original_action']['action'],12)
        self.assertTrue(any(c['action']==12 for c in evidence['setup']['confirmations']))
        self.assertEqual(evidence['confirmation_motor']['executing_action_id'],evidence['original_action']['id'])
        self.assertEqual(evidence['confirmation_motor']['executing_target'],evidence['original_action']['target'])
        self.assertEqual(evidence['confirmation_motor']['mode'],'normal')
        self.assertTrue(evidence['confirmation_motor']['motor_success'])
        self.assertEqual(evidence['observed_consumption']['action_id'],evidence['original_action']['id'])
        self.assertEqual(evidence['observed_consumption']['target'],evidence['original_action']['target'])
        self.assertEqual(evidence['feedback_queue_calls_for_original_action'],1)
        self.assertEqual(evidence['repeat_consumptions_for_original_action'],0)

if __name__=='__main__':unittest.main()
