"""Independently reconstruct and audit recorded CB-04 prepared starts."""
import argparse,hashlib,json
from pathlib import Path
from inherited_preparation import restore_prepared,clone_prepared_motor,prepared_snapshot
from prepared_development import digest

def main():
 p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
 rows=[json.loads(line) for line in a.raw.read_text().splitlines()];checks=0;delayed=0
 for row in rows:
  source=restore_prepared(row['prepared_checkpoint']);base=prepared_snapshot(source);bs=base['state'];bm=bs['model']
  assert row['preparation']==base['receipt'] and row['preparation']['processed_count']==29
  assert row['preparation']['brain_tick_after']>0
  for item in row['immediate']:
   clone=clone_prepared_motor(source,item['condition']);cp=prepared_snapshot(clone);cs=cp['state'];cm=cs['model']
   assert digest(cp)==item['initial_checkpoint_sha256']
   assert cp['receipt']==base['receipt'] and cs['individual']==bs['individual']
   for k in ('reserve','body_strength','obstacle_present'):assert cs[k]==bs[k],k
   for k in ('evidence','decisions','pending'):assert cm[k]==bm[k],k
   if item['condition']=='candidate':assert cm['confirmations']==[] and cm['confirmation_attempts']==[]
   else:assert cm['schema']==bm['schema']
   checks+=1
  for item in row['delayed']:
   assert item['interval']['ticks']==640 and item['post_interval_checkpoint']['receipt']==base['receipt']
   assert item['post_interval_checkpoint']['state']['individual']['time']==640
   assert item['result']['start_tick']==640
   delayed+=1
 assert checks==32 and delayed==8
 result={'raw_sha256':hashlib.sha256(a.raw.read_bytes()).hexdigest(),'matched_full_initial_checkpoints':checks,
         'delayed_interval_receipts':delayed,'note':'Reconstructed from saved prepared checkpoint; intended model schema and condition differences are validated separately.'}
 with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result))

if __name__=='__main__':main()
