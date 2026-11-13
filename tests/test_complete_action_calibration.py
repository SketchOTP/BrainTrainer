"""Bounded evidence for the natural brain-selected interaction diagnostic."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from complete_action_benchmark import individual,opportunity
from motor_benchmark import PROGRAM

@unittest.skipUnless(PROGRAM.exists(),'requires locally provided brain program')
class CompleteActionCalibrationTests(unittest.TestCase):
    def test_natural_action_contacts_consumes_and_routes_feedback(self):
        e=individual(0,'candidate','test-natural')
        result=opportunity(e,0,0,2.,True,64,'healthy','sustained')
        self.assertTrue(result['completed']);self.assertTrue(result['contact'])
        self.assertEqual(result['completion']['target'],'object-0')
        actions=[x['event']['choice'] for x in result['events']]
        self.assertTrue(any(x['action']==12 and x['target']=='object-0' for x in actions))
        action_id=result['completion']['action_id']
        self.assertTrue(any(item['event']=='contact' and item['action_id']==action_id
                            for t in result['events'] for item in t['event']['lifecycle_events']))
        self.assertEqual([x['action_id'] for x in e.pending],[action_id])
        delivered=[];original=e.brain.queue_inputs
        def observe(inputs):delivered.append(inputs);return original(inputs)
        e.brain.queue_inputs=observe
        try:e.tick()
        finally:del e.brain.__dict__['queue_inputs']
        self.assertEqual(delivered,[{'resp':{2:-.25}}]);self.assertEqual(e.pending,[])

    def test_no_brain_eat_request_remains_unsuccessful(self):
        e=individual(1,'candidate','test-no-choice')
        result=opportunity(e,1,0,2.,True,64,'healthy','sustained')
        self.assertFalse(result['requested_eat']);self.assertFalse(result['completed'])
        self.assertTrue(result['timed_out']);self.assertEqual(result['ticks'],64)
        self.assertGreaterEqual(result['reserve_cost'],0.)

if __name__=='__main__':unittest.main()
