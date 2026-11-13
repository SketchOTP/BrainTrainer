"""Restrict the live Littleroot home to the starter house and workshop."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path

from continuing_companion import digest
from habitat_store import HabitatStore, STORE_SCHEMA
from world_body import scoped_town_pack_hash, town_canopy_pack_hash, pack


def install(home: Path, evidence: Path) -> dict:
    store = HabitatStore(home)
    try:
        companion = store.load()
        world = companion._host.world
        if world is None or world.get('pack_sha256') != town_canopy_pack_hash():
            if world is not None and world.get('pack_sha256') == scoped_town_pack_hash():
                return {'changed': False, 'identity': companion.identity}
            raise ValueError('the live individual must be on Littleroot v7 before scoping v8')

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

        companion.scope_town_world(actor='companion-person')
        after = companion.checkpoint_header()
        expected = deepcopy(before['host'])
        expected_state = expected['state']['individual']
        actual_state = after['host']['state']['individual']
        for key in ('world', 'position', 'velocity', 'active_action'):
            expected_state[key] = deepcopy(actual_state[key])
        for identity, obj in expected_state['objects'].items():
            for key in ('x', 'y', 'region'):
                obj[key] = actual_state['objects'][identity][key]
        if (after['host'] != expected or after['lineage'] != before['lineage'] or
                len(companion._events) != before_count + 1 or
                companion._events.prefix_digest(before_count) != before_history):
            raise ValueError('town scope candidate changed unrelated personal state')
        event = companion._events[-1]
        if (event['kind'] != 'implementation-change' or
                event['payload'].get('operation') != 'scope-town-world'):
            raise ValueError('candidate lacks its attributed town-scope event')
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
            'prior_pack_sha256': town_canopy_pack_hash(),
            'installed_pack_sha256': scoped_town_pack_hash(),
            'active_home_regions': pack(scoped_town_pack_hash())['home_regions'],
            'excluded_live_region_labels': [
                'MAP_LITTLEROOT_TOWN_MAYS_HOUSE_1F',
                'MAP_LITTLEROOT_TOWN_MAYS_HOUSE_2F',
                'MAP_LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB',
            ],
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
