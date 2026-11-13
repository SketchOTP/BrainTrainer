import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

from creature_brain import Brain, BrainConfig, ObservedObject


def config(**changes):
    return BrainConfig(drives=("hunger", "cold"), actions=("eat", "warm"),
                       exploration_probability=0, **changes)


def world():
    return [ObservedObject("apple", "food", {"eat": 1}),
            ObservedObject("blanket", "shelter", {"warm": 1})]


class CoreTests(unittest.TestCase):
    def test_current_needs_change_object_attention_and_action(self):
        brain = Brain(config())
        brain.prime("food", "eat", {"hunger": 0.7, "cold": 0})
        brain.prime("shelter", "warm", {"hunger": 0, "cold": 0.7})
        hungry = brain.choose({"hunger": 1, "cold": 0.1}, world())
        cold = brain.choose({"hunger": 0.1, "cold": 1}, world())
        self.assertEqual((hungry.chosen.object_id, hungry.chosen.action), ("apple", "eat"))
        self.assertEqual((cold.chosen.object_id, cold.chosen.action), ("blanket", "warm"))
        for decision in (hungry, cold):
            for c in decision.candidates:
                self.assertAlmostEqual(c.score, c.accessibility * (
                    sum(c.drive_contributions) + c.feedback_contribution))

    def test_accessibility_scales_score_and_zero_is_not_selected(self):
        brain = Brain(config())
        brain.prime("food", "eat", {"hunger": 1, "cold": 0})
        observations = [ObservedObject("blocked", "food", {"eat": 0}),
                        ObservedObject("far", "food", {"eat": 0.2}),
                        ObservedObject("near", "food", {"eat": 0.8})]
        choice = brain.choose({"hunger": 0.5, "cold": 0}, observations)
        self.assertEqual(choice.chosen.object_id, "near")
        self.assertEqual(len(choice.candidates), 2)
        self.assertAlmostEqual(choice.chosen.score, 0.4)

    def test_signed_outcomes_change_preferences_and_generalize_category(self):
        brain = Brain(config(learning_rate=1))
        brain.prime("food", "eat", {"hunger": 0.4, "cold": 0})
        brain.prime("bad", "eat", {"hunger": 0.6, "cold": 0})
        observations = [ObservedObject("good", "food", {"eat": 1}),
                        ObservedObject("unknown", "bad", {"eat": 1})]
        choice = brain.choose({"hunger": 0.7, "cold": 0}, observations)
        self.assertEqual(choice.chosen.object_id, "unknown")
        learned = brain.learn(choice.decision_id, {"hunger": 1, "cold": 0})
        self.assertAlmostEqual(learned.observed_relief[0], -0.3)
        self.assertLess(brain.association("bad", "eat")["short_relief"]["hunger"], 0)
        next_choice = brain.choose({"hunger": 0.7, "cold": 0}, observations)
        self.assertEqual(next_choice.chosen.object_id, "good")
        brain.learn(next_choice.decision_id, {"hunger": 0.2, "cold": 0.1})
        learned_food = brain.association("food", "eat")["short_relief"]
        self.assertAlmostEqual(learned_food["hunger"], 0.5)
        self.assertAlmostEqual(learned_food["cold"], -0.1)
        other_apple = brain.choose({"hunger": 1, "cold": 0},
                                  [ObservedObject("new-apple", "food", {"eat": 1})])
        self.assertAlmostEqual(other_apple.chosen.score, 0.5)

    def test_feedback_does_not_fabricate_drive_relief(self):
        brain = Brain(config(learning_rate=1))
        choice = brain.choose({"hunger": 0.5, "cold": 0.5}, world())
        brain.learn(choice.decision_id, {"hunger": 0.5, "cold": 0.5}, feedback=-1)
        association = brain.association(choice.chosen.category, choice.chosen.action)
        self.assertEqual(association["short_relief"], {"hunger": 0.0, "cold": 0.0})
        self.assertEqual(association["short_feedback"], -1)
        another = brain.choose({"hunger": 0.5, "cold": 0.5},
                               [ObservedObject("same", choice.chosen.category,
                                               {choice.chosen.action: 1})])
        brain.learn(another.decision_id, {"hunger": 0.5, "cold": 0.5})
        self.assertEqual(brain.association(choice.chosen.category,
                                          choice.chosen.action)["short_feedback"], -1)

    def test_outcome_is_consumed_once_and_invalid_outcome_preserves_pending(self):
        brain = Brain(config())
        decision = brain.choose({"hunger": 1, "cold": 0}, world())
        with self.assertRaises(ValueError):
            brain.learn(decision.decision_id, {"hunger": math.nan, "cold": 0})
        self.assertIn(decision.decision_id, brain.pending_actions)
        brain.learn(decision.decision_id, {"hunger": 0.5, "cold": 0})
        with self.assertRaises(KeyError):
            brain.learn(decision.decision_id, {"hunger": 0.5, "cold": 0})
        with self.assertRaises(ValueError):
            brain.prime(decision.chosen.category, decision.chosen.action,
                        {"hunger": 1, "cold": 0})

    def test_consolidation_preserves_lasting_learning_and_relaxation_recovers_prior(self):
        brain = Brain(config(learning_rate=1, consolidation_rate=0, relaxation_rate=0.5))
        brain.prime("food", "eat", {"hunger": 0.8, "cold": 0})
        decision = brain.choose({"hunger": 0.4, "cold": 0},
                                [ObservedObject("apple", "food", {"eat": 1})])
        brain.learn(decision.decision_id, {"hunger": 0.6, "cold": 0})
        self.assertAlmostEqual(brain.association("food", "eat")["short_relief"]["hunger"], -0.2)
        self.assertEqual(brain.association("food", "eat")["long_relief"]["hunger"], 0.8)
        brain.advance(3)
        self.assertGreater(brain.association("food", "eat")["short_relief"]["hunger"], 0.6)
        consolidated = Brain(config(learning_rate=1, consolidation_rate=0.5, relaxation_rate=0))
        decision = consolidated.choose({"hunger": 1, "cold": 0}, world())
        consolidated.learn(decision.decision_id, {"hunger": 0.2, "cold": 0})
        consolidated.advance(3)
        self.assertAlmostEqual(consolidated.association("food", "eat")["long_relief"]["hunger"], 0.7)

    def test_checkpoint_preserves_pending_credit_and_seeded_continuation(self):
        cfg = BrainConfig(drives=("hunger", "cold"), actions=("eat", "warm"),
                          exploration_probability=1, seed=932)
        brain = Brain(cfg)
        pending = brain.choose({"hunger": 0.5, "cold": 0.5}, world())
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "brain.json"
            brain.save(checkpoint)
            restored = Brain.load(checkpoint)
            with self.assertRaises(FileExistsError):
                brain.save(checkpoint)
            a = brain.learn(pending.decision_id, {"hunger": 0.1, "cold": 0.9})
            b = restored.learn(pending.decision_id, {"hunger": 0.1, "cold": 0.9})
            self.assertEqual(a, b)
            for _ in range(24):
                self.assertEqual(brain.choose({"hunger": 0.5, "cold": 0.5}, world()),
                                 restored.choose({"hunger": 0.5, "cold": 0.5}, world()))
            self.assertEqual(brain.to_dict(), restored.to_dict())

    def test_empty_perception_and_explicit_discard_do_not_invent_outcomes(self):
        brain = Brain(config())
        self.assertIsNone(brain.choose({"hunger": 1, "cold": 0}, []))
        self.assertEqual(brain.pending_actions, ())
        d = brain.choose({"hunger": 1, "cold": 0}, world())
        brain.discard(d.decision_id)
        self.assertEqual(brain.pending_actions, ())
        self.assertEqual(brain.association(d.chosen.category, d.chosen.action)["samples"], 0)

    def test_invalid_numeric_and_shape_inputs_fail_before_learning(self):
        brain = Brain(config())
        for value in (-0.1, 1.1, math.inf, math.nan, True):
            with self.assertRaises(ValueError):
                brain.choose({"hunger": value, "cold": 0}, world())
        with self.assertRaises(ValueError):
            brain.choose({"hunger": 1}, world())
        with self.assertRaises(ValueError):
            brain.choose({"hunger": 1, "cold": 0}, [
                ObservedObject("a", "food", {"eat": 1}),
                ObservedObject("a", "food", {"eat": 1})])
        with self.assertRaises(ValueError):
            brain.choose({"hunger": 1, "cold": 0}, [ObservedObject("a", "food", {"fly": 1})])
        with self.assertRaises(ValueError):
            Brain(BrainConfig(drives=("hunger", "hunger"), actions=("eat",)))

    def test_checkpoint_rejects_unknown_models_and_invalid_weight_dimensions(self):
        brain = Brain(config())
        brain.choose({"hunger": 1, "cold": 0}, world())
        data = json.loads(json.dumps(brain.to_dict()))
        changed = copy.deepcopy(data)
        changed["model"] = "not-this-brain"
        with self.assertRaises(ValueError):
            Brain.from_dict(changed)
        data["associations"][0]["short"].append(0)
        with self.assertRaises(ValueError):
            Brain.from_dict(data)

    def test_inspection_is_detached(self):
        brain = Brain(config())
        brain.prime("food", "eat", {"hunger": 0.7, "cold": 0})
        view = brain.association("food", "eat")
        view["short_relief"]["hunger"] = -1
        self.assertEqual(brain.association("food", "eat")["short_relief"]["hunger"], 0.7)


if __name__ == "__main__":
    unittest.main()
