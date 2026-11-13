"""Install the town ground and tree-rim update without replacing the individual."""
import argparse
import json
import os
from pathlib import Path

from continuing_companion import digest
from habitat_store import HabitatStore, STORE_SCHEMA
from world_body import town_canopy_pack_hash


def install(home: Path, evidence: Path) -> dict:
    store = HabitatStore(home)
    try:
        companion = store.load()
        if (companion._host.world is not None and
                companion._host.world['pack_sha256'] == town_canopy_pack_hash()):
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
        companion.install_town_canopy(actor='companion-person')
        after = companion.checkpoint_header()

        expected = deepcopy(before['host'])
        state = expected['state']['individual']
        actual = after['host']['state']['individual']
        for key in ('world', 'position', 'velocity', 'active_action'):
            state[key] = deepcopy(actual[key])
        for name, obj in state['objects'].items():
            for key in ('x', 'y', 'region'):
                obj[key] = actual['objects'][name][key]
        if (after['host'] != expected or after['lineage'] != before['lineage'] or
                len(companion._events) != before_count + 1 or
                companion._events.prefix_digest(before_count) != before_history):
            raise ValueError('candidate changed state beyond the declared town visual update')
        implementation_event = companion._events[-1]
        if (implementation_event['kind'] != 'implementation-change' or
                implementation_event['payload'].get('operation') != 'install-town-canopy'):
            raise ValueError('candidate lacks the attributed town visual update record')

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
            raise ValueError('installed checkpoint differs from the candidate header')

        receipt = {
            'changed': True, 'identity': companion.identity,
            'branch': companion._lineage['branch_id'], 'tick': companion.time,
            'before_header_sha256': digest(before), 'after_header_sha256': digest(after),
            'before_history_sha256': before_history, 'after_history_sha256': after_history,
            'before_event_count': before_count, 'after_event_count': len(companion._events),
            'preserved': ['identity and branch', 'clock and random state',
                'neural and motor state', 'personal event history and learned policies',
                'objects and garden model'],
            'world_change': 'irregular grass texture patches and continuous perimeter tree canopy',
            'implementation_event': implementation_event,
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
