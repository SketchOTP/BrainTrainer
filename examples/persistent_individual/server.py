"""One-command local live view; shutdown saves the same individual."""
import argparse
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
import uuid
from pathlib import Path
import signal
import threading
import time

from individual import Individual
from operational_log import append_receipt

ROOT=Path(__file__).resolve().parents[2]
PROGRAM=ROOT/'research/docking-station-20261103/resources/chichi-brain-program.json'
PAGE=Path(__file__).with_name('view.html')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=Path)
    p.add_argument('--seed',type=int,default=0);p.add_argument('--port',type=int)
    p.add_argument('--start-paused',action='store_true',help='Start without advancing until Run or Step')
    group=p.add_mutually_exclusive_group()
    group.add_argument('--experimental-motor-model',action='store_true',help='Use the existing experimental motor model')
    group.add_argument('--experimental-recovery-probe',action='store_true',help='Use the experimental faster-probing motor model')
    group.add_argument('--experimental-confirm-recovery',action='store_true',help='Use the experimental confirmation-based motor model')
    group.add_argument('--experimental-action-prediction',action='store_true',help='Use passive complete-action predictions with the existing motor controller')
    args=p.parse_args()
    motor_mode=args.experimental_motor_model or args.experimental_recovery_probe or args.experimental_confirm_recovery or args.experimental_action_prediction
    if args.state is None:
        filename=('action-prediction-individual.json' if args.experimental_action_prediction else
                  'confirmation-individual.json' if args.experimental_confirm_recovery else
                  'recovery-individual.json' if args.experimental_recovery_probe else
                  'motor-individual.json' if args.experimental_motor_model else 'individual.json')
        args.state=ROOT/'runs/persistent-individual'/filename
    if args.port is None:args.port=46333 if args.experimental_action_prediction else 46332 if args.experimental_confirm_recovery else 46330 if args.experimental_recovery_probe else 46329 if motor_mode else 46328
    if not 1024<=args.port<=65535:p.error('port must be 1024..65535')
    args.state.parent.mkdir(parents=True,exist_ok=True)
    lock_file=args.state.with_name(args.state.name+'.lock').open('a')
    try:fcntl.flock(lock_file,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:p.error('this individual is already open')
    action_observer=None
    if args.experimental_action_prediction:
        from complete_action_prediction import CompleteActionObserver,load_observed
        from inherited_preparation import prepare_inherited,clone_prepared_motor
        from motor_benchmark import MotorIndividual
        if args.state.exists():creature,action_observer=load_observed(args.state)
        else:
            source=MotorIndividual(PROGRAM,seed=args.seed,condition='adaptive')
            prepare_inherited(source,PROGRAM)
            creature=clone_prepared_motor(source,'baseline');action_observer=CompleteActionObserver()
    elif args.experimental_confirm_recovery:
        from confirmation_individual import ConfirmationMotorIndividual
        creature=ConfirmationMotorIndividual.load_motor(args.state) if args.state.exists() else ConfirmationMotorIndividual(PROGRAM,seed=args.seed)
    elif args.experimental_recovery_probe:
        from recovery_individual import RecoveryMotorIndividual
        creature=RecoveryMotorIndividual.load_motor(args.state) if args.state.exists() else RecoveryMotorIndividual(PROGRAM,seed=args.seed)
    elif args.experimental_motor_model:
        from motor_benchmark import MotorIndividual
        creature=MotorIndividual.load_motor(args.state) if args.state.exists() else MotorIndividual(PROGRAM,seed=args.seed,condition='adaptive')
        if creature.condition!='adaptive':p.error('interactive motor model requires an adaptive checkpoint')
    else:creature=Individual.load(args.state) if args.state.exists() else Individual(PROGRAM,seed=args.seed)
    lock=threading.RLock();stop=threading.Event();running=not args.start_paused;latest_motor=None;staged_preview=None
    session_id=str(uuid.uuid4());journal=args.state.with_name(args.state.name+'.lifecycle.jsonl')
    durable_tick=None;worker_error=None;shutdown_signal=None
    def log(event,**fields):
        append_receipt(journal,event,session_id=session_id,pid=os.getpid(),identity=creature.identity,**fields)
    def save():
        nonlocal durable_tick
        if action_observer is not None:
            from complete_action_prediction import save_observed
            save_observed(creature,action_observer,args.state)
        elif motor_mode:creature.save_motor(args.state)
        else:creature.save(args.state)
        # The checkpoint writer fsyncs its temporary file; sync the directory
        # after its atomic rename before advertising this tick as durable.
        directory=os.open(args.state.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
        durable_tick=creature.time
        log('checkpoint_written',durable_tick=durable_tick)
    def tick():
        nonlocal latest_motor,staged_preview
        staged_preview=None
        if action_observer is None:creature.tick()
        else:
            observed=action_observer.tick(creature)
            # Persist the reconciled action/model state before journaling its
            # events. A process crash can still occur between the two files;
            # the journal is observational, not an atomic transaction log.
            if observed['action_prediction_events']:save()
            for event in observed['action_prediction_events']:
                log('action_prediction',action_prediction=event)
        if motor_mode and creature.motor_records:
            latest_motor=creature.motor_records[-1];creature.motor_records.clear()
    log('session_started',restored=args.state.exists(),initial_tick=creature.time)
    save()

    class Handler(BaseHTTPRequestHandler):
        def respond(self,status,body,kind='application/json'):
            data=body if isinstance(body,bytes) else json.dumps(body,allow_nan=False).encode()
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
        def valid_host(self):
            return self.headers.get('Host')==f'127.0.0.1:{args.port}'
        def do_GET(self):
            if not self.valid_host():return self.respond(403,{'error':'invalid host'})
            if self.path=='/':return self.respond(200,PAGE.read_bytes(),'text/html; charset=utf-8')
            if self.path!='/state':return self.respond(404,{'error':'not found'})
            with lock:
                self.respond(200,{'identity':creature.identity,'time':creature.time,'running':running,
                    'position':creature.position,'energy':creature.energy,'hunger':creature.hunger,
                    'objects':list(creature.objects.values()),'event':creature.last_event,
                    'active_action':creature.active_action,'pending_count':len(creature.pending),
                    'last_durable_tick':durable_tick,'lifecycle_log':str(journal),'worker_error':worker_error,
                    'action_prediction':{'pending':[{k:v for k,v in p['forecast'].items() if not k.startswith('_')} for p in action_observer.pending.values()],
                                         'latest_forecast':action_observer.latest_forecast,'latest_terminal':action_observer.latest_terminal,
                                         'preview':staged_preview['forecast'] if staged_preview is not None else None}
                                         if action_observer is not None else None,
                    'motor':{'body_strength':creature.body_strength,'reserve':creature.reserve,'last':latest_motor,
                             'model':'confirmation' if args.experimental_confirm_recovery else 'recovery-probe' if args.experimental_recovery_probe else 'baseline'}
                    if motor_mode else None})
        def do_POST(self):
            nonlocal running,staged_preview
            if not self.valid_host() or self.headers.get('Origin') not in (None,f'http://127.0.0.1:{args.port}'):
                return self.respond(403,{'error':'invalid origin or host'})
            if self.headers.get_content_type()!='application/json':return self.respond(415,{'error':'expected JSON'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length<0 or length>4096:raise ValueError('invalid request size')
                body=json.loads(self.rfile.read(length) or b'{}')
                with lock:
                    if self.path=='/place':
                        creature.place(body['identity'],body['x'],body.get('visible',True));staged_preview=None
                    elif self.path=='/running':
                        if type(body['running']) is not bool:raise ValueError('invalid running state')
                        running=body['running'];staged_preview=None
                    elif self.path=='/tick':
                        if action_observer is None:tick()
                        else:
                            from preview_action import preview_next_action,state_token
                            if staged_preview is not None and state_token(creature,action_observer)==staged_preview['state_token']:
                                tick()
                            else:
                                staged_preview=preview_next_action(creature,action_observer)
                                if staged_preview['forecast'] is None:tick()
                    elif self.path=='/recharge' and motor_mode:
                        creature.reserve=100.0;staged_preview=None
                    elif self.path=='/body' and motor_mode:
                        strength=body['strength']
                        if isinstance(strength,bool) or not isinstance(strength,(int,float)) or not math.isfinite(strength) or not 0<=strength<=1:
                            raise ValueError('strength must be a finite number from 0 to 1')
                        creature.body_strength=float(strength);staged_preview=None
                    elif self.path!='/save':return self.respond(404,{'error':'not found'})
                    save()
                self.respond(200,{'ok':True})
            except (KeyError,ValueError,TypeError,json.JSONDecodeError) as error:self.respond(400,{'error':str(error)})
        def log_message(self,fmt,*args):return

    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    def worker():
        nonlocal running,worker_error,staged_preview
        while not stop.wait(.25):
            preview=None
            with lock:
                if running:
                    try:
                        if action_observer is None:tick()
                        else:
                            from preview_action import preview_next_action
                            candidate=preview_next_action(creature,action_observer)
                            if candidate['forecast'] is None:tick()
                            else:staged_preview=preview=candidate
                        if preview is None and creature.time%20==0:save()
                    except Exception as error:
                        running=False;worker_error=type(error).__name__+': '+str(error)
                        log('worker_failed',error_type=type(error).__name__,tick=creature.time,durable_tick=durable_tick)
            if preview is not None and not stop.wait(1.5):
                with lock:
                    if running and staged_preview is preview:
                        try:
                            from preview_action import state_token
                            if state_token(creature,action_observer)==preview['state_token']:
                                tick()
                                if creature.time%20==0:save()
                            else:staged_preview=None
                        except Exception as error:
                            running=False;worker_error=type(error).__name__+': '+str(error)
                            log('worker_failed',error_type=type(error).__name__,tick=creature.time,durable_tick=durable_tick)
    thread=threading.Thread(target=worker,daemon=True);thread.start()
    def shutdown(signum,frame):
        nonlocal shutdown_signal
        shutdown_signal=signum
        log('shutdown_requested',signal=signum,tick=creature.time,durable_tick=durable_tick)
        stop.set();threading.Thread(target=server.shutdown,daemon=True).start()
    old_int=signal.signal(signal.SIGINT,shutdown);old_term=signal.signal(signal.SIGTERM,shutdown)
    print(f'Creature {creature.identity}: http://127.0.0.1:{args.port}  (Ctrl+C saves)',flush=True)
    error_type=None
    try:server.serve_forever(poll_interval=.2)
    except BaseException as error:
        error_type=type(error).__name__
        log('server_error',error_type=error_type,tick=creature.time,durable_tick=durable_tick)
        raise
    finally:
        stop.set();thread.join();
        with lock:save()
        log('server_shutdown',signal=shutdown_signal,error_type=error_type,tick=creature.time,durable_tick=durable_tick,exit_status='unobserved')
        server.server_close();lock_file.close();signal.signal(signal.SIGINT,old_int);signal.signal(signal.SIGTERM,old_term)


if __name__=='__main__':main()
