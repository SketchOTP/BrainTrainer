"""Frozen bounded rehearsal panel with an explicitly instrumented ablation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from continuing_companion import ContinuingCompanion, canonical
from creature_brain.development import LEGACY_MODEL


def run(seed,program,folder):
    c=ContinuingCompanion(program,seed=seed)
    for obj in ('object-0','toy'):c.place(obj,0,actor='evaluator',visible=False)
    c.place('object-1',.5,actor='evaluator')
    for _ in range(32):
        event=c.tick()
        if event['outcome']['completed']:break
    acquired=event['outcome']['completed'] and event['outcome']['hunger_adjustment']>0
    c.place('object-1',c._host.position+.5,actor='evaluator')
    c.save(folder/f'{seed}-acquired.json')
    row={'seed':seed,'acquired_adverse_outcome':acquired,'arms':{}}
    for arm in ('legacy','rehearsal','suppressed'):
        child=c.fork(purpose=f'{arm} rehearsal panel branch')
        if arm=='legacy':
            child._append('implementation-change',{'operation':'enable-development','actor':'evaluator','model':LEGACY_MODEL})
            child._development_enabled=True
        else:child.enable_development(actor='evaluator')
        if arm=='suppressed':
            child._mind.rehearsal_due=lambda:False
            child._append('external-intervention',{'operation':'evaluation-suppress-rehearsal',
                'actor':'evaluator','limitation':'future continuation requires this harness intervention'})
        start=child._host.reserve
        child._host.body_strength=0.
        child._append('external-intervention',{'operation':'test-body-strength','value':0.,'actor':'evaluator'})
        events=[child.tick() for _ in range(24)]
        spent=start-child._host.reserve
        child.save(folder/f'{seed}-{arm}-impaired.json')
        child._host.body_strength=1.
        child._append('external-intervention',{'operation':'test-body-strength','value':1.,'actor':'evaluator'})
        recovery=[child.tick() for _ in range(12)]
        child.save(folder/f'{seed}-{arm}-final.json')
        away=[]
        for i,e in enumerate(recovery,1):
            relative=next((o['relative_position'] for o in e['observation']['objects'] if o['identity']=='object-1'),None)
            if relative is not None and (e['body_motion']['after']-e['body_motion']['before'])*relative<0:away.append(i)
        row['arms'][arm]={'impairment_reserve_spent':spent,'first_away_recovery_tick':away[0] if away else None,
            'away_recovery_ticks':away,'events':events+recovery,'review':child.self_review(),
            'harmful_consumptions':sum(e['outcome']['completed'] and e['outcome']['hunger_adjustment']>0 for e in events+recovery)}
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False)
    root=Path(__file__).resolve().parents[2]
    sources=list((root/'src').rglob('*.py'))+list((root/'examples/persistent_individual').glob('*.py'))+[root/'docs/REHEARSAL_GOAL_PROTOCOL.md']
    hashes={}
    for source in sources:
        rel=source.relative_to(root);target=a.output/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        hashes[str(rel)]=hashlib.sha256(target.read_bytes()).hexdigest()
    (a.output/'manifest.json').write_text(json.dumps(hashes,indent=2)+'\n')
    program=root/'research/docking-station-20261103/resources/chichi-brain-program.json'
    with (a.output/'cases.jsonl').open('x') as out:
        for seed in range(40,44):
            row=run(seed,program,a.output);out.write(canonical(row)+'\n');out.flush()
            print(json.dumps({'seed':seed,'acquired':row['acquired_adverse_outcome'],
                'arms':{k:{n:v[n] for n in ('impairment_reserve_spent','first_away_recovery_tick','harmful_consumptions')} for k,v in row['arms'].items()}}),flush=True)


if __name__=='__main__':main()
