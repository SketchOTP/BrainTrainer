# Continuing companion habitat

The developmental individual now has a separate local browser habitat. It uses
`ContinuingCompanion` directly, including its brain, world, remembered outcomes,
self-set goals, rehearsal, executable revision and verified teaching. It does not
replace the original viewers or import their individuals.

Launch from this candidate root:

```sh
PYTHONPATH=src .venv/bin/python \
  examples/persistent_individual/habitat.py \
  --home runs/habitat-visual-qualification --port 46341
```

The qualified instance is already listening at http://127.0.0.1:<port> and paused.
Its identity is `<record-id>`. Do not launch a duplicate;
the directory lock rejects a second owner. A restart always begins paused and
restores the checkpoint without inventing elapsed experiences. An initial attempt
on port 46340 failed to bind; its receipt is preserved. The same saved individual
was then opened on 46341.

Run enables autonomous ticks. One moment advances a paused individual. Offering
food or a device changes the actual world and records an attributed intervention.
The brain chooses activity. A request for help comes from a real unresolved goal;
a suggestion changes its limited practice plan and remains unverified until real
outcomes support or fail it. Rehearse invokes the existing offline model rehearsal,
which does not claim real outcomes. The figure's gaze follows its actual target;
movement and action text reflect executed behavior. The figure is an initial
neutral design, not a claim that personality or affect has been completed.

## Persistence and recovery

Every successful tick and command writes a complete checkpoint to `current.json`
using an atomic replacement, with `previous.json` retaining the prior write.
These are two complete histories, not a growing directory of full copies.
Exclusive ownership covers the directory. If writing fails, activity pauses and
the in-memory state is retained; Save / retry attempts to preserve it. The UI
shows actual and durable ticks separately. It does not pretend an unsaved tick
was preserved. An abrupt exit after an acknowledged successful write was tested.
This does not establish power-loss behavior on every filesystem.

Missing current state with recovery evidence does not silently create another
individual. Corrupt state is not silently rolled back. Preserve the directory and
inspect previous/pending files before any manual recovery; rollback changes history
and requires explicit attribution. Automated rollback UI is unfinished.

## Observed evidence

Three tests passed: real HTTP teaching with abrupt process restart; injected
write failure with pause and retry; and exclusive ownership plus missing-current
recovery refusal. The real browser was inspected and used to offer the patient
lantern, observe an autonomous request after three no-effect attempts, provide
five additional attempts, and observe two real visible changes supporting the
advice. The same individual was left paused at tick 93, with durable tick 93.
See `validation/habitat-receipt.json`, `habitat-tests.log`,
`habitat-observed-state.json` and `habitat-teaching-visible.jpg`.

The interface is one integrated surface, not completion of the end goal. Sustained
ordinary life, richer embodiment and activities, resource replenishment, personality,
person recognition and relationship development, additional types of self-directed
code improvement, and improvement of the improvement process remain unfinished.
The event-capacity bound still stops rather than discards history; long-term
archival is required before sustained unattended use. Android/device acceptance
has not been performed.

## Qualified v6 adoption

The continuing individual has now adopted developmental v6 and intrinsic rest.
Its identity, branch, neural/body state and full prior history were checked before
and after; only the declared rest capability flag and one attributed implementation
event changed. No lived tick was added during migration. Its previous raw checkpoint,
normalized before-image, candidate and adoption receipt are retained under
`validation/visible-v6-upgrade/`. This is a developer-qualified upgrade, not a
creature-initiated code revision.

The habitat exposes maintenance goals and reserve. Real rest execution was visibly
verified on an explicit test branch, whose UI labels its branch identity. That
branch advanced from moment 93 to 94 and gained 0.5 reserve. It was then stopped;
its experience was not merged into the continuing individual. The main habitat
on port 46341 remains paused at moment 93, now running v6, with its prior teaching
history intact. Four migration/persistence tests passed. The tests cover exclusive
ownership, before-image preservation, idempotent adoption, durable HTTP teaching,
restart and injected write recovery. See `validation/habitat-upgrade-final-tests.log`,
`habitat-v6-observed-state.json` and `habitat-rest-visible.jpg`.

Use `upgrade_habitat.py --home DIRECTORY --evidence NEW_DIRECTORY` only while the
individual's owner is stopped. The lock enforces exclusive migration; repeated
adoption of the same version is a no-op. The tool preserves the raw before-image
and checks the exact allowed state difference before installation.

## Storage format update

The candidate storage owner now supports [immutable history segments](HISTORY_ARCHIVE.md).
After a future restart and save, `current.json` and `previous.json` may be directory
manifests rather than standalone envelopes. Preserve the full habitat directory,
or use the documented portable export. The currently running instance was not
converted during archive qualification. The existing memory-capacity stop remains.

## V9 adoption into the continuing individual

The qualified v7–v9 capabilities and segmented/lazy history owner are now installed
in the same visible individual at `http://127.0.0.1:<port>`. The previous owner was
confirmed paused and saved, then stopped cleanly before exclusive offline adoption.
The server restarted successfully with v9 and remains paused at tick 93. Identity
`<record-id>` and branch
`<record-id>` are unchanged.

The upgrade preserved the complete prior event prefix, neural state, learned
skills, teaching history, body values and lineage. It added the declared hold
capability and one attributed implementation-adoption event. This was a developer
upgrade, not a claimed self-directed revision by the visible creature. The UI
correctly still shows zero creature code revisions in this individual's history.

The checkpoint now uses `creature-brain-segmented-habitat-v1`; use the storage
owner for reading or exporting it, and preserve the entire habitat directory for
backup. The raw prior file, portable before-image, candidate and adoption receipt
are in `validation/visible-v9-adoption/`. Never start an old full-envelope-only
reader against this manifest.

A separate explicit fork ran 96 actual ticks, including failed rest, one request
for help, an attributed external repair, verified recovery and two familiar
activity goals. Restored continuation matched complete state, and its history
crossed the 128-record archive boundary. The fork is saved at tick 189 in
`runs/visible-v9-adoption-test`; it is not running and its experiences were not
merged into the main individual's history. The main checkpoint remained unchanged.

Browser inspection after reload confirmed the same paused individual, tick 93,
104 records, prior teaching result and two observed changes. A screenshot was
inspected during verification. The live endpoint independently reports v9. This
proves deployment and preserved visible state, not that this individual's future
life has already demonstrated every newly installed capability. Earlier statements
above about the runtime still using v6 or full-envelope storage are superseded.

## V10 shared-activity adoption

The continuing companion was subsequently upgraded from v9 to v10 with its full
prior history, host state, lineage, skills and teaching preserved exactly. It
remains paused at tick 93 with 105 records, no availability report and no invented
shared activity. The UI now offers **I'm here for a while** and **Quiet time**;
relevant familiar activity can produce **Watch together** / **Not now** invitations.
See [shared-activity evidence and limits](SHARED_ACTIVITY_RESULTS.md). Adoption
before-images and the verified runtime state are in `validation/visible-v10-adoption/`.

## V11 action-feasibility adoption

The visible individual subsequently adopted v11, preserving its full prior history,
host state, lineage, teaching and skills. It remains paused at tick 93 with 106
records. The new executive can use experienced action failures to defer repeated
unavailable proposals into quiet holds; new availability overrides old exclusions.
See ACTION_FEASIBILITY_RESULTS.md and `validation/visible-v11-adoption/`. This
external upgrade did not add test experiences or creature-directed code revisions.

## V12: persistent exploration adopted

The same continuing individual now runs v12, paused at tick 93 with 107 records.
Actual displacement informs movement expectations and persistent exploration
goals. Four paired histories increased spatial coverage, with nonuniform costs.
Legacy missing-motion handling was repaired and all affected-module reruns passed.
Identity, lineage, full prior history, host state, skills and teaching were
preserved. See EXPLORATION_RESULTS.md and validation/visible-v12-adoption/.
The full developmental goal remains active and incomplete.
