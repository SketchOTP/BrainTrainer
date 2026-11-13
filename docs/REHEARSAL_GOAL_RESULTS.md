# Automatic rehearsal and goal revision

The corrected v2 executive can maintain an active goal independently of the
inherited brain's changing proposals. After three observed non-progress retreat
attempts, it initiates offline rehearsal, revises the goal to wait and probe,
executes four held actions, and then tests movement again. A real successful
probe updates the goal back to ordinary action selection. The body-strength
setting and recovery transition are not executive inputs.

This is a small functional cycle of experience, reflection, rehearsal, goal
revision and changed behavior. The four-action waiting interval and available
initial strategy are authored. The brain has not yet learned to generate arbitrary
strategies, learned a rich generative world model, or demonstrated general dreaming.
Rehearsals remain explicitly separate from experienced outcomes and do not advance
the simulated world. Review counters called `real_attempts` and `real_completions`
cover terminal interaction reports; they exclude movement attempts and deliberate
waiting. They are not general motor competence totals.

## Frozen four-seed comparison

All four cases met the [predeclared bounded gates](REHEARSAL_GOAL_PROTOCOL.md).
Each acquired its adverse-outcome history through actual brain-selected action.
During 24 impaired ticks, the rehearsal arm spent **0.34 reserve units**, versus
**0.87** for the same v2 executive with automatic rehearsal scheduling suppressed.
In each of the four cases, first away movement after recovery occurred at tick
**4** with rehearsal versus tick **1** with rehearsal suppressed. All rehearsal
cases demonstrated at least three real away steps within 12 recovery ticks.
No arm consumed harmful food during the impairment/recovery comparison.

The earlier v1 arm spent 0.93, 1.14, 0.81 and 0.24 units. Its first away movement
was unobserved within the window for one seed, and occurred at ticks 1, 3 and 2
for the others. Thus v2 is not uniformly cheaper than v1. The ablation isolates
the scheduling path within v2; the v1 comparison also changes goal persistence.
The observed tradeoff is reduced repeated effort against delayed recovery probing.

The independent audit verified source digests, checkpoint histories, actual
reserve differences, zero dreamed outcome/time increments and **80** links from
recorded rehearsals to subsequent real held actions. The ablation deliberately
monkey-patches only `rehearsal_due` in the evaluation harness and records that
intervention. Its future checkpoint continuation requires that same harness;
an uninstrumented resume would reinstate automatic scheduling. It is not a normal
product mode or evidence of a portable disabled-rehearsal individual.

## Failure preserved and structural correction

The initial development attempt changed a goal only when the substrate continued
proposing eat. When the substrate switched to movement, the pending plan stalled
and the recovery test failed. The failed source, test log and raw trace are in
`validation/dream-development-v2/failed-source/` and its parent directory.

The fix gives an active goal ownership of its short action sequence, with a known
useful resource taking precedence over avoidance practice. The new regression
requires a rehearsed action even when the substrate proposal changes. Rehearsal
and action capacity are reserved together before either proceeds, so a full ledger
does not leave an unrecorded partial step.

## Continuity and verification

- 34 related tests passed in 25.412 seconds; no failures, errors or skips.
- Actual child-process restart preserved a pending rehearsed plan and subsequent
  automatic rehearsals, exact checkpoint continuation and review state.
- Explicit v1-to-v2 adoption preserves identity, host state and the entire prior
  history, then records an implementation event. This adoption is developer-led;
  it is not evidence of creature-directed executable self-modification.
- One six-tick legacy continuation exactly matched the preserved v1 code's complete
  checkpoint. The first comparison attempt failed before creature load because
  the archived host lacked sibling modules on its import path; that failure is
  retained. The corrected comparison verified the shared dependencies unchanged.

Evidence: `validation/rehearsal-panel-v1/{manifest.json,cases.jsonl,audit.json}`,
`validation/rehearsal-related-tests.log`, and
`validation/development-v1-compatibility/receipt.json`.

The full end goal remains incomplete. Next work must broaden self-set learning
and improvement goals beyond this avoidance task, use richer memories and
rehearsed alternatives, and connect measured limitations to actual implementation
experiments. A successful local wait/probe policy is not the definition of the brain.
