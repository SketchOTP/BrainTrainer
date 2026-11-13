# Actual live revision retention qualification

Source: continuing live checkpoint at tick 19816, identity
<record-id>. The read-only source was exported before an explicit test fork;
no test state was written into the running habitat.

The fork and its restored copy produced identical events for 24 consecutive ticks
and identical full snapshots afterward. The source object remained unchanged.
All six recorded successful workshop-lantern continuations remain permitted by
the retained executable policy. The original default policy would have stopped
4 of those six decisions prematurely. Evidence references were verified as actual
experience events with actual experience completions.

This comparison is a counterfactual evaluation on recorded inputs, not a new
paired physical/world experiment, and does not establish broad generalization.
The 24-tick continuation establishes exact restoration for this checkpoint and
interval, not universal recovery. The full companion goal remains incomplete.

Reproduce from the candidate root using the project Python environment and
PYTHONPATH=src:tests:examples/persistent_individual with
validation/live-workshop-retention/probe.py. The script reads the then-current
live checkpoint; source.json pins the checkpoint used for this result.

Evidence: result.json, source.json and probe.log in the same validation directory.
