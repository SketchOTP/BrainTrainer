"""Forecast must not expose hidden food value or body strength."""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from motor_benchmark import MotorIndividual,PROGRAM
from complete_action_prediction import CompleteActionObserver

@unittest.skipUnless(PROGRAM.exists(),'requires local program')
class HiddenInputTests(unittest.TestCase):
    def test_hidden_strength_and_food_value_are_not_in_forecast(self):
        a=MotorIndividual(PROGRAM,seed=0,condition='adaptive',identity='same')
        b=MotorIndividual(PROGRAM,seed=0,condition='adaptive',identity='same')
        for e in (a,b):
            e.place('object-0',3);e.place('object-1',-3);e.place('toy',0,False)
            e.brain.tick=lambda *args,**kwargs:SimpleNamespace(attention=3,decision=4,action=12)
        b.body_strength=.2;b.initial_good=1
        left=CompleteActionObserver();right=CompleteActionObserver()
        af=left.tick(a,opportunity_deadline=64)['action_prediction_events'][0]
        bf=right.tick(b,opportunity_deadline=64)['action_prediction_events'][0]
        self.assertEqual(af,bf)
        self.assertNotEqual(a.motor_records[-1]['progress'],b.motor_records[-1]['progress'])

if __name__=='__main__':unittest.main()
