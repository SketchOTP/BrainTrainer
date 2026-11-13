"""Compare two isolated Docking Station chemical recordings with the model.

Both runs use one female stage1 creature in a neutral world with no food,
then one STIM79 of strength0.125. Values from CAOS are rounded to six places.
"""
from pathlib import Path
import hashlib,json
from creature_brain.body import DEFAULT_GENOME
from creature_brain.genome_physiology import GenomePhysiology

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'research/docking-station-20261103/runtime-calibration'
CAPTURES=(BASE/'captured/stage1-child-live.json',BASE/'captures/20261103T204404Z-age1-female-full/logs/calibration.json')
CHEMICALS=(34,35,36,4,9,11,2,3,6,12,5,10,149,150,151)


def compare():
    comparisons=[];full_baseline=None;organs=None
    for capture in CAPTURES:
        records=json.loads(capture.read_text())
        body=GenomePhysiology.from_file(DEFAULT_GENOME,age_stage=1,sex='female',tick_seconds=.2)
        count=0;fed=False
        for row in records:
            label=row['label']
            if label in ('fed_stim79','fed_stim79_atomic'):
                if body.kernel.ticks not in (40,41):raise ValueError('unexpected native tick position')
                body.stimulate(79,.125);fed=True;continue
            if label=='adult_all_chemicals':
                values=row['response'].split()
                if values[0]!='CHEM' or len(values)!=257:raise ValueError('invalid full chemical baseline')
                body.step(.2)
                full_baseline=max(abs(a-float(b)) for a,b in zip(body.chemicals,values[1:]))
                continue
            if not (label=='baseline' and capture==CAPTURES[1] or label.startswith('nofood_') or label.startswith('fed_')):continue
            values=row['response'].split()
            if values[0]!='OBS' or len(values)!=7+len(CHEMICALS):raise ValueError('invalid captured observation')
            if int(values[5])!=1:raise ValueError('unexpected native life stage')
            age_ticks=int(values[6])
            if age_ticks%4:raise ValueError('observation is not at a creature tick boundary')
            target=age_ticks//4
            if target<body.kernel.ticks:raise ValueError('captured age moved backwards')
            while body.kernel.ticks<target:body.step(.2)
            differences={str(i):body.chemicals[i]-float(v) for i,v in zip(CHEMICALS,values[7:])}
            comparisons.append({'capture':capture.name,'label':label,'native_age_ticks':age_ticks,
                                'model_biochemical_ticks':target,'phase':'stim79' if fed else 'no-food',
                                'max_absolute_difference':max(abs(v) for v in differences.values()),
                                'differences':differences})
            count+=1
        if not fed or count!=(17 if capture==CAPTURES[0] else 18):raise ValueError('capture coverage incomplete')
    findings=json.loads((BASE/'findings.json').read_text())
    native_organs=findings['organs']
    body=GenomePhysiology.from_file(DEFAULT_GENOME,age_stage=1,sex='female',tick_seconds=.2);body.step(.2)
    if len(native_organs)!=len(body.kernel.organs):raise ValueError('organ count mismatch')
    errors=[]
    for actual,model in zip(native_organs,body.kernel.organs):
        counts=(model.definition.receptor_count,len(model.definition.emitters),len(model.definition.reactions))
        if counts!=(actual['receptors'],actual['emitters'],actual['reactions']):raise ValueError('organ gene count mismatch')
        errors.append(abs(model.definition.energy_cost-actual['energy_cost']))
    organs={'count':len(native_organs),'counts_match':True,'max_energy_cost_difference':max(errors)}
    maximum=max(x['max_absolute_difference'] for x in comparisons)
    passed=maximum<2e-5 and full_baseline<2e-5 and organs['max_energy_cost_difference']<2e-5
    return {'status':'passed' if passed else 'difference-exceeds-tolerance',
            'captures':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in CAPTURES],
            'template_genome_sha256':body.kernel.source_sha256,
            'runtime_genome_copy_sha256':findings['runtime_genome_copy']['sha256'],
            'genome_identity_note':'Runtime file differs in parental-name bytes and opaque trailing data; compare expressed gene records, not whole-file hashes.',
            'model_profile':'0.2-second nominal biochemical update',
            'organism':'female stage1 Chichi, isolated neutral world','chemical_ids':CHEMICALS,
            'sample_count':len(comparisons),'max_absolute_difference':maximum,'tolerance':2e-5,
            'all_256_chemical_baseline_max_difference':full_baseline,'organs':organs,'samples':comparisons,
            'scope':'Two isolated native runs at one life stage; six-decimal CAOS readouts, controlled no-food/STIM79. No long-term, full-world, x87 bitwise, or biological validation.'}


if __name__=='__main__':
    result=compare();path=ROOT/'runs/nominal-survival/native-physiology-comparison.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','sample_count','max_absolute_difference','all_256_chemical_baseline_max_difference','organs','scope')},indent=2))
    if result['status']!='passed':raise SystemExit(1)
