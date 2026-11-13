"""Local original pet presentation of the genome-driven research simulation.

Run: python -m creature_brain.pet --open
No offline progression: closing the server suspends the saved creature. Buttons
change its world or offer teaching cues; only its genome brain chooses motors.
"""
from __future__ import annotations

import argparse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import signal
import secrets
import tempfile
import threading
import time
from urllib.parse import urlsplit
import webbrowser

from .body import DEFAULT_BRAIN, DEFAULT_GENOME
from .simulation import Simulation, make_demo
from .world import WorldObject
from . import vision

ASSETS = Path(__file__).with_name('pet_web')
MODEL = 'standalone-pet-session-v1'
ACTIONS = {0:'Looking',1:'Pushing',2:'Pulling',3:'Deactivating',4:'Approaching',
           5:'Retreating',6:'Picking up',7:'Dropping',8:'Expressing',9:'Resting',
           10:'Going left',11:'Going right',12:'Eating',13:'Hitting'}


def pet_name(value):
    if not isinstance(value,str) or not 1 <= len(value.strip()) <= 32 or not all(c.isprintable() for c in value):
        raise ValueError('Use a name with 1–32 printable characters.')
    return value.strip()


def new_simulation(seed=7):
    simulation=make_demo(DEFAULT_BRAIN,physiology_genome=DEFAULT_GENOME,count=1,
                         seed=seed,dt=.2,timing_profile='docking-nominal')
    # An original gentle habitat, rather than the benchmark's hazard course.
    for key in ('danger','toxic-food'):
        simulation.world.objects.pop(key,None)
    simulation.world.enable_pet_habitat()
    simulation.autonomy_mode='learned'
    return simulation


class _TickSchedule:
    """Monotonic deadlines: processing consumes the period, never a backlog."""
    def __init__(self, period, now):
        self.period=period;self.deadline=now+period;self.lag=0.0

    def delay(self, now):return max(0.0,self.deadline-now)

    def complete(self, started, finished, advanced):
        self.lag=max(0.0,started-self.deadline,finished-self.deadline-self.period) if advanced else 0.0
        if not advanced or finished>=self.deadline+self.period:
            self.deadline=finished+self.period
        else:self.deadline+=self.period


class PetSession:
    """Serializes browser actions, simulation ticks and checkpoint snapshots."""
    def __init__(self, simulation, path, *, name='Moss', paused=False, events=(), last_survival_cue=None):
        if len(simulation.creatures)!=1:
            raise ValueError('The pet habitat requires exactly one creature.')
        creature=next(iter(simulation.creatures.values()))
        if (getattr(creature.body,'MODEL',None)!='genome-physiology-v1'
                or not math.isclose(simulation.dt,.2,abs_tol=1e-12)
                or not math.isclose(creature.body.kernel.tick_seconds,.2,abs_tol=1e-12)):
            raise ValueError('The pet requires the genome body and nominal 0.2-second cadence.')
        if type(paused) is not bool:
            raise ValueError('Invalid paused flag.')
        if not isinstance(events,(list,tuple)) or len(events)>12 or any(not isinstance(e,str) or len(e)>180 for e in events):
            raise ValueError('Invalid pet event history.')
        validated_name=pet_name(name)
        simulation.world.enable_pet_habitat()
        self.simulation=simulation; self.path=Path(path); self.name=validated_name
        self.paused=paused; self.events=deque(events,maxlen=12)
        self.journal=deque(maxlen=80)
        self.last_survival_cue=(dict(last_survival_cue) if isinstance(last_survival_cue,dict)
                                and isinstance(last_survival_cue.get('need'),str)
                                and isinstance(last_survival_cue.get('target'),str)
                                and isinstance(last_survival_cue.get('time'),(int,float)) else None)
        self.lock=threading.RLock();self.stop_event=threading.Event()
        self.thread=None;self.last_frame=None;self.error=None;self.last_saved=None;self.clock_lag=0.0
        self._journal_signature=None
        self._research_cached_at=0.0;self._research_cache=None

    @classmethod
    def open(cls,path,*,name='Moss',seed=7):
        path=Path(path)
        if not path.exists():return cls(new_simulation(seed),path,name=name)
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or data.get('model')!=MODEL or data.get('schema')!=1:
            raise ValueError('Unrecognized pet checkpoint; the existing file was preserved.')
        simulation=Simulation.from_dict(data['simulation'])
        # Pre-learning pet saves used the scripted curiosity adapter. Keep
        # its saved state, but start the upgraded pet in learned-recall mode.
        if 'autonomy_mode' not in data['simulation']:simulation.autonomy_mode='learned'
        return cls(simulation,path,name=data['name'],
                   paused=data['paused'],events=data['events'],
                   last_survival_cue=data.get('last_survival_cue'))._load_journal(data.get('journal',()))

    def _load_journal(self, entries):
        if isinstance(entries,list):
            for row in entries[-self.journal.maxlen:]:
                if (isinstance(row,dict) and isinstance(row.get('time'),(int,float))
                        and isinstance(row.get('text'),str)):
                    self.journal.append(dict(row))
        if self.journal:
            row=self.journal[-1]
            self._journal_signature=(row.get('outcome'),row.get('target'),row.get('detail'))
        return self

    @property
    def identity(self):return next(iter(self.simulation.creatures))

    def _event(self,message):self.events.append(message)

    def snapshot(self):
        with self.lock:
            sim=self.simulation;c=sim.creatures[self.identity];p=sim.world.agents[self.identity]
            f=self.last_frame or {}
            sleeping=c.body.sleep_state!='awake'
            return {'name':self.name,'paused':self.paused,'error':self.error,
                    'saved':self.last_saved,'clock_lag':self.clock_lag,'step':sim.steps,'time':sim.world.time,'dt':sim.dt,
                    'alive':c.body.alive,'sleep':c.body.sleep_state,
                    'action':'Sleeping' if sleeping else ACTIONS.get(f.get('action'),'Observing'),
                    'outcome':'sleeping' if sleeping else f.get('outcome','ready'),
                    'intention':None if sleeping else f.get('intention'),
                    'habitat_event':None if sleeping else f.get('habitat_event'),
                    'target':None if sleeping else f.get('target'),'carrying':p.carrying,'drives':list(c.body.drives),
                    'body_metrics':self._body_metrics(c.body,p,sim.world,self.identity),
                    'memory':{'observations':c.experience.total_observations,
                              'retained':len(c.experience.episodes),'recent':list(c.experience.episodes)[-5:],
                              'visual_examples':len(c.experience.visual_examples),
                              'learned_associations':len(c.experience.associations),
                              'mode':sim.autonomy_mode},
                    'progress':{'brain_ticks':c.brain.tick_count,'simulated_hours':sim.world.time/3600,
                                'actions':sum(sim.actions.values()),'eating_events':sim.outcomes.get('ate',0),
                                'play_events':sim.outcomes.get('played',0),
                                'discovered_items':sum(o.discoveries for o in sim.world.objects.values()),
                                'carried_items':int(p.carrying is not None),
                                'items_stored':sum(len(o.storage) for o in sim.world.objects.values()),
                                'decorations':sum(len(o.decorations) for o in sim.world.objects.values())},
                    'journal':list(self.journal),
                    'last_survival_cue':dict(self.last_survival_cue) if self.last_survival_cue else None,
                    'research':self._latest_research(),
                    'learning_limits':{'growth_stages':False,'construction':False,'crafting':False,
                                       'self_chosen_goals':False,'code_promotion':'manual'},
                    'pet':{'x':p.x,'y':p.y,'heading':p.heading,
                           'moving':f.get('outcome')=='moved' and not self.paused and c.body.alive and c.body.sleep_state=='awake'},'world':{'width':sim.world.width,'height':sim.world.height,'visual_palette':vision.PALETTE},
                    'objects':[{'id':o.object_id,'x':o.x,'y':o.y,'kind':o.kind,
                                'quantity':o.quantity,'holder':o.holder,'category':o.category,
                                'stored_in':o.stored_in,'visual':vision.pixels_for(o)}
                               for o in sim.world.objects.values() if o.enabled and o.kind in ('food','toy','home','trinket','danger')],
                    'habitat':sim.world.habitat_snapshot(self.identity),'events':list(self.events)}

    @staticmethod
    def _body_metrics(body, pose, world, identity):
        chemicals=body.chemicals
        def nearest(rows):
            rows=[(math.hypot(row['x']-pose.x,row['y']-pose.y),row) for row in rows]
            if not rows:return None
            distance,row=min(rows,key=lambda pair:pair[0])
            return {'id':row.get('object_id',row.get('id')),'label':row.get('label',row.get('object_id','resource').replace('-',' ')),
                    'distance':round(distance,1),'x':row['x'],'y':row['y']}
        food=[{'object_id':o.object_id,'x':o.x,'y':o.y} for o in world.objects.values()
              if o.enabled and o.kind=='food' and o.quantity>0 and o.stored_in is None and o.holder in (None,identity)]
        features=(world.habitat or {}).get('features',())
        feature_labels={f['id']:f['label'] for f in features}
        bushes=[{'object_id':o.object_id,'label':feature_labels.get(o.object_id,o.object_id.replace('-',' ')),
                 'x':o.x,'y':o.y} for o in world.objects.values()
                if o.enabled and o.kind=='bush' and o.quantity>0]
        water=[f for f in features if f['kind']=='water']
        shelter=[f for f in features if f['kind']=='shelter']
        companions=[{'object_id':key,'x':other.x,'y':other.y} for key,other in world.agents.items() if key!=identity and other.active]
        return {'food_drives':list(body.drives[1:4]),'tired_drive':body.drives[6],
                'sleep_drive':body.drives[7],'company_drive':body.drives[8],
                'cold_drive':body.drives[4],'hot_drive':body.drives[5],
                'water_reserve':chemicals[33],'energy_reserve':chemicals[34],
                'atp':chemicals[35],'health':body.health,
                'sleep_state':body.sleep_state,'temperature':body.temperature,
                'digital_identity':'simulated creature','companions':len(companions),
                'resources':{'food':nearest(food),'food_count':len(food),
                             'foraging':nearest(bushes),'foraging_count':len(bushes),
                             'water':nearest(water),'shelter':nearest(shelter),
                             'companion':nearest(companions)}}

    def _latest_research(self):
        now=time.monotonic()
        if self._research_cache is not None and now-self._research_cached_at<10:
            return self._research_cache
        root=Path(__file__).resolve().parents[2]/'runs'/'self-improvement'
        choices=sorted(root.glob('*/result.json'),key=lambda p:p.parent.name,reverse=True)
        result=None
        for path in choices:
            try:
                row=json.loads(path.read_text(encoding='utf-8'))
                tests=path.parent/'tests.log'
                count=None
                if tests.is_file():
                    for line in tests.read_text(encoding='utf-8',errors='replace').splitlines():
                        if line.startswith('Ran ') and ' tests in ' in line:
                            count=int(line.split()[1]);break
                benchmark_path=path.parent/'candidate'/'runs'/'retention'/'baseline.json'
                benchmark=None
                if benchmark_path.is_file():
                    data=json.loads(benchmark_path.read_text(encoding='utf-8'))
                    benchmark={'completed_seeds':data['aggregate']['completed_seeds'],
                               'failed_seeds':data['aggregate']['failed_seeds'],
                               'mean_eating_difference':data['aggregate']['mean_paired_eating_event_difference'],
                               'zero_exposure_seeds':len(data['aggregate']['seeds_without_successful_training_exposure'])}
                result={'run_id':path.parent.name,'status':row.get('status'),
                        'proposal_model':row.get('proposal_model'),
                        'implementation_model':row.get('implementation_model'),
                        'tests_passed':count if row.get('checks_exit_code')==0 else None,
                        'candidate_promoted':bool(row.get('promoted',False)),
                        'benchmark':benchmark}
                break
            except (OSError,ValueError,KeyError,TypeError):
                continue
        self._research_cache=result;self._research_cached_at=now
        return result

    def action(self,data):
        if not isinstance(data,dict):raise ValueError('Expected an action object.')
        with self.lock:
            operation=data.get('action');sim=self.simulation;c=sim.creatures[self.identity]
            if self.error:raise ValueError('The simulation failed; the last valid checkpoint was preserved.')
            if operation=='rename':
                self.name=pet_name(data.get('name'));self._event('Named '+self.name+'.')
            elif operation=='pause':
                if type(data.get('paused')) is not bool:raise ValueError('Expected a paused flag.')
                if not data['paused'] and (self.error or not c.body.alive):
                    raise ValueError('This session cannot resume. Its checkpoint remains available.')
                self.paused=data['paused'];self._event('Habitat paused.' if self.paused else 'Habitat resumed.')
            elif operation=='save':pass
            elif operation=='autonomy':
                mode=data.get('mode')
                if mode not in ('learned','scripted'):raise ValueError('Unknown exploration mode.')
                sim.autonomy_mode=mode
                self._event('Using learned recall.' if mode=='learned' else 'Using guided exploration.')
            elif operation in ('feed','play','rest','feature'):
                if not c.body.alive:raise ValueError('This creature has died. Its checkpoint remains available.')
                p=sim.world.agents[self.identity]
                if operation=='feature':
                    feature_id,cue_id=data.get('feature'),data.get('cue')
                    if not isinstance(feature_id,str) or not isinstance(cue_id,str):raise ValueError('Choose a place and an advertised cue.')
                    sim.offer_feature(self.identity,feature_id,cue_id)
                    feature=next(f for f in sim.world.habitat_snapshot(self.identity)['features'] if f['id']==feature_id)
                    cue=next(c for c in feature['cues'] if c['id']==cue_id)
                    self._event('Offered '+cue['label'].lower()+' at '+feature['label']+'. The brain chooses its response.')
                elif operation=='rest':
                    sim.offer_feature(self.identity,'habitat-hut','sleep')
                    self._event('Offered a shelter rest cue. The brain chooses its response.')
                else:
                    recipe=data.get('food','meal')
                    if operation=='feed' and recipe not in ('seed','fruit','meal'):
                        raise ValueError('Unknown food.')
                    key='keeper-toy' if operation=='play' else 'keeper-'+recipe
                    category=21 if operation=='play' else {'seed':3,'fruit':8,'meal':11}[recipe]
                    kind='toy' if operation=='play' else 'food'
                    x=min(sim.world.width,max(0,p.x+.55));y=p.y
                    obj=sim.world.objects.get(key)
                    if obj is None:
                        obj=WorldObject(key,category,x,y,kind=kind,quantity=1,initial_quantity=3)
                        sim.world.add_object(obj)
                    else:
                        if obj.holder is None:obj.x,obj.y=x,y
                        obj.quantity=min(3,obj.quantity+1);obj.enabled=True
                    self._event('Placed a toy nearby.' if operation=='play' else 'Placed '+recipe+' nearby. Eating remains its choice.')
            else:raise ValueError('Unknown pet action.')
            self.save()
            return self.snapshot()

    def tick_once(self):
        with self.lock:
            if self.paused or self.error:return False
            frame=self.simulation.step()
            self.last_frame=frame['creatures'][0]
            intent=self.last_frame.get('intention')
            if isinstance(intent,dict) and intent.get('source')=='survival-affordance':
                self.last_survival_cue={'need':intent.get('need','survival'),
                                        'target':intent.get('target',''),
                                        'time':round(self.simulation.world.time,1),
                                        'step':self.simulation.steps}
            self._record_activity(self.last_frame)
            if not self.simulation.creatures[self.identity].body.alive:
                self.paused=True;self._event('The creature died; its final state is preserved.')
                self.save()
            return True

    def _record_activity(self, frame):
        outcome=frame.get('outcome','idle');target=frame.get('target')
        detail=frame.get('habitat_event')
        body=self.simulation.creatures[self.identity].body
        if outcome=='sleeping':
            detail=body.sleep_state
            signature=('sleeping',None,detail)
            if signature==self._journal_signature:return
            self._journal_signature=signature
            self.journal.append({'time':round(self.simulation.world.time,1),'step':self.simulation.steps,
                                 'action':'Sleeping','outcome':'sleeping','target':None,
                                 'detail':detail,'text':'Sleeping · '+detail.upper(),
                                 'memory_count':self.simulation.creatures[self.identity].experience.total_observations})
            return
        signature=(outcome,target,detail)
        if outcome in ('moved','idle','looked') and target is None and not detail:
            return
        if signature==self._journal_signature:
            return
        self._journal_signature=signature
        feature=next((f for f in (self.simulation.world.habitat or {}).get('features',())
                      if f['id']==target),None)
        obj=self.simulation.world.objects.get(target) if target else None
        where=feature['label'] if feature else obj.object_id.replace('-',' ') if obj else target
        action=ACTIONS.get(frame.get('action'),'Observing')
        if detail:
            text=str(detail)
        elif where:
            text=f'{action} {where} · {outcome.replace("-"," ")}'
        else:
            text=f'{action} · {outcome.replace("-"," ")}'
        self.journal.append({'time':round(self.simulation.world.time,1),'step':self.simulation.steps,
                             'action':action,'outcome':outcome,'target':target,
                             'detail':detail,'text':text,
                             'memory_count':self.simulation.creatures[self.identity].experience.total_observations})

    def save(self):
        with self.lock:
            data={'model':MODEL,'schema':1,'name':self.name,'paused':self.paused,
                  'events':list(self.events),'journal':list(self.journal),
                  'last_survival_cue':dict(self.last_survival_cue) if self.last_survival_cue else None,
                  'simulation':self.simulation.to_dict()}
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,
                                                 prefix=self.path.name+'.',suffix='.tmp',delete=False) as output:
                    temporary=Path(output.name)
                    json.dump(data,output,allow_nan=False,separators=(',',':'));output.write('\n')
                    output.flush();os.fsync(output.fileno())
                os.replace(temporary,self.path);temporary=None
                self.last_saved=time.strftime('%H:%M:%S')
            finally:
                if temporary is not None:temporary.unlink(missing_ok=True)

    def start(self):
        if self.thread is not None:raise RuntimeError('Pet clock already started.')
        self.thread=threading.Thread(target=self._run,name='pet-simulation',daemon=False)
        self.thread.start()

    def _run(self):
        last_save=time.monotonic();schedule=_TickSchedule(self.simulation.dt,last_save)
        while not self.stop_event.wait(schedule.delay(time.monotonic())):
            started=time.monotonic()
            try:
                advanced=self.tick_once()
                if time.monotonic()-last_save>=15:
                    self.save();last_save=time.monotonic()
                schedule.complete(started,time.monotonic(),advanced)
                with self.lock:self.clock_lag=schedule.lag
            except Exception as error:
                with self.lock:
                    self.error='Simulation paused: '+str(error);self.paused=True
                # Keep the last valid on-disk checkpoint if a tick failed.
                return

    def close(self):
        self.stop_event.set()
        if self.thread is not None:self.thread.join()
        # A failed mutation may be incomplete; retain the last valid save.
        if self.error is None:self.save()


def make_server(session,port=8765):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,data,content_type='application/json; charset=utf-8'):
            body=json.dumps(data,allow_nan=False).encode() if isinstance(data,dict) else data
            self.send_response(status);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def valid_host(self):
            port=self.server.server_address[1]
            return self.headers.get('Host') in ('127.0.0.1:'+str(port),'localhost:'+str(port))
        def do_GET(self):
            if not self.valid_host():self.reply(403,{'error':'Invalid local host.'});return
            path=urlsplit(self.path).path
            if path=='/api/state':self.reply(200,dict(session.snapshot(),control_token=token));return
            file={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8'),
                  '/app.js':('app.js','text/javascript; charset=utf-8'),
                  '/habitat.png':('habitat.png','image/png'),
                  '/moss-detailed-v1.png':('moss-detailed-v1.png','image/png'),
                  '/moss-robot-v1.png':('moss-robot-v1.png','image/png'),
                  '/moss-animated-v1.png':('moss-animated-v1.png','image/png')}.get(path)
            if file is None:self.reply(404,{'error':'Not found.'});return
            self.reply(200,(ASSETS/file[0]).read_bytes(),file[1])
        def do_POST(self):
            if not self.valid_host():self.reply(403,{'error':'Invalid local host.'});return
            if not secrets.compare_digest(self.headers.get('X-Pet-Token',''),token):
                self.reply(403,{'error':'Missing local control token.'});return
            if self.path!='/api/action':self.reply(404,{'error':'Not found.'});return
            origin=self.headers.get('Origin')
            expected='http://'+self.headers.get('Host','')
            if self.headers.get('Sec-Fetch-Site')=='cross-site' or (origin is not None and origin!=expected):
                self.reply(403,{'error':'Only this local page can change the pet.'});return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=4096:raise ValueError('Invalid action size.')
                if self.headers.get_content_type()!='application/json':raise ValueError('Expected JSON.')
                data=json.loads(self.rfile.read(length))
                self.reply(200,session.action(data))
            except (ValueError,KeyError,TypeError) as error:self.reply(400,{'error':str(error)})
            except OSError:self.reply(500,{'error':'Checkpoint could not be saved.'})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True
    return server


def main(argv=None):
    parser=argparse.ArgumentParser(description='Original local pet with a genome-driven research brain.')
    parser.add_argument('--checkpoint',type=Path,default=Path.home()/'.local/state/creature-brain/pet.json')
    parser.add_argument('--name',default='Moss',help='Name for a new pet; existing saved names are retained.')
    parser.add_argument('--seed',type=int,default=7);parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--open',action='store_true',help='Open the local browser page.')
    args=parser.parse_args(argv)
    if not 0<=args.port<=65535:parser.error('port must be 0–65535')
    # Linux/POSIX file lock prevents two processes advancing the same saved pet.
    import fcntl
    args.checkpoint.parent.mkdir(parents=True,exist_ok=True)
    with args.checkpoint.with_suffix(args.checkpoint.suffix+'.lock').open('a') as owner:
        try:fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:parser.exit(1,'That pet checkpoint is already open in another process.\n')
        try:session=PetSession.open(args.checkpoint,name=args.name,seed=args.seed)
        except (ValueError,KeyError,TypeError,OSError) as error:parser.exit(1,str(error)+'\n')
        server=None
        try:
            server=make_server(session,args.port);session.save();session.start()
            url='http://127.0.0.1:'+str(server.server_address[1])+'/'
            print('Pet habitat: '+url+'\nCheckpoint: '+str(args.checkpoint)+'\nClose with Ctrl+C; closed habitats do not advance.',flush=True)
            if args.open:webbrowser.open(url)
            def stop(*_):raise KeyboardInterrupt
            signal.signal(signal.SIGTERM,stop)
            server.serve_forever(poll_interval=.2)
        except KeyboardInterrupt:pass
        finally:
            if server is not None:server.server_close()
            session.close()


if __name__=='__main__':main()
