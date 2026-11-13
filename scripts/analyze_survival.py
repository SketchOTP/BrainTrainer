"""Summarize actual full-brain genomic survival trials without hiding deaths."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUNS=ROOT/'runs/genome-biochemistry-verification'


def main():
    cases=[];invalid=[]
    with (RUNS/'survival-timeseries.csv').open('w') as stream:
        writer=csv.writer(stream)
        writer.writerow(['trial','seed','time_seconds','creature','alive','glycogen4',
                         'ATP35','energy34','life125','minimum_organ_health',
                         'protein_hunger','starch_hunger','fat_hunger','fatigue','sleepy','action','outcome'])
        for path in sorted(RUNS.glob('survival-*/summary.json')):
            data=json.loads(path.read_text());frames=0;actors=0;last=None
            with gzip.open(path.parent/'trajectory.jsonl.gz','rt') as trace:
                for line in trace:
                    frame=json.loads(line);frames+=1;last=frame
                    actors+=len(frame['creatures'])
                    if frame['time']%30!=0 and frame['step']!=data['steps']:continue
                    for c in frame['creatures']:
                        b=c['biochemistry'];chem=b['chemicals']
                        writer.writerow([path.parent.name,data['seed'],frame['time'],c['id'],c['alive'],
                                         c['health'],c['energy'],chem['34'],chem['125'],min(b['organ_health']),
                                         *c['drives'][1:4],c['drives'][6],c['drives'][7],c['action'],c['outcome']])
            current={key:hashlib.sha256((ROOT/key).read_bytes()).hexdigest() for key in data['source_sha256']}
            valid=(frames==data['steps'] and last['time']==data['simulated_seconds'] and
                   data['failure'] is None and data['sources_unchanged'] and current==data['source_sha256'] and
                   data['four_step_checkpoint_continuation_equal'] and data['teacher_commands']==0)
            if not valid:invalid.append(path.parent.name)
            final=[{'id':c['id'],'alive':c['alive'],'display_health_glycogen4':c['health'],
                    'ATP35':c['energy'],'energy34':c['biochemistry']['chemicals']['34'],
                    'minimum_organ_health':min(c['biochemistry']['organ_health']),
                    'death_time':data['death_times'][c['id']],
                    'feeding_events':data['feeding_events'].get(c['id'],0)} for c in last['creatures']]
            cases.append({'trial':path.parent.name,'environment':data['environment'],'seed':data['seed'],
                          'requested_seconds':data['requested_seconds'],'observed_seconds':data['simulated_seconds'],
                          'actor_frames':actors,'status':data['trial_status'],'valid_recording':valid,
                          'final':final,'outcomes':data['outcome_counts'],'sleep_counts':data['sleep_counts'],
                          'wall_seconds':data['wall_seconds'],'process_cpu_seconds':data['process_cpu_seconds'],
                          'summary':str(path.relative_to(ROOT))})
    if not cases:raise RuntimeError('no completed trial summaries')
    report={'status':'passed-recording-and-continuation-checks' if not invalid else 'invalid-recordings',
            'invalid_recordings':invalid,'cases':cases,
            'total_actor_frames':sum(c['actor_frames'] for c in cases),
            'survivors_at_horizon':sum(a['alive'] for c in cases for a in c['final']),
            'observed_deaths':sum(not a['alive'] for c in cases for a in c['final']),
            'limits':['Horizon survivors are censored observations, not lifetime-survival proof.',
                      'No observed starvation death means the starvation boundary remains unqualified.',
                      'Small trial count and two seeds do not establish robust survival or hazard avoidance.',
                      'Native numerical/wall-clock parity and biological realism remain unverified.']}
    (RUNS/'survival-report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    lines=['# Genome-driven autonomous survival trials','',
           'Full15-lobe/29-tract brains and genome biochemical bodies; no teacher commands, rescue feeding or fallback policy. Timebase: one biochemical update per simulated second.','',
           '| Environment / seed | Observed seconds | Alive at end | Feeding events | Final Glycogen4 | Final ATP35 |',
           '|---|---:|---:|---:|---|---|']
    for case in cases:
        final=case['final'];lines.append('| '+case['environment']+' / '+str(case['seed'])+' | '+str(int(case['observed_seconds']))+' | '+str(sum(x['alive'] for x in final))+'/'+str(len(final))+' | '+str(sum(x['feeding_events'] for x in final))+' | '+', '.join(f"{x['display_health_glycogen4']:.4f}" for x in final)+' | '+', '.join(f"{x['ATP35']:.4f}" for x in final)+' |')
    lines+=['','Each original simulation matched its restored continuation for four further steps, including persistent biochemical feedback state. Complete compressed trajectories, source hashes, initial states, final checkpoints and sampled replays accompany each trial.','',
            '## Interpretation','',*['- '+value for value in report['limits']],
            '', 'Glycogen4 is the recovered native display-health chemical, not the mean organ condition. ATP, Energy34, Life125, individual organs and drives are recorded independently.','',
            'The supplied-food and depleted worlds share seed7 and the same initial genome/body parameters. Their nutritional outcomes are observed model behavior; no claim of biological or live-game validation follows.','',
            '[Detailed results](survival-report.json) · [Thirty-second time series](survival-timeseries.csv)']
    (RUNS/'SURVIVAL_REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(report,indent=2))
    if invalid:raise SystemExit(1)


if __name__=='__main__':main()
