"""Summarize already completed preference cases without changing their evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics

from creature_brain.benchmark.run import summarize


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('cases',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    entries=[json.loads(line) for line in args.cases.read_text().splitlines()]
    if not entries: raise ValueError('no completed cases')
    if len({x['signature'] for x in entries}) != 1: raise ValueError('mixed experiment fingerprints')
    runs=[entry['run'] for entry in entries]
    group={}
    for body in ('walking','swimming'):
        for variant in ('training','layout','appearance','novel_identity'):
            for split in ('development','heldout'):
                key=f'{body}/{variant}/{split}'
                data=[x for x in runs if x['embodiment']==body and x['variant']==variant
                      and (x['seed'] < 16)==(split=='development')]
                if not data: continue
                group[key]={}
                for condition in ('feedback','feedback_withheld'):
                    sub=[x for x in data if x['condition']==condition]
                    if not sub: continue
                    first=[]; statuses=Counter()
                    for run in sub:
                        ends=[x for x in run['history'] if x['opportunity_end']]
                        if ends: first.append(int(ends[0]['success']))
                        statuses.update(x['outcome']['status'] for x in ends)
                    group[key][condition]={
                        'completed_seeds':len(sub),'first_opportunity_success_rate':statistics.fmean(first) if first else None,
                        'terminal_outcomes':dict(statuses),
                        'process_cpu_seconds_sum':sum(x['cpu_seconds'] for x in sub),
                        'max_worker_peak_rss_kib_cumulative':max(x['worker_peak_rss_kib_cumulative'] for x in sub),
                        'checkpoint_results':[x['midpoint_checkpoint_continuation_equal'] for x in sub
                                              if x['midpoint_checkpoint_continuation_equal'] is not None]}
    result={'schema':1,'fingerprint':entries[0]['signature'],'completed_cases':len(runs),
            'expected_complete_cases':896,'complete':len(runs)==896,
            'control_qualified':False,'control':'feedback withheld, not learning disabled',
            'phase_comparisons':summarize(runs),'first_opportunity_and_costs':group}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'completed_cases':len(runs),'expected':896,'output':str(args.output)}))


if __name__=='__main__':main()
