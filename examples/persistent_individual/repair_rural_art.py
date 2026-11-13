"""Offline owner-directed native tree assembly repair, preserving the individual."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from continuing_companion import ContinuingCompanion,digest
from habitat_store import HabitatStore
from world_body import visual_pack_hash

def configure(home,evidence):
    store=HabitatStore(home)
    try:
        c=store.load()
        if c._host.world is not None and c._host.world['pack_sha256']==visual_pack_hash():return {'changed':False,'identity':c.identity}
        evidence=Path(evidence);evidence.mkdir(parents=True,exist_ok=False)
        (evidence/'original-current.json').write_bytes(store.current.read_bytes())
        before=c.snapshot();c.save(evidence/'before.json')
        c.repair_rural_art(actor='companion-person');after=c.snapshot()
        expected=deepcopy(before['host']);state=expected['state']['individual'];actual=after['host']['state']['individual']
        for key in ('world','position','velocity','active_action'):state[key]=deepcopy(actual[key])
        for name,obj in state['objects'].items():
            for key in ('x','y','region'):obj[key]=actual['objects'][name][key]
        if after['host']!=expected or after['lineage']!=before['lineage'] or after['events'][:-1]!=before['events']:
            raise ValueError('migration changed state beyond the declared body relocation')
        if ContinuingCompanion.restore(after).snapshot()!=after:raise ValueError('candidate does not restore exactly')
        c.save(evidence/'candidate.json');store.save(c)
        if store.load().snapshot()!=after:raise ValueError('installed state differs from candidate')
        receipt={'changed':True,'identity':c.identity,'branch':c._lineage['branch_id'],'tick':c.time,
            'before_sha256':digest(before),'after_sha256':digest(after),
            'preserved':['identity','branch','clock','neural state','random state','motor model','personal history','learned practice policies','object behavior'],
            'body_changes':['body coordinates and facing','complete native trees; roofs preserved; pond, farm and doors unchanged','object locations','pending action explicitly cancelled for owner-directed relocation'],
            'implementation_event':after['events'][-1]}
        (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
    finally:store.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(configure(args.home,args.evidence)))
