"""One-tick tract transfer probes, restricted to compatible same-seed brains."""
from copy import deepcopy
import hashlib
import json

from creature_brain import DefaultBrain


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def graft_tract(recipient, donor):
    """Copy the entire drive→comb tract into a compatible recipient snapshot."""
    for field in ('definition', 'seed', 'age_stage', 'sex'):
        if recipient[field] != donor[field]:
            raise ValueError('incompatible brain ' + field)
    owner = DefaultBrain.from_dict(recipient)
    indices = [i for i, t in enumerate(owner.tracts)
               if (t.gene_id, t.source_lobe, t.destination_lobe) == (7, 'driv', 'comb')]
    if len(indices) != 1:
        raise ValueError('expected exactly one gene-7 drive-combination tract')
    i = indices[0]
    result = deepcopy(recipient)
    result['tracts'][i] = deepcopy(donor['tracts'][i])
    # Validation includes all endpoint indices, variables, helper and weak queue.
    DefaultBrain.from_dict(result)
    return result, i


def probe_graft(recipient, donor, inputs, chemicals):
    """Apply one identical observation and chemical vector; execute no outcome."""
    state, index = graft_tract(recipient, donor)
    outside_before = deepcopy(state)
    outside_before['tracts'][index] = None
    reference = deepcopy(recipient)
    reference['tracts'][index] = None
    if outside_before != reference:
        raise RuntimeError('tract graft altered recipient non-target state')
    brain = DefaultBrain.from_dict(state)
    result = brain.tick(inputs=deepcopy(inputs), chemicals=chemicals.copy())
    return {'attention': result.attention, 'decision': result.decision, 'action': result.action,
            'target': {3: 'object-0', 8: 'object-1'}.get(result.attention),
            'recipient_except_tract_sha256': digest(reference),
            'donor_tract_sha256': digest(state['tracts'][index]),
            'post_tick_brain_sha256': digest(brain.to_dict())}
