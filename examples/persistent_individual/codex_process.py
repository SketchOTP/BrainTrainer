"""Owned Codex subprocess lifetime shared by reflection and asset workers."""
import os,signal,subprocess,time

def execute(command,directory,*,timeout,cancel=None):
 env=os.environ.copy()
 for key in ('OPENAI_API_KEY','CODEX_API_KEY'):env.pop(key,None)
 with (directory/'events.jsonl').open('xb') as output,(directory/'stderr.log').open('xb') as error:
  child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=output,stderr=error,
   cwd=directory,env=env,start_new_session=True)
  try:
   deadline=time.monotonic()+timeout;data=(directory/'prompt.txt').read_bytes()
   while True:
    if cancel is not None and cancel.is_set():raise RuntimeError('Codex worker cancelled by owner shutdown')
    remaining=deadline-time.monotonic()
    if remaining<=0:raise TimeoutError('Codex worker deadline exceeded')
    try:child.communicate(data,timeout=min(.25,remaining));break
    except subprocess.TimeoutExpired:data=None
  except BaseException:
   if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
   child.communicate();raise
 return child.returncode
