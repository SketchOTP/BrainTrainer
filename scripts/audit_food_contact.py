"""Analyze retained food diagnostic movement and eat failures; no simulation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('choose a new output')
    data=json.loads(a.capture.read_text()); groups={}
    for row in data['rows']:
        key=f"{row['embodiment']}/{row['task']}/{row['condition']}"
        g=groups.setdefault(key,{'eat_requests':0,'eat_in_contact':0,'eat_out_of_contact':0,
          'eat_without_target':0,'completed_consumptions':0,'out_of_contact_gap_bins':Counter(),
          'movement_toward':0,'movement_away':0,'movement_unchanged':0,'movement_not_followed':0,
          'prior_action_before_eat':Counter()})
        events=row['history']
        for i,event in enumerate(events):
            action=event['choice'];outcome=event['outcome'];target=action['target']
            objects=event['observation']['objects'];obj=next((x for x in objects if x['identity']==target),None)
            if action['action']==12:
                g['eat_requests']+=1
                if obj is None:g['eat_without_target']+=1
                elif obj['contact']:g['eat_in_contact']+=1
                else:
                    g['eat_out_of_contact']+=1;gap=max(0.0,obj['distance']-.85)
                    g['out_of_contact_gap_bins']['<=0.2' if gap<=.2 else '<=0.5' if gap<=.5 else '>0.5']+=1
                if outcome['completed']:g['completed_consumptions']+=1
                previous=events[i-1] if i and events[i-1]['opportunity']==event['opportunity'] else None
                g['prior_action_before_eat'][str(previous['choice']['action']) if previous else 'first_tick']+=1
            if outcome['status']=='moving' and obj is not None:
                nxt=events[i+1] if i+1<len(events) and events[i+1]['opportunity']==event['opportunity'] else None
                next_obj=next((x for x in nxt['observation']['objects'] if x['identity']==target),None) if nxt else None
                if next_obj is None:g['movement_not_followed']+=1
                elif next_obj['distance'] < obj['distance']-1e-12:g['movement_toward']+=1
                elif next_obj['distance'] > obj['distance']+1e-12:g['movement_away']+=1
                else:g['movement_unchanged']+=1
    out={'capture_sha256':hashlib.sha256(a.capture.read_bytes()).hexdigest(),
         'scope':'four development seeds; per-step movement and eat requests; observational, not causal',
         'contact_radius':.85,'groups':groups}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'output':str(a.output),'groups':len(groups)}))

if __name__=='__main__':main()
