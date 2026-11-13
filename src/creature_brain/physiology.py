"""Original simplified physiology for the research creature simulator.

Time is measured in simulated seconds. This model supplies the twenty observed
Docking Station drive channels and their verified chemical indices. Its rates,
energy balance, thermal model, illness and sleep clock are new simulation design
choices. It does not execute the game's organ/reaction/receptor genome.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import ClassVar

DRIVE_NAMES = (
    "hurt", "hungry for protein", "hungry for starch", "hungry for fat", "cold",
    "hot", "tired", "sleepy", "lonely", "crowded", "scared", "bored", "angry",
    "friendly", "homesick", "low down", "high up", "trapped", "trapped", "patient",
)
DRIVE_CHEMICAL_IDS = tuple(range(148, 163)) + tuple(range(199, 204))


def _number(value: float, label: str, minimum: float = 0.0,
            maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    value = float(value)
    if not math.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{label} is outside its finite permitted range")
    return value


def _unit(value: float) -> float:
    return min(1.0, max(0.0, value))


@dataclass(frozen=True)
class PhysiologyConfig:
    """Per-second simulation rates; all values are adaptations."""
    protein_use: float = 0.00012
    starch_use: float = 0.00042
    fat_use: float = 0.00020
    fatigue_rate: float = 0.0007
    sleep_debt_rate: float = 0.00035
    sleep_recovery: float = 0.0014
    fatigue_recovery: float = 0.003
    nrem_duration: float = 30.0
    rem_duration: float = 15.0
    minimum_sleep: float = 90.0
    starvation_damage: float = 0.00055

    def __post_init__(self):
        for name, value in asdict(self).items():
            _number(value, name)
        if self.nrem_duration == 0 or self.rem_duration == 0:
            raise ValueError("sleep stages must have positive duration")


class Physiology:
    """Bounded body state, twenty drives and a 256-channel chemical adapter."""
    SCHEMA: ClassVar[int] = 1
    SLEEP_STATES: ClassVar[tuple[str, ...]] = ("awake", "nrem", "rem")

    def __init__(self, config: PhysiologyConfig | None = None):
        self.config = config or PhysiologyConfig()
        self.clock = 0.0
        self.protein = 0.75
        self.starch = 0.75
        self.fat = 0.75
        self.energy = 0.75
        self.temperature = 37.0
        self.health = 1.0
        self.injury = 0.0
        self.pain = 0.0
        self.toxin = 0.0
        self.fatigue = 0.15
        self.sleep_debt = 0.12
        self.stress = 0.0
        self.loneliness = 0.15
        self.boredom = 0.15
        self.anger = 0.0
        self.social_comfort = 0.0
        self.homesickness = 0.0
        self.reward = 0.0
        self.punishment = 0.0
        self.sleep_state = "awake"
        self.sleep_elapsed = 0.0
        self.sleep_total = 0.0
        self.resting = False
        self.alive = True
        self.death_reason: str | None = None
        self.last_wake_reason = "initial"
        self._ambient = 22.0
        self._nearby = 0
        self._at_home = False
        self._threat = 0.0
        self._separation = 0.0
        self._height = 0.0
        self._trapped = 0.0

    @property
    def drives(self) -> list[float]:
        crowd = _unit((self._nearby - 3) / 6)
        return [_unit(v) for v in (
            max(self.pain, self.injury * 0.7),
            1 - self.protein, 1 - self.starch, 1 - self.fat,
            max((36.7 - self.temperature) / 3, (18 - self._ambient) / 35),
            max((self.temperature - 37.5) / 3, (self._ambient - 29) / 25),
            self.fatigue, self.sleep_debt,
            max(self.loneliness, self._separation * 0.8), crowd,
            max(self._threat, self.stress * 0.8), self.boredom,
            self.anger, 0.2 + self.loneliness * 0.25 + max(self.social_comfort, 0) * 0.4,
            self.homesickness, max(-self._height, 0), max(self._height, 0),
            self._trapped, self._trapped * 0.5,
            0.1 + self.resting * 0.3 + max(self.social_comfort, 0) * 0.1,
        )]

    @property
    def chemicals(self) -> list[float]:
        result = [0.0] * 256
        for index, value in zip(DRIVE_CHEMICAL_IDS, self.drives):
            result[index] = value
        result[204], result[205] = self.reward, self.punishment
        if self.alive and self.sleep_state == "nrem":
            result[212] = _unit(self.sleep_elapsed / self.config.nrem_duration)
        if self.alive and self.sleep_state == "rem":
            result[213] = 1.0
        return result

    def ingest(self, protein: float = 0, starch: float = 0, fat: float = 0,
               toxin: float = 0) -> None:
        quantities = [_number(v, k) for k, v in (("protein", protein), ("starch", starch),
                                                ("fat", fat), ("toxin", toxin))]
        if not self.alive:
            return
        protein, starch, fat, toxin = quantities
        absorbed = sum(min(1 - getattr(self, k), v)
                       for k, v in (("protein", protein), ("starch", starch), ("fat", fat)))
        self.protein, self.starch, self.fat = (
            _unit(self.protein + protein), _unit(self.starch + starch), _unit(self.fat + fat))
        self.toxin = _unit(self.toxin + toxin)
        self.reward = _unit(self.reward + absorbed * 0.4)
        self.punishment = _unit(self.punishment + toxin * 0.6)
        if toxin:
            self.pain = _unit(self.pain + toxin * 0.3)

    def hurt(self, amount: float) -> None:
        amount = _number(amount, "amount", maximum=1)
        if not self.alive:
            return
        self.injury = _unit(self.injury + amount * 0.5)
        self.pain = _unit(self.pain + amount)
        self.health = _unit(self.health - amount * 0.3)
        self.stress = _unit(self.stress + amount * 0.6)
        self.punishment = _unit(self.punishment + amount)
        if amount > 0.05:
            self.wake("pain")
        if self.health <= 0:
            self._die("injury")

    def soothe(self, amount: float) -> None:
        amount = _number(amount, "amount", maximum=1)
        if not self.alive:
            return
        self.pain = _unit(self.pain - amount)
        self.stress = _unit(self.stress - amount * 0.6)
        self.reward = _unit(self.reward + amount * 0.2)

    def interact(self, positive: float = 0, negative: float = 0) -> None:
        """Apply an actual social event; proximity alone supplies no reward."""
        positive = _number(positive, "positive", maximum=1)
        negative = _number(negative, "negative", maximum=1)
        if not self.alive:
            return
        self.social_comfort = min(1.0, max(-1.0, self.social_comfort + 0.4 * (positive - negative)))
        self.loneliness = _unit(self.loneliness - positive * 0.35)
        self.anger = _unit(self.anger + negative * 0.4 - positive * 0.2)
        self.stress = _unit(self.stress + negative * 0.5 - positive * 0.3)
        self.reward = _unit(self.reward + positive * 0.2)
        self.punishment = _unit(self.punishment + negative * 0.4)
        if negative > 0.3:
            self.wake("social threat")

    def set_resting(self, resting: bool = True) -> None:
        if not isinstance(resting, bool):
            raise ValueError("resting must be boolean")
        self.resting = resting

    def request_sleep(self) -> bool:
        if not self.alive or self.pain > 0.35 or self._threat > 0.4:
            return False
        if self.sleep_state == "awake":
            self.sleep_state = "nrem"
            self.sleep_elapsed = self.sleep_total = 0.0
            self.resting = True
        return True

    def wake(self, reason: str = "external") -> None:
        if not isinstance(reason, str):
            raise ValueError("wake reason must be text")
        self.sleep_state = "awake"
        self.sleep_elapsed = self.sleep_total = 0.0
        self.resting = False
        self.last_wake_reason = reason

    def _die(self, reason: str) -> None:
        self.alive = False
        self.health = 0.0
        self.death_reason = reason
        self.wake("death")

    def step(self, dt: float = 1.0, *, ambient_temperature: float = 22.0,
             effort: float = 0.0, nearby_creatures: int = 0, at_home: bool = False,
             stimulation: float = 0.0, threat: float = 0.0, separation: float = 0.0,
             height: float = 0.0, trapped: float = 0.0) -> list[float]:
        dt = _number(dt, "dt")
        ambient_temperature = _number(ambient_temperature, "ambient_temperature", -100, 100)
        effort = _number(effort, "effort", maximum=1)
        stimulation = _number(stimulation, "stimulation", maximum=1)
        threat = _number(threat, "threat", maximum=1)
        separation = _number(separation, "separation", maximum=1)
        height = _number(height, "height", -1, 1)
        trapped = _number(trapped, "trapped", maximum=1)
        if isinstance(nearby_creatures, bool) or not isinstance(nearby_creatures, int) or nearby_creatures < 0:
            raise ValueError("nearby_creatures must be a nonnegative integer")
        if not isinstance(at_home, bool):
            raise ValueError("at_home must be boolean")
        self._ambient, self._nearby, self._at_home = ambient_temperature, nearby_creatures, at_home
        self._threat, self._separation = threat, separation
        self._height, self._trapped = height, trapped
        remaining = dt
        while remaining > 0:
            if not self.alive:
                self.clock += remaining
                break
            part = min(remaining, 1.0)
            self._advance(part, effort, stimulation)
            self.clock += part
            remaining -= part
        return self.drives

    def _advance(self, dt: float, effort: float, stimulation: float) -> None:
        if self.sleep_state not in self.SLEEP_STATES:
            raise ValueError("invalid sleep state")
        if self.sleep_state != "awake" and (self._threat > 0.4 or self.pain > 0.35):
            self.wake("threat" if self._threat > 0.4 else "pain")
        asleep = self.sleep_state != "awake"
        metabolism = (0.55 if asleep else 1.0) + effort * 1.5
        self.protein = _unit(self.protein - self.config.protein_use * metabolism * dt)
        self.starch = _unit(self.starch - self.config.starch_use * metabolism * dt)
        self.fat = _unit(self.fat - self.config.fat_use * metabolism * dt)
        reserves = 0.25 * self.protein + 0.45 * self.starch + 0.30 * self.fat
        self.energy = _unit(self.energy + (reserves - self.energy) * 0.004 * dt - effort * 0.0005 * dt)
        regulated = 0.035 + 0.035 * (1 - self.energy)
        temperature_target = 37 + (self._ambient - 22) * regulated
        self.temperature += (temperature_target - self.temperature) * min(1, 0.015 * dt)
        self.toxin = _unit(self.toxin - 0.0004 * dt)
        self.pain = _unit(self.pain - 0.002 * dt + self.toxin * 0.0015 * dt)
        self.injury = _unit(self.injury - 0.00015 * self.energy * dt)
        self.stress = _unit(self.stress + (self._threat * 0.005 - 0.001) * dt)
        self.anger = _unit(self.anger - 0.0006 * dt)
        self.social_comfort *= math.exp(-dt / 900)
        self.loneliness = _unit(self.loneliness + (0.0006 if self._nearby == 0 else -0.002) * dt)
        self.boredom = _unit(self.boredom + (0.0008 - stimulation * 0.004) * dt)
        self.homesickness = _unit(self.homesickness + (-0.003 if self._at_home else 0.0001) * dt)
        if asleep:
            recovery = 1.1 if self.sleep_state == "nrem" else 0.9
            self.fatigue = _unit(self.fatigue - self.config.fatigue_recovery * recovery * dt)
            self.sleep_debt = _unit(self.sleep_debt - self.config.sleep_recovery * dt)
            self.sleep_elapsed += dt
            self.sleep_total += dt
            duration = self.config.nrem_duration if self.sleep_state == "nrem" else self.config.rem_duration
            while self.sleep_elapsed >= duration:
                self.sleep_elapsed -= duration
                self.sleep_state = "rem" if self.sleep_state == "nrem" else "nrem"
                duration = self.config.nrem_duration if self.sleep_state == "nrem" else self.config.rem_duration
            if self.sleep_total >= self.config.minimum_sleep and self.sleep_debt < 0.1 and self.fatigue < 0.2:
                self.wake("recovered")
        else:
            self.fatigue = _unit(self.fatigue + (
                -0.001 if self.resting else self.config.fatigue_rate + effort * 0.002) * dt)
            self.sleep_debt = _unit(self.sleep_debt + self.config.sleep_debt_rate * dt)
            if (self.sleep_debt > 0.92 or self.fatigue > 0.98) and self._threat < 0.3:
                self.request_sleep()
        starvation = max(0, 0.10 - reserves) / 0.10
        deficiency = max(0, 0.04 - min(self.protein, self.starch, self.fat)) / 0.04
        thermal_damage = max(0, abs(self.temperature - 37) - 2.0) * 0.0006
        damage = (self.config.starvation_damage * starvation + deficiency * 0.00006
                  + self.toxin * 0.0008 + thermal_damage + self.injury * 0.00005)
        healing = 0.00006 * self.energy if damage == 0 else 0
        self.health = _unit(self.health + (healing - damage) * dt)
        self.reward *= math.exp(-dt / 5)
        self.punishment *= math.exp(-dt / 8)
        if self.health <= 0:
            reason = "starvation" if starvation else ("temperature" if thermal_damage else "illness or injury")
            self._die(reason)

    def to_dict(self) -> dict:
        return {"schema": self.SCHEMA, "model": "simplified-physiology-v1",
                "config": asdict(self.config),
                "state": {key: value for key, value in self.__dict__.items() if key != "config"}}

    @classmethod
    def from_dict(cls, data: dict) -> Physiology:
        if data.get("schema") != cls.SCHEMA or data.get("model") != "simplified-physiology-v1":
            raise ValueError("unsupported physiology checkpoint")
        body = cls(PhysiologyConfig(**data["config"]))
        state = data["state"]
        if set(state) != set(body.__dict__) - {"config"}:
            raise ValueError("physiology checkpoint state fields do not match")
        for key, current in body.__dict__.items():
            if key == "config":
                continue
            value = state[key]
            if isinstance(current, bool):
                if not isinstance(value, bool):
                    raise ValueError(f"invalid boolean state {key}")
            elif isinstance(current, (int, float)):
                _number(value, key, -100 if key in ("temperature", "_ambient") else (-1 if key in ("social_comfort", "_height") else 0))
            elif current is not None and not isinstance(value, str):
                raise ValueError(f"invalid text state {key}")
        if state["sleep_state"] not in cls.SLEEP_STATES:
            raise ValueError("invalid sleep stage")
        for key in ("protein", "starch", "fat", "energy", "health", "injury", "pain", "toxin",
                    "fatigue", "sleep_debt", "stress", "loneliness", "boredom", "anger",
                    "homesickness", "reward", "punishment", "_threat", "_separation", "_trapped"):
            _number(state[key], key, 0, 1)
        _number(state["social_comfort"], "social_comfort", -1, 1)
        _number(state["_height"], "_height", -1, 1)
        if isinstance(state["_nearby"], bool) or not isinstance(state["_nearby"], int):
            raise ValueError("invalid nearby creature count")
        if state["death_reason"] is not None and not isinstance(state["death_reason"], str):
            raise ValueError("invalid death reason")
        if state["alive"] != (state["health"] > 0):
            raise ValueError("health and alive state disagree")
        body.__dict__.update(state)
        return body
