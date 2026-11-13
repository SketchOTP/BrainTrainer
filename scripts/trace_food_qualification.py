"""Trace brain-chosen single-food actions and the subsequent feedback tick."""
import hashlib
import json
from pathlib import Path
import sys

from creature_brain.benchmark.qualification import QualificationExperiment


def main(program, output):
    output=Path(output)
    if output.exists():raise FileExistsError('choose a new output')
    rows=[]
    for body in ('walking','swimming'):
        for task in ('single_contact','single_distance'):
            for index in (0,1):
                exp=QualificationExperiment(program,seed=index,embodiment=body,condition='feedback',
                       task=task,food_index=index,max_steps=32,opportunities_per_phase=1,trace=True)
                while exp.opportunity == 0:
                    exp.tick()
                completed=exp.history[-1]['outcome']['completed']
                if completed:
                    exp.tick()  # deliver the completed event's pending response
                rows.append({'embodiment':body,'task':task,'food_index':index,
                             'completed_first_opportunity':completed,'events':exp.history})
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'program_sha256':hashlib.sha256(Path(program).read_bytes()).hexdigest(),
                                  'scope':'brain-chosen actions; feedback tick only after consumption',
                                  'cases':rows},allow_nan=False,indent=2)+'\n')
    print(json.dumps({'output':str(output),'completed':sum(r['completed_first_opportunity'] for r in rows),'cases':len(rows)}))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
