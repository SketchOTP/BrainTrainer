"""Test gene-7 freeze after a brain-chosen food event in the reconstruction."""
import hashlib,json,sys
from pathlib import Path
from creature_brain.benchmark.qualification import QualificationExperiment
from creature_brain.benchmark.connection_freeze import freeze_drive_comb_tract_state


def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main(program,output):
    dest=Path(output)
    if dest.exists():raise FileExistsError('choose a new output')
    exp=QualificationExperiment(program,seed=0,embodiment='walking',condition='feedback',
          task='single_contact',food_index=0,trace=False,max_steps=32,opportunities_per_phase=2)
    while not exp.pending and exp.time<32:exp.tick()
    if not exp.pending:raise RuntimeError('brain did not generate a completed outcome')
    snapshot=json.loads(json.dumps(exp.snapshot()))
    normal=QualificationExperiment.restore(snapshot);frozen=QualificationExperiment.restore(snapshot)
    before=normal.brain.to_dict()['tracts'][5]
    n_in=[];n_out=[];old=normal.brain._update_tract
    def observe(t):
        wanted=(t.gene_id,t.source_lobe,t.destination_lobe)==(7,'driv','comb')
        if wanted:n_in.append(normal.brain.to_dict())
        x=old(t)
        if wanted:n_out.append(normal.brain.to_dict())
        return x
    normal.brain._update_tract=observe
    event_n=normal.tick();del normal.brain._update_tract
    c_in=[];c_out=[]
    with freeze_drive_comb_tract_state(frozen.brain,before=c_in.append,before_discard=c_out.append):
        event_c=frozen.tick()
    n,c=normal.brain.to_dict(),frozen.brain.to_dict()
    changed=n['tracts'][5]!=before;frozen_equal=c['tracts'][5]==before
    del n['tracts'][5];del c['tracts'][5]
    res={'scope':'reconstruction, brain-selected completed food event, one matched feedback tick; not native runtime',
      'completed_action':exp.history[-1]['choice'],'completed_outcome':exp.history[-1]['outcome'],
      'pending_feedback':snapshot['pending'],'initial_experiment_sha256':digest(snapshot),
      'entry_state_equal':n_in==c_in,'pre_discard_state_equal':n_out==c_out,
      'tick_events_equal':event_n==event_c,'post_tick_non_target_brain_state_equal':n==c,
      'normal_target_tract_changed':changed,'controlled_target_tract_frozen':frozen_equal,
      'ordinary_tract_weak':normal.brain.tracts[5].weak,'frozen_tract_weak':frozen.brain.tracts[5].weak,
      'learning_disabled_global':False}
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
