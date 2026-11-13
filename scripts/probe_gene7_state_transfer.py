"""Development-only matched recipient grafts from verified replay checkpoints."""
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time

from creature_brain.benchmark.research_checkpoint import restore_research_checkpoint
from creature_brain.benchmark.tract_transfer_probe import digest, probe_graft


def replay(job):
    seed, good, checkpoint, expected = job
    exp = restore_research_checkpoint(checkpoint)
    states = {'pre': exp.brain.to_dict()}
    checked = 0
    while exp.opportunity < 60:
        event = exp.tick()
        if json.dumps(event, sort_keys=True) != json.dumps(expected[checked], sort_keys=True):
            raise RuntimeError(f'replay mismatch at seed={seed} good={good} step={checked}')
        checked += 1
        if event['opportunity_end'] and exp.opportunity in (20, 60):
            states[str(exp.opportunity)] = exp.brain.to_dict()
    return {'seed': seed, 'good': good, 'replayed_steps': checked, 'states': states}


def main(original, output):
    path = Path(output); states_path = path.with_suffix('.states.jsonl')
    if path.exists() or states_path.exists(): raise FileExistsError('choose new output')
    jobs=[]
    with open(original) as f:
        for line in f:
            row=json.loads(line)
            if row['seed'] in range(4) and row['body']=='walking' and row['mirror'] is False and row['control']=='ordinary':
                events=[s['event'] for s in row['steps'] if s['event']['opportunity'] < 60]
                jobs.append((row['seed'],row['good'],row['initial_checkpoint'],events))
            if len(jobs)==8: break
    if {(j[0],j[1]) for j in jobs}!={(s,g) for s in range(4) for g in (0,1)}:
        raise RuntimeError('missing source branches')
    started=time.monotonic(); captures={}
    with states_path.open('x') as f, ProcessPoolExecutor(max_workers=4) as pool:
        for row in pool.map(replay,jobs):
            captures[(row['seed'],row['good'])]=row['states']
            f.write(json.dumps(row,allow_nan=False)+'\n'); f.flush()
            print('replayed',row['seed'],row['good'],'steps',row['replayed_steps'],flush=True)
    inputs={'visn':{3:.5,8:.5},'driv':{2:.8}}
    probes=[]
    for seed in range(4):
        for recipient_good in (0,1):
            for recipient_stage in ('pre','20','60'):
                recipient=captures[(seed,recipient_good)][recipient_stage]
                chemicals=recipient['chemicals'].copy(); chemicals[150]=.8
                for stage in ('pre','20','60'):
                    for donor_good in ((0,) if stage=='pre' else (0,1)):
                        donor=captures[(seed,donor_good)][stage]
                        probe=probe_graft(recipient,donor,inputs,chemicals)
                        probes.append({'seed':seed,'recipient_good':recipient_good,'recipient_stage':recipient_stage,
                                       'donor_good':donor_good,'donor_stage':stage,**probe})
    summaries={}
    for stage in ('20','60'):
        pairs=[]
        for seed in range(4):
            for recipient_good in (0,1):
                for recipient_stage in ('pre','20','60'):
                    a=next(p for p in probes if (p['seed'],p['recipient_good'],p['recipient_stage'],p['donor_stage'],p['donor_good'])==(seed,recipient_good,recipient_stage,stage,0))
                    b=next(p for p in probes if (p['seed'],p['recipient_good'],p['recipient_stage'],p['donor_stage'],p['donor_good'])==(seed,recipient_good,recipient_stage,stage,1))
                    if a['recipient_except_tract_sha256'] != b['recipient_except_tract_sha256']:raise RuntimeError('recipient changed')
                    wanted_a='object-0' if stage=='20' else 'object-1'
                    wanted_b='object-1' if stage=='20' else 'object-0'
                    pairs.append({'seed':seed,'recipient_good':recipient_good,'recipient_stage':recipient_stage,
                                  'different_targets':a['target']!=b['target'],
                                  'both_targets_follow_outcome':a['target']==wanted_a and b['target']==wanted_b,
                                  'both_eat_and_follow':a['target']==wanted_a and b['target']==wanted_b and a['action']==b['action']==12})
        summaries[stage]={'pairs':len(pairs),'different_targets':sum(p['different_targets'] for p in pairs),
                          'both_targets_follow_outcome':sum(p['both_targets_follow_outcome'] for p in pairs),
                          'both_eat_and_follow':sum(p['both_eat_and_follow'] for p in pairs),'details':pairs}
    root=Path(__file__).resolve().parents[1]
    files=['scripts/probe_gene7_state_transfer.py','src/creature_brain/benchmark/tract_transfer_probe.py',
           'src/creature_brain/neural.py','src/creature_brain/svrule.py',
           'src/creature_brain/benchmark/action_lifecycle.py','src/creature_brain/benchmark/food.py']
    report={'scope':'development seeds 0-3, walking only, original vs reversed value assignment; no held-out claim',
            'source_cases':str(original),'checkpoints':'states JSONL contains replay-verified complete brain state',
            'source_sha256':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files},
            'observation_inputs':inputs,'states_sha256':hashlib.sha256(states_path.read_bytes()).hexdigest(),
            'probes':probes,'summaries':summaries,'elapsed_seconds':time.monotonic()-started,
            'limitations':['same seed and body only; 4 development seeds','recipients retain their own neural activity, pending lobe inputs, chemistry and RNG',
                           'input frames and chemistry are identical within recipient donor comparisons',
                           'donor tract reflects whole experiences, not an isolated food-value signal',
                           'no outcome delivered during probe']}
    path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
