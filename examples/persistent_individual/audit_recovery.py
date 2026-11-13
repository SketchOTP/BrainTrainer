"""Independently audit frozen recovery results and per-attempt action ownership."""
import argparse,hashlib,json,random
from pathlib import Path

SCENARIOS=('sustained','brief','noisy')
CONDITIONS=('normal','effort','baseline','candidate')


def main():
    p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('manifest',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();manifest=json.loads(a.manifest.read_text())
    for path,digest in manifest['sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('changed frozen source: '+path)
    lines=a.raw.read_text().splitlines();rows=[json.loads(s) for s in lines];seeds=manifest['seeds']
    expected={(s,scenario,condition) for s in seeds for scenario in SCENARIOS for condition in CONDITIONS}
    keys=[(r['seed'],r['scenario'],r['condition']) for r in rows]
    if len(keys)!=len(expected) or set(keys)!=expected:raise ValueError('case keys incomplete or duplicate')
    counts={'motor_attempts':0,'eligible':0,'blocked':0,'mismatched_ownership':0,'invalid_predictions':0,
            'duplicate_attempt_ids':0,'wrong_physical_schedule':0,'bad_continuations':0,'cases':len(rows)}
    for row in rows:
        if len(row['events'])!=540 or not row['checkpoint_continuation_equal']:counts['bad_continuations']+=1
        seed=row['seed'];scenario=row['scenario'];end=210 if scenario=='brief' else 360
        for tick,event in enumerate(row['events']):
            strength=.2 if 180<=tick<end else 1.0
            if scenario=='noisy' and strength==.2 and random.Random(seed*1000003+tick+901001).random()<.1:strength=1.0
            if event['time']!=tick+1 or event['body_strength']!=strength or event['obstacle_present']!=(tick%53==17):
                counts['wrong_physical_schedule']+=1
        ids=set()
        for m in row['motor']:
            counts['motor_attempts']+=1
            if m['motor_attempt_id']!=f"{m['executing_action_id']}:motor:{m['tick']}":counts['mismatched_ownership']+=1
            if m['motor_attempt_id'] in ids:counts['duplicate_attempt_ids']+=1
            ids.add(m['motor_attempt_id'])
            event=row['events'][m['tick']]
            if (m['action_id'],m['brain_action'],m['brain_target'])!=(event['choice']['id'],event['choice']['action'],event['choice']['target']):counts['mismatched_ownership']+=1
            if (m['executing_action_id'],m['executing_action'],m['executing_target'])!=(event['outcome']['action_id'],event['outcome']['action'],event['outcome']['target']):counts['mismatched_ownership']+=1
            if m['prediction']!=m['predictions'][m['mode']]['success_probability']:counts['invalid_predictions']+=1
            if m['motor_success'] is None:
                counts['blocked']+=1
                if not m['cancel_kept_evidence']:counts['mismatched_ownership']+=1
            else:counts['eligible']+=1
    counts['raw_sha256']=hashlib.sha256(a.raw.read_bytes()).hexdigest()
    counts['verified']=not any(counts[k] for k in ('mismatched_ownership','invalid_predictions','duplicate_attempt_ids','wrong_physical_schedule','bad_continuations'))
    a.output.write_text(json.dumps(counts,indent=2)+'\n');print(json.dumps(counts,indent=2))
    if not counts['verified']:raise ValueError('audit failed')

if __name__=='__main__':main()
