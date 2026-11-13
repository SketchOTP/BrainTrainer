"""CB-03 paired observational replay: initial seed 0 versus 1.

Both runs reconstruct the archived 2-unit, mirror-false, baseline calibration
with unchanged natural brain ticks and no injected feedback. Instrumentation
captures tick inputs and post-update neural states; all recorded host outputs
must match the archived opportunity exactly. This cannot isolate any particular
connection, because changing seed also changes neural initialization and RNG.
"""
import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from complete_action_benchmark import individual,opportunity

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'runs/self-model/complete-action/calibration.jsonl'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

def mapping(brain):
    a=next(t for t in brain.tracts if (t.source_lobe,t.destination_lobe)==('comb','attn'))
    d=next(t for t in brain.tracts if (t.source_lobe,t.destination_lobe)==('comb','decn'))
    visual={x.source for x in a.dendrites if x.destination==3}
    eat={x.source for x in d.dendrites if x.destination==4}
    cells=sorted(visual & eat)
    if len(cells)!=1:raise RuntimeError(f'ambiguous food/eat cells {cells}')
    return cells[0]


def replay(seed, archived):
    e=individual(seed,'baseline',f'cb02-dev-{seed}-0');brain=e.brain
    initial=brain.to_dict();initial_hash=hashlib.sha256(canonical(initial).encode()).hexdigest()
    cell=mapping(brain);records=[];original=brain.tick
    def observed(inputs=None,chemicals=None):
        pre={'inputs':deepcopy(inputs),'chemicals':deepcopy(chemicals),
             'pending_lobe_inputs':{k:{str(i):v for i,v in enumerate(l.inputs) if v!=0.0}
                                    for k,l in brain.lobes.items()}}
        output=original(inputs,chemicals)
        selected={name:deepcopy(brain.lobes[name].neurons) for name in ('decn','stim','driv','visn','attn')}
        selected['food_eat_comb']={'index':cell,'state':deepcopy(brain.lobes['comb'].neurons[cell])}
        selected['comb_winner']={'index':brain.lobes['comb'].winner,
                                  'state':deepcopy(brain.lobes['comb'].neurons[brain.lobes['comb'].winner])}
        records.append({'frame':len(records),'pre':pre,'output':asdict(output),'post':selected})
        return output
    brain.tick=observed
    try:actual=opportunity(e,seed,0,2.0,False,64,'healthy','sustained')
    finally:del brain.tick
    expected=archived['result'];same=canonical(actual)==canonical(expected)
    choice_verified=all(rec['output']['decision']==event['event']['choice']['decision'] and
                        rec['output']['action']==event['event']['choice']['action'] and
                        rec['output']['attention']==event['event']['choice']['attention']
                        for rec,event in zip(records,actual['events']))
    return {'seed':seed,'initial_brain_sha256':initial_hash,'food_eat_comb':cell,'full_host_result_matches_archive':same,
            'each_brain_output_matches_choice':choice_verified,'requested_eat':actual['requested_eat'],
            'completed':actual['completed'],'frames':records}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows=[json.loads(s) for s in SOURCE.open()];selected={r['seed']:r for r in rows if r['distance']==2.0 and
          r['condition']=='baseline' and r['mirror'] is False and r['seed'] in (0,1)}
    assert set(selected)=={0,1}
    cases=[replay(seed,selected[seed]) for seed in (0,1)]
    inputs_identical=all(canonical(x['pre'])==canonical(y['pre']) for x,y in zip(cases[0]['frames'],cases[1]['frames']))
    output={'scope':'CB-03 paired replay #2: natural seed0 vs seed1, baseline mirror false, 2.0 units',
        'limitation':'Seed changes initial neural state, connections and RNG; this pair does not isolate a specific cause. Captures are reconstructed, not native engine evidence.',
        'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'identical_all_captured_pre_frames':inputs_identical,
        'cases':cases}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(output,f,sort_keys=True,allow_nan=False);f.write('\n')
    print('matches archived host results:',[c['full_host_result_matches_archive'] for c in cases],
          'tick outputs verified:',[c['each_brain_output_matches_choice'] for c in cases],
          'identical captured inputs/chemicals/queues:',inputs_identical)
    if not all(c['full_host_result_matches_archive'] and c['each_brain_output_matches_choice'] for c in cases):raise SystemExit(1)

if __name__=='__main__':main()
