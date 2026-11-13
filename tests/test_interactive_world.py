"""Physical habitat consequences and actual genome-driven sensory-cue scenarios."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import unittest
from types import SimpleNamespace

from creature_brain.body import DEFAULT_BRAIN,DEFAULT_GENOME
from creature_brain.simulation import Simulation,make_demo
from creature_brain.world import World,WorldObject,Pose
from creature_brain import exploration


class InteractiveWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=make_demo(DEFAULT_BRAIN,physiology_genome=DEFAULT_GENOME,count=1,dt=.2,
                           timing_profile='docking-nominal').to_dict()

    def simulation(self):
        sim=Simulation.from_dict(deepcopy(self.base));sim.world.enable_pet_habitat();return sim

    def world(self):
        world=World();world.add_agent(Pose('pet',10,6));world.enable_pet_habitat();return world

    def stand_at(self,world,key):
        feature=world.objects['habitat-'+key];pose=next(iter(world.agents.values()));pose.x,pose.y=feature.x,feature.y
        return pose,feature

    def test_migration_is_additive_idempotent_and_keeps_all_existing_state(self):
        sim=Simulation.from_dict(deepcopy(self.base));sim.step();before=sim.to_dict()
        objects={k:asdict(o) for k,o in sim.world.objects.items()};poses={k:asdict(p) for k,p in sim.world.agents.items()}
        sim.world.enable_pet_habitat();first=sim.to_dict();sim.world.enable_pet_habitat()
        self.assertEqual(first,sim.to_dict())
        self.assertEqual(before['creatures'],sim.to_dict()['creatures'])
        self.assertEqual(objects,{k:asdict(sim.world.objects[k]) for k in objects})
        self.assertEqual(poses,{k:asdict(p) for k,p in sim.world.agents.items()})
        self.assertEqual(sim.world.habitat['profile'],'forest-pet-v1')
        self.assertGreaterEqual(len(sim.world.habitat['features']),8)

    def test_dirty_bush_activity_washing_wetness_and_shelter_drying_are_durable(self):
        world=self.world();pose,bush=self.stand_at(world,'west-bush')
        clean=pose.cleanliness;world.act('pet',1,bush.object_id,.2)
        self.assertLess(pose.cleanliness,clean)
        pose,water=self.stand_at(world,'water');dirty=pose.cleanliness
        self.assertEqual(world.act('pet',1,water.object_id,1).status,'washed')
        self.assertGreater(pose.cleanliness,dirty);self.assertGreater(pose.wetness,0)
        wet=pose.wetness;pose,hut=self.stand_at(world,'hut');world.step(1)
        self.assertLess(pose.wetness,wet)
        restored=World.from_dict(json.loads(json.dumps(world.to_dict())))
        self.assertEqual(world.to_dict(),restored.to_dict())

    def test_water_drink_and_wash_reach_actual_genome_chemical33(self):
        sim=self.simulation();pose,water=self.stand_at(sim.world,'water');c=sim.creatures[pose.creature_id]
        c.body.kernel.chemicals[33]=.2
        before=deepcopy(c.brain.to_dict());position=(pose.x,pose.y)
        sim.offer_feature(pose.creature_id,water.object_id,'drink')
        self.assertEqual(c.brain.to_dict(),before);self.assertEqual((pose.x,pose.y),position)
        drank=False
        for _ in range(60):
            f=sim.step()['creatures'][0]
            self.assertEqual(f['action'],c.brain.output().action)
            if f['outcome']=='drank':drank=True;break
        self.assertTrue(drank,'spoken noun/verb cue should recruit actual drink/eat decision')
        self.assertGreater(c.body.kernel.chemicals[33],.2)
        self.assertGreater(pose.water_intake,0)
        self.assertGreaterEqual(pose.wetness,0)

    def test_actual_genome_decisions_wash_forage_enter_and_discover_after_sensory_cues(self):
        for landmark,cue,expected in [('water','wash','washed'),('west-bush','forage','foraged'),
                                      ('hut','enter','entered'),('cache','search','discovered')]:
            with self.subTest(landmark=landmark):
                sim=self.simulation();pose,obj=self.stand_at(sim.world,landmark)
                creature=sim.creatures[pose.creature_id]
                sim.offer_feature(pose.creature_id,obj.object_id,cue)
                for _ in range(60):
                    frame=sim.step()['creatures'][0]
                    self.assertEqual(frame['action'],creature.brain.output().action)
                    if frame['outcome']==expected:break
                self.assertEqual(frame['outcome'],expected)

    def test_shelter_entry_and_sleep_use_physical_interior(self):
        world=self.world();pose,hut=self.stand_at(world,'hut');feature=world._feature(hut.object_id)
        positions=[]
        for _ in range(30):
            old=(pose.x,pose.y);result=world.act('pet',9,hut.object_id,.2);positions.append((pose.x,pose.y))
            self.assertLessEqual(((pose.x-old[0])**2+(pose.y-old[1])**2)**.5,.2+1e-9)
            if result.status=='resting':break
        self.assertTrue(pose.inside);self.assertEqual(pose.shelter,hut.object_id)
        self.assertAlmostEqual(pose.x,feature['interior'][0]);self.assertAlmostEqual(pose.y,feature['interior'][1])
        self.assertTrue(result.request_sleep);self.assertTrue(result.resting)
        self.assertGreater(world.sense('pet').ambient_temperature,world.temperature+3)

    def test_pickup_storage_decor_and_retrieval_preserve_item_identity(self):
        world=self.world();pose,hut=self.stand_at(world,'hut')
        world.add_object(WorldObject('keepsake',21,pose.x,pose.y,kind='trinket'))
        self.assertEqual(world.act('pet',6,'keepsake',.2).status,'picked-up')
        self.assertEqual(world.act('pet',7,hut.object_id,.2).status,'stored')
        self.assertEqual(hut.storage,['keepsake']);self.assertIsNone(pose.carrying)
        self.assertEqual(world.objects['keepsake'].stored_in,hut.object_id)
        self.assertEqual(world.act('pet',1,hut.object_id,.2).status,'decorated')
        self.assertEqual(hut.decorations,['keepsake'])
        restored=World.from_dict(world.to_dict());self.assertEqual(restored.to_dict(),world.to_dict())
        self.assertEqual(world.act('pet',6,hut.object_id,.2).status,'picked-up')
        self.assertEqual(pose.carrying,'keepsake');self.assertEqual(hut.storage,[]);self.assertEqual(hut.decorations,[])

    def test_forage_costs_stock_regenerates_and_discovers_real_food_and_trinkets(self):
        world=self.world();pose,bush=self.stand_at(world,'west-bush');found=[]
        start=bush.quantity
        for _ in range(3):
            out=world.act('pet',1,bush.object_id,.2);found.extend(out.spawned);world.step(5)
        self.assertEqual(len(found),3)
        self.assertEqual([world.objects[key].kind for key in found],['food','food','trinket'])
        self.assertLess(bush.quantity,start)
        stock=bush.quantity;world.step(10);self.assertGreater(bush.quantity,stock)
        self.assertEqual(bush.discoveries,3)

    def test_stairs_and_far_trail_move_through_actual_waypoints(self):
        world=self.world();pose=world.agents['pet'];arch=world.objects['habitat-arch']
        history=[]
        for _ in range(200):
            previous=(pose.x,pose.y);out=world.act('pet',4,arch.object_id,.2);history.append((pose.x,pose.y))
            self.assertLessEqual(((pose.x-previous[0])**2+(pose.y-previous[1])**2)**.5,.2+1e-9)
            if out.status=='explored':break
        self.assertAlmostEqual(pose.x,arch.x);self.assertAlmostEqual(pose.y,arch.y)
        self.assertGreater(pose.elevation,.9)
        route=next(r for r in world.habitat['routes'] if r['id']==arch.object_id)
        for x,y,z in route['points'][1:]:self.assertTrue(any(abs(a-x)<.21 and abs(b-y)<.21 for a,b in history))
        trail=world.objects['habitat-trail']
        for _ in range(220):
            out=world.act('pet',4,trail.object_id,.2)
            if out.status=='explored':break
        self.assertAlmostEqual(pose.x,trail.x);self.assertAlmostEqual(pose.y,trail.y)
        self.assertLess(pose.y,.01)

    def test_hidden_cache_is_one_time_persisted_opportunity(self):
        world=self.world();pose,cache=self.stand_at(world,'cache')
        pose.x=max(0,cache.x-1.0);before=pose.x
        self.assertEqual(world.act('pet',5,cache.object_id,.2).status,'moved')
        self.assertLess(pose.x,before);self.assertEqual(cache.discoveries,0)
        pose.x,pose.y=cache.x,cache.y
        first=world.act('pet',1,cache.object_id,.2);second=world.act('pet',1,cache.object_id,.2)
        self.assertEqual(first.status,'discovered');self.assertEqual(second.status,'cache-empty')
        self.assertEqual(len(first.spawned),1);self.assertEqual(cache.discoveries,1)
        restored=World.from_dict(world.to_dict());self.assertEqual(restored.objects[cache.object_id].discoveries,1)

    def test_looking_does_not_walk_and_landmarks_cannot_be_deactivated(self):
        world=self.world();pose=world.agents['pet'];start=(pose.x,pose.y)
        for feature in world.habitat['features']:
            obj=world.objects[feature['id']]
            self.assertEqual(world.act('pet',0,obj.object_id,.2).status,'looked')
            self.assertEqual((pose.x,pose.y),start)
            self.assertEqual(world.act('pet',3,obj.object_id,.2).status,'unavailable-action')
            self.assertTrue(obj.enabled)

    def test_location_and_elevation_stop_reporting_stairs_after_departure(self):
        world=self.world();pose,stairs=self.stand_at(world,'stairs')
        pose.location='stairs';pose.elevation=1
        world.step(.2);self.assertEqual(pose.location,'stairs')
        pose.x,pose.y=10,6
        world.step(.2)
        self.assertEqual(pose.location,'clearing');self.assertEqual(pose.elevation,0)

    def test_habitat_checkpoint_preserves_cues_navigation_body_and_continuation(self):
        sim=self.simulation();identity=next(iter(sim.creatures));sim.offer_feature(identity,'habitat-west-bush','forage')
        for _ in range(3):sim.step()
        restored=Simulation.from_dict(json.loads(json.dumps(sim.to_dict(),allow_nan=False)))
        self.assertEqual(sim.to_dict(),restored.to_dict())
        for _ in range(4):self.assertEqual(sim.step(),restored.step())
        self.assertEqual(sim.to_dict(),restored.to_dict())

    def test_curiosity_offers_sensory_intent_without_replacing_the_brain(self):
        sim=self.simulation();identity=next(iter(sim.creatures));creature=sim.creatures[identity]
        saw_intention=False
        for _ in range(20):
            frame=sim.step()['creatures'][0]
            saw_intention |= frame['intention'] is not None
            self.assertFalse(frame['commanded'])
            self.assertEqual(frame['action'],creature.brain.output().action)
        self.assertTrue(saw_intention)
        saved=json.loads(json.dumps(sim.to_dict(),allow_nan=False))
        restored=Simulation.from_dict(saved)
        self.assertEqual(sim.to_dict(),restored.to_dict())
        for _ in range(4):self.assertEqual(sim.step(),restored.step())
        self.assertEqual(sim.to_dict(),restored.to_dict())
        # A person's cue takes priority over the internal intention.
        sim.offer_feature(identity,'habitat-water','wash')
        frame=sim.step()['creatures'][0]
        self.assertTrue(frame['commanded']);self.assertIsNone(frame['intention'])
        self.assertEqual(frame['action'],creature.brain.output().action)

    def test_low_energy_prioritizes_actual_available_food(self):
        world=self.world()
        world.add_object(WorldObject('meal',11,10.5,6,kind='food',quantity=1))
        chemicals=[0.0]*256;chemicals[34]=.2;chemicals[35]=.9
        body=SimpleNamespace(alive=True,sleep_state='awake',drives=[0.0]*20,energy=.9,
                             kernel=object(),chemicals=chemicals)
        actor=SimpleNamespace(creature_id='pet',body=body,command=None,exploration=None)
        cue=exploration.intention(world,actor,.2)
        self.assertEqual(cue['target'],'meal');self.assertEqual(cue['action'],12)
        self.assertEqual(world.agents['pet'].x,10)

    def test_curiosity_does_not_repeatedly_target_an_empty_cache(self):
        world=self.world();cache=world.objects['habitat-cache']
        for obj in world.objects.values():obj.enabled=(obj is cache)
        body=SimpleNamespace(alive=True,sleep_state='awake',drives=[0.0]*20,energy=1.0)
        actor=SimpleNamespace(creature_id='pet',body=body,command=None,exploration=None)
        self.assertEqual(exploration.intention(world,actor,.2)['target'],cache.object_id)
        actor.exploration=None;cache.discoveries=1
        self.assertIsNone(exploration.intention(world,actor,.2))

    def test_legacy_world_defaults_and_benchmark_remain_without_habitat(self):
        world=World();world.add_agent(Pose('pet',2,2));saved=world.to_dict();saved.pop('habitat')
        for key in ['wetness','water_intake','cleanliness','shelter','inside','elevation','location','route','route_target']:saved['agents'][0].pop(key)
        restored=World.from_dict(saved)
        self.assertIsNone(restored.habitat);self.assertEqual(restored.agents['pet'].wetness,0)
        original=Simulation.from_dict(deepcopy(self.base));self.assertIsNone(original.world.habitat)
        old=deepcopy(self.base)
        for creature in old['creatures']:creature.pop('exploration',None)
        self.assertIsNone(next(iter(Simulation.from_dict(old).creatures.values())).exploration)


if __name__=='__main__':unittest.main()
