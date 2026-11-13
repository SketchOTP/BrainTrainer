"""Launch the local server and record the child process status actually observed.

Pass server options after ``--``, for example ``-- --experimental-confirm-recovery``.
The launcher can report only exits it observes; a killed launcher cannot record
its own exit, and absence of a child-exit record is not evidence of any cause.
"""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import uuid
from operational_log import append_receipt

ROOT=Path(__file__).resolve().parents[2]
SERVER=Path(__file__).with_name('server.py')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--process-log',type=Path,default=ROOT/'runs/persistent-individual/process-observations.jsonl')
    p.add_argument('server_args',nargs=argparse.REMAINDER)
    args=p.parse_args();server_args=args.server_args
    if server_args and server_args[0]=='--':server_args=server_args[1:]
    session_id=str(uuid.uuid4());child=subprocess.Popen([sys.executable,str(SERVER),*server_args],start_new_session=True)
    append_receipt(args.process_log,'child_started',session_id=session_id,launcher_pid=os.getpid(),child_pid=child.pid)
    def forward(signum,frame):
        append_receipt(args.process_log,'signal_forwarded',session_id=session_id,child_pid=child.pid,signal=signum)
        if child.poll() is None:
            try:child.send_signal(signum)
            except ProcessLookupError:pass
    old={sig:signal.signal(sig,forward) for sig in (signal.SIGINT,signal.SIGTERM)}
    try:
        status=child.wait()
        append_receipt(args.process_log,'child_exit_observed',session_id=session_id,child_pid=child.pid,returncode=status)
        return status if status>=0 else 128-status
    finally:
        for sig,handler in old.items():signal.signal(sig,handler)

if __name__=='__main__':raise SystemExit(main())
