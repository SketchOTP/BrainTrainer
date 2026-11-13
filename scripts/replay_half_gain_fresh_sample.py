"""Rerun four predetermined fresh cases using the same frozen implementation.

This independently re-executes the saved cases from fresh seed construction,
then checks the starting checkpoint against the saved one. It is not an
independent implementation and does not restore the producer's unsaved midpoint.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import json
from pathlib import Path
import resource
import time

import evaluate_half_gain_fresh as fresh

SELECTED = {(96,'walking',False,0,mode) for mode in fresh.MODES} | {
            (111,'swimming',True,1,mode) for mode in fresh.MODES}
FIELDS = ('initial_checkpoint','final_brain','history','deliveries','phase_tract','probes',
          'checkpoint_continuation_equal')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True,type=Path);p.add_argument('--shard-report',action='append',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists() or len(a.shard_report)!=4:raise ValueError('new output and four shard receipts required')
    m=json.loads(a.manifest.read_text());fresh.check_manifest(m);mh=fresh.file_hash(a.manifest)
    selected={};sources=[];shards=set()
    for report_path in a.shard_report:
        receipt=json.loads(report_path.read_text());i=receipt['shard'];cp=Path(receipt['case_file'])
        if (i not in range(4) or i in shards or receipt['manifest_sha256']!=mh or
                receipt['schema']!='half-gain-fresh-shard-v1' or receipt['cases']!=64 or
                fresh.file_hash(cp)!=receipt['case_sha256']):raise ValueError('invalid source receipt')
        shards.add(i);sources.append({'path':str(cp),'sha256':receipt['case_sha256']})
        with cp.open('rb') as stream:
            for line in stream:
                row=json.loads(line);key=fresh.row_key(row)
                if key in SELECTED:
                    if key in selected:raise ValueError('duplicate selected case')
                    fresh.validate_row(row,SELECTED);selected[key]=row
    if set(selected)!=SELECTED or shards!=set(range(4)):raise ValueError('selected cases missing')
    started=time.monotonic();checks=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        pending={pool.submit(fresh.case,(m['program'],*key)):key for key in SELECTED}
        while pending:
            done,_=wait(pending,return_when=FIRST_COMPLETED)
            for future in done:
                key=pending.pop(future);rerun=future.result();old=selected[key]
                matched={field:fresh.normalized(rerun[field])==fresh.normalized(old[field]) for field in FIELDS}
                if not all(matched.values()):raise RuntimeError(f'replay mismatch: {key} {matched}')
                checks.append({'case':list(key),'matched':matched,'steps':len(rerun['history']),
                               'elapsed_seconds':rerun['elapsed_seconds'],'cpu_seconds':rerun['cpu_seconds'],
                               'worker_peak_rss_kib_cumulative':rerun['worker_peak_rss_kib_cumulative']})
                print(f'{len(checks)}/{len(SELECTED)} replayed',flush=True)
    if fresh.file_hash(a.manifest)!=mh:raise ValueError('manifest changed during replay')
    result={'scope':'four predetermined fresh cases reconstructed from seeds and checked against saved initial checkpoints using the same frozen implementation',
            'manifest_sha256':mh,'source_sha256':fresh.file_hash(Path(__file__)),'sources':sources,
            'checks':checks,'all_match':True,'wall_seconds':time.monotonic()-started,
            'summed_case_cpu_seconds':sum(c['cpu_seconds'] for c in checks),
            'max_cumulative_worker_rss_kib':max(c['worker_peak_rss_kib_cumulative'] for c in checks),
            'limitations':['Same implementation as producer; not an independent implementation or native execution.',
              'Midpoint is newly reconstructed, not a retained producer midpoint.',
              'Largest cumulative per-worker RSS, not process-family peak.']}
    with a.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
