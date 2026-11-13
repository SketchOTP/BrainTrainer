"""Bounded, identity-specific social learning for the standalone simulator.

Identity slots address individual forf neurons, not three invented channel rows.
Familiarity, affinity, threat dynamics and replacement policy are new simulation
choices, separate from the genome brain's own learned forf variables. Native
evidence identifies per-slot state variable5 as the current seen flag and
PostInit reserves one of the36 configured forf neurons (35 tracked identities).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable


def _bounded(value: float, name: str, low: float = 0, high: float | None = 1) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value) or value < low or (high is not None and value > high):
        raise ValueError(f"invalid {name}")
    return value


@dataclass
class _Relationship:
    other_id: str
    slot: int
    familiarity: float = 0.0
    affinity: float = 0.0
    threat: float = 0.0
    recent_signed: float = 0.0
    last_seen: float = 0.0
    encounter_order: int = 0
    observations: int = 0


class SocialMemory:
    """Stable bounded identity slots and separately attributable social events.

    Call ``advance(dt, present_ids)`` once per world step, then ``observe`` for
    visible contacts. Observe's dt is contact duration, not a second global
    clock advance. Positive/negative signals describe this identity's actual
    action; food reward is never credited to an arbitrary nearby creature.
    """
    SCHEMA = 1
    FORF_LAYOUT = "native-seen-flags-for-state-variable-5-v1"
    FORF_CELL_COUNT = 36
    TRACKED_CAPACITY = FORF_CELL_COUNT - 1
    FORF_SEEN_VARIABLE = 5

    def __init__(self, capacity: int = 35):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or not 1 <= capacity <= self.TRACKED_CAPACITY:
            raise ValueError("social capacity must be between one and thirty-five")
        self.capacity = capacity
        self.clock = 0.0
        self._order = 0
        self._records: dict[str, _Relationship] = {}
        self._present: set[str] = set()

    def advance(self, dt: float = 1.0, present_ids: Iterable[str] = ()) -> None:
        dt = _bounded(dt, "dt", high=None)
        present = set(present_ids)
        if any(not isinstance(v, str) or not v for v in present):
            raise ValueError("social identities must be nonempty strings")
        self.clock += dt
        self._present = present
        for row in self._records.values():
            row.familiarity *= math.exp(-dt / 7200)
            row.affinity *= math.exp(-dt / 36000)
            row.threat *= math.exp(-dt / 900)
            row.recent_signed *= math.exp(-dt / 30)

    def slot(self, other_id: str) -> int | None:
        row = self._records.get(other_id)
        return None if row is None else row.slot

    def observe(self, other_id: str, positive: float = 0, negative: float = 0,
                dt: float = 1.0) -> dict:
        if not isinstance(other_id, str) or not other_id:
            raise ValueError("other_id must be a nonempty string")
        positive, negative = _bounded(positive, "positive"), _bounded(negative, "negative")
        dt = _bounded(dt, "dt", high=None)
        if other_id not in self._records:
            if len(self._records) == self.capacity:
                evicted = min(self._records.values(), key=lambda row: (row.encounter_order, row.slot))
                slot = evicted.slot
                del self._records[evicted.other_id]
                self._present.discard(evicted.other_id)
            else:
                used = {row.slot for row in self._records.values()}
                slot = next(index for index in range(self.capacity) if index not in used)
            self._records[other_id] = _Relationship(other_id, slot)
        row = self._records[other_id]
        self._order += 1
        row.encounter_order = self._order
        row.last_seen = self.clock
        row.observations += 1
        row.familiarity += (1 - row.familiarity) * min(0.25, 0.02 + dt / 120)
        row.affinity = min(1.0, max(-1.0, row.affinity
                                  + 0.25 * positive * (1 - row.affinity)
                                  - 0.35 * negative * (1 + row.affinity)))
        row.threat = min(1.0, max(0.0, row.threat
                                + 0.5 * negative * (1 - row.threat)
                                - 0.2 * positive * row.threat))
        row.recent_signed = min(1.0, max(-1.0, row.recent_signed + positive - negative))
        self._present.add(other_id)
        return self.opinion(other_id)

    def opinion(self, other_id: str) -> dict:
        row = self._records.get(other_id)
        if row is None:
            return {"other_id": other_id, "slot": None, "familiarity": 0.0,
                    "affinity": 0.0, "threat": 0.0, "recent_signed": 0.0,
                    "present": other_id in self._present, "observations": 0,
                    "last_seen": None}
        return {**asdict(row), "present": other_id in self._present}

    @property
    def identities(self) -> tuple[str, ...]:
        return tuple(row.other_id for row in sorted(self._records.values(), key=lambda row: row.slot))

    def separation_distress(self, present_ids: Iterable[str] | None = None) -> float:
        """Bounded attachment absence, separate from count-based loneliness."""
        present = self._present if present_ids is None else set(present_ids)
        return max((row.familiarity * max(row.affinity, 0)
                    for row in self._records.values() if row.other_id not in present), default=0.0)

    def nearby_threat(self, present_ids: Iterable[str] | None = None) -> float:
        present = self._present if present_ids is None else set(present_ids)
        return max((row.threat for row in self._records.values() if row.other_id in present), default=0.0)

    def forf_inputs(self) -> list[float]:
        """Return36 seen flags for forf state variable5, NOT neuronal input0.

        The neural adapter must assign result[i] to forf[i].variables[5]. It
        must not overwrite learned variables0/2 with this module's independent
        affinity estimates. Native ClearSeenFriends also clears variable7 for
        absent identities; the owning neural adapter handles that separately.
        """
        result = [0.0] * self.FORF_CELL_COUNT
        for row in self._records.values():
            if row.other_id in self._present:
                result[row.slot] = 1.0
        return result

    def to_dict(self) -> dict:
        return {"schema": self.SCHEMA, "model": "identity-social-reference-v1",
                "forf_layout": self.FORF_LAYOUT, "capacity": self.capacity,
                "clock": self.clock, "order": self._order,
                "present": sorted(self._present),
                "records": [asdict(row) for row in sorted(self._records.values(), key=lambda row: row.slot)]}

    @classmethod
    def from_dict(cls, data: dict) -> SocialMemory:
        if (data.get("schema") != cls.SCHEMA or data.get("model") != "identity-social-reference-v1"
                or data.get("forf_layout") != cls.FORF_LAYOUT):
            raise ValueError("unsupported social memory checkpoint")
        memory = cls(data["capacity"])
        memory.clock = _bounded(data["clock"], "clock", high=None)
        order = data["order"]
        if isinstance(order, bool) or not isinstance(order, int) or order < 0:
            raise ValueError("invalid social encounter clock")
        memory._order = order
        if len(data["records"]) > memory.capacity:
            raise ValueError("social checkpoint exceeds slot capacity")
        slots = set()
        for value in data["records"]:
            row = _Relationship(**value)
            if not isinstance(row.other_id, str) or not row.other_id or row.other_id in memory._records:
                raise ValueError("invalid or duplicate social identity")
            if isinstance(row.slot, bool) or not isinstance(row.slot, int) or not 0 <= row.slot < memory.capacity or row.slot in slots:
                raise ValueError("invalid or duplicate social slot")
            slots.add(row.slot)
            for key in ("familiarity", "threat"):
                _bounded(getattr(row, key), key)
            for key in ("affinity", "recent_signed"):
                _bounded(getattr(row, key), key, -1, 1)
            _bounded(row.last_seen, "last_seen", high=memory.clock)
            for key in ("observations", "encounter_order"):
                v = getattr(row, key)
                if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                    raise ValueError(f"invalid social {key}")
            if row.encounter_order > memory._order:
                raise ValueError("social encounter order exceeds clock")
            memory._records[row.other_id] = row
        memory._present = set(data["present"])
        if any(not isinstance(v, str) or not v for v in memory._present):
            raise ValueError("invalid currently observed identity")
        return memory
