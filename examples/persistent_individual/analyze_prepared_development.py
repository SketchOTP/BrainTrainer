"""Evaluate CB-04 development gates from complete preserved case rows."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('raw',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    rows=[json.loads(s) for s in a.raw.read_text().splitlines()]
    if sorted(r['seed'] for r in rows)!=list(range(4)):raise ValueError('expected four unique development seeds')
    immediate=[v for row in rows for v in row['immediate']];delayed=[v for row in rows for v in row['delayed']]
    if len(immediate)!=32 or len(delayed)!=8:raise ValueError('incomplete scheduled population')
    expect={(s,m,c) for s in range(4) for m in (False,True) for c in ('normal','effort','baseline','candidate')}
    if {(v['seed'],v['mirror'],v['condition']) for v in immediate}!=expect:raise ValueError('bad immediate keys')
    if {(v['seed'],v['mirror'],v['condition']) for v in delayed}!={(s,m,'normal') for s in range(4) for m in (False,True)}:raise ValueError('bad delayed keys')
    def stats(cases,minimum):
        passed=[v for v in cases if v['result']['completed']];seeds=sorted({v['seed'] for v in passed});mirrors=sorted({v['mirror'] for v in passed})
        flags=Counter()
        for v in cases:
            r=v['result'];flags['requested']+=r['requested_eat'];flags['contact']+=r['contact'];flags['blocked']+=r['blocked'];flags['exhausted']+=r['exhausted'];flags['interrupted']+=r['interruptions']>0;flags['timeout']+=r['timed_out'];flags['unsupported_choice_ticks']+=sum(t['event']['outcome']['status']=='unavailable-action' for t in r['events']);flags['motor_measured_failures']+=sum(v['motor_success'] is False for v in r['motor']);flags['motor_unknown_blocks']+=sum(v['motor_success'] is None for v in r['motor'])
        return {'scheduled':len(cases),'completed':len(passed),'successful_seeds':seeds,'successful_mirrors':mirrors,
                'successes':[{'seed':v['seed'],'mirror':v['mirror'],'condition':v['condition'],'ticks':v['result']['ticks']} for v in passed],
                'flags':dict(flags),'gate':len(passed)>=minimum and len(seeds)>=2 and set(mirrors)=={False,True}}
    result={'immediate':stats(immediate,8),'delayed':stats(delayed,2),
            'profile':'cb04-inherited-instincts-age1-one-pass-v1','fresh_qualifies':False,
            'elapsed_case_seconds_sum':sum(r['elapsed_seconds'] for r in rows),'cpu_seconds_sum':sum(r['cpu_seconds'] for r in rows),
            'max_worker_peak_kib':max(r['peak_worker_kib'] for r in rows),
            'raw_sha256':hashlib.sha256(a.raw.read_bytes()).hexdigest()}
    result['fresh_qualifies']=result['immediate']['gate'] and result['delayed']['gate']
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
