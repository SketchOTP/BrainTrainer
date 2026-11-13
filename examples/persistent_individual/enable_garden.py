"""Offline, attributed garden adoption with a preserved before-image."""
from pathlib import Path
from copy import deepcopy
import argparse,json
from habitat_store import HabitatStore
from continuing_companion import ContinuingCompanion,digest
from garden import plots

def adopt(home,evidence,*,nutrition=False):
 store=HabitatStore(home)
 try:
  c=store.load()
  garden=(c._host.world or {}).get('garden')
  if ('nutrition' in (garden or {}) if nutrition else garden is not None):return {'changed':False,'identity':c.identity}
  evidence=Path(evidence);evidence.mkdir(parents=True,exist_ok=False)
  (evidence/'original-current.json').write_bytes(store.current.read_bytes())
  before=c.snapshot();c.save(evidence/'before.json')
  if nutrition:c.enable_berry_nutrition(actor='qualified-stored-food-adoption')
  else:c.enable_garden(actor='qualified-garden-adoption')
  after=c.snapshot()
  comparable=deepcopy(after['host']);individual=comparable['state']['individual']
  if nutrition:individual['world']['garden'].pop('nutrition')
  else:
   individual['world'].pop('garden');individual['objects']={k:v for k,v in individual['objects'].items() if k not in plots()}
  if comparable!=before['host'] or after['events'][:-1]!=before['events'] or after['lineage']!=before['lineage']:raise ValueError('garden adoption changed prior individual state')
  if ContinuingCompanion.restore(after).snapshot()!=after:raise ValueError('garden candidate did not restore exactly')
  c.save(evidence/'candidate.json');store.save(c)
  if store.load().snapshot()!=after:raise ValueError('garden installation differs from candidate')
  receipt={'changed':True,'identity':c.identity,'tick':c.time,'before_sha256':digest(before),'after_sha256':digest(after),'preserved':['prior host state','prior events','lineage'],'added':['stored food capability','zero consumption counters','attributed nutrition implementation event'] if nutrition else ['six native berry plots','empty berry inventory','attributed garden implementation event']}
  (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
 finally:store.close()

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--nutrition',action='store_true');p.add_argument('--home',required=True,type=Path);p.add_argument('--evidence',required=True,type=Path);a=p.parse_args();print(json.dumps(adopt(a.home,a.evidence,nutrition=a.nutrition)))
