# Lazy retained event history

The habitat can now keep archived raw events on disk while retaining one verified
128-event block and the current tail in memory. Indexed and sliced access returns
copies, so callers cannot silently edit old records. After a successful checkpoint,
the raw cache and tail contain at most 255 event records. A burst of unsaved events
can grow the tail until the next checkpoint, and event sizes vary; this is a record
count bound, not a fixed byte bound for the entire creature.

The history owner maintains an incremental digest of the canonical event sequence.
Append-only records preserve the committed prefix digest. Saves verify file
freshness and reuse unchanged segment references, then publish any newly completed
blocks. Changed file identity, size or timestamps cause digest verification again.
Missing or corrupt required data fails visibly. Partial writes and interrupted
commits retain their existing recovery behavior.

Portable snapshots and explicit exports still materialize complete envelopes.
Normal habitat saves use a history-free checkpoint header and the archive owner,
so they do not materialize the full ledger. Restore validates the archive content
and full-history digest, then streams event provenance checks and cognitive
reconstruction together. The same clock, branch, inherited receipt and model/body
compatibility checks remain. A failed restore never returns the partial object.

## Boundaries still to solve

The event-capacity stop remains a total-history limit. Paging does not silently
reinterpret it as a working-memory allowance. Cognitive projections still retain
cumulative information, and startup still replays history. Portable export can
have a substantial temporary memory cost. Incremental validated cognitive
checkpoints, selective retrieval and a deliberate capacity policy remain needed
for sustained long life. No evidence or personal history is discarded here.

The current visible runtime has not been restarted for this change. Its checkpoint
and experiences remain untouched. The storage and lazy-history code will be used
by a subsequent qualified restart/save; this document does not claim deployment.

## Qualification

All 73 related regression tests passed in 96.200 seconds. Coverage includes
archive corruption and interrupted saves, real process restart, portable export,
learned teaching, maintenance, familiar activities and executable practice revision.
The lazy-reader boundary checks also verify returned-event isolation, incremental
hash equality, unchanged-archive reuse and the unchanged capacity stop.

One paired run loaded an actual 761-event experimental history, saved it, performed
ten actual ticks with saves, restored it and compared complete state and review.
Both implementations ended with the same 771-event state digest.

| Measure | Eager segmented reader | Lazy reader |
|---|---:|---:|
| Retained raw event records | 771 | 131 |
| Estimated retained history Python bytes | 5,846,912 | 985,838 |
| First-save CPU seconds | 0.084 | 0.135 |
| Ten ticks/saves CPU seconds | 1.321 | 0.582 |
| Completed-task elapsed seconds | 2.000 | 1.544 |
| Completed-task CPU seconds | 1.937 | 1.494 |
| Peak process RSS KiB | 60,244 | 51,336 |

The estimated retained history graph decreased 83%; update-phase CPU decreased
56%, while initial conversion cost more. This is one paired measurement, not a
general speed guarantee. Each used a fresh process and directory; OS caches were
uncontrolled. Imports were excluded. The task included full portable equality
checks, which temporarily materialize history. No children ran inside the task.
Object-graph estimates are not whole-brain memory. Peak RSS includes the entire
process. Agent token cost was not measured. Raw results and runner are retained
in `validation/lazy-history-measurement/`.

All 267 pinned original files were verified unchanged. A read-only live check
confirmed the same visible identity and branch, paused and durable at tick 93.
The goal remains incomplete.

Deployment update: these qualified changes were subsequently adopted by the same
visible individual as v9, preserving prior history at tick 93. See
[the adoption record](CONTINUING_HABITAT.md#v9-adoption-into-the-continuing-individual).
The earlier not-deployed statements above describe qualification-time state.
