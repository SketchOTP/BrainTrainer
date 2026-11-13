import json
import unittest
from types import SimpleNamespace

from creature_brain.experience import ExperienceMemory
from creature_brain.world import World,WorldObject,Pose
from creature_brain import vision


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.world=World();self.world.add_agent(Pose('pet',5,5))
        self.food=WorldObject('training-food',8,5,5,kind='food',quantity=20)
        self.world.add_object(self.food)
        self.memory=ExperienceMemory();self.drives=[0.0]*20;self.drives[2]=.7
        body=SimpleNamespace(alive=True,sleep_state='awake',drives=self.drives)
        self.creature=SimpleNamespace(creature_id='pet',body=body,command=None)

    def exposure(self, food, start, count):
        for i in range(count):
            out=self.world.act('pet',12,food.object_id,1)
            self.memory.observe(now=start+i,target=food.object_id,category=food.category,action=12,
                                result=out,drives=self.drives,water_before=.5)

    def test_positive_experience_generalizes_to_new_identity_and_survives_reload(self):
        self.assertIsNone(self.memory.recall(self.world,self.creature))
        self.exposure(self.food,1,8)
        saved=json.loads(json.dumps(self.memory.to_dict()))
        restored=ExperienceMemory.from_dict(saved)
        self.assertEqual(restored.to_dict(),saved)
        self.food.enabled=False
        self.world.add_object(WorldObject('new-fruit',8,6,5,kind='food'))
        cue=restored.recall(self.world,self.creature)
        self.assertEqual((cue['target'],cue['category'],cue['action']),('new-fruit',8,12))
        self.creature.command={'action':0}
        self.assertIsNone(restored.recall(self.world,self.creature))

    def test_high_food_signal_points_toward_real_food_without_motor_override(self):
        self.food.enabled=False
        self.world.add_object(WorldObject('visible-food',8,5,5,kind='food',quantity=2))
        self.world.enable_pet_habitat()
        chemicals=[0.0]*256;chemicals[33]=1.0;chemicals[34]=1.0
        self.creature.body.kernel=object();self.creature.body.chemicals=chemicals
        self.drives[2]=.8
        cue=self.memory._survival_cue(self.world,self.creature)
        self.assertEqual((cue['target'],cue['action'],cue['need'],cue['source']),
                         ('visible-food',12,'food','survival-affordance'))
        self.assertNotIn('motor_override',cue)

    def test_negative_experience_reverses_association(self):
        self.exposure(self.food,1,8)
        self.food.toxin=1.0
        self.exposure(self.food,10,70)
        self.assertLess(self.memory.associations['8:12']['mean'],0)
        self.assertIsNone(self.memory.recall(self.world,self.creature))
        self.assertLessEqual(len(self.memory.episodes),96)

    def test_known_harmful_object_is_distinguished_from_familiar_safe_object(self):
        self.exposure(self.food,1,8)
        bad=WorldObject('bad-fruit',8,5.2,5,kind='food',quantity=20,toxin=1)
        self.world.add_object(bad)
        self.exposure(bad,10,8)
        cue=self.memory.recall(self.world,self.creature)
        self.assertEqual(cue['target'],'training-food')

    def test_invalid_memory_is_rejected(self):
        self.exposure(self.food,1,4)
        state=self.memory.to_dict();state['associations']['8:12']['mean']=float('nan')
        with self.assertRaises(ValueError):ExperienceMemory.from_dict(state)

    def test_exported_memory_does_not_share_mutable_episodes(self):
        self.exposure(self.food,1,4)
        state=self.memory.to_dict();state['episodes'][0]['target']='changed'
        self.assertEqual(self.memory.episodes[0]['target'],'training-food')

    def test_resting_does_not_attribute_the_nearest_object_as_a_cause(self):
        out=self.world.act('pet',9,self.food.object_id,1)
        self.assertEqual(out.status,'resting')
        self.memory.observe(now=1,target=self.food.object_id,category=self.food.category,action=9,
                            result=out,drives=self.drives,water_before=.5)
        self.assertEqual(self.memory.total_observations,0)

    def test_current_need_changes_the_value_of_the_same_experience(self):
        self.exposure(self.food,1,8)
        self.assertIsNotNone(self.memory.recall(self.world,self.creature))
        self.drives[2]=0
        self.assertIsNone(self.memory.recall(self.world,self.creature))

    def test_first_harm_becomes_durable_object_specific_aversion(self):
        self.food.toxin=1
        self.exposure(self.food,1,1)
        state=self.memory.to_dict()
        # Recent episodic memories can roll off without losing the hazard.
        state['episodes']=[]
        restored=ExperienceMemory.from_dict(state)
        cue=restored.intention(self.world,self.creature)
        self.assertEqual((cue['source'],cue['target'],cue['action']),('aversion','training-food',5))
        self.creature.command={'action':12}
        self.assertIsNone(restored.intention(self.world,self.creature))

    def test_new_harm_is_not_suppressed_by_sampling_interval(self):
        self.exposure(self.food,1,1)
        self.food.toxin=1
        out=self.world.act('pet',12,self.food.object_id,.2)
        self.memory.observe(now=1.2,target=self.food.object_id,category=8,action=12,
                            result=out,drives=self.drives,water_before=.5)
        self.assertIn(self.food.object_id,self.memory.risks)

    def test_changed_object_can_be_relearned_after_repeated_safe_exposures(self):
        self.food.toxin=1;self.exposure(self.food,1,1)
        self.food.toxin=0;self.exposure(self.food,3,4)
        self.assertIn(self.food.object_id,self.memory.risks)
        self.exposure(self.food,7,1)
        self.assertNotIn(self.food.object_id,self.memory.risks)

    def test_stalled_aversion_does_not_hide_a_different_known_hazard(self):
        self.food.toxin=1;self.exposure(self.food,1,1)
        other=WorldObject('other-danger',8,5.4,5,kind='food',quantity=2,toxin=1)
        self.world.add_object(other);self.exposure(other,2,1)
        self.world.time=2
        self.assertEqual(self.memory.intention(self.world,self.creature)['target'],self.food.object_id)
        self.world.time=14.2
        self.memory.intention(self.world,self.creature)
        self.assertEqual(self.memory.intention(self.world,self.creature)['target'],'other-danger')

    def test_legacy_symbolic_labels_do_not_trigger_visual_generalization(self):
        for idx in range(2):
            item=WorldObject('bad-'+str(idx),8,5,5,kind='food',quantity=2,toxin=1,percepts=['mark-a'])
            self.world.add_object(item);out=self.world.act('pet',12,item.object_id,1)
            self.memory.observe(now=idx+1,target=item.object_id,category=item.category,action=12,
                                result=out,drives=self.drives,water_before=.5,percepts=item.percepts)
            item.enabled=False
        self.food.enabled=False
        novel=WorldObject('novel',11,5.5,5,kind='food',quantity=2,percepts=['mark-a'])
        self.world.add_object(novel)
        cue=self.memory.intention(self.world,self.creature)
        self.assertIsNone(cue)
        novel.percepts=['mark-b']
        self.assertIsNone(self.memory.intention(self.world,self.creature))

    def test_visual_outcomes_generalize_from_pixels_not_hidden_toxin_or_labels(self):
        base=vision.pixels_for(self.food)
        def image(mark,variation=0):
            rows=[list(row) for row in base]
            for y in range(4,7):
                for x in range(4,7):rows[y][x]=mark
            if variation:rows[7][7]='w'
            return [''.join(row) for row in rows]
        for i in range(4):
            harmful=i<2;obj=WorldObject('sample-'+str(i),8,5,5,kind='food',quantity=2,
                                       toxin=1 if harmful else 0,visual=image('b' if harmful else 'y',i%2))
            self.world.add_object(obj);out=self.world.act('pet',12,obj.object_id,1)
            self.memory.observe(now=i+1,target=obj.object_id,category=8,action=12,result=out,
                                drives=self.drives,water_before=.5,visual=vision.pixels_for(obj))
            obj.enabled=False
        self.food.enabled=False
        dangerous=WorldObject('new-danger',11,5.5,5,kind='food',visual=image('b',1),percepts=['unrelated'])
        self.world.add_object(dangerous)
        self.assertEqual(self.memory.classify_visual(vision.pixels_for(dangerous)),'harmful')
        self.assertEqual(self.memory.intention(self.world,self.creature)['source'],'aversion')
        # Changing hidden toxicity cannot change a prediction before exposure.
        dangerous.toxin=1
        self.assertEqual(self.memory.classify_visual(vision.pixels_for(dangerous)),'harmful')
        dangerous.visual=image('y',1)
        self.assertEqual(self.memory.classify_visual(vision.pixels_for(dangerous)),'safe')
        dangerous.visual=['p'*12 for _ in range(12)]
        self.assertEqual(self.memory.classify_visual(vision.pixels_for(dangerous)),'unknown')

    def test_sustained_action_triggers_a_temporary_orienting_cue(self):
        for tick in range(20):
            self.memory.note_action(now=(tick+1)*.2,target=self.food.object_id,category=8,action=12,status='ate',dt=.2)
        self.world.time=4.2
        cue=self.memory.intention(self.world,self.creature)
        self.assertEqual((cue['source'],cue['action']),('habituation',0))
        restored=ExperienceMemory.from_dict(self.memory.to_dict())
        self.assertEqual(restored.to_dict(),self.memory.to_dict())
        self.world.time=17
        self.assertIsNone(restored.intention(self.world,self.creature))

    def test_sustained_looking_can_cue_moving_on(self):
        for tick in range(20):
            self.memory.note_action(now=(tick+1)*.2,target=self.food.object_id,category=8,action=0,status='looked',dt=.2)
        self.world.time=4.2
        cue=self.memory.intention(self.world,self.creature)
        self.assertEqual((cue['source'],cue['action']),('habituation',5))

    def test_repetition_temporarily_suppresses_recall_of_that_action(self):
        self.exposure(self.food,1,8)
        for tick in range(20):
            self.memory.note_action(now=10+(tick+1)*.2,target=self.food.object_id,category=8,action=12,status='ate',dt=.2)
        self.world.time=14.2
        self.assertIsNone(self.memory.recall(self.world,self.creature))
        self.world.time=41
        self.assertEqual(self.memory.recall(self.world,self.creature)['action'],12)


if __name__=='__main__':unittest.main()
