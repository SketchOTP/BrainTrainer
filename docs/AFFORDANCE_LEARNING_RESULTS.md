# Self-set learning goals beyond avoidance

The v3 developmental brain can notice an unfamiliar interaction affordance, create
a practice goal, approach its target, try the interaction and learn an observed
state transition. It distinguishes discovery from verification of a known skill
on a new object. Goals and evidence survive an actual process restart during
practice. No teacher names the task or issues an action sequence.

Two opt-in digital body devices provide real consequences: a switch flips state;
a counter increments it. The learner receives current appearance, geometry and
available actions, not the device's implementation function. This is an authored
virtual body, not a claim of Docking Station parity. The shared lifecycle now
calls the body's execution hook, and only actual consumption hides a target;
completing another kind of action no longer implies that the object disappeared.
Device state is validated by the body owner on restore.

## Frozen eight-case comparison

Seeds 60–63 each encountered both device functions under opaque type labels and
mirrored geometry. Every case met the [bounded protocol](AFFORDANCE_LEARNING_PROTOCOL.md):

- The creature approached the unfamiliar device and produced two actual state
  changes, retaining their before/after appearances and provenance.
- On a new object with the same type, intact memory created a verification goal,
  correctly predicted its initial effect, and required one real activation.
- With only the derived skill projection cleared, the same brain/body state
  created a discovery goal and required two real activations.

All eight retained predictions matched observations. The independent audit checked
40 actual state changes and the evidence behind the goals. Transfer took 12 ticks
with retained skills and 13 with the projection cleared. This modest difference
comes from an authored verification stopping rule; it is not an independently
learned optimal sample budget. The ablation keeps original episode history, so a
normal checkpoint restore reconstructs the cleared projection. Reproducing that
control requires the explicit evaluation harness intervention.

The model predicts only transitions it has observed. It has not inferred arbitrary
counter arithmetic or generalized toggle algorithms. Available-action hints,
curiosity priorities, interaction candidates, and stopping thresholds are authored
starting mechanisms. Broad causal reasoning, personality and self-directed
executable development remain unproven.

## Integrated behavior and validation

Mixed scenes required a further scheduling rule: a different learning activity
can take priority over repeatedly retreating from a known adverse interaction.
Known harmful interactions are excluded from curiosity practice. The initial
mixed-scene test exercised successful device learning but failed its deferred-goal
assertion because its setup had not established the avoidance history it meant
to test. The corrected fixture first acquires a natural adverse outcome, then
introduces the mixed scene. It verifies actual goal deferral, device learning and
no additional harmful consumption. The failed fixture and log remain preserved.

Validation executed:

- Initial related selection: 42 passed, 30.811 seconds.
- Expanded integration selection: 44 passed and the one fixture assertion above
  failed; log retained. No production test failure was omitted.
- Final corrected curriculum selection: all seven passed, 7.476 seconds,
  including process restart, mixed goals, harmful-practice exclusion, invalid
  device checkpoints and wrong-action attribution.
- Two previously seen panel cases were rerun after the integration corrections;
  their persisted JSON case records matched exactly. The first comparator
  incorrectly compared tuple-containing Python objects with parsed JSON lists;
  its failure is retained, and the corrected audit compares parsed evidence on
  both sides. This is a bounded compatibility follow-up, not another held-out panel.
- One archived v2 continuation matched the current v2 mode after removing only
  the additive `observation_after` field. Physical, neural, goal-decision and
  remaining checkpoint data matched. No universal compatibility claim is made.

## Evidence

`validation/affordance-panel-v1/` contains the frozen source, raw cases, all
checkpoints and `audit.json`. Raw cases SHA-256:
`bbbe9ec82c105ea9efeba44b70ae49d2fdc633abf4154f60e949293c9346b991`.

Logs and follow-ups:
`validation/curriculum-tests.log`,
`validation/curriculum-integrated-tests.log`,
`validation/curriculum-mixed-final-tests.log`,
`validation/curriculum-mixed-scene-initial/`,
`validation/affordance-postintegration-replay/receipt.json`, and
`validation/curriculum-v2-compatibility/receipt.json`.

The full goal remains active. Next work must turn unresolved practice into useful
diagnosis and alternative generation, then connect self-selected improvement
goals to evaluated executable changes. These two device tasks are supporting
experiments, not the definition of the intended creature.
