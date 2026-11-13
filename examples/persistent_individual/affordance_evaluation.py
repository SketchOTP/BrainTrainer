"""Natural practice and retained-skill transfer; no supplied task goals."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from continuing_companion import ContinuingCompanion,canonical


def run(seed,function,program,folder):
    case=f'{seed}-{function}';label=f'widget-{seed}-{0 if function=="switch" else 1}'
    sign=-1 if seed%2 else 1
    c=ContinuingCompanion(program,seed=seed)
    for obj in ('object-0','object-1'):c.place(obj,0,actor='evaluator',visible=False)
    c.configure_device('toy',function=function,type_id=label,actor='evaluator')
    c.place('toy',sign*2.,actor='evaluator');c.enable_development(actor='evaluator')
    training=[]
    for _ in range(24):
        training.append(c.tick())
        if any(g['target']=='toy' and g['status']=='demonstrated-visible-effect' for g in c.self_review()['learning_goals']):break
    c.place('toy',0,actor='evaluator',visible=False)
    c.configure_device('object-0',function=function,type_id=label,actor='evaluator')
    c.place('object-0',c._host.position-sign*4.,actor='evaluator')
    c.save(folder/f'{case}-trained.json')
    row={'seed':seed,'function':function,'type_label':label,'sign':sign,'training':training,'arms':{}}
    for arm in ('retained','cleared'):
        child=c.fork(purpose=f'{arm} skill transfer evaluation')
        if arm=='cleared':
            child._mind.curriculum.skills.clear()
            child._append('external-intervention',{'operation':'evaluation-clear-skill-projection','actor':'evaluator',
                          'limitation':'restore reconstructs memory; ablation requires harness intervention'})
        events=[]
        for _ in range(24):
            events.append(child.tick())
            if any(g['target']=='object-0' and g['status']=='demonstrated-visible-effect' for g in child.self_review()['learning_goals']):break
        child.save(folder/f'{case}-{arm}.json')
        row['arms'][arm]={'events':events,'review':child.self_review(),'device_state':child._host.objects['object-0']['state']}
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False)
    root=Path(__file__).resolve().parents[2];hashes={}
    for source in list((root/'src').rglob('*.py'))+list((root/'examples/persistent_individual').glob('*.py'))+[root/'docs/AFFORDANCE_LEARNING_PROTOCOL.md']:
        rel=source.relative_to(root);target=a.output/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        hashes[str(rel)]=hashlib.sha256(target.read_bytes()).hexdigest()
    (a.output/'manifest.json').write_text(json.dumps(hashes,indent=2)+'\n')
    program=root/'research/docking-station-20261103/resources/chichi-brain-program.json'
    with (a.output/'cases.jsonl').open('x') as out:
        for seed in range(60,64):
            for function in ('switch','counter'):
                row=run(seed,function,program,a.output);out.write(canonical(row)+'\n');out.flush()
                print(json.dumps({'seed':seed,'function':function,'training_ticks':len(row['training']),
                    'arms':{k:{'ticks':len(v['events']),'activations':sum(e['outcome']['status']=='activated' for e in v['events'])} for k,v in row['arms'].items()}}),flush=True)


if __name__=='__main__':main()
