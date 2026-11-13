"""Enable rest-linked reflective dreaming without replacing the individual."""
import argparse
import json
import os
from pathlib import Path

from continuing_companion import digest
from habitat_store import HabitatStore, STORE_SCHEMA


def enable(home: Path, evidence: Path) -> dict:
    store = HabitatStore(home)
    try:
        companion = store.load()
        if companion._llm_dreams_enabled:
            return {'changed': False, 'identity': companion.identity}
        evidence.mkdir(parents=True, exist_ok=False)
        try:
            os.link(store.current, evidence / 'original-current.json')
        except OSError:
            (evidence / 'original-current.json').write_bytes(store.current.read_bytes())
        before = companion.checkpoint_header()
        before_count = len(companion._events)
        before_history = digest(companion._events)
        (evidence / 'before-header.json').write_text(json.dumps({
            'schema': STORE_SCHEMA, 'companion': before, 'event_count': before_count,
            'history_sha256': before_history,
        }, sort_keys=True, separators=(',', ':')) + '\n')
        companion.enable_reflective_dreams(actor='companion-person')
        after = companion.checkpoint_header()
        if (after['host'] != before['host'] or after['lineage'] != before['lineage'] or
                len(companion._events) != before_count + 1 or
                companion._events.prefix_digest(before_count) != before_history):
            raise ValueError('dream-cycle adoption changed prior personal state')
        event = companion._events[-1]
        if (event['kind'] != 'implementation-change' or
                event['payload'].get('operation') != 'enable-rest-linked-reflective-dreams'):
            raise ValueError('dream-cycle adoption lacks its attributed implementation event')
        after_history = digest(companion._events)
        (evidence / 'candidate-header.json').write_text(json.dumps({
            'schema': STORE_SCHEMA, 'companion': after, 'event_count': len(companion._events),
            'history_sha256': after_history,
        }, sort_keys=True, separators=(',', ':')) + '\n')
        store.save(companion)
        installed = json.loads(store.current.read_text())
        header = dict(installed.get('companion', {}));header.pop('events', None)
        if (installed.get('schema') != STORE_SCHEMA or header != after or
                installed.get('event_count') != len(companion._events) or
                installed.get('history_sha256') != after_history):
            raise ValueError('installed checkpoint differs from the candidate header')
        receipt = {'changed': True, 'identity': companion.identity,
            'branch': companion._lineage['branch_id'], 'tick': companion.time,
            'before_history_sha256': before_history, 'after_history_sha256': after_history,
            'before_event_count': before_count, 'after_event_count': len(companion._events),
            'prior_host_state_preserved': True,
            'implementation_event': event,
            'scope': 'bounded OAuth reflection after observed rest; hypotheses only until later embodied outcomes'}
        (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        return receipt
    finally:
        store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(enable(args.home, args.evidence)))
