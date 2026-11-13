"""Run a bounded, autonomous full-genome survival trial and preserve failures.

No teacher commands, emergency feeding, motor fallback or hidden rescue. A live
creature at the horizon is right-censored, not proof of lifetime survival.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import time
import traceback

from creature_brain.__main__ import replay_html
from creature_brain.body import DEFAULT_BRAIN, DEFAULT_GENOME
from creature_brain.simulation import Simulation, make_demo

ROOT=Path(__file__).resolve().parents[1]
if not __debug__:
    raise RuntimeError('survival verification requires Python assertions enabled')


def source_hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for pattern in ('src/creature_brain/*.py','scripts/survival_benchmark.py')
            for p in sorted(ROOT.glob(pattern)) if p.name!='pet.py'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=7)
    parser.add_argument('--seconds',type=int,default=3600)
    parser.add_argument('--creatures',type=int,default=2)
    parser.add_argument('--environment',choices=('safe','hazards','depleted'),default='safe')
    parser.add_argument('--timing',choices=('docking-nominal','legacy'),default='docking-nominal')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not 600<args.seconds<=86400:parser.error('--seconds must exceed600 and be at most86400')
    if args.output.exists() and any(args.output.iterdir()):parser.error('use a new empty output directory to preserve trial receipts')
    args.output.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter();cpu_started=time.process_time();hashes=source_hashes()
    dt=.2 if args.timing=='docking-nominal' else 1.0
    sim=make_demo(DEFAULT_BRAIN,physiology_genome=DEFAULT_GENOME,seed=args.seed,count=args.creatures,dt=dt,timing_profile=args.timing)
    for creature in sim.creatures.values():
        assert creature.body.MODEL=='genome-physiology-v1'
        assert len(creature.brain.lobes)==15 and len(creature.brain.tracts)==29
    if args.environment!='hazards':
        sim.world.objects['danger'].enabled=False
        sim.world.objects['toxic-food'].enabled=False
    if args.environment=='depleted':
        for obj in sim.world.objects.values():
            if obj.kind=='food':obj.quantity=0;obj.regeneration=0
    initial={key:{'body':c.body.to_dict(),'brain_tick':c.brain.tick_count} for key,c in sim.creatures.items()}
    (args.output/'initial-state.json').write_text(json.dumps(initial,allow_nan=False)+'\n')
    deaths={key:None for key in sim.creatures};minimum_health={key:c.body.health for key,c in sim.creatures.items()}
    minimum_atp={key:c.body.energy for key,c in sim.creatures.items()};food_events=Counter();replays=[]
    total_steps=round(args.seconds/dt)
    stride=max(1,math.ceil(total_steps/1200));failure=None;last_frame=None
    with gzip.open(args.output/'trajectory.jsonl.gz','wt') as trace:
        try:
            for tick in range(total_steps):
                frame=sim.step();last_frame=frame
                for c in frame['creatures']:
                    if c['commanded']:raise AssertionError('autonomous trial contains a teacher command')
                    if not all(math.isfinite(v) and 0<=v<=1 for v in c['drives']):raise AssertionError('invalid drive state')
                    if not all(math.isfinite(v) and 0<=v<=1 for v in c['biochemistry']['chemicals'].values()):raise AssertionError('invalid chemical state')
                    minimum_health[c['id']]=min(minimum_health[c['id']],c['health'])
                    minimum_atp[c['id']]=min(minimum_atp[c['id']],c['energy'])
                    if c['outcome']=='ate':food_events[c['id']]+=1
                    if not c['alive'] and deaths[c['id']] is None:deaths[c['id']]=sim.world.time
                trace.write(json.dumps(frame,allow_nan=False)+'\n')
                if tick%stride==0:replays.append(frame)
                if tick%120==0:
                    (args.output/'progress.json').write_text(json.dumps({'seconds':sim.world.time,'requested':args.seconds,
                        'alive':{k:c.body.alive for k,c in sim.creatures.items()},'food_events':dict(food_events),
                        'wall_seconds':time.perf_counter()-started})+'\n')
                if not any(c.body.alive for c in sim.creatures.values()):break
        except Exception as error:
            failure={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
    if last_frame is not None and (not replays or replays[-1]['step']!=last_frame['step']):replays.append(last_frame)
    sim.save(args.output/'checkpoint.json')
    summary=sim.summary();horizon_steps=sim.steps
    continuation_equal=None
    if failure is None:
        restored=Simulation.load(args.output/'checkpoint.json')
        continuation_equal=all(sim.step()==restored.step() for _ in range(4)) and sim.to_dict()==restored.to_dict()
        if not continuation_equal:failure={'type':'CheckpointContinuationMismatch'}
    summary.update({'trial_status':'failed' if failure else ('horizon_reached' if horizon_steps==total_steps else 'all_dead'),
        'environment':args.environment,'seed':args.seed,'requested_seconds':args.seconds,'timing_profile':args.timing,
        'autonomous':True,'teacher_commands':0,'rescue_or_fallback':False,
        'death_times':deaths,'minimum_display_health_glycogen':minimum_health,'minimum_atp':minimum_atp,
        'feeding_events':dict(food_events),'four_step_checkpoint_continuation_equal':continuation_equal,
        'wall_seconds':time.perf_counter()-started,'process_cpu_seconds':time.process_time()-cpu_started,
        'source_sha256':hashes,'sources_unchanged':hashes==source_hashes(),'failure':failure,
        'qualification':'Genome-driven body research model; nominal timing follows static default world tick and creature cadence, not a live measured clock. Body/world and64s causal window are adaptations. Horizon survivors are censored; native/biological parity unqualified.'})
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    (args.output/'replay.html').write_text(replay_html(replays,sim.world,summary))
    print(json.dumps({key:summary[key] for key in ('trial_status','simulated_seconds','death_times','feeding_events','wall_seconds','failure')},indent=2))
    if failure:raise SystemExit(1)


if __name__=='__main__':main()
