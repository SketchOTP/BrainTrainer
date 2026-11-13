"""Genome-owned biochemistry with an explicit physical-world/life adapter.

Nutrients, reactions, half-lives, emitters, organ condition, and twenty body
needs belong to Biochemistry. Hunger is never computed as inverse food stores.
The adapter adds world exposure/event recipes and a declared sleep-stage clock;
it is not a complete reconstruction of native skeletal, sensory or life code.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import math
import json
import struct
from pathlib import Path
from typing import Mapping

from .biochemistry import Biochemistry
from .genome import codon, expressed


def _number(value, name, low=0.0, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be numeric')
    value = float(value)
    if not math.isfinite(value) or value < low or (high is not None and value > high):
        raise ValueError(f'{name} is outside its finite permitted range')
    return value


def _clip(value):
    return min(1.0, max(0.0, value))


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _compile_stimuli(records, age_stage, sex):
    selected = {}
    for record in records:
        header, fields = record['header'], record['fields']
        if expressed(header, age_stage, sex):
            selected[fields['stimulus']] = {'kind': 'stimulus',
                                           'header': dict(header), 'fields': dict(fields),
                                           'offset': record.get('offset')}
    return tuple(json.dumps(selected[k], sort_keys=True) for k in sorted(selected))


@dataclass(frozen=True)
class GenomePhysiologyConfig:
    """Adapter values, in simulated seconds; none are genome reaction rates."""
    nrem_duration: float = 30.0
    rem_duration: float = 15.0
    minimum_sleep: float = 90.0
    maximum_sleep: float = 300.0
    auto_sleep_refractory: float = 60.0
    basal_activity: float = 0.15
    nearby_scale: float = 12.0
    air_quality: float = 1.0
    thermal_stimulus_rate: float = 0.01
    threat_stimulus_rate: float = 0.01
    separation_stimulus_rate: float = 0.002

    def __post_init__(self):
        for name, value in asdict(self).items():
            _number(value, name)
        if min(self.nrem_duration, self.rem_duration, self.nearby_scale) <= 0:
            raise ValueError('stage durations and nearby scale must be positive')
        if self.maximum_sleep < self.minimum_sleep or self.maximum_sleep == 0:
            raise ValueError('maximum sleep must cover minimum sleep')
        _number(self.basal_activity, 'basal_activity', 0, 1)
        _number(self.air_quality, 'air_quality', 0, 1)


class GenomePhysiology:
    """A body whose metabolic state and need outputs come from actual genes.

    ``health`` preserves the recovered native display definition: chemical4,
    Glycogen. It is not an average of organ health and can be zero while alive.
    Death is latched only by the recovered life-death receptor (1,3,0).
    ``organ_health`` exposes organ state separately. No handwritten starvation
    timer or inverse-nutrient hunger pathway is used.
    """
    MODEL = 'genome-physiology-v1'
    SCHEMA = 1
    SLEEP_STATES = ('awake', 'nrem', 'rem')
    FOOD_CHEMICALS = {'protein': 12, 'starch': 5, 'fat': 10}
    DRIVE_LOCUS = (1, 5)
    DEATH_LOCUS = (1, 3, 0)
    ADAPTATIONS = (
        'The host selects the biochemical update interval; nominal 0.2 seconds derives from native default tick scheduling, not a measured runtime clock.',
        'Physical exposure to temperature/threat/separation supplies explicit chemical stimuli; coefficients are original world-adapter choices.',
        'Genomic STIM food recipes own hunger relief and nutrition; explicit raw ingredient dosing is a separate mode. Generic toxin is modeled as Glycotoxin70.',
        'Muscular activity, nearby-count normalization, air availability and altitude are world-to-emitter adapter values.',
        'Sleep stage timing and maximum sleep duration are an original scheduler; asleep emitter locus and PreREM212/REM213 channel identities are native-informed.',
        'Social pat/slap recipes use expressed STIM2/4; source-agent/action learning gates remain host-owned.',
        'Full skeletal physiology, reproduction and automatic native age-stage transitions are not implemented here.',
    )

    def __init__(self, kernel: Biochemistry, config: GenomePhysiologyConfig | None = None):
        if not isinstance(kernel, Biochemistry):
            raise TypeError('GenomePhysiology requires a Biochemistry kernel')
        self.kernel = kernel
        self.config = config or GenomePhysiologyConfig()
        # The genome parser/immutable definition has one owner. This is a
        # compiled expressed-STIM cache, not a second source representation.
        stimulus_records = [row for row in json.loads(kernel.definition.canonical_json)['records']
                            if row['kind'] == 'stimulus']
        self._stimuli = _compile_stimuli(stimulus_records, kernel.age_stage, kernel.sex)
        self.last_stimulus = None
        self.clock = 0.0
        self.temperature = 37.0
        self.sleep_state = 'awake'
        self.sleep_elapsed = 0.0
        self.sleep_total = 0.0
        self._auto_sleep_not_before = 0.0
        self.resting = False
        self._alive = True
        self.death_reason = None
        self.last_wake_reason = 'initial'
        self._ambient = 22.0
        self._nearby = 0
        self._at_home = False
        self._threat = 0.0
        self._separation = 0.0
        self._height = 0.0
        self._trapped = 0.0
        self._neural_loci = {}
        self._neuronal_values = {}
        self._apply_life_outputs()

    @classmethod
    def from_file(cls, path: str | Path, *, age_stage=3, sex='female', config=None, tick_seconds=1.0):
        return cls(Biochemistry.from_file(path, age_stage=age_stage, sex=sex, tick_seconds=tick_seconds), config)

    @property
    def alive(self):
        return self._alive

    @property
    def drives(self):
        outputs = self.kernel.receptors()
        return [_clip(outputs.get((1, 5, i), 0.0)) for i in range(20)]

    @property
    def chemicals(self):
        return self.kernel.chemicals.copy()

    @property
    def organ_health(self):
        return [organ.health for organ in self.kernel.organs]

    def _set_chemical(self, index, value):
        self.kernel.chemicals[index] = _number(value, 'chemical concentration', 0, 1)

    protein = property(lambda self: self.kernel.chemicals[12], lambda self, v: self._set_chemical(12, v))
    starch = property(lambda self: self.kernel.chemicals[5], lambda self, v: self._set_chemical(5, v))
    fat = property(lambda self: self.kernel.chemicals[10], lambda self, v: self._set_chemical(10, v))
    energy = property(lambda self: self.kernel.chemicals[35], lambda self, v: self._set_chemical(35, v))
    health = property(lambda self: self.kernel.chemicals[4], lambda self, v: self._set_chemical(4, v))
    fatigue = property(lambda self: self.kernel.chemicals[154], lambda self, v: self._set_chemical(154, v))
    sleep_debt = property(lambda self: self.kernel.chemicals[155], lambda self, v: self._set_chemical(155, v))
    pain = property(lambda self: self.kernel.chemicals[148], lambda self, v: self._set_chemical(148, v))
    injury = property(lambda self: self.kernel.chemicals[127], lambda self, v: self._set_chemical(127, v))
    toxin = property(lambda self: self.kernel.chemicals[70], lambda self, v: self._set_chemical(70, v))
    stress = property(lambda self: self.kernel.chemicals[128], lambda self, v: self._set_chemical(128, v))
    loneliness = property(lambda self: self.kernel.chemicals[156], lambda self, v: self._set_chemical(156, v))
    boredom = property(lambda self: self.kernel.chemicals[159], lambda self, v: self._set_chemical(159, v))
    anger = property(lambda self: self.kernel.chemicals[160], lambda self, v: self._set_chemical(160, v))
    homesickness = property(lambda self: self.kernel.chemicals[162], lambda self, v: self._set_chemical(162, v))
    reward = property(lambda self: self.kernel.chemicals[204], lambda self, v: self._set_chemical(204, v))
    punishment = property(lambda self: self.kernel.chemicals[205], lambda self, v: self._set_chemical(205, v))

    @property
    def social_comfort(self):
        return self.kernel.chemicals[161] - self.kernel.chemicals[158]

    def neural_receptor_outputs(self):
        """Return organ0 receptor bindings unchanged for the neural owner."""
        return {key: value for key, value in self.kernel.receptors().items() if key[0] == 0}

    def stimulate(self, stimulus_id, strength=1.0):
        """Apply the supplied genotype's chemical recipe for a scripted STIM.

        Native InitFromGenome00433f10 maps packed chemical IDs and signed
        amounts; SensoryStimulate004444d0 scales and saturates each adjustment.
        Per-channel learning flags are retained in the receipt. Full native
        source-agent/action gating is host-owned, not implemented here.
        """
        if type(stimulus_id) is not int or not 0 <= stimulus_id <= 255:
            raise ValueError('stimulus ID must be a byte')
        strength = _number(strength, 'stimulus strength')
        raw = next((json.loads(row) for row in self._stimuli
                    if json.loads(row)['fields']['stimulus'] == stimulus_id), None)
        if raw is None:
            raise ValueError(f'no expressed genome stimulus {stimulus_id}')
        f = raw['fields']; changes = []
        for i in range(4):
            encoded = f[f'chemical{i}']
            chemical = 0 if encoded == 255 else (encoded+148 if encoded <= 107 else encoded-107)
            signed = _f32(codon(f[f'amount{i}'], 0, 248) * _f32(1/124) - 1)
            amount = max(-1.0, min(1.0, signed * strength))
            changes.append({'chemical': chemical, 'amount': amount,
                            'learning_enabled': not bool(f['features'] & (0x10 << i))})
        receipt = {'stimulus_id': stimulus_id, 'strength': strength,
                   'gene_id': raw['header']['id'], 'offset': raw['offset'],
                   'features': f['features'], 'changes': changes}
        if self.alive:
            for change in changes:
                self.kernel.inject(change['chemical'], change['amount'])
            self.last_stimulus = receipt
        return deepcopy(receipt)

    def ingest(self, protein=0, starch=0, fat=0, toxin=0, *,
               stimulus_id=None, stimulus_strength=1.0):
        """Use either a genomic food STIM OR explicit raw ingredient dosing.

        Passing both a food STIM and positive macro doses is rejected, avoiding
        doubled nutrition. The simulation maps seed/fruit/food scripts to
        genotype stimuli77/78/79 and supplies consumed quantity as strength.
        Without a STIM only raw chemical stores are changed; hunger effects
        follow whatever reactions/receptors are present, never an inverse rule.
        """
        values = [_number(v, name, 0, 1) for name, v in
                  (('protein', protein), ('starch', starch), ('fat', fat), ('toxin', toxin))]
        if stimulus_id is not None and any(values[:3]):
            raise ValueError('choose genomic food stimulus or raw macros, not both')
        if not self.alive:
            return None
        if stimulus_id is not None:
            receipt = self.stimulate(stimulus_id, stimulus_strength)
        else:
            receipt = None
            for index, value in zip((12, 5, 10), values[:3]):
                self.kernel.inject(index, value)
        self.kernel.inject(70, values[3])
        return receipt

    def hurt(self, amount):
        amount = _number(amount, 'amount', 0, 1)
        if self.alive:
            self.kernel.inject(148, amount)
            self.kernel.inject(127, amount * 0.5)
            if amount > 0.05:
                self.wake('pain')

    def soothe(self, amount):
        amount = _number(amount, 'amount', 0, 1)
        if self.alive:
            self.kernel.inject(148, -amount)
            self.kernel.inject(128, -amount * 0.3)

    def interact(self, positive=0, negative=0):
        """Use expressed genomic pat/slap STIM2/4 chemical recipes.

        Contact strength and event selection are world-adapter decisions;
        signed chemical adjustments and learning flags belong to the genotype.
        Separate physical hurt, where appropriate, is supplied by the actor.
        """
        positive, negative = _number(positive, 'positive', 0, 1), _number(negative, 'negative', 0, 1)
        if not self.alive:
            return
        if positive:
            self.stimulate(2, positive)
        if negative:
            self.stimulate(4, negative)
        if negative > 0.3:
            self.wake('social threat')

    def set_resting(self, value=True):
        if type(value) is not bool:
            raise ValueError('resting must be boolean')
        self.resting = value

    def request_sleep(self):
        if not self.alive or self.pain > 0.35 or self._threat > 0.4:
            return False
        if self.sleep_state == 'awake':
            self.sleep_state = 'nrem'
            self.sleep_elapsed = self.sleep_total = 0.0
            self.resting = True
        return True

    def wake(self, reason='external'):
        if not isinstance(reason, str):
            raise ValueError('wake reason must be text')
        self.sleep_state = 'awake'
        self.sleep_elapsed = self.sleep_total = 0.0
        self.resting = False
        self.last_wake_reason = reason
        if reason == 'adapter sleep cycle complete':
            # A persistently high gene signal must not immediately undo the
            # scheduler's own maximum-duration wake. Brain-requested sleep is
            # still available; this only gates the host's automatic trigger.
            self._auto_sleep_not_before = self.clock + self.config.auto_sleep_refractory

    def _apply_life_outputs(self):
        if self._alive and self.kernel.receptors().get(self.DEATH_LOCUS, 0.0) > 0:
            self._alive = False
            self.death_reason = 'genome life-death receptor (1,3,0)'
            self.wake('death')

    def _sleep_clock(self, dt):
        if self.sleep_state != 'awake':
            if self.pain > 0.35 or self._threat > 0.4:
                self.wake('threat' if self._threat > 0.4 else 'pain')
            else:
                self.sleep_elapsed += dt
                self.sleep_total += dt
                duration = self.config.nrem_duration if self.sleep_state == 'nrem' else self.config.rem_duration
                while self.sleep_elapsed >= duration:
                    self.sleep_elapsed -= duration
                    self.sleep_state = 'rem' if self.sleep_state == 'nrem' else 'nrem'
                    duration = self.config.nrem_duration if self.sleep_state == 'nrem' else self.config.rem_duration
                if self.sleep_total >= self.config.maximum_sleep or (
                        self.sleep_total >= self.config.minimum_sleep and self.sleep_debt < 0.1):
                    self.wake('adapter sleep cycle complete')
        elif self.sleep_debt > 0.92 and self._threat < 0.3 and self.clock >= self._auto_sleep_not_before:
            self.request_sleep()
        # The brain catalogue fixes these channel identities. Their temporal
        # course here is explicitly the adapter's clock, not a gene reaction.
        self.kernel.chemicals[212] = (min(1.0, self.sleep_elapsed / self.config.nrem_duration)
                                     if self.sleep_state == 'nrem' else 0.0)
        self.kernel.chemicals[213] = float(self.sleep_state == 'rem')

    def _world_loci(self, effort):
        activity = 0.0 if self.sleep_state != 'awake' else (
            0.0 if self.resting else _clip(self.config.basal_activity + effort))
        values = {
            (1, 0, 0): activity,
            (1, 4, 0): 1.0,
            (1, 4, 1): float(self.sleep_state != 'awake'),
            (1, 4, 5): _clip(self._nearby / self.config.nearby_scale),
            (1, 4, 9): self.config.air_quality,
            (1, 4, 10): max(0.0, self._height),
            (1, 4, 11): max(0.0, -self._height),
        }
        # Host-provided exact neural/motor loci take precedence over defaults.
        values.update(self._neural_loci)
        return values

    def step(self, dt=1.0, *, ambient_temperature=22.0, effort=0.0,
             nearby_creatures=0, at_home=False, stimulation=0.0, threat=0.0,
             separation=0.0, height=0.0, trapped=0.0,
             neural_loci: Mapping | None = None, neuronal_values: Mapping | None = None):
        """Advance the gene kernel and explicit physical/sleep adapters.

        Zero seconds updates input snapshots without running chemistry. The
        legacy stimulation scalar is validated for interface compatibility but
        makes no invented chemical adjustment: call stimulate(id, strength)
        for the genotype's actual event recipe.
        """
        dt = _number(dt, 'dt', 0, 3600)
        ambient_temperature = _number(ambient_temperature, 'ambient_temperature', -100, 100)
        effort = _number(effort, 'effort', 0, 1)
        stimulation = _number(stimulation, 'stimulation', 0, 1)
        threat = _number(threat, 'threat', 0, 1)
        separation = _number(separation, 'separation', 0, 1)
        height = _number(height, 'height', -1, 1)
        trapped = _number(trapped, 'trapped', 0, 1)
        if type(nearby_creatures) is not int or nearby_creatures < 0 or type(at_home) is not bool:
            raise ValueError('invalid nearby count or home flag')
        loci = self._neural_loci if neural_loci is None else self.kernel._mapping(neural_loci, 3, 'host loci')
        neurons = self._neuronal_values if neuronal_values is None else self.kernel._mapping(neuronal_values, 2, 'host neural values')
        self._ambient, self._nearby, self._at_home = ambient_temperature, nearby_creatures, at_home
        self._threat, self._separation, self._height, self._trapped = threat, separation, height, trapped
        self._neural_loci, self._neuronal_values = dict(loci), dict(neurons)
        if dt == 0:
            self.kernel.step(0, self._world_loci(effort), neuronal_values=self._neuronal_values)
            return self.drives
        remaining = dt
        while remaining > 0:
            if not self.alive:
                self.clock += remaining
                break
            part = min(1.0, remaining)
            self._sleep_clock(part)
            self.temperature += (37 + (self._ambient - 22) * 0.04 - self.temperature) * min(1, part * 0.015)
            for chemical, amount in (
                (152, self.config.thermal_stimulus_rate * max(0, 18-self._ambient) / 35),
                (153, self.config.thermal_stimulus_rate * max(0, self._ambient-29) / 25),
                (158, self.config.threat_stimulus_rate * self._threat),
                (156, self.config.separation_stimulus_rate * self._separation),
            ):
                self.kernel.inject(chemical, max(-1.0, min(1.0, amount * part)))
            self.kernel.step(part, self._world_loci(effort), neuronal_values=self._neuronal_values)
            self.clock += part
            self._apply_life_outputs()
            remaining -= part
        return self.drives

    def same_definition(self, other):
        """Compare all expressed chemical/STIM genes and adapter configuration."""
        return (isinstance(other, GenomePhysiology)
                and self.kernel.age_stage == other.kernel.age_stage
                and self.kernel.sex == other.kernel.sex
                and self.kernel.tick_seconds == other.kernel.tick_seconds
                and self.config == other.config
                and self._stimuli == other._stimuli
                and (self.kernel.definition is other.kernel.definition
                     or self.kernel.definition == other.kernel.definition))

    def clone(self):
        other = object.__new__(type(self))
        other.__dict__ = {key: (self.kernel.clone() if key == 'kernel' else
                              self.config if key == 'config' else self._stimuli if key == '_stimuli' else deepcopy(value))
                          for key, value in self.__dict__.items()}
        return other

    def to_dict(self):
        return {'schema': self.SCHEMA, 'model': self.MODEL, 'config': asdict(self.config),
                'kernel': self.kernel.to_dict(),
                'state': {key: deepcopy(value) for key, value in self.__dict__.items()
                          if key not in ('kernel', 'config', '_neural_loci', '_neuronal_values', '_stimuli')},
                'neural_loci': [[*key, value] for key, value in self._neural_loci.items()],
                'neuronal_values': [[*key, value] for key, value in self._neuronal_values.items()]}

    @classmethod
    def from_dict(cls, data):
        if data.get('schema') != cls.SCHEMA or data.get('model') != cls.MODEL:
            raise ValueError('unsupported genome physiology checkpoint')
        body = cls(Biochemistry.from_dict(data['kernel']), GenomePhysiologyConfig(**data['config']))
        state = dict(data['state'])
        # Checkpoints written before the automatic-trigger refractory period.
        state.setdefault('_auto_sleep_not_before', 0.0)
        expected = set(body.__dict__) - {'kernel', 'config', '_neural_loci', '_neuronal_values', '_stimuli'}
        if set(state) != expected:
            raise ValueError('genome physiology state fields differ')
        for key in ('clock', 'sleep_elapsed', 'sleep_total', '_auto_sleep_not_before'):
            _number(state[key], key)
        _number(state['temperature'], 'temperature', -100, 100)
        _number(state['_ambient'], 'ambient', -100, 100)
        for key in ('_threat', '_separation', '_trapped'):
            _number(state[key], key, 0, 1)
        _number(state['_height'], 'height', -1, 1)
        if state['sleep_state'] not in cls.SLEEP_STATES:
            raise ValueError('invalid sleep state')
        if any(type(state[key]) is not bool for key in ('_alive', 'resting', '_at_home')):
            raise ValueError('invalid boolean state')
        if type(state['_nearby']) is not int or state['_nearby'] < 0:
            raise ValueError('invalid nearby count')
        if state['death_reason'] is not None and not isinstance(state['death_reason'], str):
            raise ValueError('invalid death reason')
        if not isinstance(state['last_wake_reason'], str):
            raise ValueError('invalid wake reason')
        body.__dict__.update(deepcopy(state))
        body._neural_loci = Biochemistry._decode_mapping(data['neural_loci'], 3, 'host loci')
        body._neuronal_values = Biochemistry._decode_mapping(data['neuronal_values'], 2, 'host neural values')
        return body
