"""Need-weighted expected drive relief with explicit, inspectable learning.

Score = accessibility * (sum(need[d] * short_relief[d]) +
                         feedback_weight * short_feedback).

A learned relief target is before_need - after_need. Long weights move toward
short weights during ``advance``; short weights also relax toward long weights.
These equations and their rates are adaptations, not original engine parity.
Short/long weights are synaptic predictions, not episodic memory systems.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import random
from typing import Mapping


def _finite(value: float, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label} must be finite and between {low} and {high}")
    return value


def _names(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    values = tuple(values)
    if not values or any(not isinstance(v, str) or not v for v in values):
        raise ValueError(f"{label} must contain nonempty names")
    if len(set(values)) != len(values):
        raise ValueError(f"{label} must be unique")
    return values


@dataclass(frozen=True)
class BrainConfig:
    drives: tuple[str, ...]
    actions: tuple[str, ...]
    learning_rate: float = 0.35
    consolidation_rate: float = 0.03
    relaxation_rate: float = 0.02
    exploration_probability: float = 0.05
    feedback_weight: float = 0.25
    seed: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "drives", _names(self.drives, "drives"))
        object.__setattr__(self, "actions", _names(self.actions, "actions"))
        for name in ("learning_rate", "consolidation_rate", "relaxation_rate",
                     "exploration_probability", "feedback_weight"):
            object.__setattr__(self, name, _finite(getattr(self, name), name, 0, 1))
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")


@dataclass(frozen=True)
class ObservedObject:
    object_id: str
    category: str
    affordances: Mapping[str, float]


@dataclass(frozen=True)
class Candidate:
    object_id: str
    category: str
    action: str
    accessibility: float
    drive_contributions: tuple[float, ...]
    feedback_contribution: float
    score: float


@dataclass(frozen=True)
class Decision:
    decision_id: int
    tick: int
    chosen: Candidate
    before_drives: tuple[float, ...]
    explored: bool
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True)
class LearningResult:
    decision_id: int
    observed_relief: tuple[float, ...]
    short_relief: tuple[float, ...]
    long_relief: tuple[float, ...]
    short_feedback: float
    samples: int


@dataclass
class _Association:
    short: list[float]
    long: list[float]
    short_feedback: float = 0.0
    long_feedback: float = 0.0
    samples: int = 0


class Brain:
    """A portable decision core whose body/world adapter supplies all perception.

    Associations generalize over category and action, while attention selects a
    concrete object. ``choose`` captures a pending action; ``learn`` assigns one
    measured outcome to it exactly once. Discard outcomes that cannot be given a
    defensible action attribution. A game or robot must supply its own action
    execution, safety boundaries, perception, physiology and clock.
    """

    MODEL = "need-relief-reference-v1"
    SCHEMA = 1

    def __init__(self, config: BrainConfig):
        self.config = config
        self.tick = 0
        self._next_id = 1
        self._rng = random.Random(config.seed)
        self._associations: dict[tuple[str, str], _Association] = {}
        self._pending: dict[int, Decision] = {}

    def _drives(self, values: Mapping[str, float]) -> tuple[float, ...]:
        if set(values) != set(self.config.drives):
            raise ValueError("drive input must contain exactly the configured drives")
        return tuple(_finite(values[d], f"drive {d}", 0, 1) for d in self.config.drives)

    def _association(self, category: str, action: str) -> _Association:
        key = (category, action)
        if key not in self._associations:
            n = len(self.config.drives)
            self._associations[key] = _Association([0.0] * n, [0.0] * n)
        return self._associations[key]

    def prime(self, category: str, action: str, relief: Mapping[str, float]) -> None:
        """Supply a declared prior; this does not implement the game's dreaming.

        Both short and long weights start at the prior. Priming an association
        already trained would overwrite experience and is refused.
        """
        if not isinstance(category, str) or not category:
            raise ValueError("category must be a nonempty string")
        if action not in self.config.actions:
            raise ValueError("unknown action")
        if set(relief) != set(self.config.drives):
            raise ValueError("prior must contain exactly the configured drives")
        vector = [_finite(relief[d], f"relief {d}", -1, 1) for d in self.config.drives]
        existing = self._associations.get((category, action))
        if existing is not None and existing.samples:
            raise ValueError("cannot prime an association after learning")
        self._associations[(category, action)] = _Association(vector.copy(), vector.copy())

    def choose(self, drives: Mapping[str, float], objects: list[ObservedObject]) -> Decision | None:
        """Choose an accessible object/action pair and retain an outcome handle.

        Empty perception or no accessible actions returns None. Ties use sorted
        object identity then the configured action order. Exploration chooses
        uniformly from accessible candidates using the checkpointed RNG.
        """
        needs = self._drives(drives)
        ids: set[str] = set()
        for obj in objects:
            if not isinstance(obj.object_id, str) or not obj.object_id:
                raise ValueError("object_id must be a nonempty string")
            if obj.object_id in ids:
                raise ValueError("object_id must be unique within one observation")
            ids.add(obj.object_id)
            if not isinstance(obj.category, str) or not obj.category:
                raise ValueError("category must be a nonempty string")
            if set(obj.affordances) - set(self.config.actions):
                raise ValueError("affordance contains an unknown action")
            for action, access in obj.affordances.items():
                _finite(access, f"accessibility {action}", 0, 1)
        candidates: list[Candidate] = []
        for obj in sorted(objects, key=lambda x: x.object_id):
            for action in self.config.actions:
                access = float(obj.affordances.get(action, 0.0))
                if access == 0:
                    continue
                association = self._association(obj.category, action)
                contributions = tuple(n * p for n, p in zip(needs, association.short))
                feedback = self.config.feedback_weight * association.short_feedback
                candidates.append(Candidate(obj.object_id, obj.category, action, access,
                                            contributions, feedback,
                                            access * (sum(contributions) + feedback)))
        self.tick += 1
        if not candidates:
            return None
        explored = self._rng.random() < self.config.exploration_probability
        selected = (self._rng.choice(candidates) if explored
                    else max(candidates, key=lambda c: c.score))
        decision = Decision(self._next_id, self.tick, selected, needs,
                            explored, tuple(candidates))
        self._next_id += 1
        self._pending[decision.decision_id] = decision
        return decision

    @property
    def pending_actions(self) -> tuple[int, ...]:
        return tuple(sorted(self._pending))

    def discard(self, decision_id: int) -> None:
        """Resolve an action without inventing a learning outcome."""
        del self._pending[decision_id]

    def learn(self, decision_id: int, after_drives: Mapping[str, float], *,
              feedback: float | None = None) -> LearningResult:
        """Assign signed drive change plus separate scalar preference feedback.

        Positive relief lowers a drive, negative relief raises it. Generic
        feedback updates a separate preference; it never fabricates drive
        relief. Omitted feedback preserves the learned preference; explicit zero is
        neutral feedback. This feedback equation is an original adaptation, not the
        game's documented accentuation/attenuation rule.
        """
        after = self._drives(after_drives)
        if feedback is not None:
            feedback = _finite(feedback, "feedback", -1, 1)
        decision = self._pending[decision_id]
        observed = tuple(a - b for a, b in zip(decision.before_drives, after))
        association = self._association(decision.chosen.category, decision.chosen.action)
        rate = self.config.learning_rate
        association.short = [p + rate * (r - p)
                             for p, r in zip(association.short, observed)]
        if feedback is not None:
            association.short_feedback += rate * (feedback - association.short_feedback)
        association.samples += 1
        del self._pending[decision_id]
        return LearningResult(decision_id, observed, tuple(association.short),
                              tuple(association.long), association.short_feedback,
                              association.samples)

    def advance(self, steps: int = 1) -> None:
        """Advance explicit model ticks and consolidate/relax learned weights.

        This is not the game's sleep/REM scheduler. Rates are per call tick, not
        physical seconds. Long weights approach short weights first, then short
        weights relax toward the updated long weights.
        """
        if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
            raise ValueError("steps must be a nonnegative integer")
        for _ in range(steps):
            for association in self._associations.values():
                for i in range(len(self.config.drives)):
                    association.long[i] += self.config.consolidation_rate * (
                        association.short[i] - association.long[i])
                    association.short[i] += self.config.relaxation_rate * (
                        association.long[i] - association.short[i])
                association.long_feedback += self.config.consolidation_rate * (
                    association.short_feedback - association.long_feedback)
                association.short_feedback += self.config.relaxation_rate * (
                    association.long_feedback - association.short_feedback)
            self.tick += 1

    def association(self, category: str, action: str) -> dict:
        """Return a detached inspection record; absent predictions remain absent."""
        value = self._associations.get((category, action))
        if value is None:
            raise KeyError((category, action))
        return {"short_relief": dict(zip(self.config.drives, value.short)),
                "long_relief": dict(zip(self.config.drives, value.long)),
                "short_feedback": value.short_feedback,
                "long_feedback": value.long_feedback, "samples": value.samples}

    def to_dict(self) -> dict:
        return {"schema": self.SCHEMA, "model": self.MODEL,
                "config": asdict(self.config), "tick": self.tick,
                "next_id": self._next_id, "rng_state": self._rng.getstate(),
                "associations": [{"category": category, "action": action,
                                  **asdict(value)}
                                 for (category, action), value in sorted(self._associations.items())],
                "pending": [asdict(self._pending[i]) for i in sorted(self._pending)]}

    @classmethod
    def from_dict(cls, data: dict) -> Brain:
        if data.get("schema") != cls.SCHEMA or data.get("model") != cls.MODEL:
            raise ValueError("unsupported brain checkpoint schema or model")
        brain = cls(BrainConfig(**data["config"]))
        for name in ("tick", "next_id"):
            value = data[name]
            if isinstance(value, bool) or not isinstance(value, int) or value < (name == "next_id"):
                raise ValueError(f"invalid checkpoint {name}")
        brain.tick, brain._next_id = data["tick"], data["next_id"]
        def tuples(value):
            return tuple(tuples(v) for v in value) if isinstance(value, (list, tuple)) else value
        brain._rng.setstate(tuples(data["rng_state"]))
        for row in data["associations"]:
            category, action = row["category"], row["action"]
            if not isinstance(category, str) or not category or action not in brain.config.actions:
                raise ValueError("invalid checkpoint association identity")
            key = (category, action)
            if key in brain._associations:
                raise ValueError("duplicate checkpoint association")
            vectors = [[_finite(v, "checkpoint weight", -1, 1) for v in row[n]]
                       for n in ("short", "long")]
            if any(len(v) != len(brain.config.drives) for v in vectors):
                raise ValueError("checkpoint weight vector dimension mismatch")
            samples = row["samples"]
            if isinstance(samples, bool) or not isinstance(samples, int) or samples < 0:
                raise ValueError("invalid checkpoint sample count")
            brain._associations[key] = _Association(
                *vectors, _finite(row["short_feedback"], "checkpoint feedback", -1, 1),
                _finite(row["long_feedback"], "checkpoint feedback", -1, 1), samples)
        for row in data["pending"]:
            def candidate(value):
                value = dict(value)
                value["drive_contributions"] = tuple(value["drive_contributions"])
                return Candidate(**value)
            decision = Decision(row["decision_id"], row["tick"], candidate(row["chosen"]),
                                tuple(row["before_drives"]), row["explored"],
                                tuple(candidate(v) for v in row["candidates"]))
            if decision.decision_id in brain._pending or not 0 < decision.decision_id < brain._next_id:
                raise ValueError("invalid pending decision identity")
            if len(decision.before_drives) != len(brain.config.drives):
                raise ValueError("pending drive vector dimension mismatch")
            for value in decision.before_drives:
                _finite(value, "pending drive", 0, 1)
            if (decision.chosen.category, decision.chosen.action) not in brain._associations:
                raise ValueError("pending decision has no association")
            brain._pending[decision.decision_id] = decision
        return brain

    def save(self, path: str | Path, *, overwrite: bool = False) -> None:
        """Save complete predictions, pending actions and Python RNG state.

        Deterministic continuation is verified on the same Python runtime;
        cross-language or cross-version RNG compatibility is not promised.
        """
        with Path(path).open("w" if overwrite else "x", encoding="utf-8") as stream:
            json.dump(self.to_dict(), stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")

    @classmethod
    def load(cls, path: str | Path) -> Brain:
        with Path(path).open(encoding="utf-8") as stream:
            return cls.from_dict(json.load(stream))
