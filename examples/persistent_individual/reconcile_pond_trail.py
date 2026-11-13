"""Install the connected v10 pond-bank trail without clearing the live route."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path

from continuing_companion import digest
from garden import GROWTH_MODEL
from habitat_store import HabitatStore, STORE_SCHEMA
from world_body import connected_town_pack_hash, natural_town_pack_hash


def install(home: Path, evidence: Path) -> dict:
    store = HabitatStore(home)
    try:
        companion = store.load()
        world = companion._host.world
        if world is None or world.get('home_region') != 'MAP_LITTLEROOT_TOWN':
            raise ValueError('the saved Littleroot home is required')
        if world.get('pack_sha256') != natural_town_pack_hash():
            raise ValueError('the live individual must be on v9 before the pond-path update')
        if companion._host.active_action is not None:
            raise ValueError('finish the current body action before the visual path update')
        garden = world.get('garden')
        if garden is not None and garden.get('model') != GROWTH_MODEL:
            raise ValueError('the live berry garden must use growth model v2')

        evidence.mkdir(parents=True, exist_ok=False)
        try:
            os.link(store.current, evidence / 'original-current.json')
        except OSError:
            (evidence / 'original-current.json').write_bytes(store.current.read_bytes())
        before = companion.checkpoint_header()
        before_count = len(companion._events)
        before_history = digest(companion._events)
        before_identity = companion.identity
        before_lineage = deepcopy(companion._lineage)
        before_tick = companion.time
        before_host = deepcopy(before['host'])
        before_world = deepcopy(world)
        (evidence / 'before-header.json').write_text(json.dumps({
            'schema': STORE_SCHEMA, 'companion': before, 'event_count': before_count,
            'history_sha256': before_history,
        }, sort_keys=True, separators=(',', ':')) + '\n')

        companion.connect_pond_trail(actor='companion-person')
        after = companion.checkpoint_header()
        individual = after['host']['state']['individual']
        expected_host = before_host
        expected_individual = expected_host['state']['individual']
        expected_individual['world']['pack_sha256'] = connected_town_pack_hash()
        if garden is not None:
            expected_individual['world']['garden']['pack_sha256'] = connected_town_pack_hash()
        if (companion.identity != before_identity or companion._lineage != before_lineage or
                companion.time != before_tick or after['host'] != expected_host or
                len(companion._events) != before_count + 1 or
                companion._events.prefix_digest(before_count) != before_history):
            raise ValueError('pond path update changed state beyond the declared pack references')
        event = companion._events[-1]
        if (event.get('kind') != 'implementation-change' or
                event.get('payload', {}).get('operation') != 'connect-pond-trail'):
            raise ValueError('pond path update lacks its attributed implementation event')
        if individual['world']['pack_sha256'] != connected_town_pack_hash():
            raise ValueError('candidate checkpoint does not reference v10')

        after_history = digest(companion._events)
        (evidence / 'candidate-header.json').write_text(json.dumps({
            'schema': STORE_SCHEMA, 'companion': after, 'event_count': len(companion._events),
            'history_sha256': after_history,
        }, sort_keys=True, separators=(',', ':')) + '\n')
        store.save(companion)
        checkpoint = json.loads(store.current.read_text())
        saved_header = dict(checkpoint.get('companion', {}))
        saved_header.pop('events', None)
        if (checkpoint.get('schema') != STORE_SCHEMA or saved_header != after or
                checkpoint.get('event_count') != len(companion._events) or
                checkpoint.get('history_sha256') != after_history):
            raise ValueError('installed checkpoint differs from the v10 candidate')

        receipt = {
            'changed': True, 'identity': before_identity,
            'branch': before_lineage['branch_id'], 'tick': before_tick,
            'event_count_before': before_count, 'event_count_after': len(companion._events),
            'history_prefix_sha256': before_history, 'old_pack_sha256': natural_town_pack_hash(),
            'new_pack_sha256': connected_town_pack_hash(),
            'current_goal_preserved': before_world.get('goal') == individual['world'].get('goal'),
            'route_preserved': before_world.get('route') == individual['world'].get('route'),
            'garden_model': (individual['world'].get('garden') or {}).get('model'),
            'implementation_event_sequence': event['sequence'],
            'validation': 'same identity, branch, clock, body route, personal history and garden state verified',
        }
        (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        return receipt
    finally:
        store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.home, args.evidence), indent=2))
