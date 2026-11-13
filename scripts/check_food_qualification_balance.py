"""Check neutral observations and physical reachability, not brain competence."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

from creature_brain.benchmark.contract import ChosenAction
from creature_brain.benchmark.qualification import QualificationExperiment


def build(program,seed,body,task,mirror):
    return QualificationExperiment(program,seed=seed,embodiment=body,condition='feedback',
        task=task,mirror=mirror,max_steps=32,opportunities_per_phase=1)


def main(program,output):
    destination=Path(output)
    if destination.exists():raise FileExistsError('choose a new output')
    checks=[]
    # Both hidden assignments must produce identical pre-outcome observations
    # for every development seed, body, task, and mirrored configuration.
    for seed in range(16):
        for body in ('walking','swimming'):
            for task in ('preference','embodied'):
                a,b=[build(program,seed,body,task,m) for m in (False,True)]
                initial=asdict(a.observe());a.initial_good ^= 1
                assert asdict(a.observe()) == initial
                assert [x.relative_position for x in a.observe().objects] == [-x.relative_position for x in b.observe().objects]
                assert [x.category for x in a.observe().objects] == [3,8]
                checks.append((seed,body,task))
    # An explicit harness intervention uses the movement adapter then executes
    # eat on each target under each assignment. It does not test brain choice.
    access=[]
    for body in ('walking','swimming'):
        for task in ('preference','embodied'):
            for mirror in (False,True):
                for index in (0,1):
                    for good in (0,1):
                        exp=build(program,0,body,task,mirror);exp.initial_good=good
                        count=0
                        while not exp.observe().objects[index].contact and count<20:
                            obj=exp.observe().objects[index]
                            exp._move(1 if obj.relative_position>0 else -1)
                            count+=1
                        obj=exp.observe().objects[index]
                        assert obj.contact
                        before=exp.energy
                        result=exp._execute(ChosenAction('instrumented',0,12,obj.category,4,obj.identity),obj)
                        assert result.completed and result.target==obj.identity
                        assert (result.energy_delta>0)==(index==good)
                        access.append({'embodiment':body,'task':task,'mirror':mirror,'target':index,
                                       'good_index':good,'instrumented_move_steps':count,
                                       'energy_before':before,'outcome':asdict(result)})
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps({'program_sha256':hashlib.sha256(Path(program).read_bytes()).hexdigest(),
         'observational_seed_body_task_checks':len(checks),'checks':checks,'instrumented_access_checks':access,
         'scope':'host counterbalancing and physical accessibility only; no brain-selected action forced'},indent=2)+'\n')
    print(json.dumps({'output':str(destination),'observational_checks':len(checks),'access_checks':len(access)}))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
