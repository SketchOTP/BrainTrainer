"""Owned offline addition of persistent workshop opportunities; no learned history import."""
from pathlib import Path
from copy import deepcopy
import argparse,json
from habitat_store import HabitatStore
from continuing_companion import ContinuingCompanion,digest

FIXTURES=(('workshop-lantern','Workshop lantern','delayed-switch',5,20,17),
          ('workshop-stone','Workshop stone','inert',2,19,20))

def adopt(home,evidence):
 store=HabitatStore(home)
 try:
  c=store.load();ids={row[0] for row in FIXTURES}
  present=ids.intersection(c._host.objects)
  if present:
   if present!=ids:raise ValueError('partial workshop addition; inspect preserved state')
   for identity,label,function,delay,x,y in FIXTURES:
    o=c._host.objects[identity]
    expected=dict(label=label,function=function,delay=delay,type_id=identity,region='MAP_LITTLEROOT_TOWN',x=x,y=y)
    if any(o.get(k)!=v for k,v in expected.items()):raise ValueError('existing workshop differs from requested fixtures')
   return {'changed':False,'identity':c.identity}
  evidence=Path(evidence);evidence.mkdir(parents=True,exist_ok=False)
  (evidence/'original-current.json').write_bytes(store.current.read_bytes())
  before=c.snapshot();c.save(evidence/'before.json')
  for identity,label,function,delay,x,y in FIXTURES:
   c.add_world_device(identity,label=label,function=function,type_id=identity,delay=delay,
       region='MAP_LITTLEROOT_TOWN',x=x,y=y,actor='qualified-workshop-world-builder')
  after=c.snapshot();comparable=deepcopy(after['host'])
  for identity in ids:del comparable['state']['individual']['objects'][identity]
  if comparable!=before['host'] or after['events'][:-2]!=before['events'] or after['lineage']!=before['lineage']:
   raise ValueError('workshop addition changed prior individual')
  if ContinuingCompanion.restore(after).snapshot()!=after:raise ValueError('workshop candidate restore differs')
  c.save(evidence/'candidate.json');store.save(c)
  if store.load().snapshot()!=after:raise ValueError('installed workshop differs')
  receipt={'changed':True,'identity':c.identity,'tick':c.time,'before_sha256':digest(before),'after_sha256':digest(after),
      'preserved':['entire prior host','full prior history','lineage'],'added':sorted(ids),
      'kind':'external environment addition; no test experiences or learned code imported'}
  (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
 finally:store.close()

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',required=True,type=Path);p.add_argument('--evidence',required=True,type=Path)
 a=p.parse_args();print(json.dumps(adopt(a.home,a.evidence)))
