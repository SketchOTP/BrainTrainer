import copy
import unittest
from creature_brain.world import Pose, World, WorldObject

class WorldTests(unittest.TestCase):
    def test_nearest_category_representative_and_no_nonexistent_targets(self):
        w=World();w.add_agent(Pose('a',1,1));w.add_object(WorldObject('far',11,8,1))
        w.add_object(WorldObject('near',11,2,1));w.add_object(WorldObject('empty',8,1,1,quantity=0))
        o=w.sense('a');self.assertEqual(o.representatives[11],'near');self.assertNotIn(8,o.representatives)
        w.objects['near'].quantity=0
        self.assertEqual(w.sense('a').representatives[11],'far')
    def test_eating_requires_navigation_and_conserves_resource(self):
        w=World(movement_speed=1);w.add_agent(Pose('a',1,1))
        w.add_object(WorldObject('meal',11,4,1,protein=0.8,quantity=1))
        first=w.act('a',12,'meal',1)
        self.assertEqual(first.status,'moved');self.assertEqual(first.protein,0)
        self.assertEqual(w.objects['meal'].quantity,1)
        for _ in range(4):out=w.act('a',12,'meal',1)
        self.assertEqual(out.status,'ate');self.assertGreater(out.protein,0)
        self.assertAlmostEqual(w.objects['meal'].quantity,0)
        self.assertNotIn(11,w.sense('a').representatives)
    def test_carry_drop_exclusive_and_checkpointed(self):
        w=World();w.add_agent(Pose('a',1,1));w.add_agent(Pose('b',1.1,1))
        w.add_object(WorldObject('seed',3,1,1,starch=0.3))
        self.assertEqual(w.act('a',6,'seed',1).status,'picked-up')
        self.assertNotIn(3,w.sense('b').representatives)
        self.assertEqual(w.act('b',12,'seed',1).status,'unavailable-action')
        self.assertEqual(w.objects['seed'].quantity,1)
        w.act('a',11,None,1)
        c=World.from_dict(w.to_dict());self.assertEqual(c.to_dict(),w.to_dict())
        self.assertEqual(c.objects['seed'].x,c.agents['a'].x)
        c.act('a',7,None,1);self.assertIsNone(c.objects['seed'].holder)
        self.assertIn(3,c.sense('b').representatives)
    def test_social_events_have_actor_recipient_and_signed_consequences(self):
        w=World();w.add_agent(Pose('a',1,1));w.add_agent(Pose('b',1.3,1))
        friendly=w.act('a',8,'b',0.25).social_events[0]
        attack=w.act('b',13,'a',0.25).social_events[0]
        self.assertEqual(friendly['recipient'],'b');self.assertGreater(friendly['positive'],0)
        self.assertEqual(attack['actor'],'b');self.assertGreater(attack['negative'],0)
    def test_boundary_clamp_hazard_exposure_and_regeneration(self):
        w=World();w.add_agent(Pose('a',0,0));w.add_object(WorldObject('danger',20,0,0,kind='danger'))
        w.add_object(WorldObject('food',11,5,5,quantity=1,regeneration=0.1))
        w.act('a',10,None,1);self.assertEqual(w.agents['a'].x,0)
        self.assertGreater(w.contact_damage(0,0,1),0)
        w.objects['food'].quantity=0;w.step(100);self.assertEqual(w.objects['food'].quantity,1)
    def test_invalid_world_input_and_inconsistent_carrier_refused(self):
        with self.assertRaises(ValueError):World(width=float('inf'))
        with self.assertRaises(ValueError):WorldObject('bad',40,1,1)
        w=World();w.add_agent(Pose('a',1,1));bad=copy.deepcopy(w.to_dict())
        bad['agents'][0]['carrying']='missing'
        with self.assertRaises(ValueError):World.from_dict(bad)
        with self.assertRaises(ValueError):w.act('a',14,None,1)
        with self.assertRaises(ValueError):w.step(-1)

if __name__=='__main__':unittest.main()
