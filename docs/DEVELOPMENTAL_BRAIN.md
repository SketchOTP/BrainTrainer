# Our developmental brain

The owner's correction is authoritative: build our own learning and developing
brain from the recovered Creatures substrate. Partner selection is out of scope.
The inherited controller may be modified or replaced; compatibility with its old
choices is a reference/control property, not the definition of success.

## Current v3 extension

The brain now discovers non-food affordances, sets practice goals, learns observed
object transitions and verifies known skills on a new target. Device-only and
mixed-scene tests cover actual effects and persistent practice, with a bounded
memory ablation. See [the affordance results](AFFORDANCE_LEARNING_RESULTS.md).
The new curriculum lives in `src/creature_brain/curriculum.py`; it is part of the
same continuing individual's executive and history, not a separate trained pet.

## Retained v2 extension

Automatic rehearsal now revises persistent goals and changes subsequent real
actions after repeated non-progress. The controlled result includes both reduced
reserve cost and delayed recovery probing. Read [the full result and limits](REHEARSAL_GOAL_RESULTS.md).
V1 continuations remain supported; explicitly adopting `--development` upgrades
an existing v1 individual with a recorded implementation event.

## Initial implementation and retained v1 evidence

`src/creature_brain/development.py` is a reusable first developmental executive.
It consumes the continuing individual's attributed experience and learned outcome
memory. The host retains the recovered neural proposal separately from the new
executive's selected action, then executes the latter through the body. This is
an intentional change to who decides behavior, not another cue that the inherited
brain must obey. Both choices and the reason remain in the evidence.

A naturally experienced adverse outcome creates an internal goal. The current
initial strategy changes a repeated harmful eating proposal into retreat;
review measures actual movement away from the target. Three successful local
steps mark the strategy locally demonstrated; this is not global mastery. A
repeat adverse outcome can create/revise an active goal. This mechanism is
currently specific to a narrow class of outcomes and must become more general.
Goals arise from experience, not a developer command naming the next target.

The brain's self-review reports real attempts, completions, outcome assessments,
goal evidence and progress. It does not pretend to know whether an implementation
fault caused a failure. Memory and reviews reconstruct from the retained ledger.

The first dreaming primitive performs explicit offline learned-model rehearsal:
it considers experienced action/type effects, predicts their response signals,
and records candidate strategies and unknown alternatives. It neither advances
the real world nor counts predictions as successful experiences. It is presently
a basic rehearsal record, not a demonstrated general world model or proof that
dreaming improves learning. V2 adds automatic failure-triggered rehearsal and goal revision. Richer learned
models, sleep cycles and broader benefits from dreaming remain required development.

## Evidence so far

Thirty related tests passed in 22.700 seconds before the semantics-preserving
move of the executive into `src/`. Tests include a naturally experienced adverse
outcome causing a goal and a changed real action, actual movement, dream/lived
experience separation, and actual OS-process restart retaining goals, reviews,
rehearsals and continuation. The focused post-move log is recorded separately.

A development comparison reused four previously seen histories (seeds 16 and 17,
both helpful-food identities). In 24 subsequent ticks, recall-only consumed one
helpful and one harmful item in every case. The new executive consumed the
helpful item and no harmful item in all four. It spent more movement reserve;
final reserve was about 99.43 versus 99.64–99.76 for recall-only. This is bounded
development evidence, not a new held-out qualification or a guarantee of safe
behavior over long use. Goal creation and action changes are authored mechanisms
operating on the individual's experience, not evidence of subjective awareness.

Raw comparisons and pinned sources:
`validation/developmental-brain-development-v1/`.
Test log: `validation/developmental-brain-tests.log`.

## Retired work and preservation

Partner-selection modules, their runner and tests are removed from active paths.
The full prior example/test sources remain in
`validation/before-developmental-brain/`, alongside the earlier frozen studies.
Historical results are preserved, not repurposed as evidence for this goal.
A checkpoint explicitly adopting the retired partner module is rejected by the
current loader with recovery direction to the archived implementation; no live
individual was migrated or overwritten. Ordinary source/reference processes were
not changed.

Use `--development` on the continuing-companion CLI to adopt this executive,
`--dream` to record an offline rehearsal, and `--learned-recall` to adopt the
existing positive-outcome memory path. These are currently research controls.
The CLI emits the actual self-review, not an invented first-person narrative.

The full goal remains incomplete: general self-set goals, autonomous review and
practice cycles, useful dreaming, digital self-understanding, self-directed
executable changes, improved improvement procedures, and sustained companionship
all require further implementation and evidence.


## V4 executable practice development

`practice_policy.py` owns the finite executable source language. `curriculum.py`
owns observed failure diagnosis and candidate generation. The isolated host
`self_development.py` owns explicitly branched execution and regression judgment.
An ordinary continuing tick services a pending creature-originating review, records
the evaluation separately from lived outcomes, adopts a passing source program,
and resumes the original goal. The adopted program and digest are reconstructed
from implementation events on restore. See EXECUTABLE_PRACTICE_RESULTS.md.

## V5 requests, advice and experiential verification

An unresolved practice goal without a justified pending executable intervention
can emit one grounded `communication` request. `offer_practice_guidance` validates
an answer against that actual request before recording attributed supplied
information. A bounded practice allowance changes a goal, not executable code.
Only subsequent real results support or fail the advice. Successful practice
requirements are retained with teacher and outcome provenance and inform a new
target of the same observed type, which still requires verification.

The CLI accepts `--guidance-goal ID --additional-attempts N --teacher SOURCE`
with `--resume CHECKPOINT --steps N --output NEW_CHECKPOINT`. Requests and advice
status are exposed in `self_review`. Source identity is supplied attribution,
not inferred person recognition. See ASSISTED_LEARNING_RESULTS.md.

## V6 maintenance and consequential rest

`maintenance.py` owns the initial drive, recorded recovery episodes and
experience-derived rest expectations. MotorIndividual owns intrinsic targetless
rest execution and reserve restoration. The continuing host supplies observed
reserve to the executive and records before/after resource observations. It does
not supply the hidden recovery-rate parameter to the maintenance learner.

V6 adoption records the rest body model explicitly. Old implementations restore
without enabling the capability. Goals and rest evidence reconstruct from actual
history, including a goal interrupted by maintenance. A failed method stops and
exposes uncertainty; autonomous repair of failed recovery is unfinished. See
MAINTENANCE_RESULTS.md for tests, controlled comparisons and deployment scope.

## V7 familiar activities and retained preferences

The curriculum can set a familiar-activity goal when no visible active practice
goal needs attention and at least 32 ticks have elapsed since goal-directed
practice. It ranks demonstrated non-harmful device interactions using their latest
eight attributed visible-effect outcomes. The chosen goal records the comparison
and evidence. New outcomes revise the ranking, including failures after a formerly
responsive object changes. Maintenance and useful food retain their existing
priority. Goal construction owns retained teaching allowances for discovery,
verification and familiar returns alike. See FAMILIAR_ACTIVITY_RESULTS.md.

`development.supports` owns the capability/version registry, used by both executive
selection and host restoration checks. New latest versions do not implicitly
remove capabilities from older supported implementations.
