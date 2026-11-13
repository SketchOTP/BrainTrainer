# Asynchronous reflective mind qualification — 2026-11-08

The candidate v33 scheduler runs a single Codex OAuth reflection worker while the
body continues acting. Request intent is saved before starting the worker; the
habitat owner admits the returned proposal and records the result. No worker
thread directly changes the creature. The main habitat remains v32, without the
`--reflect` option; no qualification history was imported.

## Lifecycle checks

Seventeen reflection, scheduling and lived-trial tests passed in 10.224 seconds
(`validation/reflection-scheduler/final-lifecycle-tests.log`). They include:
provider failure retention, malformed terminal receipts leaving recovery pending
while body activity continues, completed receipt recovery after restart, duplicate
admission prevention when a trial was saved before its result, response integrity,
owned provider cancellation/reaping, and distinct actual trial outcomes.

Malformed receipts previously could raise attribute/key errors in the scheduler.
`llm_reflection.read_receipt` now owns terminal receipt validation. Missing,
malformed or unknown receipts do not become failures or successful proposals; they
remain recovery-required. Malformed packet objects are rejected before hashing.
Normal cancellation kills and reaps the owned provider and retains its failure
receipt. Unexpected host-crash recovery with no receipt still needs a recovery
workflow; it does not automatically launch another request.

## Actual OAuth scheduling and outcome review

An explicit qualification individual continued for 65 body ticks while the first
OAuth proposal ran. Its actual trial then spent four ticks approaching the toy;
it never reached an interaction attempt. The outcome was incomplete, not a failed
skill or successful learning claim. This is evidence of a changing situation during
reflection: the individual had moved away since the proposal's source snapshot.

The same individual's scheduler later requested review of that actual outcome.
During this second OAuth request the body advanced another 64 ticks. The returned
review correctly cited the four approach events, distinguished zero eligible
attempts from failed interactions, and increased its proposed total allowance
from four to sixteen world ticks. The second trial also exhausted its allowance
while approaching, with zero interaction attempts. Both results restored exactly.

Evidence is in `validation/reflection-scheduler/oauth-02/`: provider request,
response, usage and terminal receipts; `result.json`; `review-result.json`; and
saved individual checkpoints. The first provider used 17,859 input and 519 output
tokens. The second provider's usage remains in its own job receipt.

The qualification harness had two failures, retained rather than hidden. Run 01
used exclusive checkpoint save for repeated writes, failed, and cancelled its
owned provider. Run 02 initially polled a future already consumed by the scheduler;
the saved admitted trial was recovered and continued without a second provider
request. The harness now uses atomic replacement and handles a consumed future.

## What this proves and what remains

The candidate can initiate a reflective job from unresolved experience, continue
bodily activity during it, perform the returned trial through its body, and ask
for a new review based on the actual outcome. The review changed its proposed
practice budget. That is a bounded demonstration of experience affecting planning.
It does not prove improved competence or a better improvement process: both
asynchronous trials were incomplete.

Before live enablement, resolve the observed stale-snapshot planning problem:
current distance at reflection request is not distance at admission. Preserve
ongoing bodily activity and the distinction between approaching and attempting;
do not retrospectively extend a returned plan or count approaching as successful
practice. Qualify a useful strategy in changing circumstances, surface the actual
reflective goal and outcome in the habitat, and retain failed attempts. Other
reflective methods, generative sprites/environment authoring and general executable
self-improvement remain incomplete.

## Timing-aware follow-up (same test individual)

The packet now projects an execution context: the snapshot tick, the fact that
body activity continues during reflection, actual prior source/admission ticks,
and the scope of the trial clock (approach and interruptions included). Recorded
latencies remain experience, not a predicted or guaranteed future delay. A test
checks five actual body ticks between source and admission, the referenced
admission event, and unchanged state during projection.

The third actual OAuth review continued the same qualification individual after
both incomplete trials. Its body advanced 71 ticks while reflection ran. The
response explicitly cited prior 64–65 tick delays and observed approach distances,
then selected an 80-world-tick allowance. The body approached for 33 ticks and
completed one interaction on the next tick, observing the predicted appearance
change. The persisted result is observed-success with one attempt; full restore
matched exactly. Evidence: `oauth-02/timing-review-result.json`,
`timing-review-individual.json`, and the corresponding request/response/receipt
under `validation/reflection-scheduler/`. Usage: 29,521 input and 721 output tokens.

This is one useful planning revision after actual unsuccessful approaches, with
additional developer-supplied timing semantics. It is not autonomous invention
of those semantics, general competence, or proof of sustained improvement of the
improvement process. Earlier failures remain part of the same test history.

The response also stated a 20-unit distance condition in prose. At execution the
observed distance was 12.1 units, within that stated condition, but the executor
had no representation for it. The subsequent implementation adds nullable
`max_target_distance` to new generated plans and checks it against actual
perception before acting. An exceeded condition stops the trial as incomplete,
with zero claimed interaction attempts. Existing historical plans without that
field retain their original semantics. Prompt guidance now names the supported
executable conditions and does not promise enforcement of other prose. The
recorded third run is preserved as generated; no field was retroactively added.

Live enablement still requires habitat presentation of reflective goals/results
and qualification in the rural world. The live v32 individual was observed running
without error at tick 26218, with reflection disabled. No live restart or migration
was performed in this timing follow-up.
