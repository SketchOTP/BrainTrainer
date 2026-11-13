"""Explicit offline adoption preserving the continuing individual's before-image."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from continuing_companion import digest
from creature_brain.development import MODEL
from habitat_store import HabitatStore

def upgrade(home,evidence):
    store=HabitatStore(home)
    try:
        c=store.load()
        if c._mind.version==MODEL:return {'changed':False,'model':MODEL,'identity':c.identity}
        evidence=Path(evidence);evidence.mkdir(parents=True,exist_ok=False)
        raw=store.current.read_bytes()
        with (evidence/'original-current.json').open('xb') as stream:stream.write(raw)
        previous_model=c._mind.version
        before=c.snapshot();c.save(evidence/'before.json')
        c.enable_development(actor='qualified-habitat-upgrade')
        after=c.snapshot();expected=deepcopy(before['host']);expected['state']['rest_enabled']=True;expected['state']['hold_enabled']=True
        if after['host']!=expected or after['lineage']!=before['lineage'] or after['events'][:-1]!=before['events']:
            raise ValueError('upgrade changed state beyond the declared capability')
        c.save(evidence/'candidate.json')
        store.save(c)
        if store.load().snapshot()!=after:raise ValueError('installed checkpoint differs from candidate')
        receipt={'changed':True,'identity':c.identity,'tick':c.time,'previous_model':previous_model,
            'model':MODEL,'before_sha256':digest(before),'after_sha256':digest(after),
            'original_file_sha256':hashlib.sha256(raw).hexdigest(),
            'preserved':['identity','branch','neural state','body state except declared rest and hold capabilities','full prior history'],
            'implementation_event':after['events'][-1]}
        (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        return receipt
    finally:store.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',required=True,type=Path);p.add_argument('--evidence',required=True,type=Path)
    args=p.parse_args();print(json.dumps(upgrade(args.home,args.evidence)))
