"""Causal history and changed-outcome probes in the actual rural habitat body."""
import json
from copy import deepcopy
from pathlib import Path
from collections import Counter
from continuing_companion import ContinuingCompanion,digest
PROGRAM=Path(__file__).resolve().parents[2]/'research/docking-station-20261103/resources/chichi-brain-program.json'


def prepare(initial, preferred):
    c=ContinuingCompanion.restore(initial).fork(purpose=f'rural preference history: {preferred}')
    c.enable_development(actor='qualification');c.enable_world(actor='qualification')
    c.set_home_town('MAP_LITTLEROOT_TOWN',actor='qualification');c.open_home_interiors(actor='qualification')
    c.make_rural_home(actor='qualification');c.repair_rural_art(actor='qualification')
    for target in ('toy','object-0'):
        for name in ('object-0','object-1','toy'):c.place(name,0,visible=False,actor='qualification-environment')
        c.configure_device(target,function='switch' if target==preferred else 'delayed-switch',delay=2,
            type_id=f'activity-{target}',actor='qualification-environment')
        c.place(target,c._host.position+.5,actor='qualification-environment')
        for _ in range(24):
            c.tick()
            if any(g['target']==target and g['status']=='demonstrated-visible-effect' for g in c._mind.curriculum.goals):break
        assert any(g['target']==target and g['status']=='demonstrated-visible-effect' for g in c._mind.curriculum.goals)
    for name in ('object-0','object-1','toy'):c.place(name,0,visible=False,actor='qualification-environment')
    for _ in range(33):c.tick()
    for target,distance in (('toy',.5),('object-0',-.5)):
        c.configure_device(target,function='switch',type_id=f'activity-{target}',actor='qualification-environment')
        c.place(target,c._host.position+distance,actor='qualification-environment')
    c.tick()
    return c


def probe(seed,out):
    initial=ContinuingCompanion(PROGRAM,seed=seed).snapshot();rows=[]
    for preferred in ('toy','object-0'):
        c=prepare(initial,preferred)
        goals=[g for g in c._mind.curriculum.goals if g['objective']=='revisit-familiar-activity']
        assert goals and goals[0]['target']==preferred,'history did not alter voluntary preference'
        first=deepcopy(goals[0])
        # Complete the first voluntary return before changing what it can accomplish.
        for _ in range(40):
            c.tick()
            if goals[0]['status']!='active':break
        assert goals[0]['status']=='demonstrated-visible-effect'
        c.configure_device(preferred,function='inert',type_id=f'activity-{preferred}',actor='qualification-environment')
        baseline=c.snapshot();start=len(c._mind.curriculum.goals)
        for _ in range(240):c.tick()
        goals=[g for g in c._mind.curriculum.goals[start:] if g['objective']=='revisit-familiar-activity']
        alternate='object-0' if preferred=='toy' else 'toy'
        assertions={'failed_old_activity':any(g['target']==preferred and g['status']=='effect-unresolved-review-needed' for g in goals),
            'returned_to_alternative':bool(goals and goals[-1]['target']==alternate),
            'alternative_success':any(g['target']==alternate and g['status']=='demonstrated-visible-effect' for g in goals)}
        after=c.snapshot()
        row={'seed':seed,'preferred_history':preferred,'first_choice':first,'checks':assertions,
            'later_choices':dict(Counter(g['target'] for g in goals)), 'goals':goals,
            'identity':c.identity,'lineage':c._lineage,'tick':c.time,'checkpoint_sha256':digest(after)}
        (out/f'{seed}-{preferred}-result.json').write_text(json.dumps(row,indent=2))
        (out/f'{seed}-{preferred}-checkpoint.json').write_text(json.dumps(after))
        assert all(assertions.values()),assertions
        assert after['events'][:len(baseline['events'])]==baseline['events']
        restored=ContinuingCompanion.restore(after)
        for _ in range(16):assert c.tick()==restored.tick()
        assert c.snapshot()==restored.snapshot()
        row['restore_continuation_ticks']=16;rows.append(row)
    return rows

if __name__=='__main__':
    out=Path('validation/world-preference');out.mkdir(parents=True,exist_ok=True)
    rows=probe(225,out)
    (out/'summary.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps([{'preferred_history':r['preferred_history'],'checks':r['checks'],'later_choices':r['later_choices']} for r in rows],indent=2))
