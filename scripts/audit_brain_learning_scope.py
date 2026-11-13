"""Conservative inventory of rule writes, not proof of runtime execution."""
from collections import Counter
import hashlib,json,sys
from pathlib import Path

from creature_brain import DefaultBrain
from creature_brain.neural import Lobe


def main(program,output):
    out=Path(output)
    if out.exists():raise FileExistsError('choose new output')
    brain=DefaultBrain.from_file(program,seed=1,age_stage=1)
    findings=[];counts=Counter()
    for component in brain.components:
        kind='lobe' if isinstance(component,Lobe) else 'tract'
        for name in ('init_rule','update_rule'):
            rule=getattr(component,name)
            for pc,ins in enumerate(rule.instructions):
                if ins.opcode==0:break
                destination=None
                if ins.opcode in (1,2,34,35,45) and ins.operand in (1,2,3,4):
                    destination={1:'source_neuron',2:'dendrite',3:'destination_neuron',4:'spare_neuron'}[ins.operand]
                elif ins.opcode==44:destination='dendrite_consolidation_0_1'
                elif ins.opcode in (43,57,58,59,60,61,62):destination='tract_helper'
                elif ins.opcode in (63,64):destination='destination_neuron_preserved_slot'
                elif ins.opcode in (65,66):destination='spare_neuron_preserved_slot'
                elif ins.opcode==42:destination='winner_competition_neurons'
                if destination:
                    counts[destination]+=1
                    findings.append({'kind':kind,'gene_id':component.gene_id,'component':component.name if kind=='lobe' else f'{component.source_lobe}->{component.destination_lobe}',
                        'rule':name,'pc':pc,'opcode':ins.opcode,'operand':ins.operand,'data':ins.data,'possible_write':destination})
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'program_sha256':hashlib.sha256(Path(program).read_bytes()).hexdigest(),
      'scope':'conservative static scan until first unconditional stop, not an execution trace or exhaustive proof of learning state',
      'counts':counts,'records':findings,'migrating_tracts':[{'gene_id':t.gene_id,'source':t.source_lobe,'destination':t.destination_lobe} for t in brain.tracts if t.migrates]},indent=2)+'\n')
    print(json.dumps({'output':str(out),'counts':counts,'records':len(findings)}))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
