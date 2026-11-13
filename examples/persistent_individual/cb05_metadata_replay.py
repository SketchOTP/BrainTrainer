"""Bounded post-panel replay of the frozen vs metadata-extended observer."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
import cb05_evaluate as runner
from cb05_condition_table import table
import complete_action_prediction as current

OLD=ROOT/'runs/self-model/cb05-prospective/frozen-complete-action-prediction.py'
RAW=ROOT/'runs/self-model/cb05-prospective/cases.jsonl'
MANIFEST=ROOT/'runs/self-model/cb05-prospective/manifest.json'


def clean(value):
    if isinstance(value,(list,tuple)):return [clean(x) for x in value]
    if not isinstance(value,dict):return value
    out={k:clean(v) for k,v in value.items() if k not in ('elapsed_seconds','cpu_seconds','peak_worker_kib')}
    if out.get('kind')=='forecast':
        for arm in ('baseline','candidate'):
            for field in ('model','schema','prior_only','insufficient_evidence'):
                out[arm].pop(field,None)
    return out


def sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def main():
    manifest=json.loads(MANIFEST.read_text());old_sha=hashlib.sha256(OLD.read_bytes()).hexdigest()
    if old_sha!=manifest['sha256']['examples/persistent_individual/complete_action_prediction.py']:
        raise ValueError('archived observer does not match frozen manifest')
    spec=importlib.util.spec_from_file_location('cb05_archived_observer',OLD)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    previous={}
    for line in RAW.open():
        obj=json.loads(line)
        if obj['seed'] in (700,707):previous[obj['seed']]=obj
    if set(previous)!={700,707}:raise ValueError('missing original cases')
    all_rows=table();results=[];t0=time.monotonic()
    target=ROOT/'runs/self-model/cb05-prospective/metadata-replay-v3-cases.jsonl'
    with target.open('x') as out:
      for seed in (700,707):
        rows=[r for r in all_rows if r['seed']==seed]
        runner.CompleteActionObserver=old.CompleteActionObserver;runner.observed_snapshot=old.observed_snapshot
        historical=runner.case((seed,rows))
        if clean(historical)!=clean(previous[seed]):raise AssertionError('archived replay differs from frozen panel')
        runner.CompleteActionObserver=current.CompleteActionObserver;runner.observed_snapshot=current.observed_snapshot
        updated=runner.case((seed,rows))
        if clean(updated)!=clean(historical):raise AssertionError('metadata change altered underlying behavior')
        count=sum(p['kind']=='forecast' for o in updated['opportunities'] for p in o['predictions'])
        for o in updated['opportunities']:
            for p in o['predictions']:
                if p['kind']=='forecast':
                    for arm in ('baseline','candidate'):
                        assert p[arm]['schema']==current.CompleteActionObserver.SCHEMA
                        assert type(p[arm]['prior_only']) is bool and type(p[arm]['insufficient_evidence']) is bool
        out.write(json.dumps({'seed':seed,'frozen':historical,'updated':updated},sort_keys=True,allow_nan=False)+'\n');out.flush()
        results.append({'seed':seed,'forecasts':count,'frozen_panel_reproduced':True,
                        'normalized_behavior_identical':True,'normalized_sha256':sha(clean(updated))})
    receipt={'scope':'post-panel compatibility check only; no new held-out score',
             'seeds':[700,707],'cases':results,'frozen_observer_sha256':old_sha,
             'updated_observer_sha256':hashlib.sha256((ROOT/'examples/persistent_individual/complete_action_prediction.py').read_bytes()).hexdigest(),
             'runner_sha256':hashlib.sha256((ROOT/'examples/persistent_individual/cb05_evaluate.py').read_bytes()).hexdigest(),
             'raw_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'elapsed_seconds':time.monotonic()-t0}
    with (target.parent/'metadata-replay-v3-receipt.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
