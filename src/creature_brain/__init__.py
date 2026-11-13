"""Brain-first public API; simulation and body components load on demand.

``DefaultBrain`` names the genome-driven neural kernel. A caller must supply a
supported brain program and own sensory, action, timing, and body integration.
"""
from importlib import import_module

_EXPORTS = {
    'DefaultBrain': ('.neural', 'GenomeBrain'),
    'GenomeBrain': ('.neural', 'GenomeBrain'),
    'SensoryRoute': ('.sensory', 'SensoryRoute'),
    'route_sensory_adjustment': ('.sensory', 'route_sensory_adjustment'),
    'Brain': ('.core', 'Brain'),
    'BrainConfig': ('.core', 'BrainConfig'),
    'Candidate': ('.core', 'Candidate'),
    'Decision': ('.core', 'Decision'),
    'LearningResult': ('.core', 'LearningResult'),
    'ObservedObject': ('.core', 'ObservedObject'),
    'Physiology': ('.physiology', 'Physiology'),
    'PhysiologyConfig': ('.physiology', 'PhysiologyConfig'),
    'SocialMemory': ('.social', 'SocialMemory'),
    'Creature': ('.simulation', 'Creature'),
    'Simulation': ('.simulation', 'Simulation'),
    'World': ('.world', 'World'),
    'WorldObject': ('.world', 'WorldObject'),
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    try:
        module, member = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}') from None
    value = getattr(import_module(module, __name__), member)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
