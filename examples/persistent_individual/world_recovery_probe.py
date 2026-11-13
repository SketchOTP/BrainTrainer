"""Real rural activity, recovery failure and resumption on a continuing-history fork."""
from pathlib import Path
from collections import Counter
import json,sys,subprocess
from habitat_store import HabitatStore
from continuing_companion import ContinuingCompanion,digest


def probe(home,out):
 out.mkdir(parents=True,exist_ok=False)
 source=HabitatStore.read_checkpoint(Path(home)/'current.json')
 source_hash=digest(source.snapshot())
 c=source.fork(purpose='rural maintenance and unfinished-activity qualification')
 for _ in range(96):
  active=next((g for g in c._mind.curriculum.goals if g['status']=='active'),None)
  if active:break
  c.tick()
 assert active,'no self-set unfinished activity to qualify'
 goal_id=active['id'];initial=c.snapshot();c.save(out/'before-failure.json')
 # The environment changes the recovery mechanism, not the executive's expectation.
 c.configure_recovery(reserve=.03,rest_rate=0,actor='qualification-environment')
 failed=[];prior_requests=len(c._mind.maintenance.requests)
 for _ in range(40):failed.append(c.tick())
 requests=c._mind.maintenance.requests[prior_requests:]
 assert len(requests)==1,'failure must produce one grounded request, not repeated requests'
 assert c._mind.maintenance.goals[-1]['status']=='recovery-needs-investigation'
 assert any(e['executive']['reason']=='conserve-before-recovery-probe' for e in failed)
 assert all(e['world_motion']['before']['x']==e['world_motion']['after']['x'] and e['world_motion']['before']['y']==e['world_motion']['after']['y'] for e in failed)
 assert next(g for g in c._mind.curriculum.goals if g['id']==goal_id)['status']=='active'
 for sequence in requests[0]['evidence']:
  event=c._events[sequence];assert event['kind']=='experience'
  assert event['payload']['body_resources']['after']==event['payload']['body_resources']['before']
 # Restore the rate without granting reserve; recovery must come from subsequent action.
 repair_tick=c.time;reserve=c._host.reserve
 c.configure_recovery(reserve=reserve,rest_rate=.5,actor='qualification-environment')
 assert c._mind.maintenance.goals[-1]['status']=='recovery-needs-investigation'
 recovered=[];completed_at=None
 for _ in range(256):
  event=c.tick();recovered.append(event)
  goal=next(g for g in c._mind.curriculum.goals if g['id']==goal_id)
  if completed_at is None and goal['status']=='demonstrated-visible-effect':completed_at=c.time
 assert completed_at is not None,'original unfinished activity did not resume and complete'
 assert c._mind.maintenance.goals[-1]['status']=='recovered-for-activity'
 reasons=Counter(e['executive']['reason'] for e in recovered)
 assert reasons['explore-world'] and reasons['practice-interaction'] and reasons['restore-observed-body-reserve']
 before_restart=c.snapshot();c.save(out/'restart-before.json')
 code="import sys;sys.path.insert(0,'examples/persistent_individual');from continuing_companion import ContinuingCompanion;c=ContinuingCompanion.load(sys.argv[1]);[c.tick() for _ in range(20)];c.save(sys.argv[2])"
 subprocess.run([sys.executable,'-c',code,str(out/'restart-before.json'),str(out/'restart-after.json')],check=True,timeout=60)
 for _ in range(20):c.tick()
 assert ContinuingCompanion.load(out/'restart-after.json').snapshot()==c.snapshot()
 assert c.snapshot()['events'][:len(initial['events'])]==initial['events']
 assert digest(source.snapshot())==source_hash
 result={'source_identity':source.identity,'source_tick':source.time,'source_sha256':source_hash,
  'test_lineage':c._lineage,'unfinished_goal':goal_id,'failure_ticks':40,'recovery_request':requests[0],
  'repair_tick':repair_tick,'repair_reserve':reserve,'original_goal_completed_at':completed_at,
  'subsequent_activity_ticks':256,'activity_reasons':dict(reasons),
  'failed_reasons':dict(Counter(e['executive']['reason'] for e in failed)),
  'cold_process_continuation_ticks':20,'final_checkpoint_sha256':digest(c.snapshot()),
  'scope':'externally imposed recovery fault and repair; autonomous response and actual rural continuation; no live-state mutation'}
 (out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
 return result

if __name__=='__main__':probe('runs/habitat-visual-qualification',Path('validation/world-recovery'))
