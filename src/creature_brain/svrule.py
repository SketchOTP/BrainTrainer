"""Original mathematical SVRule reference from local REA Evidence.

Source: engine.exe FUN_00406ee0, InitFromGenome FUN_004096b0 and tract
helpers, preserved under research/docking-station-20261103/native/evidence.
This is static-evidence-informed Python, not an x87/float32 parity emulator or
a complete creature/lobe scheduler. Fractional native ROUND/ftol inputs and
negative array indices are refused. The default execute API commits atomically;
execute_trusted mutates prevalidated contexts in place and requires tick abortion
on failure.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, fields
import math


class SVRuleError(ValueError):
    """Invalid rule/state or a nonfinite result."""


class UnsupportedSemantics(SVRuleError):
    """The reference refuses a native behavior not qualified by its evidence."""


# The 69 little-endian u32 values read at 0x005e0f0c. 0=no operand,
# 1=value operand, 2=writable variable operand.
OPCODE_TYPES = (
    0, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 2, 2,
    1, 1, 1, 1, 1, 1, 0, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
)


def _number(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SVRuleError(f"{name} must be a finite number")
    try:
        result = float(value)
    except OverflowError as error:
        raise SVRuleError(f"{name} exceeds the reference numeric range") from error
    if not math.isfinite(result):
        raise SVRuleError(f"{name} must be finite")
    return result


def _integer(value: float, name: str) -> int:
    value = _number(value, name)
    if not value.is_integer() or not -(2**31) <= value < 2**31:
        raise UnsupportedSemantics(f"{name}: fractional/overflow native conversion is unqualified")
    return int(value)


def _bound(value: float, lower: float = -1.0) -> float:
    return min(1.0, max(lower, _number(value, "bounded result")))


def normalise_byte(value: int) -> float:
    """Genomic literal decoding; native constant is float32 approximately 1/248."""
    if type(value) is not int or not 0 <= value <= 255:
        raise SVRuleError("literal data must be a byte")
    return min(value / 248.0, 1.0)


def decode_codon(value: int, minimum: int, maximum: int) -> int:
    """Genome::GetCodon(0x00424c90) folds out-of-range bytes, not clamps."""
    if type(value) is not int or not 0 <= value <= 255:
        raise SVRuleError("codon must be a byte")
    if type(minimum) is not int or type(maximum) is not int or not 0 <= minimum <= maximum <= 255:
        raise SVRuleError("codon interval must be ordered byte bounds")
    if minimum <= value <= maximum:
        return value
    return value % (maximum - minimum + 1) + minimum


@dataclass(frozen=True)
class Instruction:
    opcode: int
    operand: int = 9
    data: int = 0
    _constant: float | None = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.opcode) is not int or not 0 <= self.opcode <= 68:
            raise SVRuleError("opcode must be in 0..68")
        if type(self.operand) is not int or not 0 <= self.operand <= 15:
            raise SVRuleError("operand must be in 0..15")
        literal = normalise_byte(self.data)
        if self.operand in (1, 2, 3, 4) and self.data > 7:
            raise SVRuleError("variable operand requires an index in 0..7")
        constants = {9: 0.0, 10: 1.0, 11: literal, 12: -literal,
                     13: literal * 10.0, 14: literal * 0.1,
                     15: float(min(self.data, 248))}
        object.__setattr__(self, "_constant", constants.get(self.operand))


@dataclass(frozen=True)
class Program:
    instructions: tuple[Instruction, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.instructions, tuple) or len(self.instructions) != 16 or not all(
            isinstance(item, Instruction) for item in self.instructions
        ):
            raise SVRuleError("a genomic program has exactly sixteen instructions")

    @classmethod
    def from_bytes(cls, data: bytes) -> Program:
        if not isinstance(data, bytes) or len(data) != 48:
            raise SVRuleError("a genomic program occupies exactly 48 bytes")
        instructions = []
        for i in range(0, 48, 3):
            opcode = decode_codon(data[i], 0, 68)
            operand = decode_codon(data[i + 1], 0, 15)
            maximum = 7 if operand in (1, 2, 3, 4) else 255
            value = decode_codon(data[i + 2], 0, maximum)
            instructions.append(Instruction(opcode, operand, value))
        return cls(tuple(instructions))

    @classmethod
    def of(cls, *instructions: Instruction) -> Program:
        if len(instructions) > 16:
            raise SVRuleError("program exceeds sixteen instructions")
        return cls(tuple(instructions) + (Instruction(0),) * (16 - len(instructions)))


@dataclass
class TractState:
    """Rule-configured helper state; enabled is the native byte at tract+9."""

    enabled: bool = True
    short_relaxation: float = 0.0
    reward_threshold: float = 0.0
    reward_rate: float = 0.0
    reward_chemical: int | None = None
    punishment_threshold: float = 0.0
    punishment_rate: float = 0.0
    punishment_chemical: int | None = None

    def validate(self) -> None:
        if type(self.enabled) is not bool:
            raise SVRuleError("tract enabled must be boolean")
        for name in ("short_relaxation", "reward_threshold", "reward_rate",
                     "punishment_threshold", "punishment_rate"):
            _number(getattr(self, name), name)
        for name in ("reward_chemical", "punishment_chemical"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or not 0 <= value <= 255):
                raise SVRuleError(f"{name} must be an optional chemical byte index")


@dataclass
class Context:
    """Explicit eight-variable arrays; aliases between arrays are preserved.

    The native initial accumulator is source[0]. Which host object supplies an
    array is a caller/scheduler responsibility. Chemicals are read-only here;
    source/destination IDs supply the offsets for operands6/8.
    """

    source: list[float] = field(default_factory=lambda: [0.0] * 8)
    dendrite: list[float] = field(default_factory=lambda: [0.0] * 8)
    neuron: list[float] = field(default_factory=lambda: [0.0] * 8)
    spare: list[float] = field(default_factory=lambda: [0.0] * 8)
    chemicals: list[float] | None = None
    source_id: int = 0
    destination_id: int = 0
    random_state: int | None = None
    tract: TractState | None = None

    def validate(self) -> None:
        for name in ("source", "dendrite", "neuron", "spare"):
            value = getattr(self, name)
            if not isinstance(value, list) or len(value) != 8:
                raise SVRuleError(f"{name} must be an eight-variable list")
            for item in value:
                _number(item, name)
        if self.chemicals is not None:
            if not isinstance(self.chemicals, list) or len(self.chemicals) != 256:
                raise SVRuleError("chemical context must contain256 values")
            for item in self.chemicals:
                _number(item, "chemical")
        for name in ("source_id", "destination_id"):
            if type(getattr(self, name)) is not int:
                raise SVRuleError(f"{name} must be an integer")
        if self.random_state is not None and (
            type(self.random_state) is not int or not 0 <= self.random_state < 2**32
        ):
            raise SVRuleError("random state must be an optional uint32 seed")
        if self.tract is not None:
            if not isinstance(self.tract, TractState):
                raise SVRuleError("tract context must be TractState or None")
            self.tract.validate()


@dataclass(frozen=True)
class ExecutionResult:
    accumulator: float
    registered_as_spare: bool
    executed_instructions: int
    stop_reason: str


def consolidate_weights(short: float, long: float, short_rate: float, long_rate: float) -> tuple[float, float]:
    """FUN_00409ae0 uses the OLD short weight for both simultaneous changes."""
    short, long, short_rate, long_rate = (
        _number(v, "weight/rate") for v in (short, long, short_rate, long_rate)
    )
    return (_number(short + (long - short) * short_rate, "short weight"),
            _number(long + (short - long) * long_rate, "long weight"))


def reinforced_weight(weight: float, signal: float, threshold: float, rate: float) -> float:
    """FUN_0040c320; callers separately choose channel and susceptibility."""
    weight, signal, threshold, rate = (
        _number(v, "reinforcement input") for v in (weight, signal, threshold, rate)
    )
    return _bound(weight + (signal - threshold) * rate) if threshold < signal else weight


def native_random_index(seed: int, upper_exclusive: int) -> tuple[int, int]:
    """One recovered LCG step and integer-scaled high15-bit sample.

    The VM float uses upper65537; connection callers can share this seed owner.
    Bounds exclude integer overflow cases not qualified by these references.
    """
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise SVRuleError("random seed must be uint32")
    if type(upper_exclusive) is not int or not 1 <= upper_exclusive <= 65537:
        raise SVRuleError("random bound must be in1..65537")
    seed = (seed * 0x19660D + 0x3C6EF35F) & 0xFFFFFFFF
    return seed, ((seed >> 17) * upper_exclusive) >> 15


def _random(context: Context) -> float:
    if context.random_state is None:
        raise UnsupportedSemantics("random operand requires an explicit uint32 seed")
    context.random_state, native_integer = native_random_index(context.random_state, 65537)
    return native_integer / 65535.0


def _variable(context: Context, instruction: Instruction) -> tuple[list[float], int] | None:
    kind = instruction.operand
    if kind == 1:
        return context.source, instruction.data
    if kind == 2:
        return context.dendrite, instruction.data
    if kind == 3:
        return context.neuron, instruction.data
    if kind == 4:
        return context.spare, instruction.data
    return None


def _operand(context: Context, instruction: Instruction, accumulator: float) -> float:
    variable = _variable(context, instruction)
    if variable is not None:
        return float(variable[0][variable[1]])
    kind, data = instruction.operand, instruction.data
    if kind == 0:
        return accumulator
    if kind == 5:
        return _random(context)
    if kind in (6, 7, 8):
        if context.chemicals is None:
            raise UnsupportedSemantics("chemical operand requires an explicit256-value context")
        index = data + ({6: context.source_id, 7: 0, 8: context.destination_id}[kind])
        if not 0 <= index < 2**31:
            raise UnsupportedSemantics("negative/overflow signed chemical indexing is unqualified")
        return float(context.chemicals[index % 256])
    return instruction._constant


def execute(program: Program, context: Context) -> ExecutionResult:
    """Execute a sixteen-slot program atomically in caller-owned explicit state.

    All69 classified operation IDs are modeled on finite, supported inputs.
    ROUND/ftol are admitted only for exact integers. Winner ties select the
    current neuron exactly as the recovered >= branch; lobe traversal/tie-order
    outside this interpreter is not modeled. No automatic post-rule reward is
    performed: native Tract::Update owns that separate step.
    """
    if not isinstance(program, Program) or not isinstance(context, Context):
        raise SVRuleError("execute requires Program and Context")
    context.validate()
    work = deepcopy(context)
    result = _interpret(program, work)
    work.validate()
    for name in ("source", "dendrite", "neuron", "spare"):
        getattr(context, name)[:] = getattr(work, name)
    context.random_state = work.random_state
    if context.tract is not None:
        for item in fields(TractState):
            setattr(context.tract, item.name, getattr(work.tract, item.name))
    return result


def execute_trusted(program: Program, context: Context) -> ExecutionResult:
    """Run the SAME interpreter in place on caller-prevalidated state.

    The scheduler must call Context.validate() when constructing/rebinding its
    contexts and keep Programs immutable. This skips cloning and whole-context
    scans. Nonfinite computed outputs still raise, but earlier valid writes are
    NOT rolled back. A failed trusted update must abort its containing tick;
    callers must not substitute a fallback action. No native parity is implied.
    """
    return _interpret(program, context)


def _interpret(program: Program, work: Context) -> ExecutionResult:
    """Single owning implementation used by both execution boundaries."""
    acc, rate, registered, pc, count, reason = float(work.source[0]), 0.0, False, 0, 0, "end"
    while pc < 16:
        instruction = program.instructions[pc]
        op = instruction.opcode
        count += 1
        advance = 1
        if op == 0:
            reason = "stop"
            break
        if OPCODE_TYPES[op] == 0:
            if op == 31:
                registered = True
            elif op == 42 and work.neuron[0] >= work.spare[0]:
                work.spare[2] = 0.0
                work.neuron[2] = work.neuron[0]
                registered = True
        elif OPCODE_TYPES[op] == 2:
            target = _variable(work, instruction)
            if target is not None:
                array, index = target
                old = array[index]
                value = {1: lambda: 0.0, 2: lambda: _bound(acc),
                         34: lambda: _bound(acc + old),
                         35: lambda: _bound(rate * old + (1.0 - rate) * acc),
                         45: lambda: _bound(abs(acc), 0.0)}[op]()
                array[index] = value
        else:
            value = _number(_operand(work, instruction, acc), "operand")
            if 4 <= op <= 15:
                conditions = {4: acc == value, 5: acc != value, 6: acc > value,
                              7: acc < value, 8: acc >= value, 9: acc <= value,
                              10: value == 0.0, 11: value != 0.0,
                              12: value > 0.0, 13: value < 0.0,
                              14: value >= 0.0, 15: value <= 0.0}
                if not conditions[op]:
                    advance = 2
            elif op in (46, 47, 53, 54, 55, 56):
                stops = {46: value == 0.0, 47: value != 0.0,
                         53: acc < value, 54: acc > value,
                         55: acc <= value, 56: acc >= value}
                if stops[op]:
                    reason = "conditional-stop"
                    break
            elif op in (48, 49, 52, 67, 68):
                take = {48: acc == 0.0, 49: acc != 0.0, 52: True,
                        67: acc < 0.0, 68: acc > 0.0}[op]
                if take:
                    target = _integer(value, "jump line") - 1
                    if target >= 16:
                        reason = "jump-beyond-program"
                        break
                    if pc < target:
                        advance = target - pc
            elif op in (63, 64, 65, 66):
                index = _integer(value, "preserved variable")
                if index < 0:
                    raise UnsupportedSemantics("negative signed variable indexing is unqualified")
                index %= 8
                array = work.neuron if op in (63, 64) else work.spare
                if op in (63, 65):
                    array[4] = array[index]
                else:
                    array[index] = array[4]
            elif op in (43, 44, 57, 58, 59, 60, 61, 62):
                tract = work.tract
                if tract is not None and tract.enabled:
                    if op == 43:
                        tract.short_relaxation = abs(value)
                    elif op == 44:
                        work.dendrite[:2] = consolidate_weights(
                            work.dendrite[0], work.dendrite[1], tract.short_relaxation, value)
                    elif op in (59, 62):
                        channel = _integer(value, "reinforcement chemical")
                        if channel < 0:
                            raise UnsupportedSemantics("negative reinforcement channel is unqualified")
                        setattr(tract, "reward_chemical" if op == 59 else "punishment_chemical", channel % 256)
                    else:
                        attribute = {57: "reward_threshold", 58: "reward_rate",
                                     60: "punishment_threshold", 61: "punishment_rate"}[op]
                        setattr(tract, attribute, _bound(value))
            elif op == 3:
                acc = value
            elif op == 16:
                acc += value
            elif op == 17:
                acc -= value
            elif op in (18, 29):
                acc = value - acc
            elif op == 19:
                acc *= value
            elif op == 20:
                if value != 0.0:
                    acc /= value
            elif op == 21:
                if acc != 0.0:
                    acc = value / acc
            elif op == 22:
                acc = min(acc, value)
            elif op == 23:
                acc = max(acc, value)
            elif op == 24:
                rate = abs(value)
            elif op == 25:
                acc = value * rate + (1.0 - rate) * acc
            elif op == 26:
                acc = -value
            elif op == 27:
                acc = abs(value)
            elif op == 28:
                acc = abs(acc - value)
            elif op == 32:
                acc = _bound(value, 0.0)
            elif op == 33:
                acc = _bound(value)
            elif op == 36:
                if work.neuron[1] < value:
                    work.neuron[1] = 0.0
            elif op == 37:
                rate = value
            elif op == 38:
                work.neuron[1] = _number(value * rate + (1.0 - rate) * work.neuron[1], "neuron input")
            elif op == 39:
                work.neuron[1] = _number(work.neuron[1] * value, "neuron input")
            elif op == 40:
                work.neuron[0] = _number(value * work.neuron[0] + (1.0 - value) * work.neuron[1], "neuron state")
            elif op == 41:
                work.neuron[0] = _number(work.neuron[0] + _random(work) * value, "neuron state")
            elif op == 50:
                if value != 0.0:
                    acc /= value
                    work.neuron[1] = _bound(work.neuron[1] + acc)
            elif op == 51:
                acc *= value
                work.neuron[1] = _bound(work.neuron[1] + acc)
            else:
                raise UnsupportedSemantics(f"unhandled opcode {op}")
        _number(acc, "accumulator")
        _number(rate, "tend/leakage rate")
        pc += advance
    return ExecutionResult(_number(acc, "accumulator output"), registered, count, reason)
