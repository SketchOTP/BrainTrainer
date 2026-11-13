import copy
from http.client import HTTPConnection
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from creature_brain.pet import PetSession, make_server, new_simulation, _TickSchedule
from creature_brain.simulation import Simulation


class PetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.initial=new_simulation().to_dict()

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'pet.json'
        self.pet=PetSession(Simulation.from_dict(copy.deepcopy(self.initial)),self.path)

    def test_nominal_genome_policy_ticks_and_pause_stops_every_clock(self):
        self.assertTrue(self.pet.tick_once())
        state=self.pet.snapshot();creature=self.pet.simulation.creatures[self.pet.identity]
        self.assertEqual(state['memory']['mode'],'learned')
        self.assertEqual(state['memory']['observations'],creature.experience.total_observations)
        self.assertEqual(self.pet.last_frame['action'],creature.brain.output().action)
        self.assertAlmostEqual(state['time'],.2)
        self.pet.action({'action':'pause','paused':True})
        saved=self.pet.simulation.to_dict()
        self.assertFalse(self.pet.tick_once());self.assertEqual(saved,self.pet.simulation.to_dict())

    def test_food_and_play_offer_resources_without_chemical_or_motor_changes(self):
        sim=self.pet.simulation;before=sim.to_dict()
        for food,category in [('seed',3),('fruit',8),('meal',11)]:
            for _ in range(4):self.pet.action({'action':'feed','food':food})
            obj=sim.world.objects['keeper-'+food]
            self.assertEqual(obj.category,category);self.assertEqual(obj.quantity,3)
        self.pet.action({'action':'play'})
        self.assertEqual(sim.world.objects['keeper-toy'].kind,'toy')
        after=sim.to_dict()
        self.assertEqual(before['creatures'],after['creatures'])
        self.assertEqual(before['world']['agents'],after['world']['agents'])
        self.assertEqual(before['steps'],after['steps'])

    def test_rest_is_only_a_teaching_cue_not_a_sleep_or_motor_override(self):
        sim=self.pet.simulation;c=sim.creatures[self.pet.identity]
        before_body=c.body.to_dict();before_brain=c.brain.to_dict()
        pose=copy.deepcopy(sim.world.agents[self.pet.identity])
        self.pet.action({'action':'rest'})
        self.assertEqual(c.command['action'],9);self.assertEqual(c.command['category'],30)
        self.assertEqual(c.body.to_dict(),before_body);self.assertEqual(c.brain.to_dict(),before_brain)
        self.assertEqual(sim.world.agents[self.pet.identity],pose)

    def test_feature_cue_uses_owner_contract_without_changing_brain_body_or_pose(self):
        sim=self.pet.simulation;c=sim.creatures[self.pet.identity]
        before_brain=c.brain.to_dict();before_body=c.body.to_dict()
        before_pose=copy.deepcopy(sim.world.agents[self.pet.identity])
        habitat=self.pet.snapshot()['habitat']
        self.assertEqual(habitat['projection'],'forest-perspective-v1')
        self.assertTrue(any(f['id']=='habitat-water' for f in habitat['features']))
        self.pet.action({'action':'feature','feature':'habitat-water','cue':'drink'})
        self.assertEqual(c.command['target'],'habitat-water')
        self.assertEqual(c.command['action'],12)
        self.assertEqual(c.command['category'],25)
        self.assertEqual(c.brain.to_dict(),before_brain);self.assertEqual(c.body.to_dict(),before_body)
        self.assertEqual(sim.world.agents[self.pet.identity],before_pose)
        with self.assertRaises(ValueError):self.pet.action({'action':'feature','feature':'habitat-water','cue':'teleport'})

    def test_legacy_pet_habitat_migration_preserves_creature_and_is_idempotent(self):
        sim=Simulation.from_dict(copy.deepcopy(self.initial))
        # A pre-habitat save has the same existing brain/body/pose, without the
        # opt-in feature definitions and their newly added world objects.
        sim.world.habitat=None
        for key in list(sim.world.objects):
            if key.startswith('habitat-'):del sim.world.objects[key]
        creature=sim.creatures[self.pet.identity].to_dict()
        pose=copy.deepcopy(sim.world.agents[self.pet.identity])
        migrated=PetSession(sim,self.path)
        self.assertEqual(migrated.simulation.creatures[self.pet.identity].to_dict(),creature)
        self.assertEqual(sim.world.agents[self.pet.identity],pose)
        migrated.save();loaded=PetSession.open(self.path)
        self.assertEqual(migrated.simulation.to_dict(),loaded.simulation.to_dict())

    def test_legacy_pet_switches_to_learned_mode_without_resetting_brain_or_body(self):
        self.pet.tick_once();self.pet.save()
        data=json.loads(self.path.read_text())
        data['simulation'].pop('autonomy_mode')
        for creature in data['simulation']['creatures']:creature.pop('experience')
        before=data['simulation']['creatures'][0]
        self.path.write_text(json.dumps(data))
        loaded=PetSession.open(self.path)
        after=next(iter(loaded.simulation.creatures.values())).to_dict()
        self.assertEqual(loaded.simulation.autonomy_mode,'learned')
        self.assertEqual(after['brain'],before['brain']);self.assertEqual(after['body'],before['body'])
        self.assertEqual(after['experience']['total_observations'],0)

    def test_exploration_mode_switch_persists_without_resetting_the_creature(self):
        self.pet.tick_once();sim=self.pet.simulation;c=sim.creatures[self.pet.identity]
        before=c.to_dict()
        self.pet.action({'action':'autonomy','mode':'scripted'})
        self.assertEqual(sim.autonomy_mode,'scripted');self.assertEqual(c.to_dict(),before)
        loaded=PetSession.open(self.path)
        self.assertEqual(loaded.simulation.autonomy_mode,'scripted')
        self.pet.action({'action':'autonomy','mode':'learned'})
        self.assertEqual(sim.autonomy_mode,'learned');self.assertEqual(c.to_dict(),before)
        with self.assertRaises(ValueError):self.pet.action({'action':'autonomy','mode':'invalid'})

    def test_checkpoint_restores_exact_continuation_and_name_pause(self):
        self.pet.tick_once();self.pet.action({'action':'rename','name':'Fern'})
        self.pet.action({'action':'pause','paused':True})
        loaded=PetSession.open(self.path,name='Ignored')
        self.assertEqual(loaded.name,'Fern');self.assertTrue(loaded.paused)
        self.assertEqual(self.pet.simulation.to_dict(),loaded.simulation.to_dict())
        self.pet.paused=False;loaded.paused=False
        self.pet.tick_once();loaded.tick_once()
        self.assertEqual(self.pet.simulation.to_dict(),loaded.simulation.to_dict())

    def test_observability_tracks_brain_progress_journal_and_survives_reload(self):
        self.pet.last_survival_cue={'need':'food','target':'balanced-food','time':10.2,'step':51}
        self.pet._record_activity({'outcome':'ate','target':'habitat-west-bush',
                                   'action':12,'habitat_event':'Found food in the ferns.'})
        state=self.pet.snapshot()
        self.assertEqual(state['journal'][-1]['text'],'Found food in the ferns.')
        self.assertEqual(state['progress']['brain_ticks'],
                         self.pet.simulation.creatures[self.pet.identity].brain.tick_count)
        self.assertIn('learned_associations',state['memory'])
        self.assertIn('research',state)
        self.pet.save();loaded=PetSession.open(self.path)
        self.assertEqual(loaded.snapshot()['journal'],state['journal'])
        self.assertEqual(loaded.snapshot()['progress'],state['progress'])
        self.assertEqual(loaded.snapshot()['last_survival_cue'],state['last_survival_cue'])

    def test_body_signals_are_separated_and_world_exposes_real_resource_locations(self):
        state=self.pet.snapshot();metrics=state['body_metrics']
        body=self.pet.simulation.creatures[self.pet.identity].body
        self.assertEqual(metrics['tired_drive'],body.drives[6])
        self.assertEqual(metrics['sleep_drive'],body.drives[7])
        self.assertEqual(metrics['water_reserve'],body.chemicals[33])
        self.assertEqual(metrics['energy_reserve'],body.chemicals[34])
        self.assertEqual(metrics['resources']['water']['id'],'habitat-water')
        self.assertEqual(metrics['resources']['shelter']['id'],'habitat-hut')
        self.assertEqual(metrics['companions'],0)

    def test_sleeping_dashboard_and_journal_do_not_replay_stale_motor_actions(self):
        body=self.pet.simulation.creatures[self.pet.identity].body
        self.assertTrue(body.request_sleep())
        self.pet.last_frame={'action':1,'outcome':'sleeping','target':'balanced-food'}
        self.pet._record_activity(self.pet.last_frame)
        state=self.pet.snapshot()
        self.assertEqual(state['action'],'Sleeping')
        self.assertIsNone(state['target'])
        self.assertEqual(state['journal'][-1]['text'],'Sleeping · NREM')
        count=len(self.pet.journal)
        self.pet._record_activity(self.pet.last_frame)
        self.assertEqual(len(self.pet.journal),count)

    def test_unknown_checkpoint_and_failed_atomic_replace_preserve_previous_file(self):
        self.path.write_text('{"schema":99}')
        with self.assertRaisesRegex(ValueError,'preserved'):PetSession.open(self.path)
        self.assertEqual(self.path.read_text(),'{"schema":99}')
        self.pet.save();before=self.path.read_bytes()
        with patch('creature_brain.pet.os.replace',side_effect=OSError('test')):
            with self.assertRaises(OSError):self.pet.save()
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(list(self.path.parent.glob('*.tmp')),[])

    def test_invalid_action_and_death_preserve_genome_state(self):
        for data in ({'action':'rename','name':'\n'}, {'action':'pause','paused':1},
                     {'action':'feed','food':'unknown'}, {'action':'teleport'}):
            before=self.pet.simulation.to_dict()
            with self.assertRaises(ValueError):self.pet.action(data)
            self.assertEqual(before,self.pet.simulation.to_dict())
        c=self.pet.simulation.creatures[self.pet.identity]
        c.body.kernel.chemicals[:]=[0.0]*256
        for _ in range(4):
            c.body.step(1)
            if not c.body.alive:break
        self.assertFalse(c.body.alive)
        with self.assertRaises(ValueError):self.pet.action({'action':'feed'})
        self.pet.paused=True
        with self.assertRaises(ValueError):self.pet.action({'action':'pause','paused':False})

    def test_http_assets_state_and_authenticated_actions_with_host_origin_rejections(self):
        server=make_server(self.pet,0)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01})
        thread.start();port=server.server_address[1]
        def request(method,path,body=None,headers=None):
            connection=HTTPConnection('127.0.0.1',port,timeout=3)
            try:
                connection.request(method,path,body,headers or {})
                response=connection.getresponse();return response.status,response.read()
            finally:connection.close()
        try:
            code,body=request('GET','/');self.assertEqual(code,200);self.assertIn(b'creature brain',body)
            self.assertIn(b'id="moss-creature"',body);self.assertIn(b'DIGITAL WORLD',body)
            self.assertIn(b'What Moss needs and where to find it',body)
            self.assertIn(b'What Moss actually did',body);self.assertIn(b'Is it improving?',body)
            for path in ('/style.css','/app.js'):self.assertEqual(request('GET',path)[0],200)
            code,art=request('GET','/habitat.png')
            self.assertEqual(code,200);self.assertTrue(art.startswith(b'\x89PNG\r\n\x1a\n'))
            code,art=request('GET','/moss-detailed-v1.png')
            self.assertEqual(code,200);self.assertTrue(art.startswith(b'\x89PNG\r\n\x1a\n'))
            code,art=request('GET','/moss-robot-v1.png')
            self.assertEqual(code,200);self.assertTrue(art.startswith(b'\x89PNG\r\n\x1a\n'))
            code,art=request('GET','/moss-animated-v1.png')
            self.assertEqual(code,200);self.assertTrue(art.startswith(b'\x89PNG\r\n\x1a\n'))
            code,art=request('GET','/habitat.png')
            self.assertEqual(code,200);self.assertTrue(art.startswith(b'\x89PNG\r\n\x1a\n'))
            code,body=request('GET','/api/state');state=json.loads(body);token=state['control_token']
            self.assertEqual(code,200);self.assertEqual(state['name'],'Moss')
            self.assertIn('progress',state);self.assertIn('journal',state);self.assertIn('research',state)
            self.assertIn('body_metrics',state);self.assertIn('resources',state['body_metrics'])
            self.assertIn('last_survival_cue',state)
            payload=json.dumps({'action':'rename','name':'Sprig'})
            headers={'Content-Type':'application/json','X-Pet-Token':token}
            self.assertEqual(request('POST','/api/action',payload,{'Content-Type':'application/json'})[0],403)
            self.assertEqual(request('POST','/api/action',payload,dict(headers,Origin='https://other.example'))[0],403)
            self.assertEqual(request('POST','/api/action',payload,dict(headers,Host='evil.example'))[0],403)
            self.assertEqual(request('GET','/api/state',headers={'Host':'evil.example'})[0],403)
            self.assertEqual(request('POST','/api/action',payload,dict(headers,**{'Sec-Fetch-Site':'cross-site'}))[0],403)
            self.assertEqual(self.pet.name,'Moss')
            code,body=request('POST','/api/action',payload,dict(headers,Origin='http://127.0.0.1:'+str(port)))
            self.assertEqual(code,200);self.assertEqual(json.loads(body)['name'],'Sprig')
            self.assertEqual(request('GET','/../pet.py')[0],404)
            self.assertEqual(request('POST','/api/action','bad',headers)[0],400)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)
        self.assertFalse(thread.is_alive())

    def test_monotonic_pacing_subtracts_work_and_drops_pause_overload_backlog(self):
        schedule=_TickSchedule(.2,0)
        self.assertAlmostEqual(schedule.delay(0),.2)
        schedule.complete(.2,.25,True)
        self.assertAlmostEqual(schedule.delay(.25),.15)
        self.assertEqual(schedule.lag,0)
        schedule.complete(.4,.75,True)
        self.assertAlmostEqual(schedule.lag,.15)
        self.assertAlmostEqual(schedule.delay(.75),.2)
        schedule.complete(.95,20,False)
        self.assertAlmostEqual(schedule.delay(20),.2)
        self.assertEqual(schedule.lag,0)
        schedule.complete(20.2,20.25,True)
        self.assertAlmostEqual(schedule.delay(20.25),.15)

    def test_background_owner_stops_and_saves_without_advancing_after_close(self):
        self.pet.start();self.pet.close()
        self.assertFalse(self.pet.thread.is_alive())
        self.assertEqual(PetSession.open(self.path).simulation.to_dict(),self.pet.simulation.to_dict())


if __name__=='__main__':unittest.main()
