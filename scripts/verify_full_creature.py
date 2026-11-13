"""Validate recorded scenarios and exact full-state continuation.

Run after the four documented CLI scenarios under runs/verification. This
checks the new standalone model, not live native-engine behavioral parity.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from creature_brain.simulation import Simulation, make_demo

ROOT=Path(__file__).resolve().parents[1]
RUNS=ROOT/'runs/verification'
results={}
for scenario in ('autonomous','feeding','sleep','social'):
    directory=RUNS/scenario
    summary=json.loads((directory/'summary.json').read_text())
    frames=[json.loads(line) for line in (directory/'trajectory.jsonl').read_text().splitlines()]
    assert len(frames)==summary['steps']
    outcomes=Counter(c['outcome'] for frame in frames for c in frame['creatures'])
    assert dict(outcomes)==summary['outcome_counts']
    assert all(0<=v<=1 for frame in frames for c in frame['creatures'] for v in c['drives'])
    assert all(0<=c['x']<=20 and 0<=c['y']<=12 for frame in frames for c in frame['creatures'])
    assert all(o['quantity']>=0 for frame in frames for o in frame['objects'])
    sim=Simulation.load(directory/'checkpoint.json')
    clone=Simulation.from_dict(json.loads(json.dumps(sim.to_dict(),allow_nan=False)))
    assert sim.to_dict()==clone.to_dict()
    for _ in range(6): assert sim.step()==clone.step()
    assert sim.to_dict()==clone.to_dict()
    if scenario=='autonomous':
        assert all(not c['commanded'] for frame in frames for c in frame['creatures'])
        assert outcomes['ate']>0
    elif scenario=='feeding':
        assert outcomes['ate']>0
        assert any(c['outcome']=='ate' and c['response'][1]<0 and c['action_reward']>0
                   for frame in frames for c in frame['creatures'])
    elif scenario=='sleep':
        assert {c['sleep'] for frame in frames for c in frame['creatures']}=={'awake','nrem','rem'}
        assert all(c['instincts_processed']>0 for c in frames[-1]['creatures'])
    elif scenario=='social':
        assert summary['event_counts']['play-contact']>0
        assert any(r['affinity']>0 and r['neural_opinion'][1]>0 for c in frames[-1]['creatures'] for r in c['social'])
    results[scenario]={'steps':len(frames),'simulated_seconds':summary['simulated_seconds'],
                       'actor_frames':sum(len(f['creatures']) for f in frames),
                       'outcomes':dict(outcomes),'events':summary['event_counts'],
                       'sleep_counts':summary['sleep_counts'],
                       'wall_seconds':summary['wall_seconds'],
                       'six_step_checkpoint_continuation_equal':True,
                       'final_health':{c['id']:c['health'] for c in frames[-1]['creatures']},
                       'final_instincts_processed':{c['id']:c['instincts_processed'] for c in frames[-1]['creatures']}}

genome=ROOT/'research/docking-station-20261103/resources/chichi-brain-program.json'
seeds={}
for seed in (1,19,73):
    sim=make_demo(genome,seed=seed,count=1,body_model='simplified')
    for _ in range(30):sim.step()
    saved=sim.to_dict()
    assert Simulation.from_dict(saved).to_dict()==saved
    seeds[str(seed)]=sim.summary()

hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for pattern in ('src/creature_brain/*.py','tests/test_*.py','scripts/*.py','pyproject.toml')
        for p in sorted(ROOT.glob(pattern))}
report={'status':'passed','scope':'standalone genome/body/world model; no native behavioral parity claim',
        'scenarios':results,'additional_short_seed_probes':seeds,'source_sha256':hashes,
        'checks':['complete scenario trace counts','bounded needs/positions/resources',
                  'full checkpoint validation','six-step exact continuation for each scenario',
                  'autonomous feeding without teacher','attributable feeding reward and signed relief',
                  'NREM/REM/wake and inherited rehearsal','positive independent and neural social opinion'],
        'qualification_limits':['one long-run seed; three short seed probes',
                                'autonomous injury is observed, not robust danger avoidance',
                                'body/world are original simplified models',
                                'native timing/numerical/migration candidate parity unqualified'],
        'replay_browser_visual_verification':{'passed':False,'reason':'Browser URL policy rejected file protocol; no workaround attempted.'}}
(RUNS/'checks.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'status':report['status'],'scenarios':results,'short_seed_probes':list(seeds)},indent=2))
