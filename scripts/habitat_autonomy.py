#!/usr/bin/env python3
"""Run an isolated, uncued continuation of a saved pet and record outcomes."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from creature_brain.simulation import Simulation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint', type=Path)
    parser.add_argument('--seconds', type=float, default=2000)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-learned', action='store_true', help='Reject scripted goals and external cues')
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error('--seconds must be positive and finite')
    raw = args.checkpoint.read_bytes()
    saved = json.loads(raw)
    sim = Simulation.from_dict(saved['simulation'])
    if sim.world.habitat is None:
        parser.error('checkpoint has no interactive habitat')
    identity = next(iter(sim.creatures))
    creature = sim.creatures[identity]
    # An experiment with no teacher prompts, even if one was pending in the save.
    pending_cue = creature.command
    creature.command = None
    if args.require_learned and sim.autonomy_mode!='learned':
        parser.error('checkpoint is not in learned mode')
    pose = sim.world.agents[identity]
    landmarks = {f['id']: f for f in sim.world.habitat['features']}
    closest = {key: math.inf for key in landmarks}
    targets, outcomes, actions, visits, feature_outcomes, events = Counter(), Counter(), Counter(), Counter(), Counter(), []
    initial_water = pose.water_intake
    previous_sleep = creature.body.sleep_state
    sleep_transitions = []
    intentions = Counter()
    cue_sources = Counter()
    intention_changes = []
    previous_intention = None
    samples = []
    bounds = [pose.x, pose.x, pose.y, pose.y]
    initial_time = sim.world.time
    steps = round(args.seconds / sim.dt)
    for i in range(steps):
        frame = sim.step()['creatures'][0]
        intent=frame.get('intention')
        if args.require_learned and frame['commanded']:raise RuntimeError('external cue during learned trial')
        if intent:
            source=intent.get('source','scripted')
            if args.require_learned and source not in ('experience','aversion','habituation'):raise RuntimeError('scripted goal during learned trial')
            cue_sources[source]+=1
        intended=intent['target'] if intent else None
        if intended: intentions[intended]+=1
        if intended != previous_intention:
            intention_changes.append({'seconds':round(sim.world.time-initial_time,2),'target':intended})
            previous_intention=intended
        if frame['action'] != creature.brain.output().action:
            raise RuntimeError('motor action did not come from the genome brain')
        if frame['sleep'] != previous_sleep:
            sleep_transitions.append({'seconds':round(sim.world.time-initial_time,2),
                                      'from':previous_sleep,'to':frame['sleep'],
                                      'sleep_debt':creature.body.sleep_debt})
            previous_sleep = frame['sleep']
        actions[str(frame['action'])] += 1
        outcomes[frame['outcome']] += 1
        targets[str(frame['target'])] += 1
        if frame['target'] in landmarks:
            feature_outcomes[frame['target']+' / '+frame['outcome']] += 1
        bounds = [min(bounds[0],pose.x),max(bounds[1],pose.x),min(bounds[2],pose.y),max(bounds[3],pose.y)]
        for key, feature in landmarks.items():
            distance = math.hypot(pose.x-feature['x'], pose.y-feature['y'])
            closest[key] = min(closest[key],distance)
            if distance <= max(feature['radius'],sim.world.interaction_radius): visits[key] += 1
        if frame['habitat_event'] or frame['outcome'] in ('drank','washed','splashed','entered','foraged','discovered','stored','decorated','explored','played'):
            events.append({'seconds':round(sim.world.time-initial_time,2),'target':frame['target'],
                           'outcome':frame['outcome'],'action':frame['action'],'event':frame['habitat_event']})
        if not frame['alive']:
            break
        if (i+1)%1000==0:
            samples.append({'seconds':round(sim.world.time-initial_time,2),'x':pose.x,'y':pose.y,
                            'sleep':frame['sleep'],'energy34':creature.body.chemicals[34],
                            'atp35':creature.body.chemicals[35],'water33':creature.body.chemicals[33],
                            'hunger':max(creature.body.drives[1:4]),'target':intended})
            print(f'{i+1}/{steps} ticks, {sim.world.time-initial_time:.1f}s, position {pose.x:.1f},{pose.y:.1f}, sleep {frame["sleep"]}, debt {creature.body.sleep_debt:.3f}',flush=True)
    result = {'created_utc':datetime.now(timezone.utc).isoformat(), 'source_checkpoint_sha256':hashlib.sha256(raw).hexdigest(),
              'pending_cue_removed': pending_cue, 'interventions':'none after start', 'requested_seconds':args.seconds,
              'elapsed_seconds':sim.world.time-initial_time, 'ticks':i+1, 'alive':creature.body.alive,
              'start_world_time':initial_time,'bounds':bounds,'actions':actions,'outcomes':outcomes,'targets':targets,
              'landmark_nearest_distances':closest,'landmark_ticks_in_range':visits,'water_intake':pose.water_intake,
              'water_consumed_during_run':pose.water_intake-initial_water,'feature_outcomes':feature_outcomes,
              'internal_intention_ticks':intentions,'intention_changes':intention_changes,
              'cue_sources':cue_sources,
              'body_samples':samples,'death_reason':creature.body.death_reason,
              'events':events,'sleep_transitions':sleep_transitions,'final_pose':{'x':pose.x,'y':pose.y,'location':pose.location,'inside':pose.inside},
              'eating_ticks':outcomes['ate']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('elapsed_seconds','ticks','alive','bounds','outcomes','landmark_nearest_distances','landmark_ticks_in_range')},indent=2),flush=True)

if __name__ == '__main__': main()
