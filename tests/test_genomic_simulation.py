"""Closed-loop integration against the actual supplied brain and body genes."""
import copy
import json
import unittest
from unittest.mock import patch

from creature_brain.body import DEFAULT_BRAIN, DEFAULT_GENOME, body_from_dict
from creature_brain.genome_physiology import GenomePhysiology
from creature_brain.neural import BrainOutput, GenomeBrain
from creature_brain.simulation import Creature, Simulation, make_demo
from creature_brain.world import WorldObject


class GenomicSimulationTests(unittest.TestCase):
    def test_nominal_tick_matches_five_updates_and_round_trips(self):
        sim=make_demo(DEFAULT_BRAIN,count=1,rehearse=False)
        c=sim.creatures['creature-1']
        for _ in range(5):sim.step()
        self.assertEqual(c.body.kernel.ticks,5)
        self.assertAlmostEqual(sim.world.time,1.0)
        restored=Simulation.from_dict(json.loads(json.dumps(sim.to_dict())))
        self.assertEqual(restored.creatures['creature-1'].body.kernel.tick_seconds,.2)
        self.assertEqual(sim.step(),restored.step())

    def test_legacy_checkpoint_defaults_to_one_second(self):
        body=GenomePhysiology.from_file(DEFAULT_GENOME)
        saved=body.to_dict();saved['kernel'].pop('tick_seconds')
        restored=GenomePhysiology.from_dict(saved)
        self.assertEqual(restored.kernel.tick_seconds,1.0)

    def single(self,dt=1):
        sim=Simulation(dt=dt)
        sim.add(Creature('one',GenomeBrain.from_file(DEFAULT_BRAIN),
                         GenomePhysiology.from_file(DEFAULT_GENOME)),5,5)
        return sim

    def test_default_body_is_genomic_and_drives_are_receptor_outputs(self):
        sim=make_demo(DEFAULT_BRAIN,count=1,rehearse=False)
        c=sim.creatures['creature-1']
        self.assertIsInstance(c.body,GenomePhysiology)
        for _ in range(8):sim.step()
        self.assertEqual(c.body.drives,[c.body.kernel.receptors().get((1,5,i),0) for i in range(20)])
        self.assertEqual((len(c.brain.lobes),len(c.brain.tracts)),(15,29))

    def test_full_checkpoint_continues_pending_causal_body_across_window_reset(self):
        sim=self.single()
        for _ in range(62):sim.step()
        saved=json.loads(json.dumps(sim.to_dict(),allow_nan=False))
        restored=Simulation.from_dict(saved)
        self.assertEqual(sim.to_dict(),restored.to_dict())
        for _ in range(8):self.assertEqual(sim.step(),restored.step())
        self.assertEqual(sim.to_dict(),restored.to_dict())

    def test_food_without_legacy_macro_fields_uses_genetic_stimulus(self):
        sim=self.single();c=sim.creatures['one']
        sim.world.add_object(WorldObject('food',11,5,5,quantity=20))
        with patch.object(c.brain,'tick',return_value=BrainOutput(11,4,12,1)):
            frame=sim.step()['creatures'][0]
        self.assertEqual(frame['outcome'],'ate')
        self.assertEqual(sim.world.objects['food'].quantity,19.5)
        self.assertGreater(c.body.protein+c.body.fat,0)
        # Genetic input79 produces protein/fat even though legacy macros are0.
        self.assertIsNotNone(c.body.last_stimulus)

    def test_single_bite_relief_survives_action_change_and_latched_biotick(self):
        sim=self.single(dt=.25);c=sim.creatures['one']
        sim.world.add_object(WorldObject('food',11,5,5,quantity=2))
        with patch.object(c.brain,'tick',return_value=BrainOutput(11,4,12,1)):
            first=sim.step()['creatures'][0]
        self.assertEqual(first['response'],[0.0]*20)
        with patch.object(c.brain,'tick',return_value=BrainOutput(11,0,0,1)):
            later=[sim.step()['creatures'][0] for _ in range(12)]
        self.assertTrue(any(c['response'][1]<0 or c['response'][3]<0 for c in later))
        self.assertTrue(all(c['action']==0 for c in later))
        self.assertEqual(sim.world.objects['food'].quantity,1.875)

    def test_tissue_aliases_do_not_leak_earlier_large_lobe_slots(self):
        sim=self.single();c=sim.creatures['one']
        ctx=sim._neural_context(c)
        self.assertIn((255,0),ctx['neuronal_values'])
        self.assertNotIn((255,1),ctx['neuronal_values'])
        self.assertNotIn((0,255,4),ctx['neural_loci'])

    def test_body_genotype_expression_and_feedback_identity_mismatches_rejected(self):
        brain=GenomeBrain.from_file(DEFAULT_BRAIN,sex='female')
        with self.assertRaises(ValueError):
            Creature('bad',brain,GenomePhysiology.from_file(DEFAULT_GENOME,sex='male'))
        sim=self.single();sim.step();data=sim.to_dict()
        control=data['creatures'][0]['feedback_body']['kernel']
        control['definition']['source_sha256']='1'*64
        # Kernel checkpoint identity includes its own source identity field.
        if 'source_sha256' in control:control['source_sha256']='1'*64
        with self.assertRaises(ValueError):Simulation.from_dict(data)
        with self.assertRaises(ValueError):body_from_dict({'model':'unknown-body'})

    def test_restored_body_world_rejects_incompatible_neural_anatomy(self):
        data=self.single().to_dict();brain=data['creatures'][0]['brain']
        for record in brain['definition']['records']:
            f=record['fields']
            for key in ('lobe','source_lobe','destination_lobe'):
                if f.get(key)=='visn':f[key]='viss'
        brain['lobes']['viss']=brain['lobes'].pop('visn')
        with self.assertRaises(ValueError):Simulation.from_dict(data)


if __name__=='__main__':unittest.main()
