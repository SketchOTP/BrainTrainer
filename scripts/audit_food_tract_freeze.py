"""Matched replay qualification for the gene-7 persistent-state control."""
import hashlib,json,sys
from pathlib import Path
from creature_brain import DefaultBrain
from creature_brain.benchmark.connection_freeze import freeze_drive_comb_tract_state

ROOT=Path(__file__).resolve().parents[1]
PROGRAM=ROOT/'research/docking-station-20261103/resources/chichi-brain-program.json'


def sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def main(output):
    path=Path(output)
    if path.exists():raise FileExistsError('choose a new output')
    initial=DefaultBrain.from_file(PROGRAM,seed=1,age_stage=1)
    t=initial.tracts[5];t.weak=[0,1,2,3,4]
    initial.lobes['comb'].neurons[163][t.destination_variable]=1
    initial.queue_inputs({'resp':{2:-.25,3:-.153225839}})
    snapshot=initial.to_dict();normal=DefaultBrain.from_dict(snapshot);controlled=DefaultBrain.from_dict(snapshot)
    normal_entry=[];normal_exit=[];old=normal._update_tract
    def watch(t):
        target=(t.gene_id,t.source_lobe,t.destination_lobe)==(7,'driv','comb')
        if target:normal_entry.append(normal.to_dict())
        result=old(t)
        if target:normal_exit.append(normal.to_dict())
        return result
    normal._update_tract=watch
    out_n=normal.tick();del normal._update_tract
    ctrl_entry=[];ctrl_exit=[]
    with freeze_drive_comb_tract_state(controlled,before=ctrl_entry.append,before_discard=ctrl_exit.append):out_c=controlled.tick()
    n,c=normal.to_dict(),controlled.to_dict();original_tract=snapshot['tracts'][5]
    frozen_tract_equal=c['tracts'][5]==original_tract;normal_tract_changed=n['tracts'][5]!=original_tract
    del n['tracts'][5];del c['tracts'][5]
    post_tick_other_equal=n==c
    saved=json.loads(json.dumps(controlled.to_dict()));restored=DefaultBrain.from_dict(saved)
    with freeze_drive_comb_tract_state(controlled):controlled.tick()
    with freeze_drive_comb_tract_state(restored):restored.tick()
    result={'scope':'controlled reconstruction, gene-7 tract persistent-state freeze only',
       'initial_sha256':sha(snapshot),'entry_state_equal':normal_entry==ctrl_entry,
       'before_discard_full_state_equal':normal_exit==ctrl_exit,
       'first_tick_output_equal':out_n==out_c,'post_tick_non_target_state_equal':post_tick_other_equal,
       'frozen_tract_equal_to_initial':frozen_tract_equal,'normal_tract_changed':normal_tract_changed,
       'normal_migrated_endpoints':[(d.source,d.destination) for d in normal.tracts[5].dendrites[:2]],
       'frozen_endpoints':[(d.source,d.destination) for d in DefaultBrain.from_dict(saved).tracts[5].dendrites[:2]],
       'checkpoint_continuation_equal':controlled.to_dict()==restored.to_dict(),
       'full_learning_disabled_qualified':False,
       'limitation':'other tracts, retained neurons, and later state divergence remain; no complete native-state or global learning ablation claim'}
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main(sys.argv[1])
