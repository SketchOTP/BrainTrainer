"""Resume a full-brain trial and optionally stop on severe reserve depletion.

The reserve threshold is an experiment definition, not a native death signal:
<=5% of initial glycogen AND <=30% of initial fat and muscle tissue, for every
creature. ATP-dependent organ failure and death are separately reported.
"""
import argparse,gzip,json,math,time,traceback
from pathlib import Path
from creature_brain.simulation import Simulation

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('kind',choices=('safe','depleted'))
p.add_argument('--checkpoint',type=Path)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--seconds',type=int,default=21600)
p.add_argument('--stop-on-severe-depletion',action='store_true')
a=p.parse_args()
if a.seconds<1:p.error('seconds must be positive')
if a.output.exists() and any(a.output.iterdir()):p.error('output directory must be new or empty')
a.output.mkdir(parents=True,exist_ok=True)
root=Path('runs/genome-biochemistry-verification')
sim=Simulation.load(a.checkpoint or root/('survival-'+a.kind+'-7')/'checkpoint.json')
baseline=json.loads((root/'survival-depleted-7'/'initial-state.json').read_text())
start=sim.world.time; last=None; error=None; reason='horizon'; begun=time.time()
with gzip.open(a.output/'trajectory.jsonl.gz','wt') as stream:
 try:
  for i in range(math.ceil(a.seconds/sim.dt)):
   last=sim.step()
   if any(c['commanded'] for c in last['creatures']):raise ValueError('unexpected teacher command')
   severe=all(all(c['biochemistry']['chemicals'][str(chemical)]<=baseline[c['id']]['body']['kernel']['chemicals'][chemical]*fraction for chemical,fraction in ((4,.05),(9,.3),(11,.3))) for c in last['creatures'])
   if i%10==0 or severe or any(not c['alive'] for c in last['creatures']):stream.write(json.dumps(last,allow_nan=False)+'\n')
   if i%120==0:
    (a.output/'progress.json').write_text(json.dumps({'time':sim.world.time,'creatures':last['creatures'],'wall_seconds':time.time()-begun})+'\n')
    sim.save(a.output/'checkpoint.json')
   if all(not c['alive'] for c in last['creatures']):reason='all-dead';break
   if a.stop_on_severe_depletion and severe:reason='severe-reserve-depletion';break
 except KeyboardInterrupt:reason='interrupted'
 except Exception as e:error={'error':str(e),'traceback':traceback.format_exc()};reason='error'
sim.save(a.output/'checkpoint.json')
(a.output/'summary.json').write_text(json.dumps({'start':start,'end':sim.world.time,'reason':reason,'error':error,'summary':sim.summary(),'last':last,'wall_seconds':time.time()-begun},indent=2)+'\n')
if error:raise SystemExit(1)
