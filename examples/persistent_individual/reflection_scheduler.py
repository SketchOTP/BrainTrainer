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

def _apply_development(c,packet,response,result):
 request=packet.get('development_request')
 current=c._mind.improvement_request()
 if not isinstance(request,dict) or current!=request:
  result.update(status='stale-development-proposal',reason='the lived goal or its evidence changed while reflection was running')
  return
 change=response.get('software_change')
 if change is not None:
  from creature_brain.practice_policy import PracticePolicy
  from self_development import evaluate,install
  c._room(3) # Evaluation, installation, and the terminal reflection receipt.
  policy=PracticePolicy(change['source'])
  if policy.sha256==c._mind.curriculum.policy.sha256:
   raise ValueError('candidate is identical to the active executable policy')
  evidence=set(request.get('evidence',[]))
  if not evidence.intersection(change['evidence_ids']) or not evidence.intersection(response['next_goal']['evidence_ids']):
   raise ValueError('code proposal does not cite the lived practice limitation')
  candidate_request={**request,'candidate_origin':'creature-llm-self-review',
   'candidates':[{'hypothesis':change['expected_effect'],'source':policy.source}]}
  report=evaluate(c,candidate_request)
  report.update(origin='creature-llm-self-review',source_request_id=packet['request_id'],
   code_evidence_ids=change['evidence_ids'],expected_effect=change['expected_effect'],
   regressions_to_watch=change['regressions_to_watch'],
   scope='LLM-proposed bounded executable policy; isolated branch regressions; lived body follow-up required for retention')
  c._append('development-evaluation',report)
  selected=next((row for row in report['candidates'] if row['sha256']==report['selected_sha256']),None)
  if selected:
   install(c,policy,request_id=request['request_id'],resume_goal=request['goal_id'],
    origin='creature-llm-self-review')
   result.update(status='code-candidate-installed-pending-lived-outcome',
    candidate_sha256=policy.sha256,evaluation_event=len(c._events)-2)
  else:
   result.update(status='code-candidate-rejected-by-branch-regressions',
    candidate_sha256=policy.sha256,evaluation_event=len(c._events)-1)
 elif response['next_goal']['method']=='practice' and response.get('trial') is not None:
  c.adopt_reflective_trial(packet,response);result['status']='trial-admitted'
 else:
  result.update(status='development-review-no-code-change',
   reason='the reflective component did not recommend executable modification')

class ReflectionScheduler:
 def __init__(self,directory,*,runner=run):
  self.directory=Path(directory);self.runner=runner
  self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='creature-reflection')
  self.future=None;self.cancel=threading.Event();self.status='idle';self.current_purpose=None
 def request_self_review(self,c,save,*,actor,focus):
  if not isinstance(actor,str) or not actor.strip():raise ValueError('self-review request requires an attributed person')
  if self.future is not None and not self.future.done():raise ValueError('a reflection is already running')
  if any(r['request_id'] not in {x['request_id'] for x in c._mind.reflective_trials.reflections}
      for r in c._mind.reflective_trials.requests):raise ValueError('a previous reflection still needs recovery')
  if c._mind.reflective_trials.active() is not None:raise ValueError('finish the current embodied trial before requesting a review')
  job_id=uuid.uuid4().hex;folder=prepare(c,self.directory/job_id,purpose='self-review',focus=focus)
  packet=json.loads((folder/'request.json').read_text())
  c._append('hypothesis',{'operation':'request-reflection','request_id':packet['request_id'],
   'job_id':job_id,'purpose':'self-review','trigger_id':focus['trigger_id'],
   'reason':'owner-requested-post-update-self-review','actor':actor,
   'evidence_event':focus['evidence_event'],'update_event':focus['update_event']})
  save();self.current_purpose='self-review';self.future=self.pool.submit(self.runner,folder,cancel=self.cancel)
  self.status='thinking';return packet['request_id']
 def poll(self,c,save):
  if not supports(c._mind.version,'reflective_trials'):return
  mind=c._mind.reflective_trials
  completed={r['request_id'] for r in mind.reflections}
  pending=next((r for r in mind.requests if r['request_id'] not in completed),None)
  if pending:
   self.current_purpose=pending.get('purpose','analysis')
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
    'provider_status':receipt['status'],'purpose':self.current_purpose,'status':'not-applied'}
   if receipt['status']=='proposal-received-not-applied':
    try:
     packet=json.loads((folder/'request.json').read_text());raw=(folder/'response.json').read_bytes();response=json.loads(raw)
     if hashlib.sha256(raw).hexdigest()!=receipt.get('response_sha256'):raise ValueError('reflection artifact differs from provider receipt')
     if not isinstance(packet,dict):raise ValueError('reflection packet is not an object')
     packet_digest=hashlib.sha256(json.dumps({k:v for k,v in packet.items() if k!='request_id'},sort_keys=True).encode()).hexdigest()
     if packet_digest!=pending['request_id']:raise ValueError('reflection packet differs from requested evidence')
     validate_response(response,packet)
     if packet.get('purpose')!=self.current_purpose:raise ValueError('reflection purpose differs from its durable request')
     result['reflection']=response
     if self.current_purpose=='dream':c.record_reflective_dream(packet,response)
     elif self.current_purpose=='development':_apply_development(c,packet,response,result)
     # A successful saved trial may precede this result after interrupted admission.
     if self.current_purpose=='development':pass
     elif any(t['request_id']==pending['request_id'] for t in mind.trials):result['status']='trial-admitted'
     elif (self.current_purpose=='self-review' and c._llm_self_review_revision>=2 and
           response['trial'] is not None and
           c._mind.reflective_trials.redundant_success_count(response['trial'])>=2):
      count=c._mind.reflective_trials.redundant_success_count(response['trial'])
      result.update(status='reflection-recorded-without-body-trial',
       reason=f'self-review proposed the same target, action and appearance condition after {count} prior observed successes; a new target or prediction is needed')
     elif response['next_goal']['method']=='practice' and response['trial'] is not None:
      c.adopt_reflective_trial(packet,response);result['status']='trial-admitted'
     else:result['status']='reflection-recorded-without-body-trial'
    except (ValueError,KeyError,OSError) as exc:result.update(status='proposal-rejected',reason=str(exc))
   else:result.update(status='provider-failed',reason=receipt.get('error','provider did not complete'))
   c._append('hypothesis',result);save();self.status=result['status'];return
  development_request=(c._mind.improvement_request() if c._llm_development_enabled and
   c._development_enabled and mind.active() is None else None)
  known_development={r.get('development_request',{}).get('request_id') for r in mind.requests
   if r.get('purpose')=='development' and isinstance(r.get('development_request'),dict)}
  if development_request and development_request['request_id'] not in known_development:
   trigger={'trigger_id':f"development:{development_request['request_id']}",
    'reason':'creature-selected-code-review','goal_id':development_request['goal_id'],
    'evidence_event':development_request['evidence'][-1]}
  elif development_request:trigger=None
  else:trigger=mind.request(c._mind.curriculum.goals,c.time)
  last=c._events[-1] if c._events else None
  rested=(last and last['kind']=='experience' and
   last['payload'].get('executed_action',{}).get('action')==0 and
   last['payload'].get('executed_action',{}).get('target') is None and
   last['payload'].get('outcome',{}).get('status')=='rested' and
   last['payload'].get('outcome',{}).get('completed'))
  if trigger is None and c._llm_dreams_enabled and rested and mind.active() is None:
   last_request_tick=mind.requests[-1]['tick'] if mind.requests else 0
   if c.time-last_request_tick>=256:
    trigger={'trigger_id':f"rest-dream:{last['sequence']}",'reason':'rest-associated-dream',
     'evidence_event':last['sequence'],'rest_event':last['sequence'],'rest_tick':last['tick']}
  if trigger is None:self.status='idle';self.current_purpose=None;return
  purpose=('development' if trigger.get('reason')=='creature-selected-code-review' else
   'dream' if c._llm_dreams_enabled and rested else
   'self-review' if c._llm_self_review_enabled and trigger.get('reason')=='review-lived-trial' else 'analysis')
  if purpose=='dream':trigger={**trigger,'rest_event':last['sequence'],'rest_tick':last['tick']}
  trigger={**trigger,'purpose':purpose}
  job_id=uuid.uuid4().hex
  folder=prepare(c,self.directory/job_id,purpose=purpose,focus=trigger)
  packet=json.loads((folder/'request.json').read_text())
  c._append('hypothesis',{'operation':'request-reflection','request_id':packet['request_id'],'job_id':job_id,
   **{k:v for k,v in trigger.items() if k!='development_request'},
   **({'development_request':development_request} if purpose=='development' else {})})
  save() # Persist intent before the provider can consume resources.
  self.current_purpose=purpose
  self.future=self.pool.submit(self.runner,folder,cancel=self.cancel);self.status='thinking'
 def close(self):
  self.cancel.set();self.pool.shutdown(wait=True)
