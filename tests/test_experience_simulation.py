import copy
import json
import unittest
from unittest.mock import patch

from creature_brain.body import DEFAULT_BRAIN, DEFAULT_GENOME
from creature_brain.neural import BrainOutput
from creature_brain.simulation import Simulation,make_demo
from creature_brain.world import WorldObject


class ExperienceSimulationTests(unittest.TestCase):
    def test_observe_mode_records_real_outcomes_and_round_trips(self):
        sim=make_demo(DEFAULT_BRAIN,physiology_genome=DEFAULT_GENOME,count=1,rehearse=False)
        sim.autonomy_mode='observe';c=next(iter(sim.creatures.values()));p=sim.world.agents[c.creature_id]
        sim.world.objects.clear();sim.world.add_object(WorldObject('test-fruit',8,p.x,p.y,kind='food',quantity=20))
        # Controlled actuation tests integration; the separate benchmark uses the real brain.
        with patch.object(c.brain,'tick',return_value=BrainOutput(8,4,12,1)):
            for _ in range(12):
                frame=sim.step()['creatures'][0]
                self.assertIsNone(frame['intention'])
        self.assertEqual(frame['outcome'],'ate')
        self.assertGreater(c.experience.total_observations,0)
        episode=c.experience.episodes[-1]
        self.assertEqual(episode['target'],'test-fruit')
        self.assertEqual(episode['position'],[p.x,p.y])
        self.assertTrue(0<=episode['hunger']<=1)
        restored=Simulation.from_dict(json.loads(json.dumps(sim.to_dict(),allow_nan=False)))
        self.assertEqual(sim.to_dict(),restored.to_dict())
        self.assertEqual(restored.autonomy_mode,'observe')
        for _ in range(4):self.assertEqual(sim.step(),restored.step())

    def test_legacy_checkpoint_loads_empty_memory_and_mode(self):
        sim=make_demo(DEFAULT_BRAIN,physiology_genome=DEFAULT_GENOME,count=1,rehearse=False)
        saved=copy.deepcopy(sim.to_dict());saved.pop('autonomy_mode')
        for row in saved['creatures']:row.pop('experience')
        restored=Simulation.from_dict(saved)
        self.assertEqual(restored.autonomy_mode,'scripted')
        self.assertEqual(next(iter(restored.creatures.values())).experience.total_observations,0)

    def test_invalid_autonomy_mode_rejected(self):
        sim=make_demo(DEFAULT_BRAIN,physiology_genome=DEFAULT_GENOME,count=1,rehearse=False)
        saved=sim.to_dict();saved['autonomy_mode']='invalid'
        with self.assertRaises(ValueError):Simulation.from_dict(saved)

    def test_memory_records_the_actual_recipient_when_an_action_redirects(self):
        sim=make_demo(DEFAULT_BRAIN,physiology_genome=DEFAULT_GENOME,count=1,rehearse=False)
        sim.world.enable_pet_habitat();sim.autonomy_mode='observe'
        c=next(iter(sim.creatures.values()));p=sim.world.agents[c.creature_id]
        hut=sim.world.objects['habitat-hut'];p.x,p.y=hut.x,hut.y
        sim.world.add_object(WorldObject('held-object',21,p.x,p.y,kind='toy'))
        sim.world.add_object(WorldObject('attended-fruit',8,p.x,p.y,kind='food'))
        self.assertEqual(sim.world.act(c.creature_id,6,'held-object',.2).status,'picked-up')
        with patch.object(c.brain,'tick',return_value=BrainOutput(8,3,7,1)):
            frame=sim.step()['creatures'][0]
        self.assertEqual((frame['outcome'],frame['target']),('stored','habitat-hut'))
        episode=c.experience.episodes[-1]
        self.assertEqual((episode['target'],episode['category']),('habitat-hut',hut.category))

    def test_contact_harm_is_attributed_to_the_colliding_hazard(self):
        sim=make_demo(DEFAULT_BRAIN,physiology_genome=DEFAULT_GENOME,count=1,rehearse=False)
        sim.autonomy_mode='observe';c=next(iter(sim.creatures.values()));p=sim.world.agents[c.creature_id]
        sim.world.objects.clear()
        sim.world.add_object(WorldObject('actual-hazard',20,p.x,p.y,kind='danger',portable=False))
        sim.world.add_object(WorldObject('unrelated-toy',21,p.x,p.y,kind='toy'))
        with patch.object(c.brain,'tick',return_value=BrainOutput(21,0,0,1)):
            sim.step()
        self.assertIn('actual-hazard',c.experience.risks)
        self.assertNotIn('unrelated-toy',c.experience.risks)
        episode=next(e for e in c.experience.episodes if e['outcome']=='injured')
        self.assertEqual((episode['target'],episode['category']),('actual-hazard',20))

    def test_dead_creature_does_not_learn_new_contact_harms(self):
        sim=make_demo(DEFAULT_BRAIN,physiology_genome=DEFAULT_GENOME,count=1,rehearse=False)
        sim.autonomy_mode='observe';c=next(iter(sim.creatures.values()));p=sim.world.agents[c.creature_id]
        sim.world.objects.clear();sim.world.add_object(WorldObject('hazard',20,p.x,p.y,kind='danger',portable=False))
        c.body._alive=False
        sim.step()
        self.assertEqual(c.experience.total_observations,0)
        self.assertEqual(c.experience.risks,{})

if __name__=='__main__':unittest.main()
