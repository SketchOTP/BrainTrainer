"""Adopt evidence-based novelty control for repeated LLM self-review goals."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path

from continuing_companion import digest
from habitat_store import HabitatStore, STORE_SCHEMA


def install(home: Path, evidence: Path) -> dict:
    store = HabitatStore(home)
    try:
        companion = store.load()
        if companion._llm_self_review_revision >= 2:
            return {'changed': False, 'identity': companion.identity,
                    'branch': companion._lineage['branch_id']}
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

        companion.improve_lived_self_review(actor='companion-person')
        after = companion.checkpoint_header()
        if (after['host'] != before['host'] or after['lineage'] != before['lineage'] or
                len(companion._events) != before_count + 1 or
                companion._events.prefix_digest(before_count) != before_history):
            raise ValueError('self-review improvement changed personal state or prior history')
        event = companion._events[-1]
        if (event['kind'] != 'implementation-change' or
                event['payload'].get('operation') != 'improve-lived-self-review'):
            raise ValueError('candidate lacks its attributed self-review update')
        after_history = digest(companion._events)
        (evidence / 'candidate-header.json').write_text(json.dumps({
            'schema': STORE_SCHEMA, 'companion': after, 'event_count': len(companion._events),
            'history_sha256': after_history,
        }, sort_keys=True, separators=(',', ':')) + '\n')

        store.save(companion)
        installed = json.loads(store.current.read_text())
        installed_header = dict(installed.get('companion', {}))
        installed_header.pop('events', None)
        if (installed.get('schema') != STORE_SCHEMA or installed_header != after or
                installed.get('event_count') != len(companion._events) or
                installed.get('history_sha256') != after_history):
            raise ValueError('installed checkpoint differs from the candidate')

        receipt = {
            'changed': True, 'identity': companion.identity,
            'branch': companion._lineage['branch_id'], 'tick': companion.time,
            'before_history_sha256': before_history, 'after_history_sha256': after_history,
            'before_event_count': before_count, 'after_event_count': len(companion._events),
            'identity_and_prior_history_preserved': True,
            'host_and_personal_state_unchanged': True,
            'implementation_event': event,
        }
        (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        return receipt
    finally:
        store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(install(args.home, args.evidence)))
