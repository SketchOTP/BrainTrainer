"""Visible local habitat for one continuing developmental companion."""
import argparse
from copy import deepcopy
import ipaddress
from urllib.parse import urlsplit
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import signal
import threading
from continuing_companion import ContinuingCompanion
from habitat_store import HabitatStore
from world_body import map_url
from garden import environment_contract
from creature_brain.development import supports

ROOT=Path(__file__).resolve().parents[2]
PROGRAM=ROOT/'research/docking-station-20261103/resources/chichi-brain-program.json'
PAGE=Path(__file__).with_name('habitat.html')
# One catalog owns the offered object behavior and its presentation.
DEVICES={
    'switch':{'label':'Light switch','function':'switch','delay':4},
    'counter':{'label':'Counting stone','function':'counter','delay':4},
    'responsive-lantern':{'label':'Two-press lantern','function':'delayed-switch','delay':2},
    'delayed-switch':{'label':'Patient lantern','function':'delayed-switch','delay':4},
    'inert':{'label':'Quiet stone','function':'inert','delay':4},
}


class Habitat:
    def __init__(self,directory,seed=0,*,reflect=False,generate_assets=False):
        self.store=HabitatStore(directory)
        try:
            if self.store.current.exists():self.creature=self.store.load()
            else:
                # Never recreate over a directory containing recovery evidence.
                if self.store.previous.exists() or list(self.store.directory.glob('pending-*.json')) or (self.store.history.exists() and any(self.store.history.iterdir())):
                    raise ValueError('current checkpoint missing; inspect recovery files before creating an individual')
                self.creature=ContinuingCompanion(PROGRAM,seed=seed)
                self.creature.enable_development(actor='habitat-initialization')
                self.creature.enable_recall(actor='habitat-initialization')
                self.save()
        except BaseException:
            self.store.close();raise
        self.lock=threading.RLock();self.running=False;self.error=None
        self.durable_tick=self.creature.time
        self._processing=None
        self.reflection=None
        if reflect:
            from reflection_scheduler import ReflectionScheduler
            self.reflection=ReflectionScheduler(self.store.directory/'reflections')
        self.asset_scheduler=None
        if generate_assets:
            from visual_asset_requests import AssetRequestScheduler
            self.asset_scheduler=AssetRequestScheduler(self.store.directory/'asset-jobs')
        self._published_state=deepcopy(self.state())

    def save(self):
        self.store.save(self.creature)
        self.durable_tick=self.creature.time
        self.error=None

    def tick(self):
        self._published_state=deepcopy(self.state())
        self._processing='evaluating-practice-candidates' if self.creature._mind.improvement_request() else 'advancing-and-saving'
        try:
            if self.reflection:self.reflection.poll(self.creature,self.save)
            self.creature.tick();self.save()
            if self.asset_scheduler:
                try:self.asset_scheduler.poll(self.creature)
                except Exception as exc:self.asset_scheduler.status=f'request-error: {type(exc).__name__}: {exc}'
        except Exception as exc:
            self.running=False;self.error=f'{type(exc).__name__}: {exc}'
            raise
        finally:
            self._published_state=deepcopy(self.state())
            self._processing=None

    def read_state(self):
        if self.lock.acquire(blocking=False):
            try:
                result=deepcopy(self.state())
                self._published_state=result
                return deepcopy(result)
            finally:self.lock.release()
        result=deepcopy(self._published_state)
        result.update(state_is_snapshot=True,processing=self._processing or 'updating-and-saving')
        return result

    def state(self):
        c=self.creature;host=c._host;review=c.self_review()
        unresolved={g['id'] for g in review.get('learning_goals',[]) if g['status']=='effect-unresolved-review-needed'}
        answered={g['goal_id'] for g in review.get('guidance_history',[])}
        requests=[r for r in review.get('assistance_requests',[]) if r['goal_id'] in unresolved and (r['operation']!='request-practice-help' or r['goal_id'] not in answered)]
        recovery_unresolved={g['id'] for g in review.get('maintenance_goals',[]) if g['status']=='recovery-needs-investigation'}
        requests=[r for r in review.get('recovery_requests',[]) if r['goal_id'] in recovery_unresolved]+requests
        motion_unresolved={g['id'] for g in review.get('world_motion_reviews',[]) if g['status']=='motion-unresolved'}
        requests=[r for r in review.get('world_motion_requests',[]) if r['goal_id'] in motion_unresolved]+requests
        # Full source/test histories remain in the checkpoint; UI uses concise projections.
        return {'identity':c.identity,'branch':c._lineage['branch_id'],'context':c._lineage['context'],
            'branch_parent':c._lineage['parent'],'tick':c.time,
            'running':self.running,'durable_tick':self.durable_tick,'error':self.error,
            'reflection_status':self.reflection.status if self.reflection else 'disabled',
            'asset_generation_status':self.asset_scheduler.status if self.asset_scheduler else 'disabled',
            'reflections':[{'status':r['status'],'summary':r.get('reflection',{}).get('summary'),
                'objective':r.get('reflection',{}).get('next_goal',{}).get('objective'),
                'reason':r.get('reason'),'event':r['event']} for r in review.get('reflection_results',[])[-2:]],
            'world':({**host.world,'x':host.position,'map_url':map_url(host.world['pack_sha256'])} if host.world is not None else None),
            'world_trace':[{'tick':e['tick'],**e['payload']['world_motion']} for e in c._events[-16:] if e['kind']=='experience' and 'world_motion' in e['payload']],
            'position':host.position,'energy':host.energy,'hunger':host.hunger,'reserve':host.reserve,
            'objects':list(host.objects.values()),'environment_objects':environment_contract(host),'event':host.last_event,
            'device_catalog':[{'id':key,'label':value['label']} for key,value in DEVICES.items()],
            'development_updates':[{'request_id':r['request_id'],'retained':r['selected_sha256'] is not None,
                'candidate_count':len(r['candidates']),
                'rejected_count':sum(not candidate['passed'] for candidate in r['candidates']),
                'accepted_test_count':sum(len(candidate['cases']) for candidate in r['candidates'] if candidate['sha256']==r['selected_sha256']),
                'scope':r['scope'],'evidence_kind':r['evidence_kind']}
                for r in review.get('development_results',[])[-3:]],
            'goals':review.get('maintenance_goals',[])+review.get('learning_goals',[])+review.get('exploration_goals',[])+review['goals'],
            'development_model':review['model'],'reflective_trials':review.get('reflective_trials',[]),'rest_enabled':host.rest_enabled,
            'rest_evidence':review.get('rest_evidence',[]),
            'shared_activity_enabled':'shared_invitations' in review,
            'companion_available':review.get('companion_available',False),
            'shared_invitations':review.get('shared_invitations',[]),
            'requests':requests,'guidance':review.get('guidance_history',[]),
            'investigation_response_enabled':supports(review['model'],'investigation_response'),
            'investigation_reports':review.get('investigation_reports',[]),
            'skills':review.get('skills',[]),'dream_count':review['dream_count'],
            'revision_count':sum(r['selected_sha256'] is not None for r in review.get('development_results',[])),
            'event_count':len(c._events),'event_capacity':c._capacity,
            'recent_events':[{'sequence':e['sequence'],'tick':e['tick'],'kind':e['kind'],
                'operation':e['payload'].get('operation'),'source':e['payload'].get('source')}
                for e in c._events[-12:]],'checkpoint':str(self.store.current)}

    def command(self,operation,body):
        if not isinstance(body,dict):raise ValueError('expected an object')
        if self.error and operation!='save':raise ValueError('save recovery is required before further activity')
        c=self.creature
        if operation=='running':
            if type(body.get('running')) is not bool:raise ValueError('running must be a boolean')
            self.running=body['running']
        elif operation=='step':
            if self.running:raise ValueError('pause before stepping')
            self.tick();return
        elif operation=='place':
            c.place(body['identity'],body['x'],visible=body.get('visible',True),actor='companion-person')
        elif operation=='device':
            function=body['function']
            if function not in DEVICES:raise ValueError('unknown device')
            device=DEVICES[function]
            c.configure_device('toy',function=device['function'],type_id=f'habitat-{function}',delay=device['delay'],actor='companion-person')
            c.place('toy',c._host.position+2,actor='companion-person')
        elif operation=='guidance':
            c.offer_practice_guidance(body['goal_id'],additional_attempts=body['additional_attempts'],source='companion-person')
        elif operation=='investigation':
            c.respond_to_investigation(body['goal_id'],body['response'],source='companion-person')
        elif operation=='availability':c.report_companion_availability(body['available'])
        elif operation=='invitation':c.respond_to_invitation(body['invitation_event'],body['response'])
        elif operation=='dream':c.dream()
        elif operation!='save':raise ValueError('unknown operation')
        try:self.save()
        except Exception as exc:
            self.running=False;self.error=f'{type(exc).__name__}: {exc}'
            raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,default=ROOT/'runs/visible-companion')
    parser.add_argument('--port',type=int,default=46340)
    parser.add_argument('--seed',type=int,default=90)
    parser.add_argument('--generate-assets',action='store_true',help='Generate uninstalled visual candidates from missing experienced activity clips')
    parser.add_argument('--reflect',action='store_true',help='Enable asynchronous OAuth reflection on unresolved activity and lived trial outcomes')
    parser.add_argument('--lan-address',help='Additional local IPv4 interface to serve the habitat on')
    parser.add_argument('--proxy-origin',help='Exact HTTPS origin of a local reverse proxy')
    args=parser.parse_args()
    proxy_authority=None
    if args.proxy_origin:
        proxy=urlsplit(args.proxy_origin)
        if proxy.scheme!='https' or not proxy.netloc or proxy.path or proxy.query or proxy.fragment or proxy.username or proxy.password:
            parser.error('proxy origin must be an HTTPS origin without a path or credentials')
        proxy_authority=proxy.netloc
    if args.lan_address:
        try:
            address=ipaddress.IPv4Address(args.lan_address)
            if not address.is_private or address.is_loopback or address.is_unspecified or address.is_multicast:
                raise ValueError('expected a private LAN interface address')
        except ValueError as exc:parser.error(str(exc))
    if not 1024<=args.port<=65535:parser.error('port must be 1024..65535')
    habitat=Habitat(args.home,args.seed,reflect=args.reflect,generate_assets=args.generate_assets);stop=threading.Event()
    origin=f'http://127.0.0.1:{args.port}'
    class Handler(BaseHTTPRequestHandler):
        def respond(self,status,body,kind='application/json'):
            data=body if isinstance(body,bytes) else json.dumps(body,allow_nan=False).encode()
            self.send_response(status);self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(data)
        def authority(self):
            return f'{self.server.server_address[0]}:{args.port}'
        def local_proxy(self):
            return bool(proxy_authority and self.server.server_address[0]=='127.0.0.1' and self.client_address[0]=='127.0.0.1')
        def valid_host(self):
            return self.headers.get('Host') in ([self.authority(),proxy_authority] if self.local_proxy() else [self.authority()])
        def do_GET(self):
            if not self.valid_host():return self.respond(403,{'error':'invalid host'})
            if self.path=='/':return self.respond(200,PAGE.read_bytes(),'text/html; charset=utf-8')
            assets={f'/assets/creature/sheet-{n}.png':(f'sheet-{n}.png','image/png') for n in range(1,5)}
            assets['/assets/creature/animation.js']=('animation.js','text/javascript; charset=utf-8')
            assets.update({f'/assets/world/{name}':(f'../world/{name}',kind) for name,kind in [('atlas.png','image/png'),('maps.json','application/json'),('littleroot-v2.json','application/json'),('rural-v3.json','application/json'),('rural-v4.json','application/json'),('rural-v4-atlas.png','image/png'),('rural-atlas.png','image/png'),('berry-oran.png','image/png'),('berry-pecha.png','image/png'),('renderer.js','text/javascript; charset=utf-8')]})
            assets.update({f'/assets/creature/etch-v3/{name}.png':(f'etch-v3/{name}.png','image/png') for name in ('movement','daily','expressions')})
            assets['/assets/creature/walk-v2.png']=('walk-v2.png','image/png')
            if self.path in assets:
                name,kind=assets[self.path]
                return self.respond(200,(PAGE.parent/'assets'/'creature'/name).read_bytes(),kind)
            if self.path!='/state':return self.respond(404,{'error':'not found'})
            self.respond(200,habitat.read_state())
        def do_POST(self):
            origins=[None,'http://'+self.authority()]
            if self.local_proxy():origins.append(args.proxy_origin)
            if not self.valid_host() or self.headers.get('Origin') not in origins:
                return self.respond(403,{'error':'invalid origin or host'})
            if self.headers.get_content_type()!='application/json':return self.respond(415,{'error':'expected JSON'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=4096:raise ValueError('invalid request size')
                body=json.loads(self.rfile.read(length))
                with habitat.lock:habitat.command(self.path.removeprefix('/'),body)
                self.respond(200,{'ok':True})
            except (ValueError,KeyError,TypeError) as exc:self.respond(400,{'error':str(exc)})
            except Exception as exc:self.respond(500,{'error':str(exc)})
        def log_message(self,*args):pass
    servers=[]
    try:
        for address in ['127.0.0.1']+([args.lan_address] if args.lan_address else []):
            servers.append(ThreadingHTTPServer((address,args.port),Handler))
    except BaseException:
        for server in servers:server.server_close()
        if habitat.asset_scheduler:habitat.asset_scheduler.close()
        if habitat.reflection:habitat.reflection.close()
        habitat.store.close();raise
    server=servers[0]
    def worker():
        while not stop.wait(.6):
            with habitat.lock:
                if habitat.running:
                    try:habitat.tick()
                    except Exception:pass # Exposed as paused recovery state by tick().
    thread=threading.Thread(target=worker,daemon=True);thread.start()
    def shutdown(*_):
        stop.set()
        for listener in servers:threading.Thread(target=listener.shutdown,daemon=True).start()
    signal.signal(signal.SIGINT,shutdown);signal.signal(signal.SIGTERM,shutdown)
    print(json.dumps({'url':origin,'identity':habitat.creature.identity,'checkpoint':str(habitat.store.current)}),flush=True)
    listeners=[threading.Thread(target=listener.serve_forever,kwargs={'poll_interval':.1},daemon=True) for listener in servers[1:]]
    for listener in listeners:listener.start()
    if args.lan_address:print(json.dumps({'lan_url':f'http://{args.lan_address}:{args.port}'}),flush=True)
    try:server.serve_forever(poll_interval=.1)
    finally:
        stop.set();thread.join()
        for listener in servers[1:]:listener.shutdown()
        for listener in listeners:listener.join()
        for listener in servers:listener.server_close()
        if habitat.asset_scheduler:habitat.asset_scheduler.close()
        if habitat.reflection:habitat.reflection.close()
        habitat.store.close()

if __name__=='__main__':main()
