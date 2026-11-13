from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from continuing_companion import ContinuingCompanion
from world_preference_probe import prepare,PROGRAM
from world_body import visit,exploration_pending

class WorldActivityCommitmentTests(unittest.TestCase):
 def scene(self,version='developmental-executive-v21',near=False):
  c=prepare(ContinuingCompanion(PROGRAM,seed=225).snapshot(),'toy')
  c._append('implementation-change',{'operation':'enable-development','actor':'test','model':version})
  h=c._host;h.position=14.;h.world.update(y=11.,route=[],route_target=None,goal={
   'id':'world-explore:qualification','region':h.world['region'],'x':14,'y':12,
   'origin':'visited-cell-memory','map_knowledge':'inherited-collision-map'})
  for name in h.objects:h.objects[name]['visible']=False
  h.objects['toy'].update(x=14. if near else 20.,y=11.,region=h.world['region'],visible=True)
  visit(h);c._append('external-intervention',{'actor':'test-environment','operation':'pending-exploration-and-familiar-play','near':near})
  return c
 def test_finishes_exploration_before_distant_familiar_play(self):
  old=self.scene('developmental-executive-v20');new=self.scene()
  self.assertEqual(old.tick()['executive']['reason'],'practice-approach')
  self.assertEqual(new.tick()['executive']['reason'],'explore-world')
  events=[new.tick() for _ in range(2)]
  self.assertEqual(events[-1]['world_motion']['exploration_review']['status'],'reached-observed-position')
  self.assertFalse(exploration_pending(new._host))
  self.assertEqual(new.tick()['executive']['reason'],'practice-approach')
 def test_nearby_interaction_and_low_reserve_still_preempt(self):
  c=self.scene(near=True)
  self.assertEqual(c.tick()['executive']['reason'],'practice-interaction')
  c=self.scene();c.configure_recovery(reserve=.1,rest_rate=.5,actor='test')
  self.assertEqual(c.tick()['executive']['reason'],'restore-observed-body-reserve')
 def test_unfinished_goal_and_exact_continuation_survive_restore(self):
  c=self.scene();c.tick();clone=ContinuingCompanion.restore(c.snapshot())
  self.assertTrue(exploration_pending(clone._host))
  for _ in range(24):self.assertEqual(c.tick(),clone.tick())
  self.assertEqual(c.snapshot(),clone.snapshot())

if __name__=='__main__':unittest.main()
