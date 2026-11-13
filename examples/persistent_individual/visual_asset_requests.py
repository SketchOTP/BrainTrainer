"""Experience-grounded requests for missing visual capabilities.

Requests belong to the visual system, not to the creature's episodic memory.
A generated candidate never establishes a new ability or replaces installed art.
"""
import hashlib,json
from pathlib import Path
from asset_generation import prepare,run

ASSETS=Path(__file__).with_name('assets')/'creature'/'etch-v3'

def harvest_requirement(companion,*,assets=ASSETS,evidence_event=None):
 manifest=json.loads((assets/'manifest.json').read_text())
 if any('harvest' in asset['rows'] for asset in manifest['assets'].values()):return None
 # Bounded recent history; later polling observes future actions without scanning
 # the full individual's life or inventing an unobserved visual need.
 if evidence_event is None:
  event=next((e for e in reversed(companion._events[-128:]) if e['kind']=='experience'
   and e['payload']['outcome']['status']=='harvested' and e['payload']['outcome']['completed']),None)
 else:
  if type(evidence_event) is not int or not 0<=evidence_event<len(companion._events):raise ValueError('unknown source experience')
  event=companion._events[evidence_event]
 if event is None or event['kind']!='experience':return None
 if event['payload']['outcome']['status']!='harvested' or not event['payload']['outcome']['completed']:return None
 payload=event['payload'];action=payload['executed_action'];outcome=payload['outcome']
 if (action['action']!=1 or outcome['action']!=action['action'] or outcome['action_id']!=action['id'] or outcome['target']!=action['target']):return None
 observed=next((o for o in payload['observation']['objects'] if o['identity']==action['target']),None)
 if observed is None or not observed['type_id'].startswith('berry:'):return None
 reference=assets/'daily.png';digest=hashlib.sha256(reference.read_bytes()).hexdigest()
 if digest!=manifest['assets']['daily']['sha256']:raise ValueError('installed visual reference differs from manifest')
 return {'intent':'harvest-berries','owner':'creature-animation','identity':companion.identity,
  'branch_id':companion._lineage['branch_id'],'evidence':{'kind':'experienced','event':event['sequence'],
   'tick':event['tick'],'branch_id':event['branch_id'],'context':event['context'],'event_sha256':hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest(),
   'action':action['action'],'target':action['target'],'outcome':outcome['status']},
  'reference':str(reference.resolve()),'reference_sha256':digest,
  'coverage':'installed daily sheet has generic interact poses, but no harvest clip',
  'ability_claim':'one recorded harvest; no new skill or mastery inferred'}

def enqueue(directory,companion,*,assets=ASSETS,evidence_event=None):
 demand=harvest_requirement(companion,assets=assets,evidence_event=evidence_event)
 if demand is None:return None
 # Deduplicate this visual capability per individual branch and reference version,
 # not per harvested berry. Keep the original motivating event unchanged.
 key=hashlib.sha256(json.dumps({k:demand[k] for k in ('intent','identity','branch_id','reference_sha256')},sort_keys=True).encode()).hexdigest()
 folder=Path(directory)/key
 if folder.exists():
  saved=json.loads((folder/'demand.json').read_text())
  if any(saved[k]!=demand[k] for k in ('intent','identity','branch_id','reference_sha256')):raise ValueError('asset request identity mismatch')
  return folder
 folder=prepare(folder,owner=demand['owner'],requirement=(
  'Create a harvest animation for the EXACT purple mechanical creature in the attached daily sheet. '
  'Preserve its face, yellow eyes, purple armor, proportions and rural overworld pixel-art style. '
  'Four consecutive poses, facing right: reach toward a berry just outside the cell; pinch/pick it; '
  'lift the small berry in its hand; return to a balanced holding pose. No eating, no other creature, '
  'no bush or scenery, no ground shadow halo. Keep all feet on one stable bottom-center baseline. '
  'This request follows an actual completed berry harvest; artwork does not establish a new skill.'),
  references=[demand['reference']],cell_width=28,cell_height=28,
  states=['reach','pick','lift','hold'])
 with (folder/'demand.json').open('x') as f:json.dump(demand,f,indent=2)
 return folder

def run_pending(folder,*,runner=run):
 folder=Path(folder)
 if not (folder/'demand.json').is_file():raise ValueError('missing grounded visual demand')
 if (folder/'receipt.json').exists():return json.loads((folder/'receipt.json').read_text())
 if (folder/'started.json').exists():return {'status':'recovery-required','installed':False}
 return runner(folder)

class AssetRequestScheduler:
 """One image worker; called after a durable habitat tick, never mutates the brain."""
 def __init__(self,directory,*,runner=run):
  from concurrent.futures import ThreadPoolExecutor
  import threading
  self.directory=Path(directory);self.runner=runner;self.cancel=threading.Event()
  self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='creature-art')
  self.future=None;self.folder=None;self.last_source=None;self.status='idle'
 def poll(self,c):
  if self.future is not None:
   if not self.future.done():self.status='generating-candidate';return
   try:self.status=self.future.result()['status']
   except Exception as e:
    self.status='generation-failed'
    (self.folder/'dispatch-result.json').write_text(json.dumps({'status':self.status,'error':f'{type(e).__name__}: {e}','installed':False}))
   self.future=None
  event=next((e for e in reversed(c._events[-2:]) if e['kind']=='experience'),None)
  if event is None or event['payload']['outcome']['status']!='harvested':return
  source=(c.identity,c._lineage['branch_id'],event['sequence'])
  if source==self.last_source:return
  self.last_source=source
  folder=enqueue(self.directory,c,evidence_event=event['sequence'])
  if folder is None:return
  self.folder=folder
  for filename in ('receipt.json','dispatch-result.json'):
   if (folder/filename).exists():
    self.status=json.loads((folder/filename).read_text())['status'];return
  if (folder/'dispatched.json').exists() or (folder/'started.json').exists():self.status='recovery-required';return
  with (folder/'dispatched.json').open('x') as f:json.dump({'event':event['sequence'],'identity':c.identity,'branch_id':c._lineage['branch_id']},f)
  self.future=self.pool.submit(self.runner,folder,cancel=self.cancel);self.status='generating-candidate'
 def close(self):
  self.cancel.set();self.pool.shutdown(wait=True)
