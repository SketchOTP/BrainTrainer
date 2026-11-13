"""Predeclared fresh-seed test of the optional 0.5 worsening-response gain."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import resource
import time

from creature_brain.benchmark.action_lifecycle import LifecycleFoodExperiment
from creature_brain.benchmark.feedback_gain import WorseningFeedbackGainExperiment

ROOT = Path(__file__).resolve().parents[1]
SEEDS = list(range(96, 112))
BODIES = ('walking', 'swimming')
MODES = ('baseline', 'gain05')
PHASES = ('experience', 'evaluation', 'reversal', 'reversal_evaluation')
FILES = ('docs/FOOD_HALF_GAIN_FRESH_PROTOCOL.md', 'scripts/evaluate_half_gain_fresh.py',
         'src/creature_brain/benchmark/feedback_gain.py', 'src/creature_brain/benchmark/action_lifecycle.py',
         'src/creature_brain/benchmark/qualification.py', 'src/creature_brain/benchmark/food.py',
         'src/creature_brain/benchmark/contract.py', 'src/creature_brain/benchmark/embodiment.py',
         'src/creature_brain/__init__.py', 'src/creature_brain/neural.py', 'src/creature_brain/svrule.py',
         'src/creature_brain/genome.py', 'src/creature_brain/sensory.py')
DEVELOPMENT = ROOT/'runs/food-qualification/worsening-feedback-gain05-dev-v1.json'


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024*1024): h.update(block)
    return h.hexdigest()


def normalized(value):
    return json.loads(json.dumps(value, allow_nan=False))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()


def source_hashes():
    return {name: file_hash(ROOT/name) for name in FILES}


def freeze(program, output):
    if output.exists(): raise FileExistsError('choose a new manifest')
    program = program.resolve()
    previous = json.loads(DEVELOPMENT.read_text())
    if previous.get('conditions') != ['baseline', 'gain05'] or previous.get('cases') != 64:
        raise ValueError('completed candidate-selection diagnostic required')
    if previous.get('program_sha256') != file_hash(program):
        raise ValueError('program differs from candidate selection')
    for name, old_hash in previous.get('source_sha256',{}).items():
        if not (ROOT/name).is_file() or file_hash(ROOT/name)!=old_hash:
            raise ValueError('candidate-selection source changed: '+name)
    if 'src/creature_brain/benchmark/feedback_gain.py' not in previous.get('source_sha256',{}):
        raise ValueError('candidate-selection extension digest missing')
    manifest = {'schema':'half-gain-fresh-v1', 'status':'frozen', 'program':str(program),
      'program_sha256':file_hash(program), 'source_sha256':source_hashes(),
      'development_result':str(DEVELOPMENT), 'development_result_sha256':file_hash(DEVELOPMENT),
      'seeds':SEEDS, 'bodies':list(BODIES), 'modes':list(MODES), 'mirrors':[False,True], 'good_types':[0,1],
      'phases':list(PHASES), 'opportunities_per_phase':20, 'max_steps':32, 'candidate_gain':.5,
      'shard_size':4, 'bootstrap_seed':20261107, 'bootstrap_samples':10000,
      'target':{'reversal_experience_min_difference':.05, 'reversal_ci_above_zero':True,
                'other_noninferiority_margin':.05, 'noninferiority_mean_not_negative':True,
                'other_endpoints':['initial_evaluation','reversal_evaluation','matched_retention_after_reversal'],
                'all_bodies_required':True}}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:
        json.dump(manifest,stream,indent=2,allow_nan=False);stream.write('\n')
    return manifest


def check_manifest(m):
    if (m.get('schema')!='half-gain-fresh-v1' or m.get('status')!='frozen' or m.get('seeds')!=SEEDS or
        m.get('bodies')!=list(BODIES) or m.get('modes')!=list(MODES) or m.get('mirrors')!=[False,True] or
        m.get('good_types')!=[0,1] or m.get('phases')!=list(PHASES) or m.get('opportunities_per_phase')!=20 or
        m.get('max_steps')!=32 or m.get('candidate_gain')!=.5 or m.get('shard_size')!=4 or
        m.get('bootstrap_seed')!=20261107 or m.get('bootstrap_samples')!=10000 or
        m.get('target')!={'reversal_experience_min_difference':.05,'reversal_ci_above_zero':True,
            'other_noninferiority_margin':.05,'noninferiority_mean_not_negative':True,
            'other_endpoints':['initial_evaluation','reversal_evaluation','matched_retention_after_reversal'],
            'all_bodies_required':True}):
        raise ValueError('frozen protocol mismatch')
    if m.get('source_sha256')!=source_hashes() or file_hash(m['program'])!=m.get('program_sha256'):
        raise ValueError('frozen program or sources changed')
    if m.get('development_result')!=str(DEVELOPMENT) or file_hash(DEVELOPMENT)!=m.get('development_result_sha256'):
        raise ValueError('development selection evidence changed')


def clone_at_boundary(experiment, matched):
    cls=type(experiment)
    clone=cls.restore(normalized(experiment.snapshot()))
    if clone.done or clone.active_action is not None:
        raise ValueError('probe requires an unfinished action boundary')
    removed=deepcopy(clone.pending);clone.pending=[]
    clone.position=clone.velocity=0.0;clone.positions=[.5,-.5]
    if matched:
        clone.energy=.5;clone.hunger=.8;clone.brain.chemicals[150]=.8
    obs=clone.observe()
    inputs={'visn':{obj.category:.5 for obj in obs.objects},'driv':{2:obs.hunger}}
    chemicals=clone.brain.chemicals.copy();chemicals[150]=clone.hunger
    output=clone.brain.tick(inputs,chemicals)
    target=next((o.identity for o in obs.objects if o.category==output.attention),None)
    high=clone.initial_good ^ int(clone.phase in ('reversal','reversal_evaluation'))
    return {'matched_needs':matched,'removed_pending':removed,'observation':normalized(asdict(obs)),
            'attention':output.attention,'decision':output.decision,'action':output.action,'target':target,
            'eat_higher':bool(output.action==12 and target==f'object-{high}'),
            'post_probe_brain_sha256':fingerprint(clone.brain.to_dict())}


def case(job):
    program,seed,body,mirror,good,mode=job
    started=time.monotonic();cpu=time.process_time()
    cls=LifecycleFoodExperiment if mode=='baseline' else WorseningFeedbackGainExperiment
    extra={} if mode=='baseline' else {'worsening_gain':.5}
    exp=cls(program,seed=seed,embodiment=body,condition='feedback',task='preference',mirror=mirror,
            max_steps=32,opportunities_per_phase=20,**extra)
    exp.initial_good=good
    initial=normalized(exp.snapshot());restored=None;probes={};phase_tract={};deliveries=[]
    while not exp.done:
        pending=deepcopy(exp.pending)
        event=exp.tick()
        if pending:deliveries.append({'time':event['observation']['time'],'phase':event['phase'],'events':pending})
        if restored is not None and normalized(restored.tick())!=normalized(event):
            raise RuntimeError('checkpoint continuation event mismatch')
        if event['opportunity_end'] and exp.opportunity in (20,40,60,80):
            tract=next(t for t in exp.brain.to_dict()['tracts'] if t['gene_id']==7)
            phase_tract[str(exp.opportunity)]=tract
        if event['opportunity_end'] and exp.opportunity in (20,60):
            before=fingerprint(normalized(exp.snapshot()))
            for matched in (False,True):
                one=clone_at_boundary(exp,matched);two=clone_at_boundary(exp,matched)
                if one!=two:raise RuntimeError('checkpoint probe mismatch')
                probes[f'{exp.opportunity}/{"matched" if matched else "unmodified"}']=one
            if fingerprint(normalized(exp.snapshot()))!=before:raise RuntimeError('probe altered continuation')
        if event['opportunity_end'] and exp.opportunity==40:
            restored=cls.restore(normalized(exp.snapshot()))
    final=normalized(exp.snapshot())
    if restored is None or normalized(restored.snapshot())!=final:raise RuntimeError('final checkpoint mismatch')
    return {'seed':seed,'body':body,'mirror':mirror,'good':good,'mode':mode,
            'initial_checkpoint':initial,'final_brain':final['brain'], 'history':normalized(exp.history),
            'deliveries':deliveries,'phase_tract':phase_tract,'probes':probes,
            'checkpoint_continuation_equal':True,'elapsed_seconds':time.monotonic()-started,
            'cpu_seconds':time.process_time()-cpu,'worker_peak_rss_kib_cumulative':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def expected(manifest,index=None):
    seeds=manifest['seeds'] if index is None else manifest['seeds'][index*4:(index+1)*4]
    return {(s,b,m,g,mode) for s in seeds for b in BODIES for m in (False,True) for g in (0,1) for mode in MODES}


def row_key(row): return (row['seed'],row['body'],row['mirror'],row['good'],row['mode'])


def validate_row(row,allowed):
    key=row_key(row)
    if key not in allowed or row.get('checkpoint_continuation_equal') is not True:raise ValueError('invalid case')
    initial=row['initial_checkpoint'];config=initial['config']
    if (config['seed']!=row['seed'] or config['embodiment']!=row['body'] or config['condition']!='feedback' or
            config['max_steps']!=32 or config['opportunities_per_phase']!=20 or
            initial['qualification']['task']!='preference' or initial['qualification']['mirror']!=row['mirror'] or
            initial['initial_good']!=row['good'] or initial['opportunity']!=0):
        raise ValueError('case initial configuration mismatch')
    marker=initial.get('feedback_extension')
    if marker!=({'version':WorseningFeedbackGainExperiment.EXTENSION,'worsening_gain':.5} if row['mode']=='gain05' else None):
        raise ValueError('candidate marker mismatch')
    if set(row['probes'])!={'20/matched','20/unmodified','60/matched','60/unmodified'} or set(row['phase_tract'])!={'20','40','60','80'}:
        raise ValueError('missing probe or tract checkpoint')
    ended=set()
    for event in row['history']:
        op=event['opportunity']
        if type(op) is not int or not 0<=op<80 or event['phase']!=PHASES[op//20]:raise ValueError('invalid opportunity')
        if event['opportunity_end']:
            if op in ended:raise ValueError('duplicate opportunity')
            ended.add(op)
    if ended!=set(range(80)):raise ValueError('incomplete opportunities')
    return key


def shard(manifest_path,index,output,workers,resume=False):
    if index not in range(4) or not 1<=workers<=12:raise ValueError('invalid shard or workers')
    manifest_bytes=manifest_path.read_bytes();mh=hashlib.sha256(manifest_bytes).hexdigest()
    m=json.loads(manifest_bytes);check_manifest(m)
    cases=output.with_suffix('.cases.jsonl');start_path=output.with_suffix('.start.json')
    if output.exists() or ((cases.exists() or start_path.exists()) and not resume):raise FileExistsError('shard exists')
    start={'schema':'half-gain-fresh-shard-start-v1','manifest_sha256':mh,'shard':index,'seeds':m['seeds'][index*4:(index+1)*4]}
    output.parent.mkdir(parents=True,exist_ok=True)
    if resume:
        if not start_path.exists() or json.loads(start_path.read_text())!=start:raise ValueError('start receipt mismatch')
        if not cases.exists():cases.touch(exist_ok=False)
    else:
        with start_path.open('x') as stream:json.dump(start,stream,indent=2);stream.write('\n')
    start_hash=file_hash(start_path);allowed=expected(m,index);seen=set();cpu=0.0;peak=0;old_count=0;pre_hash=None
    started=time.monotonic()
    if resume:
        pre_hash=file_hash(cases)
        with cases.open('rb') as stream:
            for line in stream:
                if not line.endswith(b'\n'):raise ValueError('truncated row; preserve before repair')
                row=json.loads(line);key=validate_row(row,allowed)
                if key in seen:raise ValueError('duplicate retained case')
                seen.add(key);cpu+=row['cpu_seconds'];peak=max(peak,row['worker_peak_rss_kib_cumulative'])
        old_count=len(seen)
    jobs=[(m['program'],*key) for key in sorted(allowed-seen)]
    with cases.open('a' if resume else 'x') as stream,ProcessPoolExecutor(max_workers=workers) as pool:
        iterator=iter(jobs);pending={pool.submit(case,next(iterator)) for _ in range(min(workers,len(jobs)))}
        while pending:
            done,pending=wait(pending,return_when=FIRST_COMPLETED)
            for future in done:
                row=future.result();key=validate_row(row,allowed)
                if key in seen:raise ValueError('duplicate case')
                stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush();seen.add(key)
                cpu+=row['cpu_seconds'];peak=max(peak,row['worker_peak_rss_kib_cumulative'])
                print(f'shard {index}: {len(seen)}/{len(allowed)}',flush=True)
                try:pending.add(pool.submit(case,next(iterator)))
                except StopIteration:pass
    if seen!=allowed:raise ValueError('incomplete shard')
    check_manifest(m)
    if file_hash(manifest_path)!=mh or file_hash(start_path)!=start_hash:raise ValueError('manifest or start receipt changed')
    report={'schema':'half-gain-fresh-shard-v1','manifest_sha256':mh,'shard':index,'seeds':start['seeds'],
            'cases':len(seen),'case_file':str(cases.resolve()),'case_sha256':file_hash(cases),
            'start_receipt':str(start_path.resolve()),'start_receipt_sha256':start_hash,
            'resumed_existing_count':old_count,'pre_resume_sha256':pre_hash,'wall_seconds_this_invocation':time.monotonic()-started,
            'summed_case_cpu_seconds':cpu,'max_cumulative_worker_rss_kib':peak}
    with output.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    return report


def interval(values,rng,count):
    n=len(values);means=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(count))
    return [means[int((count-1)*.025)],means[int((count-1)*.975)]]


def analyze(manifest_path,reports,output):
    if output.exists() or len(reports)!=4:raise ValueError('new output and four receipts required')
    mh=file_hash(manifest_path);m=json.loads(manifest_path.read_text());check_manifest(m)
    allowed=expected(m);seen=set();shards=set();pairs=defaultdict(dict);values=defaultdict(dict)
    retention=defaultdict(dict);totals=defaultdict(Counter);first=defaultdict(list);sources=[];cpu=0.;peak=0
    for report_path in reports:
        receipt=json.loads(report_path.read_text());i=receipt['shard']
        if (receipt['schema']!='half-gain-fresh-shard-v1' or i not in range(4) or i in shards or
                receipt['manifest_sha256']!=mh or receipt['seeds']!=m['seeds'][i*4:(i+1)*4] or receipt['cases']!=64):
            raise ValueError('invalid shard receipt')
        shards.add(i);sp=Path(receipt['start_receipt']);cp=Path(receipt['case_file'])
        start=json.loads(sp.read_text())
        if file_hash(sp)!=receipt['start_receipt_sha256'] or start!={'schema':'half-gain-fresh-shard-start-v1',
             'manifest_sha256':mh,'shard':i,'seeds':receipt['seeds']} or file_hash(cp)!=receipt['case_sha256']:
            raise ValueError('receipt or case digest mismatch')
        count=0
        with cp.open('rb') as stream:
            for line in stream:
                if not line.endswith(b'\n'):raise ValueError('truncated case')
                row=json.loads(line);key=validate_row(row,allowed)
                if key in seen or key[0] not in receipt['seeds']:raise ValueError('duplicate or misplaced case')
                seen.add(key);count+=1;cpu+=row['cpu_seconds'];peak=max(peak,row['worker_peak_rss_kib_cumulative'])
                initial=deepcopy(row['initial_checkpoint']);extension=initial.pop('feedback_extension',None)
                if extension!=({'version':WorseningFeedbackGainExperiment.EXTENSION,'worsening_gain':.5} if row['mode']=='gain05' else None):
                    raise ValueError('extension marker mismatch')
                pairs[key[:-1]][row['mode']]=fingerprint(initial)
                branch=(row['mirror'],row['good'])
                for pname,probe in row['probes'].items():
                    k=(row['body'],row['seed'],row['mode'],pname)
                    if branch in retention[k]:raise ValueError('duplicate probe')
                    retention[k][branch]=int(probe['eat_higher'])
                first_good=None
                for event in row['history']:
                    t=totals[f"{row['body']}/{row['mode']}/{event['phase']}"]
                    t['steps']+=1;t['eat_ticks']+=int(event['choice']['action']==12)
                    t['action_'+str(event['choice']['action'])]+=1;t['target_'+str(event['choice']['target'])]+=1
                    if not event['opportunity_end']:continue
                    t['opportunities']+=1;t['completed']+=int(event['outcome']['completed']);t['success']+=int(event['success'])
                    k=(row['body'],row['seed'],row['mode'],event['phase'],event['opportunity']%20)
                    if branch in values[k]:raise ValueError('duplicate scored opportunity')
                    values[k][branch]=(int(event['success']),int(event['outcome']['completed']))
                    if event['phase']=='reversal' and event['success'] and first_good is None:first_good=event['opportunity']-39
                first[(row['body'],row['mode'])].append(first_good)
        if count!=64:raise ValueError('wrong shard count')
        sources.append({'receipt':str(report_path),'receipt_sha256':file_hash(report_path),'case_file':str(cp),'case_sha256':receipt['case_sha256']})
    if seen!=allowed or shards!=set(range(4)) or any(set(p)!=set(MODES) or p['baseline']!=p['gain05'] for p in pairs.values()):
        raise ValueError('incomplete cases or paired initial states differ')
    rng=random.Random(m['bootstrap_seed']);phases={};curves={};probes={}
    branches={(mirror,good) for mirror in (False,True) for good in (0,1)}
    def compare(by_mode):
        differences=[a-b for a,b in zip(by_mode['gain05'],by_mode['baseline'])]
        avg=sum(differences)/len(differences)
        return {'baseline':float(sum(by_mode['baseline'])/16),'gain05':float(sum(by_mode['gain05'])/16),
                'difference':float(avg),'paired_95pct_bootstrap_interval':interval([float(v) for v in differences],rng,10000),
                'seed_differences':[float(v) for v in differences]}
    for body in BODIES:
        for phase in PHASES:
            estimates={mode:[] for mode in MODES}
            for seed in SEEDS:
                for mode in MODES:
                    rates=[]
                    for op in range(20):
                        v=values[(body,seed,mode,phase,op)]
                        if set(v)!=branches:raise ValueError('missing branch opportunity')
                        rates.append(Fraction(sum(x[0] for x in v.values()),4))
                    estimates[mode].append(sum(rates)/20)
            phases[f'{body}/{phase}']=compare(estimates)
            for op in range(20):
                curves[f'{body}/{phase}/{op+1}']={mode:sum(sum(v[0] for v in values[(body,seed,mode,phase,op)].values())/4
                    for seed in SEEDS)/16 for mode in MODES}
        for probe_name in ('20/matched','20/unmodified','60/matched','60/unmodified'):
            estimates={mode:[] for mode in MODES}
            for seed in SEEDS:
                for mode in MODES:
                    v=retention[(body,seed,mode,probe_name)]
                    if set(v)!=branches:raise ValueError('missing probe branch')
                    estimates[mode].append(Fraction(sum(v.values()),4))
            probes[f'{body}/{probe_name}']=compare(estimates)
    target={}
    for body in BODIES:
        early=phases[f'{body}/reversal'];initial=phases[f'{body}/evaluation'];late=phases[f'{body}/reversal_evaluation'];ret=probes[f'{body}/60/matched']
        target[body]={'early_reversal':early['difference']>=.05 and early['paired_95pct_bootstrap_interval'][0]>0,
          'initial_noninferior':initial['difference']>=0 and initial['paired_95pct_bootstrap_interval'][0]>-.05,
          'late_reversal_noninferior':late['difference']>=0 and late['paired_95pct_bootstrap_interval'][0]>-.05,
          'retention_noninferior':ret['difference']>=0 and ret['paired_95pct_bootstrap_interval'][0]>-.05}
    for t in totals.values():
        t['noncompletion']=t['opportunities']-t['completed']
        t['conditional_success']=t['success']/t['completed'] if t['completed'] else None
    result={'schema':'half-gain-fresh-analysis-v1','manifest_sha256':mh,'cases':len(seen),'sources':sources,
      'all_paired_initial_snapshots_match':True,'producer_all_checkpoint_continuations_match':True,
      'phase_summaries':phases,'retention_probes':probes,'per_opportunity_curves':curves,'totals':dict(totals),
      'first_new_good_in_reversal':{f'{body}/{mode}':vals for (body,mode),vals in first.items()},
      'target_by_body':target,'overall_target_met':all(all(v.values()) for v in target.values()),
      'summed_case_cpu_seconds':cpu,'max_cumulative_worker_rss_kib':peak,
      'limitations':['Only 16 fresh seeds per body; noninferiority margin is operational.',
       'Retention probes preserve other neural state; they are not isolated tract-state transplants.',
       'Gain affects transient computation as well as potential learning.',
       'Experimental action interruption is not verified against native brain-chosen interruption.',
       'Per-case checkpoint continuation is producer-checked, not independently replayed for every fresh case.',
       'Worker peak RSS is cumulative per worker, not process-family peak.']}
    with output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    f=sub.add_parser('freeze');f.add_argument('--program',required=True,type=Path);f.add_argument('--output',required=True,type=Path)
    s=sub.add_parser('shard');s.add_argument('--manifest',required=True,type=Path);s.add_argument('--shard',required=True,type=int)
    s.add_argument('--output',required=True,type=Path);s.add_argument('--workers',type=int,default=12);s.add_argument('--resume',action='store_true')
    a=sub.add_parser('analyze');a.add_argument('--manifest',required=True,type=Path);a.add_argument('--shard-report',action='append',required=True,type=Path);a.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    if args.command=='freeze':freeze(args.program,args.output)
    elif args.command=='shard':shard(args.manifest,args.shard,args.output,args.workers,args.resume)
    else:analyze(args.manifest,args.shard_report,args.output)


if __name__=='__main__':main()
