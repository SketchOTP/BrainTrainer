"""Environment authoring jobs; world rules remain owned by the simulation.

A package is a proposal, not executable behavior or a learned creature skill.
Existing native art can satisfy it without commissioning replacement artwork.
"""
import hashlib
import json
from pathlib import Path
from asset_generation import prepare


def validate_package(package):
    if not isinstance(package, dict):
        raise ValueError('environment package required')
    for key in ('object_type', 'purpose', 'basis'):
        if not isinstance(package.get(key), str) or not package[key].strip():
            raise ValueError(f'{key} required')
    states = package.get('states')
    if not isinstance(states, list) or not 1 <= len(states) <= 32 or any(
        not isinstance(s, str) or not s.strip() for s in states
    ) or len(set(states)) != len(states):
        raise ValueError('unique visual states required')
    if type(package.get('walkable')) is not bool:
        raise ValueError('explicit collision behavior required')
    transitions = package.get('transitions')
    if not isinstance(transitions, list) or not transitions:
        raise ValueError('interaction or growth transitions required')
    for transition in transitions:
        if not isinstance(transition, dict) or transition.get('from') not in states or transition.get('to') not in states:
            raise ValueError('transition references unknown visual state')
        trigger = transition.get('trigger')
        if trigger == 'interaction':
            if type(transition.get('action')) is not int or transition['action'] < 0 or type(transition.get('requires_contact')) is not bool:
                raise ValueError('explicit action and contact requirement required')
            if not isinstance(transition.get('failure'), str) or not transition['failure'].strip():
                raise ValueError('failed interaction behavior required')
        elif trigger == 'world-ticks':
            if type(transition.get('duration')) is not int or transition['duration'] < 1:
                raise ValueError('positive world tick duration required')
        else:
            raise ValueError('unknown transition trigger')
        if not isinstance(transition.get('effects'), list) or any(not isinstance(s, str) or not s.strip() for s in transition['effects']):
            raise ValueError('explicit resource effects required')
    return package


def prepare_environment(directory, *, package, references, cell_width, cell_height):
    """Commission all visual states together; preserve behavior for qualification.

    No state change, collision change or resource effect is installed here.
    """
    validate_package(package)
    # Freeze the caller's proposal and bind it to the exact artwork request.
    encoded = json.dumps(package, sort_keys=True, allow_nan=False)
    folder = prepare(directory, owner='environment-object', requirement=(
        'Create a native rural overworld object matching the attached town assets. '
        'All states must keep the same footprint and anchor. Show resource depletion '
        'and recovery honestly; do not add decorations that resemble usable resources. '
        'Behavior proposal (artwork does not implement it): ' + encoded),
        references=references, cell_width=cell_width, cell_height=cell_height,
        states=package['states'])
    record = {'package': json.loads(encoded), 'package_sha256': hashlib.sha256(encoded.encode()).hexdigest(),
              'asset_request_id': json.loads((folder/'request.json').read_text())['request_id'],
              'status': 'candidate-requested', 'installed': False,
              'required_qualification': ['native-scale visual inspection in town',
                  'actual contact and failed interaction trials',
                  'resource conservation and world-clock transitions',
                  'collision and doorway connectivity', 'checkpoint continuity'],
              'learning_claim': 'none; creature must experience the installed object'}
    (folder/'environment-package.json').write_text(json.dumps(record, indent=2))
    return folder
