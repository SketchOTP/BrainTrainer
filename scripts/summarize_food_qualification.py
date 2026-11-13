"""Summarize recorded development calibration traces; no new trials."""
import argparse
from collections import Counter
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('cases',type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    rows=[json.loads(s) for s in a.cases.read_text().splitlines()]
    groups={}
    for row in rows:
        key=f"{row['budget']}/{row['embodiment']}/{row['task']}/{int(row['mirror'])}"
        g=groups.setdefault(key,{'seeds':0,'completed_seeds':0,'censored_seeds':[],
              'time_to_first_interaction':[],'ticks':0,'attention_selections':Counter(),
              'target_selections':Counter(),'motor_actions':Counter(),
              'eat_actions_by_target':Counter(),'completed_by_target':Counter(),
              'completed_high_value':0,'completed_low_value':0,'energy_delta_sum':0.0})
        g['seeds']+=1;g['completed_seeds']+=int(row['completed']);g['ticks']+=row['ticks']
        g['time_to_first_interaction'].append(row['first_interaction_tick'])
        if not row['completed']:g['censored_seeds'].append(row['seed'])
        for event in row['history']:
            choice=event['choice'];outcome=event['outcome'];target=choice['target']
            g['attention_selections'][str(choice['attention'])]+=1
            g['target_selections'][str(target)]+=1
            g['motor_actions'][str(choice['action'])]+=1
            if choice['action']==12:g['eat_actions_by_target'][str(target)]+=1
            if outcome['completed']:
                g['completed_by_target'][str(outcome['target'])]+=1
                g['completed_high_value']+=int(event['success'])
                g['completed_low_value']+=int(not event['success'])
                g['energy_delta_sum']+=outcome['energy_delta']
    result={'schema':1,'cases':len(rows),'expected_cases':640,'complete':len(rows)==640,
            'denominator':'stops after first completed consumption or 20 opportunities per case',
            'warning':'selection among completed interactions is conditional and is not proof of learning',
            'groups':groups}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'cases':len(rows),'complete':result['complete'],'output':str(a.output)}))

if __name__=='__main__':main()
