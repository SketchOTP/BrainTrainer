# Separate experimental decision core

This earlier model remains available for comparison. The full genome simulation does not call it.

## Use the experimental decision core

```python
from creature_brain import Brain, BrainConfig, ObservedObject

brain = Brain(BrainConfig(
    drives=("hunger", "cold"), actions=("eat", "rest"),
    exploration_probability=0.0, seed=7,
))
brain.prime("food", "eat", {"hunger": 0.6, "cold": 0.0})
brain.prime("shelter", "rest", {"hunger": 0.0, "cold": 0.7})

choice = brain.choose(
    {"hunger": 0.8, "cold": 0.1},
    [ObservedObject("apple", "food", {"eat": 1.0}),
     ObservedObject("nest", "shelter", {"rest": 1.0})],
)
# The adapter executes the chosen action and measures its consequences.
if choice is not None:
    outcome = brain.learn(choice.decision_id, {"hunger": 0.3, "cold": 0.1})
```

A body/world adapter supplies perception, normalized needs, affordances, action execution and correctly attributed outcomes. The choice includes score contributions for inspection. Call `discard` when an outcome cannot be attributed; do not invent positive feedback. Category/action associations generalize across observed objects. `prime` supplies declared priors, not the game's instinct rehearsal. Explicit `advance` calls update the model's own weight timescales, not a measured game clock.

Checkpoints retain learned weights, RNG state and pending action handles. Defaults, rates, exploration, score summation, generic-feedback treatment and consolidation equations are original design choices; [implementation_receipt.json](../implementation_receipt.json) records them.
