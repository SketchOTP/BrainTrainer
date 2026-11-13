"""Reconstruct one preselected development branch and trace first good reversal food."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from creature_brain.benchmark.research_checkpoint import restore_research_checkpoint
from replay_saved_gene7_continuations import ROOT, extract, normalized


def changes(before, after):
    return [{'neuron': n, 'variable': v, 'before': a, 'after': b}
            for n, (left, right) in enumerate(zip(before, after))
            for v, (a, b) in enumerate(zip(left, right)) if a != b]


def main(output):
    dest = Path(output)
    if dest.exists():
        raise FileExistsError('choose new output')
    analysis_path = ROOT/'runs/food-qualification/gene7-contact-development-v1-recovered-analysis.json'
    analysis = json.loads(analysis_path.read_text())
    digests = {x['path']: x['sha256'] for x in analysis['case_sources']}
    selected = extract([ROOT/x['path'] for x in analysis['case_sources']], digests)
    key = (0, 'walking', False, 0, 'ordinary')
    row = selected[key]
    experiment = restore_research_checkpoint(row['initial_checkpoint'])
    for i, step in enumerate(row['steps']):
        event = experiment.tick()
        if normalized(event) != step['event']:
            raise AssertionError(f'captured event mismatch at {i}')
        if event['phase'] == 'reversal' and event['success']:
            break
    else:
        raise RuntimeError('preselected branch has no successful reversal consumption')
    if not experiment.pending or i + 1 >= len(row['steps']):
        raise RuntimeError('missing attributed pending feedback or next tick')
    before_resp = deepcopy(experiment.brain.lobes['resp'].neurons)
    before_drive = deepcopy(experiment.brain.lobes['driv'].neurons)
    pending = deepcopy(experiment.pending)
    tract = next(t for t in experiment.brain.tracts if (t.gene_id,t.source_lobe,t.destination_lobe)==(7,'driv','comb'))
    before_dendrites = [(d.source,d.destination,d.variables.copy()) for d in tract.dendrites]
    before_weak = tract.weak.copy()
    response_inputs_before = experiment.brain.lobes['resp'].inputs.copy()
    next_event = experiment.tick()
    if normalized(next_event) != row['steps'][i+1]['event']:
        raise AssertionError('feedback-tick event mismatches recorded run')
    after_dendrites = [(d.source,d.destination,d.variables.copy()) for d in tract.dendrites]
    dendrites = [{'index': n,'before': a,'after': b} for n,(a,b) in enumerate(zip(before_dendrites,after_dendrites)) if a!=b]
    result = {'scope':'one reconstructed, predetermined development branch; observational association, not native execution',
              'case':list(key), 'consumption_step':i+1, 'consumption':event,
              'pending_feedback':pending, 'response_inputs_before_delivery':response_inputs_before,
              'feedback_tick':next_event, 'response_changes':changes(before_resp,experiment.brain.lobes['resp'].neurons),
              'drive_changes':changes(before_drive,experiment.brain.lobes['driv'].neurons),
              'gene7_weak_before':before_weak, 'gene7_weak_after':tract.weak.copy(),
              'gene7_dendrite_changes':dendrites,
              'source_case_digests':digests, 'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'output':str(dest),'case':key,'consumption_step':i+1,'pending':pending,
       'response_changes':result['response_changes'],'drive_changes':result['drive_changes'],
       'gene7_dendrite_change_count':len(dendrites),'weak_before':before_weak,'weak_after':tract.weak},indent=2))


if __name__=='__main__':main(sys.argv[1])
