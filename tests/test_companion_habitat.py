from pathlib import Path
import sys
import json
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from habitat import Habitat
from habitat_store import HabitatStore
from continuing_companion import ContinuingCompanion,canonical

class CompanionHabitatTests(unittest.TestCase):
    def test_failed_save_pauses_and_retry_retains_actual_unsaved_experience(self):
        with tempfile.TemporaryDirectory() as d:
            h=Habitat(d,90)
            try:
                h.running=True;before=h.durable_tick
                with patch.object(h.store,'save',side_effect=OSError('injected disk failure')):
                    with self.assertRaises(OSError):h.tick()
                self.assertFalse(h.running);self.assertEqual(h.durable_tick,before)
                self.assertEqual(h.creature.time,before+1);self.assertIn('disk failure',h.state()['error'])
                with self.assertRaises(ValueError):h.command('step',{})
                h.command('save',{})
                self.assertIsNone(h.error)
                self.assertEqual(canonical(h.creature.snapshot()),canonical(h.store.load().snapshot()))
                self.assertEqual(h.store.load(previous=True).time,before)
            finally:h.store.close()

    def test_exclusive_ownership_and_no_silent_recreation(self):
        with tempfile.TemporaryDirectory() as d:
            h=Habitat(d,90)
            try:
                with self.assertRaises(BlockingIOError):Habitat(d,90)
                h.command('step',{})
            finally:h.store.close()
            Path(d,'current.json').rename(Path(d,'preserved-current.json'))
            with self.assertRaisesRegex(ValueError,'recovery'):Habitat(d,90)
            self.assertTrue(Path(d,'previous.json').exists())

    def test_real_http_teaching_and_abrupt_process_restart(self):
        with tempfile.TemporaryDirectory() as d:
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            url=f'http://127.0.0.1:{port}'
            def start():
                p=subprocess.Popen([sys.executable,'examples/persistent_individual/habitat.py','--home',d,'--port',str(port)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                for _ in range(200):
                    if p.poll() is not None:self.fail(p.stderr.read().decode())
                    try:return p,read()
                    except OSError:time.sleep(.05)
                p.kill();p.wait();self.fail('startup timeout')
            def read():
                with urllib.request.urlopen(url+'/state',timeout=10) as response:return json.load(response)
            def post(path,data):
                req=urllib.request.Request(url+'/'+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'},method='POST')
                with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)
            p,initial=start()
            try:
                for obj in ('object-0','object-1'):post('place',{'identity':obj,'x':0,'visible':False})
                post('device',{'function':'delayed-switch'})
                post('place',{'identity':'toy','x':.5,'visible':True})
                for _ in range(16):
                    post('step',{});state=read()
                    if state['requests']:break
                self.assertTrue(state['requests'])
                post('guidance',{'goal_id':state['requests'][0]['goal_id'],'additional_attempts':5})
                self.assertEqual(read()['guidance'][0]['status'],'unverified')
                for _ in range(5):post('step',{})
                state=read();self.assertEqual(state['guidance'][0]['status'],'supported-in-this-context')
                self.assertEqual(state['durable_tick'],state['tick'])
                saved=canonical(HabitatStore.read_checkpoint(Path(d)/'current.json').snapshot())
                p.kill();p.wait(timeout=5);p.stderr.close()
                p,resumed=start()
                self.assertEqual(resumed,state)
                self.assertEqual(canonical(HabitatStore.read_checkpoint(Path(d)/'current.json').snapshot()),saved)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    req=urllib.request.Request(url+'/running',data=b'{"running":true}',headers={'Content-Type':'application/json','Origin':'http://foreign.invalid'},method='POST')
                    urllib.request.urlopen(req,timeout=5)
                self.assertEqual(error.exception.code,403)
                self.assertFalse(read()['running'])
            finally:
                if p.poll() is None:p.terminate();p.wait(timeout=10)
                p.stderr.close()

if __name__=='__main__':unittest.main()
