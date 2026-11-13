"""Run with PYTHONPATH=src python3 examples/learning_demo.py.

Original reference equations; not an execution of the Docking Station genome.
The tiny world supplies physiological outcomes, not dialogue or an LLM.
"""
from dataclasses import asdict
import json

from creature_brain import Brain, BrainConfig, ObservedObject


def run_demo() -> dict:
    brain = Brain(BrainConfig(drives=("hunger", "cold"), actions=("eat", "warm"),
                              learning_rate=0.5, exploration_probability=0, seed=7))
    brain.prime("food", "eat", {"hunger": 0.35, "cold": 0})
    brain.prime("unknown-food", "eat", {"hunger": 0.55, "cold": 0})
    brain.prime("shelter", "warm", {"hunger": 0, "cold": 0.6})
    world = [ObservedObject("apple", "food", {"eat": 1}),
             ObservedObject("bitter-berry", "unknown-food", {"eat": 1}),
             ObservedObject("blanket", "shelter", {"warm": 1})]
    hungry = {"hunger": 0.8, "cold": 0.1}
    first = brain.choose(hungry, world)
    bad_outcome = brain.learn(first.decision_id, {"hunger": 1, "cold": 0.1})
    second = brain.choose(hungry, world)
    good_outcome = brain.learn(second.decision_id, {"hunger": 0.3, "cold": 0.1})
    cold = brain.choose({"hunger": 0.1, "cold": 1}, world)
    brain.discard(cold.decision_id)
    brain.advance(20)
    result = {"model": Brain.MODEL,
              "parity": "original experimental adaptation; not original-engine parity",
              "first_choice": first.chosen.object_id,
              "observed_first_relief": list(bad_outcome.observed_relief),
              "choice_after_bad_outcome": second.chosen.object_id,
              "observed_second_relief": list(good_outcome.observed_relief),
              "choice_when_cold": cold.chosen.object_id,
              "consolidated_food_association": brain.association("food", "eat"),
              "initial_decision_trace": asdict(first)}
    assert result["first_choice"] == "bitter-berry"
    assert result["choice_after_bad_outcome"] == "apple"
    assert result["choice_when_cold"] == "blanket"
    return result


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, allow_nan=False))
