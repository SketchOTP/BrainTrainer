"""Prospective self-development qualification in the actual rural body."""
import json,sys,subprocess
from pathlib import Path
from continuing_companion import ContinuingCompanion,digest
from world_body import rural_pack_hash,visual_pack_hash
PROGRAM=Path(__file__).resolve().parents[2]/'research/docking-station-20261103/resources/chichi-brain-program.json'

def probe(seed):
 c=ContinuingCompanion(PROGRAM,seed=seed).fork(purpose=f'prospective rural software improvement seed {seed}')
 c.enable_development(actor='qualification');c.enable_world(actor='qualification');c.set_home_town('MAP_LITTLEROOT_TOWN',actor='qualification');c.open_home_interiors(actor='qualification');c.make_rural_home(actor='qualification');c.repair_rural_art(actor='qualification')
 for name in ('object-0','object-1'):c.place(name,c._host.position,visible=False,actor='qualification-environment')
 c.configure_device('toy',function='delayed-switch',type_id='world-first',delay=2,actor='qualification-environment');c.place('toy',c._host.position+3,actor='qualification-environment')
 for _ in range(40):
  c.tick()
  if c._mind.curriculum.policy.counter=='no_change_streak':break
 first=c._mind.curriculum.policy.sha256
 assert c._mind.curriculum.policy.counter=='no_change_streak','first revision not demonstrated'
 c.configure_device('toy',function='delayed-switch',type_id='world-second',delay=2,actor='qualification-environment')
 changed=False
 for _ in range(40):
  c.tick(allow_improvement=False)
  goal=next((g for g in c._mind.curriculum.goals if g['type_id']=='world-second'),None)
  if goal and goal['changes']==1 and not changed:
   c.configure_device('toy',function='delayed-switch',type_id='world-second',delay=4,actor='qualification-environment');changed=True
  if c._mind.improvement_request():break
 assert c._mind.improvement_request(),'second request not demonstrated'
 before=c.snapshot();c.tick();reports=c.self_review()['development_results']
 assert len(reports)==2 and c._mind.curriculum.policy.counter=='progress_sensitive','second revision not demonstrated'
 assert c.snapshot()['events'][:len(before['events'])]==before['events'] and c.snapshot()['lineage']==before['lineage']
 assert c._mind.curriculum.policy.sha256!=first
 for report in reports:
  assert any(not p['passed'] for p in report['candidates'])
  accepted=next(p for p in report['candidates'] if p['sha256']==report['selected_sha256'])
  assert accepted['passed'] and not accepted['untested_profiles']
  for candidate in report['candidates']:
   for case in candidate['cases']:
    assert case['lineage']['context']=='test' and case['lineage']['branch_id']!=c._lineage['branch_id']
    assert any('world_motion' in e['payload'] for e in case['test_events'] if e['kind']=='experience')
 # Prior learned object behavior must still work on a distinct target after both changes.
 c.place('toy',0,visible=False,actor='qualification-environment')
 c.configure_device('object-0',function='delayed-switch',type_id='world-first',delay=2,actor='qualification-environment');c.place('object-0',c._host.position,actor='qualification-environment')
 clone=ContinuingCompanion.restore(c.snapshot())
 directory=Path('validation/world-self-development');start=directory/f'seed-{seed}-restart-before.json';end=directory/f'seed-{seed}-restart-after.json';c.save(start)
 code="import sys;sys.path.insert(0,'examples/persistent_individual');from continuing_companion import ContinuingCompanion;c=ContinuingCompanion.load(sys.argv[1]);[c.tick() for _ in range(12)];c.save(sys.argv[2])"
 subprocess.run([sys.executable,'-c',code,str(start),str(end)],check=True,timeout=60)
 for _ in range(12):assert c.tick()==clone.tick()
 assert ContinuingCompanion.load(end).snapshot()==c.snapshot()
 assert c.snapshot()==clone.snapshot()
 goal=next(g for g in c._mind.curriculum.goals if g['target']=='object-0')
 assert goal['status']=='demonstrated-visible-effect'
 movement=[e['payload']['world_motion'] for e in c._events if e['kind']=='experience' and 'world_motion' in e['payload']]
 travelled=sum(abs(m['after']['x']-m['before']['x'])+abs(m['after']['y']-m['before']['y']) for m in movement if m['before']['region']==m['after']['region'])
 assert travelled>=2,'approach movement not demonstrated'
 return {'travelled_cells':travelled,'seed':seed,'identity':c.identity,'lineage':c._lineage,'tick':c.time,'reports':reports,'retained_skill':goal,'checkpoint_sha256':digest(c.snapshot()),'exact_restored_continuation':True,'cold_process_continuation_ticks':12,'scope':'externally arranged two device changes; creature initiates and evaluates finite practice-code revisions in actual 2D body'}

if __name__=='__main__':
 out=Path('validation/world-self-development');out.mkdir(parents=True,exist_ok=True)
 for seed in (201,202,203):
  try:
   result=probe(seed);(out/f'seed-{seed}.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'seed':seed,'passed':True,'tick':result['tick']}),flush=True)
  except Exception as error:
   (out/f'seed-{seed}-failure.json').write_text(json.dumps({'seed':seed,'error':repr(error)},indent=2));raise
