"""Conditional CB-04 fresh histories; call only after both development gates pass."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import json,hashlib
from pathlib import Path
import resource,time
from complete_action_benchmark import CONDITIONS,SCENARIOS,opportunity
from inherited_preparation import prepare_inherited,clone_prepared_motor,prepared_snapshot,restore_prepared
from motor_benchmark import MotorIndividual,PROGRAM
from prepared_development import signature,digest


def seed_cases(seed):
    started=time.monotonic(); cpu=time.process_time()
    source=MotorIndividual(PROGRAM,seed=seed,condition='adaptive',identity=f'cb04-fresh-{seed}')
    receipt=prepare_inherited(source,PROGRAM); prepared=prepared_snapshot(source);matched=digest(signature(source))
    source_state=prepared['state'];source_model=source_state['model']
    rows=[]
    for scenario in SCENARIOS:
        for condition in CONDITIONS:
            e=clone_prepared_motor(source,condition)
            if digest(signature(e))!=matched:raise AssertionError('nonmatching prepared initial state')
            initial=prepared_snapshot(e);state=initial['state'];model=state['model']
            if initial['receipt']!=prepared['receipt'] or state['individual']!=source_state['individual']:
                raise AssertionError('nonmatching full individual or receipt')
            if any(state[k]!=source_state[k] for k in ('reserve','body_strength','obstacle_present')):
                raise AssertionError('nonmatching motor body')
            if any(model[k]!=source_model[k] for k in ('evidence','decisions','pending')):
                raise AssertionError('nonmatching model evidence')
            if condition=='candidate' and (model['confirmations'] or model['confirmation_attempts']):
                raise AssertionError('unexpected initial confirmation state')
            results=[];op=0;continuity=None
            while op<24:
                phase=('healthy','impaired','recovery')[op//8]
                results.append(opportunity(e,seed,op,2.0,bool(seed%2),64,phase,scenario))
                if op==11:
                    checkpoint=json.loads(json.dumps(prepared_snapshot(e),allow_nan=False))
                    restored=restore_prepared(checkpoint)
                    resumed_a=opportunity(e,seed,12,2.0,bool(seed%2),64,'impaired',scenario)
                    resumed_b=opportunity(restored,seed,12,2.0,bool(seed%2),64,'impaired',scenario)
                    continuity=(json.dumps(resumed_a,sort_keys=True)==json.dumps(resumed_b,sort_keys=True) and
                                digest(prepared_snapshot(e))==digest(prepared_snapshot(restored)))
                    if not continuity:raise AssertionError('checkpoint continuation mismatch')
                    results.append(resumed_a);op=13
                else:op+=1
            rows.append({'seed':seed,'condition':condition,'scenario':scenario,'mirror':bool(seed%2),
                         'matched_start_sha256':matched,'initial_checkpoint_sha256':digest(initial),
                         'checkpoint_continuation_equal':continuity,'results':results,'final_checkpoint':prepared_snapshot(e)})
    if digest(signature(source))!=matched:raise AssertionError('source changed')
    return {'seed':seed,'preparation':receipt,'prepared_checkpoint':prepared,'cases':rows,
            'elapsed_seconds':time.monotonic()-started,'cpu_seconds':time.process_time()-cpu,
            'peak_worker_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--qualification',type=Path,required=True);p.add_argument('--qualification-raw',type=Path,required=True)
    p.add_argument('--qualification-audit',type=Path,required=True);p.add_argument('--workers',type=int,default=4)
    args=p.parse_args();result=json.loads(args.qualification.read_text())
    if result.get('fresh_qualifies') is not True or not result.get('immediate',{}).get('gate') or not result.get('delayed',{}).get('gate'):
        p.error('both development gates must pass before fresh evaluation')
    raw_sha=hashlib.sha256(args.qualification_raw.read_bytes()).hexdigest()
    audit=json.loads(args.qualification_audit.read_text())
    if (result.get('raw_sha256')!=raw_sha or audit.get('raw_sha256')!=raw_sha or
            audit.get('matched_full_initial_checkpoints')!=32 or audit.get('delayed_interval_receipts')!=8):
        p.error('development raw and complete matched-start audit must agree')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool,args.output.open('x') as f:
        for row in pool.map(seed_cases,range(500,516)):
            f.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n');f.flush()
            print('seed',row['seed'],'cases',len(row['cases']),flush=True)

if __name__=='__main__':main()
