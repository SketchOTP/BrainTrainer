"""Independent sham-graft and pre-versus-experienced transfer verification."""
import hashlib
import json
import sys
from pathlib import Path

from creature_brain import DefaultBrain
from creature_brain.benchmark.tract_transfer_probe import digest, probe_graft


def main(report_path, states_path, output_path):
    report=json.loads(Path(report_path).read_text())
    states_raw=Path(states_path).read_bytes()
    if hashlib.sha256(states_raw).hexdigest()!=report['states_sha256']:
        raise ValueError('stage snapshot digest does not match transfer report')
    root=Path(__file__).resolve().parents[1]
    for name, sha in report['source_sha256'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha:
            raise ValueError('source differs: '+name)
    states={(x['seed'],x['good']):x['states'] for x in (json.loads(line) for line in states_raw.splitlines())}
    if set(states)!={(s,g) for s in range(4) for g in (0,1)}:raise ValueError('incomplete stage snapshots')
    inputs={'visn':{3:.5,8:.5},'driv':{2:.8}}
    probes=report['probes']; checks=[]
    for (seed,good), stages in sorted(states.items()):
        for stage, recipient in stages.items():
            chem=recipient['chemicals'].copy();chem[150]=.8
            direct=DefaultBrain.from_dict(recipient);out=direct.tick(inputs,chem)
            sham=probe_graft(recipient,recipient,inputs,chem)
            matching=[p for p in probes if (p['seed'],p['recipient_good'],p['recipient_stage'],p['donor_stage'])==(seed,good,stage,stage)
                      and (stage=='pre' or p['donor_good']==good)]
            same=(len(matching)==1 and matching[0]['target']==sham['target'] and matching[0]['action']==sham['action']
                  and matching[0]['post_tick_brain_sha256']==sham['post_tick_brain_sha256']
                  and (out.attention,out.decision,out.action)==(sham['attention'],sham['decision'],sham['action'])
                  and digest(direct.to_dict())==sham['post_tick_brain_sha256'])
            if not same:raise RuntimeError(f'sham or no-graft mismatch: {seed}/{good}/{stage}')
            checks.append({'seed':seed,'good':good,'stage':stage,'matches_direct_ungrafted':True})
    comparisons={}
    for stage in ('20','60'):
        n=changed=correct=eat_correct=0
        by_seed={str(seed):{'n':0,'target_changed':0,'new_target_value_consistent':0} for seed in range(4)}
        for seed in range(4):
            for rg in (0,1):
                for rs in ('pre','20','60'):
                    pre=next(p for p in probes if (p['seed'],p['recipient_good'],p['recipient_stage'],p['donor_stage'])==(seed,rg,rs,'pre'))
                    for donor in (0,1):
                        after=next(p for p in probes if (p['seed'],p['recipient_good'],p['recipient_stage'],p['donor_stage'],p['donor_good'])==(seed,rg,rs,stage,donor))
                        if pre['recipient_except_tract_sha256']!=after['recipient_except_tract_sha256']:
                            raise ValueError('recipient differs between pre/post graft')
                        good='object-'+str(donor ^ (stage=='60'))
                        n+=1;changed+=pre['target']!=after['target'];correct+=after['target']==good
                        eat_correct+=after['target']==good and after['action']==12
                        cell=by_seed[str(seed)];cell['n']+=1;cell['target_changed']+=pre['target']!=after['target'];cell['new_target_value_consistent']+=after['target']==good
        comparisons[stage]={'comparisons':n,'target_changed_from_pre':changed,'post_target_matches_donor_value':correct,
                            'post_eat_and_target_match_donor_value':eat_correct,'by_seed':by_seed}
    out={'scope':'4 walking development seeds; correlated recipient contexts, not independent trials',
         'source_report_sha256':hashlib.sha256(Path(report_path).read_bytes()).hexdigest(),
         'saved_states_sha256':hashlib.sha256(states_raw).hexdigest(),
         'source_digests_verified':True,'sham_grafts':checks,'pre_vs_post':comparisons,
         'limitations':['whole gene-7 tract carries donor experience, not isolated food value',
                        'recipient state remains fixed within each comparison; no external outcomes are delivered',
                        '6 recipient contexts per seed are correlated','only walking, seeds 0 through 3']}
    output=Path(output_path)
    if output.exists():raise FileExistsError('choose new output')
    output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'sham_checks':len(checks),'pre_vs_post':comparisons},indent=2))

if __name__=='__main__':main(*sys.argv[1:])
