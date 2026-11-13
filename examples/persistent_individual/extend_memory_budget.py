"""Offline, attributed capacity extension with a preserved portable before-image."""
import argparse,json
from pathlib import Path
from habitat_store import HabitatStore
from continuing_companion import digest

def extend(home,capacity,evidence,actor):
    store=HabitatStore(home)
    try:
        c=store.load();before=c.snapshot()
        # Validate on a separate restored envelope before creating evidence or writing the store.
        candidate=c.restore(before);candidate.extend_memory_budget(capacity,actor=actor)
        after=candidate.snapshot()
        assert after['events'][:-1]==before['events'] and after['host']==before['host'] and after['lineage']==before['lineage']
        evidence=Path(evidence);evidence.mkdir(parents=True,exist_ok=False)
        c.save(evidence/'before.json');candidate.save(evidence/'candidate.json')
        store.save(candidate)
        if store.load().snapshot()!=after:raise ValueError('stored memory extension differs from candidate')
        receipt={'identity':c.identity,'tick':c.time,'previous_capacity':before['event_capacity'],
            'capacity':capacity,'before_sha256':digest(before),'after_sha256':digest(after),
            'change':'external memory allocation; exact prior history and host preserved'}
        (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
    finally:store.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',required=True,type=Path);parser.add_argument('--capacity',required=True,type=int)
    parser.add_argument('--evidence',required=True,type=Path);parser.add_argument('--actor',required=True)
    args=parser.parse_args();print(json.dumps(extend(args.home,args.capacity,args.evidence,args.actor)))
