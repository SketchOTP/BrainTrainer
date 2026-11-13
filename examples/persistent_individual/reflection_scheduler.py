"""One asynchronous reflection worker; admission stays with the habitat owner.

Call poll while holding the habitat lock. Worker threads never touch the creature.
An unfinished worker with no owned handle after restart requires recovery rather
than an automatic duplicate inference request.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import threading
import uuid
from creature_brain.development import supports
from llm_reflection import prepare,run,validate_response,read_receipt

class ReflectionScheduler:
 def __init__(self,directory,*,runner=run):
  self.directory=Path(directory);self.runner=runner
  self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='creature-reflection')
  self.future=None;self.cancel=threading.Event();self.status='idle'
 def poll(self,c,save):
  if not supports(c._mind.version,'reflective_trials'):return
  mind=c._mind.reflective_trials
  completed={r['request_id'] for r in mind.reflections}
  pending=next((r for r in mind.requests if r['request_id'] not in completed),None)
  if pending:
   folder=self.directory/pending['job_id']
   if self.future is not None and not self.future.done():self.status='thinking';return
   receipt_path=folder/'receipt.json'
   if not receipt_path.exists():self.status='recovery-required';return
   try:receipt=read_receipt(folder,pending['request_id'])
   except (OSError,ValueError):self.status='recovery-required';return
   if self.future is not None:
    try:self.future.result()
    except Exception:pass # Receipt is the retained provider failure evidence.
    self.future=None
   result={'operation':'reflection-result','request_id':pending['request_id'],'job_id':pending['job_id'],
    'provider_status':receipt['status'],'status':'not-applied'}
   if receipt['status']=='proposal-received-not-applied':
    try:
     packet=json.loads((folder/'request.json').read_text());raw=(folder/'response.json').read_bytes();response=json.loads(raw)
     if hashlib.sha256(raw).hexdigest()!=receipt.get('response_sha256'):raise ValueError('reflection artifact differs from provider receipt')
     if not isinstance(packet,dict):raise ValueError('reflection packet is not an object')
     packet_digest=hashlib.sha256(json.dumps({k:v for k,v in packet.items() if k!='request_id'},sort_keys=True).encode()).hexdigest()
     if packet_digest!=pending['request_id']:raise ValueError('reflection packet differs from requested evidence')
     validate_response(response,packet)
     result['reflection']=response
     # A successful saved trial may precede this result after interrupted admission.
     if any(t['request_id']==pending['request_id'] for t in mind.trials):result['status']='trial-admitted'
     elif response['next_goal']['method']=='practice' and response['trial'] is not None:
      c.adopt_reflective_trial(packet,response);result['status']='trial-admitted'
     else:result['status']='reflection-recorded-without-body-trial'
    except (ValueError,KeyError,OSError) as exc:result.update(status='proposal-rejected',reason=str(exc))
   else:result.update(status='provider-failed',reason=receipt.get('error','provider did not complete'))
   c._append('hypothesis',result);save();self.status=result['status'];return
  trigger=mind.request(c._mind.curriculum.goals,c.time)
  if trigger is None:self.status='idle';return
  job_id=uuid.uuid4().hex
  folder=prepare(c,self.directory/job_id,purpose='analysis',focus=trigger)
  packet=json.loads((folder/'request.json').read_text())
  c._append('hypothesis',{'operation':'request-reflection','request_id':packet['request_id'],'job_id':job_id,**trigger})
  save() # Persist intent before the provider can consume resources.
  self.future=self.pool.submit(self.runner,folder,cancel=self.cancel);self.status='thinking'
 def close(self):
  self.cancel.set();self.pool.shutdown(wait=True)
