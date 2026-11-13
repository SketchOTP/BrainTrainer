# Segmented habitat history

The habitat storage owner now separates immutable history from frequently changing
body/brain state. Completed groups of 128 events are stored in `history/` under
the SHA-256 of their exact serialized bytes. `current.json` and `previous.json`
contain the remaining tail, complete current body/brain state and ordered segment
references. Each manifest records the full history count and digest. Restoration
verifies each referenced segment, its ordering, the full history digest and the
ordinary companion continuity/provenance invariants.

Archive files are published only after a complete temporary write and fsync. The
archive directory is synced before the current checkpoint is replaced. Failed
or interrupted work can leave unreferenced recovery files; normal saves never
prune them or old segments. Missing or damaged referenced history fails visibly.
Retries after a partial segment write and after an interrupted commit were tested.
Saving a different branch, identity or rewritten prior history over the current
individual is rejected.

## Format ownership and portable export

`HabitatStore.read_checkpoint(path)` owns both legacy complete checkpoints and
the new segmented format, including previous checkpoints. Habitat startup,
migration and persistence tests use that owner rather than interpreting storage
files independently. Legacy files are readable and are migrated on the next save;
their original bytes remain in the previous checkpoint at that write.

A segmented checkpoint requires its sibling `history/` directory. Copy the whole
habitat directory for operational backup, or export a portable complete envelope:

```sh
PYTHONPATH=src .venv/bin/python \
  examples/persistent_individual/habitat_store.py \
  --checkpoint runs/visible-companion/current.json \
  --output /path/to/a-new-portable-checkpoint.json
```

Export is read-only and can read a running habitat's atomic checkpoint. The output
must be a new path. It remains compatible with `ContinuingCompanion.load`, its CLI,
and existing portable tooling. Do not pass a segmented manifest directly to that
portable-envelope reader. Before-images from implementation upgrades include a
portable `before.json` as well as the original raw storage file.

## Evidence and costs

Nine archive/migration/HTTP integration tests passed, followed by all six archive
boundary tests after adding partial-write retry coverage. This covers ten distinct
checks across the two runs, not a claimed ten-test single run. Checks include
legacy conversion, segment reuse, portable CLI export, matching continued actions,
missing/tampered/reordered segments, invalid layout/capacity, rewrite refusal,
partial writes, interrupted commits, ownership and real process restart.

A paired completed task used an actual retained 248-event experimental history:
load, first write, ten real ticks with saves, restore and compare. Final portable
state digests matched exactly. The first write and subsequent update phase were
measured separately in fresh subprocesses/directories; OS caches were uncontrolled.

| Measure | Previous full-file store | Segmented store |
|---|---:|---:|
| First-write serialized bytes | 850,199 | 850,477 |
| Ten updates serialized bytes | 8,613,529 | 5,080,560 |
| Completed-task elapsed seconds | 1.330 | 1.142 |
| Completed-task CPU seconds | 0.938 | 1.096 |
| Peak process RSS KiB | 42,388 | 42,280 |

Bytes count actual newly serialized current files plus newly published segments;
hard-linked recovery copies do not duplicate writes. Imports are excluded from
timing; no child processes ran inside each measured task. Peak RSS is the whole
process high-water mark. Agent token cost was not measured. The measured update
write reduction is 41%, with about 17% more completed-task CPU. This single paired
run does not establish general latency or CPU improvement. Receipts and the runner
are in `validation/archive-measurement/`.

## Remaining limits and deployment

At this initial segmentation milestone, this was not bounded online memory. The creature
held and reconstructed the full event ledger and projections in memory,
and its event-capacity stop remains. Save currently serializes and verifies history,
so CPU cost still grows with lifetime. Incremental validated projections, online
archival/access and capacity management remain necessary for sustained long life.
No history is discarded to conceal that limit.

The already-running visible v6 habitat remains paused at moment 93, on its existing
storage implementation and full-envelope file. It was not restarted or converted
in this turn. A subsequent restart uses the new storage owner; the next save then
migrates the file format while preserving the same full personal history.

Subsequent [lazy-history qualification](LAZY_HISTORY.md) removes full raw-ledger
retention during normal checkpointed activity and adds incremental save hashing.
Cumulative cognitive projections, startup replay and total event capacity remain
limitations. The measurements above describe the earlier segmentation change.

Deployment update: these qualified changes were subsequently adopted by the same
visible individual as v9, preserving prior history at tick 93. See
[the adoption record](CONTINUING_HABITAT.md#v9-adoption-into-the-continuing-individual).
The earlier not-deployed statements above describe qualification-time state.
