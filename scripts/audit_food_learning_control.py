"""Controlled reconstruction audit, not a whole-learning-off claim."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from creature_brain import DefaultBrain
from creature_brain.benchmark.migration_gate import suppress_drive_comb_migration

ROOT=Path(__file__).resolve().parents[1]
PROGRAM=ROOT/'research/docking-station-20261103/resources/chichi-brain-program.json'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def main(output):
    original=DefaultBrain.from_file(PROGRAM,seed=1,age_stage=1)
    t=original.tracts[5];t.weak=[0,1,2,3,4]
    original.lobes['comb'].neurons[163][t.destination_variable]=1
    original.queue_inputs({'resp':{2:-.25,3:-.153225839}})
    baseline=original.to_dict()
    on,off=DefaultBrain.from_dict(baseline),DefaultBrain.from_dict(baseline)
    on_entry=[];off_entry=[];normal=on._migrate
    def observe(tract):
        if (tract.gene_id,tract.source_lobe,tract.destination_lobe)==(7,'driv','comb'):
            on_entry.append(on.to_dict())
        normal(tract)
    on._migrate=observe
    on.tick()
    with suppress_drive_comb_migration(off,off_entry.append):off.tick()
    del on._migrate
    control_snapshot=off.to_dict()
    restored=DefaultBrain.from_dict(json.loads(json.dumps(control_snapshot)))
    with suppress_drive_comb_migration(off):off.tick()
    with suppress_drive_comb_migration(restored):restored.tick()
    # Repeat without an eligible migration: whole checkpoint and output match.
    a=DefaultBrain.from_file(PROGRAM,seed=2,age_stage=1);b=DefaultBrain.from_dict(a.to_dict())
    a.tick();b.tick()
    c=DefaultBrain.from_dict(a.to_dict())
    with suppress_drive_comb_migration(c):out_c=c.tick()
    out_a=a.tick()
    # A captured partial-state reconstruction retains nonzero weight changes
    # even while this structural control is active.
    source=ROOT/'research/docking-station-20261103/brain-connections-20261106/queue-causal-replay/compare.py'
    spec=importlib.util.spec_from_file_location('weight_probe',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    brain=module.branches()['nonprefix'];tract=brain.tracts[5];before=[d.variables[:2] for d in tract.dendrites]
    with suppress_drive_comb_migration(brain):brain.tick({'driv':{9:1,12:1},'visn':{3:.5}})
    weights=[{'record':i,'before':v,'after':d.variables[:2]} for i,(v,d) in enumerate(zip(before,tract.dendrites)) if v!=d.variables[:2]]
    result={'schema':1,'scope':'reconstruction-only opt-in gene-7 structural migration ablation',
            'pre_first_migration_snapshots_equal':on_entry==off_entry,
            'pre_first_migration_sha256':digest(on_entry[0]),
            'ordinary_first_two_endpoints':[(d.source,d.destination) for d in on.tracts[5].dendrites[:2]],
            'gated_first_two_endpoints':[(d.source,d.destination) for d in DefaultBrain.from_dict(control_snapshot).tracts[5].dendrites[:2]],
            'gated_migrations':control_snapshot['tracts'][5]['migrations'],
            'no_eligible_migration_entire_tick_equal':out_a==out_c and a.to_dict()==c.to_dict(),
            'gated_checkpoint_continuation_equal':off.to_dict()==restored.to_dict(),
            'weight_states_changing_despite_gate':weights,
            'qualification':'structural drive-to-combination migration ablation only; weights and other learning remain active',
            'general_learning_disabled':False}
    path=Path(output)
    if path.exists():raise FileExistsError('choose a new output')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main(sys.argv[1])
