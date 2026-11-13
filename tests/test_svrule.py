"""Semantic examples for the native-evidence reference, not engine parity tests."""

import math
import unittest

from creature_brain.svrule import (
    Context, ExecutionResult, Instruction as I, OPCODE_TYPES, Program,
    SVRuleError, TractState, UnsupportedSemantics, consolidate_weights,
    execute, normalise_byte, reinforced_weight,
    execute_trusted, native_random_index,
    decode_codon,
)


class SVRuleTests(unittest.TestCase):
    def run_program(self, *instructions, context=None):
        context = context or Context()
        return execute(Program.of(*instructions), context), context

    def test_literal_scaling_and_saturation(self):
        self.assertEqual(normalise_byte(124), 0.5)
        self.assertEqual(normalise_byte(0), 0.0)
        self.assertEqual(normalise_byte(248), 1.0)
        self.assertEqual(normalise_byte(255), 1.0)
        for byte in (-1, 256, 1.0, True):
            with self.subTest(byte=byte), self.assertRaises(SVRuleError):
                normalise_byte(byte)

    def test_all_constant_operand_forms(self):
        for operand, data, expected in (
            (9, 123, 0), (10, 123, 1), (11, 124, 0.5),
            (12, 124, -0.5), (13, 124, 5), (14, 124, 0.05),
            (15, 200, 200), (15, 255, 248),
        ):
            with self.subTest(operand=operand):
                result, _ = self.run_program(I(3, operand, data))
                self.assertAlmostEqual(result.accumulator, expected)

    def test_program_framing_and_bytes(self):
        program = Program.from_bytes(bytes([3, 11, 124, 2, 3, 0]) + bytes(42))
        context = Context()
        execute(program, context)
        self.assertEqual(context.neuron[0], 0.5)
        self.assertEqual(len(OPCODE_TYPES), 69)
        for bad in (b"", bytes(47), bytes(49)):
            with self.assertRaises(SVRuleError):
                Program.from_bytes(bad)
        with self.assertRaises(SVRuleError):
            Program.of(*(I(30) for _ in range(17)))
        with self.assertRaises(SVRuleError):
            I(69)
        with self.assertRaises(SVRuleError):
            I(3, 16)
        with self.assertRaises(SVRuleError):
            I(2, 3, 8)
        with self.assertRaises(SVRuleError):
            Program([I(0)] * 16)

    def test_initial_accumulator_is_source_slot_zero(self):
        context = Context(source=[0.75] + [0.0] * 7)
        result = execute(Program.of(), context)
        self.assertEqual(result.accumulator, 0.75)
        self.assertEqual(result.stop_reason, "stop")

    def test_arithmetic_and_bounded_writes(self):
        context = Context()
        result, _ = self.run_program(I(3, 11, 124), I(16, 10), I(19, 13, 124),
                                     I(2, 3, 0), I(26, 10), I(17, 10),
                                     I(2, 2, 1), context=context)
        self.assertEqual(context.neuron[0], 1.0)
        self.assertEqual(context.dendrite[1], -1.0)
        self.assertEqual(result.accumulator, -2.0)

    def test_variable_banks_and_accumulator_operand(self):
        context = Context()
        context.source[2], context.dendrite[2], context.neuron[2], context.spare[2] = .1, .2, .3, .4
        for operand, expected in ((1, .1), (2, .2), (3, .3), (4, .4)):
            with self.subTest(operand=operand):
                result, _ = self.run_program(I(3, operand, 2), context=context)
                self.assertEqual(result.accumulator, expected)
        result, _ = self.run_program(I(3, 10), I(16, 0))
        self.assertEqual(result.accumulator, 2)

    def test_clear_add_store_abs_and_tend_store(self):
        context = Context()
        context.neuron[0] = .8
        self.run_program(I(3, 11, 62), I(34, 3, 0), context=context)
        self.assertEqual(context.neuron[0], 1)
        self.run_program(I(1, 3, 0), context=context)
        self.assertEqual(context.neuron[0], 0)
        self.run_program(I(3, 12, 124), I(45, 3, 1), context=context)
        self.assertEqual(context.neuron[1], .5)
        # Native35 is rate*old_target + (1-rate)*accumulator.
        context.neuron[2] = .8
        self.run_program(I(24, 11, 62), I(3, 11, 0), I(35, 3, 2), context=context)
        self.assertEqual(context.neuron[2], .2)

    def test_invalid_store_destination_is_native_noop(self):
        context = Context()
        self.run_program(I(3, 10), I(2, 7, 1), context=context)
        self.assertEqual(context.neuron, [0] * 8)

    def test_both_zero_divisions_preserve_accumulator(self):
        result, _ = self.run_program(I(3, 10), I(20, 9))
        self.assertEqual(result.accumulator, 1)
        result, _ = self.run_program(I(3, 9), I(21, 10))
        self.assertEqual(result.accumulator, 0)

    def test_condition_fourteen_is_nonnegative_and_fifteen_nonpositive(self):
        for opcode in (14, 15):
            for value in (-.5, 0.0, .5):
                context = Context()
                context.source[1] = value
                self.run_program(I(opcode, 1, 1), I(3, 10), I(2, 3, 0), context=context)
                expected = value >= 0 if opcode == 14 else value <= 0
                self.assertEqual(context.neuron[0], float(expected), (opcode, value))

    def test_comparison_skip_next_only(self):
        context = Context()
        self.run_program(I(3, 10), I(7, 9), I(1, 1, 0), I(2, 3, 0), context=context)
        self.assertEqual(context.neuron[0], 1)
        self.assertEqual(context.source[0], 0)

    def test_forward_jump_uses_one_based_line_and_backward_jump_does_not_loop(self):
        result, context = self.run_program(
            I(52, 15, 4), I(3, 10), I(2, 3, 0), I(3, 11, 124),
            I(52, 15, 1), I(2, 3, 1),
        )
        self.assertEqual(context.neuron[:2], [0, .5])
        self.assertLessEqual(result.executed_instructions, 16)
        result, _ = self.run_program(I(52, 15, 17))
        self.assertEqual(result.stop_reason, "jump-beyond-program")

    def test_fractional_jump_and_negative_preserve_are_explicitly_refused(self):
        context = Context()
        context.source[1] = .5
        with self.assertRaises(UnsupportedSemantics):
            self.run_program(I(52, 1, 1), context=context)
        with self.assertRaises(UnsupportedSemantics):
            self.run_program(I(63, 12, 248))

    def test_preserve_restore_uses_slot_four_and_nonnegative_modulo_eight(self):
        context = Context()
        context.neuron[3] = .6
        self.run_program(I(63, 15, 11), I(1, 3, 3), I(64, 15, 3), context=context)
        self.assertEqual(context.neuron[3], .6)

    def test_stop_comparisons_are_inclusive_where_native_is_inclusive(self):
        for opcode in (55, 56):
            result, context = self.run_program(I(opcode, 9), I(3, 10), I(2, 3, 0))
            self.assertEqual(context.neuron[0], 0)
            self.assertEqual(result.stop_reason, "conditional-stop")

    def test_winner_flag_and_ties_select_current_neuron(self):
        for current, previous, wins in ((.7, .2, True), (.7, .7, True), (.2, .7, False)):
            context = Context()
            context.neuron[0], context.spare[0], context.spare[2] = current, previous, .9
            result, _ = self.run_program(I(42), context=context)
            self.assertEqual(result.registered_as_spare, wins)
            self.assertEqual(context.neuron[2], current if wins else 0)
            self.assertEqual(context.spare[2], 0 if wins else .9)
        result, _ = self.run_program(I(31))
        self.assertTrue(result.registered_as_spare)

    def test_shared_spare_current_array_preserves_native_alias_effect(self):
        shared = [.8, 0, .5, 0, 0, 0, 0, 0]
        context = Context(neuron=shared, spare=shared)
        self.run_program(I(42), context=context)
        self.assertIs(context.neuron, context.spare)
        self.assertEqual(shared[2], .8)

    def test_chemical_banks_are_explicit_offset_read_only_and_wrap_nonnegative(self):
        context = Context(chemicals=[0.0] * 256, source_id=254, destination_id=257)
        context.chemicals[1], context.chemicals[2] = .25, .75
        for operand, data, expected in ((7, 1, .25), (6, 3, .25), (8, 1, .75)):
            result, _ = self.run_program(I(3, operand, data), context=context)
            self.assertEqual(result.accumulator, expected)
        with self.assertRaises(UnsupportedSemantics):
            self.run_program(I(3, 7, 1))
        context.source_id = -2
        with self.assertRaises(UnsupportedSemantics):
            self.run_program(I(3, 6, 0), context=context)

    def test_threshold_and_neuron_dynamics_use_slot_one(self):
        context = Context()
        context.neuron[:2] = [.2, .4]
        self.run_program(I(36, 11, 124), context=context)
        self.assertEqual(context.neuron[1], 0)
        self.run_program(I(37, 11, 124), I(38, 10), I(39, 11, 124), I(40, 11, 124), context=context)
        self.assertEqual(context.neuron[1], .25)
        self.assertAlmostEqual(context.neuron[0], .225)

    def test_random_requires_seed_and_is_repeatable(self):
        with self.assertRaises(UnsupportedSemantics):
            self.run_program(I(3, 5))
        first, a = self.run_program(I(3, 5), context=Context(random_state=0))
        second, b = self.run_program(I(3, 5), context=Context(random_state=0))
        self.assertEqual(first, second)
        self.assertEqual(a.random_state, 1013904223)
        self.assertEqual(a.random_state, b.random_state)
        self.assertGreaterEqual(first.accumulator, 0)
        self.assertLessEqual(first.accumulator, 1)

    def test_tract_setters_clamp_threshold_rate_and_channel_byte(self):
        context = Context(tract=TractState())
        self.run_program(I(57, 13, 248), I(58, 12, 124), I(59, 15, 204),
                         I(60, 12, 248), I(61, 10), I(62, 15, 205), context=context)
        self.assertEqual(context.tract.reward_threshold, 1)
        self.assertEqual(context.tract.reward_rate, -.5)
        self.assertEqual(context.tract.reward_chemical, 204)
        self.assertEqual(context.tract.punishment_threshold, -1)
        self.assertEqual(context.tract.punishment_rate, 1)
        self.assertEqual(context.tract.punishment_chemical, 205)
        with self.assertRaises(UnsupportedSemantics):
            self.run_program(I(59, 11, 124), context=context)

    def test_tract_helpers_are_noops_without_an_enabled_tract(self):
        self.run_program(I(43, 10), I(44, 10), I(57, 10))
        context = Context(tract=TractState(enabled=False))
        self.run_program(I(43, 10), I(57, 10), context=context)
        self.assertEqual(context.tract.short_relaxation, 0)
        self.assertEqual(context.tract.reward_threshold, 0)

    def test_weight_consolidation_uses_old_short_for_both_results(self):
        self.assertEqual(consolidate_weights(.8, .2, .5, .25), (.5, .35000000000000003))
        context = Context(tract=TractState())
        context.dendrite[:2] = [.8, .2]
        self.run_program(I(43, 12, 124), I(44, 11, 62), context=context)
        self.assertAlmostEqual(context.dendrite[0], .5)
        self.assertAlmostEqual(context.dendrite[1], .35)

    def test_reinforcement_is_thresholded_signed_and_bounded(self):
        self.assertEqual(reinforced_weight(.2, .1, .1, .5), .2)
        self.assertAlmostEqual(reinforced_weight(.2, .7, .1, .5), .5)
        self.assertAlmostEqual(reinforced_weight(.2, .7, .1, -.5), -.1)
        self.assertEqual(reinforced_weight(.9, 1, 0, 1), 1)

    def test_nonfinite_inputs_and_results_are_refused_atomically(self):
        for value in (math.nan, math.inf, -math.inf):
            context = Context()
            context.neuron[0] = value
            with self.assertRaises(SVRuleError):
                self.run_program(I(30), context=context)
        context = Context()
        context.source[1] = 1e308
        with self.assertRaises(SVRuleError):
            self.run_program(I(3, 10), I(2, 3, 0), I(3, 1, 1), I(19, 1, 1), context=context)
        self.assertEqual(context.neuron[0], 0)
        context.source[1] = .5
        with self.assertRaises(UnsupportedSemantics):
            self.run_program(I(3, 10), I(2, 3, 0), I(52, 1, 1), context=context)
        self.assertEqual(context.neuron[0], 0)

    def test_eight_variable_and_chemical_shape_invariants(self):
        for name in ("source", "dendrite", "neuron", "spare"):
            for size in (0, 7, 9):
                context = Context()
                setattr(context, name, [0.] * size)
                with self.subTest(name=name, size=size), self.assertRaises(SVRuleError):
                    execute(Program.of(), context)
        with self.assertRaises(SVRuleError):
            execute(Program.of(), Context(chemicals=[0.] * 255))
        with self.assertRaises(SVRuleError):
            execute(Program.of(), Context(tract="invalid"))

    def test_every_native_opcode_has_an_admitted_finite_example(self):
        for opcode in range(69):
            with self.subTest(opcode=opcode):
                # Integer1 is safe for jumps, conversions, division and preserved indices.
                instruction = I(opcode, 3, 0) if OPCODE_TYPES[opcode] == 2 else I(opcode, 15, 1)
                result, _ = self.run_program(instruction, context=Context(random_state=1, tract=TractState()))
                self.assertIsInstance(result, ExecutionResult)

    def test_trusted_and_atomic_boundaries_share_all_opcode_semantics(self):
        from copy import deepcopy
        for opcode in range(69):
            with self.subTest(opcode=opcode):
                original = Context(random_state=9, tract=TractState(), chemicals=[0.] * 256)
                original.source[:2] = [.5, .25]
                original.neuron[:4] = [.4, .2, .1, .8]
                original.dendrite[:2] = [.6, .3]
                other = deepcopy(original)
                instruction = I(opcode, 3, 0) if OPCODE_TYPES[opcode] == 2 else I(opcode, 15, 1)
                program = Program.of(instruction)
                other.validate()
                self.assertEqual(execute(program, original), execute_trusted(program, other))
                self.assertEqual(original, other)

    def test_trusted_kernel_does_not_clone_chemistry_or_scan_whole_context(self):
        from unittest.mock import patch
        context = Context(chemicals=[.25] * 256)
        context.validate()
        chemistry = context.chemicals
        with patch.object(Context, 'validate', side_effect=AssertionError('unexpected rescan')):
            with patch('creature_brain.svrule.deepcopy', side_effect=AssertionError('unexpected clone')):
                execute_trusted(Program.of(I(3, 7, 1), I(2, 3, 0)), context)
        self.assertIs(context.chemicals, chemistry)
        self.assertEqual(context.neuron[0], .25)

    def test_trusted_failure_rejects_nonfinite_output_without_claiming_atomicity(self):
        context = Context()
        context.source[1] = 1e308
        context.validate()
        with self.assertRaises(SVRuleError):
            execute_trusted(Program.of(I(3, 10), I(2, 3, 0), I(3, 1, 1), I(19, 1, 1)), context)
        self.assertEqual(context.neuron[0], 1.0)
        context.source[0] = math.nan
        with self.assertRaises(SVRuleError):
            execute_trusted(Program.of(), context)

    def test_shared_integer_rng_owner(self):
        self.assertEqual(native_random_index(0, 40), (1013904223, 9))
        for bound in (0, -1, 65538, True):
            with self.assertRaises(SVRuleError):
                native_random_index(0, bound)

    def test_genomic_codon_ranges_fold_instead_of_clamping(self):
        self.assertEqual(decode_codon(248, 0, 248), 248)
        self.assertEqual(decode_codon(249, 0, 248), 0)
        self.assertEqual(decode_codon(255, 0, 7), 7)
        self.assertEqual(decode_codon(0, 2, 5), 2)
        self.assertEqual(decode_codon(8, 2, 5), 2)
        program = Program.from_bytes(bytes([255, 255, 255, 3, 3, 255]) + bytes(42))
        self.assertEqual(program.instructions[0], I(255 % 69, 15, 255))
        self.assertEqual(program.instructions[1], I(3, 3, 7))


if __name__ == "__main__":
    unittest.main()
