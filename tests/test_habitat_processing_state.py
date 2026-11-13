import unittest,threading
from tempfile import TemporaryDirectory
from pathlib import Path
from habitat import Habitat
class ProcessingStateTests(unittest.TestCase):
 def test_reads_do_not_wait_for_owned_tick_and_snapshot_is_independent(self):
  with TemporaryDirectory() as directory:
   h=Habitat(Path(directory));entered=threading.Event();release=threading.Event();original=h.creature.tick;errors=[]
   before=h.read_state()
   def delayed():
    entered.set()
    if not release.wait(5):raise RuntimeError('test did not release tick')
    return original()
   h.creature.tick=delayed
   def work():
    try:
     with h.lock:h.tick()
    except BaseException as exc:errors.append(exc)
   worker=threading.Thread(target=work);worker.start()
   try:
    self.assertTrue(entered.wait(5));snapshot=h.read_state()
    self.assertTrue(snapshot['state_is_snapshot']);self.assertEqual(snapshot['tick'],before['tick'])
    snapshot['objects'][0]['visible']=False
    self.assertEqual(h.read_state()['objects'],before['objects'])
   finally:release.set();worker.join(10);h.store.close()
   self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
   after=h.read_state();self.assertNotIn('state_is_snapshot',after);self.assertEqual(after['tick'],before['tick']+1)
