"""Trace feedback-sensitive retained state after a brain-selected food event.

The matched branches receive the same sensory frames and chemistry; only the
attributed response input differs. Differences are feedback-sensitive state,
not proof that every changed value constitutes a learned association.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from creature_brain.benchmark.food import TRACKED
from creature_brain.benchmark.qualification import QualificationExperiment
from creature_brain import DefaultBrain, route_sensory_adjustment


def difference(a, b, brain):
    lobes = {}
    for name in a['lobes']:
        x, y = a['lobes'][name], b['lobes'][name]
        slots = Counter()
        samples = []
        for index, (left, right) in enumerate(zip(x['neurons'], y['neurons'])):
            for slot, (v, w) in enumerate(zip(left, right)):
                if v != w:
                    slots[str(slot)] += 1
                    if len(samples) < 4:
                        samples.append({'neuron': index, 'slot': slot, 'left': v, 'right': w})
        if slots or x['winner'] != y['winner'] or x['inputs'] != y['inputs']:
            lobes[name] = {'changed_slots': dict(slots), 'winner': [x['winner'], y['winner']],
                           'pending_inputs_differ': x['inputs'] != y['inputs'], 'samples': samples}
    tracts = []
    for tract, x, y in zip(brain.tracts, a['tracts'], b['tracts']):
        slots = Counter()
        endpoints = 0
        samples = []
        for index, (left, right) in enumerate(zip(x['dendrites'], y['dendrites'])):
            if (left['source'], left['destination']) != (right['source'], right['destination']):
                endpoints += 1
            for slot, (v, w) in enumerate(zip(left['variables'], right['variables'])):
                if v != w:
                    slots[str(slot)] += 1
                    if len(samples) < 3:
                        samples.append({'dendrite': index, 'slot': slot, 'left': v, 'right': w})
        if slots or endpoints or x['weak'] != y['weak'] or x['helper'] != y['helper']:
            tracts.append({'gene_id': tract.gene_id, 'source': tract.source_lobe,
                           'destination': tract.destination_lobe, 'changed_variable_slots': dict(slots),
                           'changed_endpoints': endpoints, 'weak_queue_differs': x['weak'] != y['weak'],
                           'helper_differs': x['helper'] != y['helper'], 'samples': samples})
    return {'lobes': lobes, 'tracts': tracts, 'rng_equal': a['rng'] == b['rng'],
            'knowledge_equal': a['knowledge'] == b['knowledge'],
            'dummy_equal': a['dummy'] == b['dummy']}


def main(program, output):
    dest = Path(output)
    if dest.exists():
        raise FileExistsError('choose a new output')
    exp = QualificationExperiment(program, seed=0, embodiment='walking', condition='feedback',
                                  task='single_contact', food_index=0, trace=False,
                                  max_steps=32, opportunities_per_phase=2)
    while not exp.pending and exp.time < 32:
        exp.tick()
    if not exp.pending:
        raise RuntimeError('brain did not generate a completed outcome')
    snap = exp.snapshot()
    initial_brain = snap['brain']
    feedback = DefaultBrain.from_dict(snap['brain'])
    withheld = DefaultBrain.from_dict(snap['brain'])
    for event in snap['pending']:
        routed = route_sensory_adjustment(150, event['hunger_adjustment'], TRACKED,
                    training=True, source_valid=True, life_state=1, synchronous_learning=0)
        feedback.queue_inputs(routed.brain_inputs())
    obs = exp.observe()
    frame = {'visn': {o.category: .5 for o in obs.objects}, 'driv': {2: obs.hunger}}
    chemicals = feedback.chemicals.copy()
    chemicals[150] = obs.hunger
    ticks = []
    for tick in range(1, 9):
        a = feedback.tick(frame, chemicals)
        b = withheld.tick(frame, chemicals)
        feedback_state = feedback.to_dict()
        withheld_state = withheld.to_dict()
        ticks.append({'tick_after_outcome': tick, 'feedback_output': vars(a),
                      'withheld_output': vars(b),
                      'state_difference': difference(feedback_state, withheld_state, feedback),
                      'feedback_changes_since_outcome': difference(feedback_state, initial_brain, feedback),
                      'withheld_changes_since_outcome': difference(withheld_state, initial_brain, withheld)})
    result = {'scope': 'one brain-chosen food outcome, reconstruction only, fixed sensory and chemistry replay',
              'limitation': 'Differences are feedback-sensitive retained state, not evidence of causation or learned preference.',
              'difference_direction': 'state_difference: feedback vs withheld; changes_since_outcome: branch vs pre-feedback checkpoint',
              'program_sha256': hashlib.sha256(Path(program).read_bytes()).hexdigest(),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'pre_feedback_brain_sha256': hashlib.sha256(json.dumps(initial_brain, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
              'completed_action': exp.history[-1]['choice'], 'outcome': exp.history[-1]['outcome'],
              'pending_response': snap['pending'], 'same_sensory_frame': frame,
              'chemical_150': chemicals[150], 'ticks': ticks,
              'whole_brain_learning_disabled_qualified': False}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'output': str(dest), 'ticks': [{'tick': t['tick_after_outcome'],
          'lobes': list(t['state_difference']['lobes']),
          'tracts': [x['gene_id'] for x in t['state_difference']['tracts']] } for t in ticks]}, indent=2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
