# Retained memory budget recovery

A full retained-event allocation stops before another action, preserving history.
The host now supports an explicit attributed increase through
`ContinuingCompanion.extend_memory_budget(capacity, actor=...)`. It appends an
external resource-allocation record, keeps host state and lineage unchanged, and
does not count this as learning or executable self-improvement. Decreases,
non-integers and missing attribution are rejected without changing state.

Restore checks the recorded allocation chain, event bounds and final header.
Older histories without allocation events keep their existing schema semantics.
No schema version or default capacity changed. A larger allocation reserves no
RAM immediately, but additional history will still increase replay/projection
costs; this is recovery infrastructure, not unlimited lifetime memory.

Offline utility, from the candidate root:

```bash
PYTHONPATH=src .venv/bin/python examples/persistent_individual/extend_memory_budget.py --home PATH --capacity COUNT --evidence NEW_DIRECTORY --actor OWNER
```

Use the project interpreter at
`.venv/bin/python` (the candidate
root does not contain its own virtual environment). The store must not be owned
by a running habitat. The utility validates a candidate, saves portable before
and candidate images, applies it through the store owner and checks exact readback.
Existing evidence directories are not overwritten. The continuing live companion
was not stopped, migrated or enlarged during this qualification.

Tests cover full-memory recovery, unchanged host/history/lineage, matching future
continuation, invalid requests, malformed allocation chains, store exclusivity,
and offline persistence. Existing continuity and archive regressions ran alongside
them; actual output is retained in validation/memory-budget/tests.log.

The live read-only audit at tick 850 found 864/10,000 records, 783 movement
outcomes, 48 activations, zero rehearsals and zero development results. Load time
was 0.222 seconds and peak RSS 31,652 KiB for that standalone audit process;
this is a single observation, not a scalability benchmark. There is no immediate
need to increase the live budget. Repetitive travel between familiar practice
and exploration remains a more immediate behavioral limitation. See live-audit.json.

## Live allocation extension

The earlier tick-850 audit above is historical. At tick 8494 the continuing individual approached its original 10,000-record allocation. Four MemoryBudgetTests passed before extending the live allocation to 100,000 records. The offline store-owned migration preserved exact prior history and host state, retained full before/candidate images, and appended an attributed external allocation event. Identity remained <record-id>. The one-time service hook was removed after successful readback, prior running intent was restored, and advancing ticks with no error were observed. Evidence: validation/live-memory-extension/.

This is external continuity maintenance, not learned improvement or unlimited memory. Replay and projection performance at the larger allocation have not been qualified.
