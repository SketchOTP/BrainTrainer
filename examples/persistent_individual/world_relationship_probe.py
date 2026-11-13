"""Compare reported participation, decline and quiet on live-history test branches."""
import json
from pathlib import Path
from continuing_companion import ContinuingCompanion,digest
from habitat_store import HabitatStore


def probe(home,out):
    out.mkdir(parents=True,exist_ok=False)
    source=HabitatStore.read_checkpoint(Path(home)/'current.json')
    source_snapshot=source.snapshot();source_digest=digest(source_snapshot)
    c=source.fork(purpose='prospective rural shared-activity qualification')
    prior=len(c._mind.shared.invitations)
    for step in range(96):
        if step%30==0:c.report_companion_availability(True)
        c.tick()
        if len(c._mind.shared.invitations)>prior:break
    assert len(c._mind.shared.invitations)>prior,'no invitation during actual rural activity'
    invitation=c._mind.shared.invitations[-1]
    assert invitation['status']=='offered'
    assert c._events[invitation['guidance_event']]['kind']=='supplied-information'
    assert c._events[invitation['teaching_outcome_event']]['kind']=='experience'
    invited=c.snapshot();c.save(out/'invited.json')
    rows=[]
    for response in ('join','decline','quiet'):
        child=ContinuingCompanion.restore(invited).fork(purpose=f'counterfactual reported response: {response}')
        start=child.time
        if response=='quiet':child.report_companion_availability(False)
        else:child.respond_to_invitation(invitation['event'],response)
        assert child.time==start
        for step in range(160):
            if response!='quiet' and step%30==0:child.report_companion_availability(True)
            child.tick()
        invitations=child._mind.shared.invitations
        current=next(i for i in invitations if i['event']==invitation['event'])
        later=[i for i in invitations if i['event']>invitation['event']]
        goal=next(g for g in child._mind.curriculum.goals if g['id']==invitation['goal_id'])
        checks={'activity_completed_independently':goal['status']=='demonstrated-visible-effect'}
        if response=='join':checks['reported_participation_completed']=current['status']=='completed-with-reported-participation'
        elif response=='decline':
            checks['decline_retained']=current['status']=='declined'
            checks['cooldown_respected']=all(child._events[i['event']]['tick']>=start+128 for i in later)
        else:
            checks['closed_when_unavailable']=current['status']=='closed-person-unavailable'
            checks['no_more_invitations']=not later
        state=child.snapshot();restored=ContinuingCompanion.restore(state)
        for _ in range(8):assert child.tick()==restored.tick()
        assert child.snapshot()==restored.snapshot()
        row={'response':response,'checks':checks,'source_sha256':source_digest,
             'lineage':state['lineage'],'start_tick':start,'end_tick':state['host']['state']['individual']['time'],
             'invitation':current,'later_invitation_ticks':[child._events[i['event']]['tick'] for i in later],
             'activity_goal':goal,'restored_continuation_ticks':8,
             'test_events':state['events'][len(invited['events']):],'checkpoint_sha256':digest(state)}
        (out/f'{response}.json').write_text(json.dumps(row,indent=2))
        rows.append({k:row[k] for k in ('response','checks','later_invitation_ticks','start_tick','end_tick')})
        print(json.dumps(rows[-1]),flush=True)
        assert all(checks.values()),checks
    assert source.snapshot()==source_snapshot,'source individual was mutated'
    result={'source_identity':source.identity,'source_tick':source.time,'source_sha256':source_digest,'cases':rows,
        'scope':'reported presence and responses in explicit test branches; no biometric recognition or actual human participation'}
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    probe('runs/habitat-visual-qualification',Path('validation/world-relationship'))
