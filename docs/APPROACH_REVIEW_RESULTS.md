# Progress-aware approach review — v13

The live audit found 11 goals marked needs-movement-investigation after 32
approach actions. The previous rule counted total approach actions without
checking whether the target was getting closer. This confused a long journey
with unsuccessful movement. V13 retains the goal while attributed observations
show progress or contact and marks it for investigation after three consecutive
matched attempts with no observed progress. Missing distance is unknown; the
cause is not assigned to body, obstacle or another agent. V1–v12 retain their
original semantics when restored.

Focused actual-world tests show a target 15 units away is reached and learned
under v13 after more than 32 approach actions; v12 abandons that goal. Zero
strength stops after three attempts, and a new stall after progress also triggers
review. Mid-journey restoration matches complete future outcomes. Unmatched
action results cannot count as approach attempts.

Five focused checks passed in 8.222 seconds. An initial combined run passed 19
existing activity/relationship/exploration checks and failed four new fixtures
because those fixtures recorded adoption without enabling the runtime executive.
Those fixtures were corrected to use the production enable_development method;
the focused final run passed. Seventeen additional curriculum/development/upgrade/
memory checks passed in 33.712 seconds. Initial failures remain in tests.log.

A paired 256-tick continuation from live tick 1232 had two false movement-review
outcomes under v12 and none under v13. Both had two completed new goals, 99
approach actions, 248 movement outcomes and eight activations; reserve outcomes
were identical. Both matched eight restored future ticks. This comparison does
not establish reduced travel, increased play, richer initiative or individuality.
The new rule is authored self-review, not creature-originated software change.

The same continuing individual adopted v13 offline at tick 1422. Exact host,
lineage, prior event prefix, skills, guidance, position and reserve were checked.
One external implementation event was added, and the prior running state resumed.
The existing Tailscale route remains healthy. All 267 original pinned project
files remain unchanged. Evidence: validation/approach-review/ and
validation/visible-v13-adoption/. The full companion goal remains incomplete.
