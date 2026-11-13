# V21: finish world exploration steps before distant familiar play

A read-only live-history audit at tick 13013 found an exploration target created
at tick 7667 still unfinished. In the last 512 experiences, 206 exploration
steps alternated with 237 familiar-play approach steps. The body repeatedly got
to within 0.65 tiles of the target before the recurring familiar activity took
over. The spatial target was walkable and reachable in the inherited map.

Linear exploration already deferred distant familiar play while an exploration
goal was active. Rural exploration lived outside that arbitration boundary, so
it had no equivalent commitment. V21 passes pending world exploration from the
body's own goal/position representation into the executive's existing familiar
activity arbitration. Nearby familiar interactions and bodily maintenance still
have their previous priority; unfamiliar-object practice is not deferred.

The first paired experiment exposed another ownership issue: arrival was only
noticed when the exploration selector ran again. Leaving for play immediately
made the old target appear pending again. The final implementation reviews the
actual matched body observation after each tick, records an arrival review in
that experience, and clears the completed world goal. This closes the goal even
when another activity takes over on the next tick. The review identifies observed
position as its basis; inherited map knowledge remains explicitly inherited.

## Qualification and limits

Evidence is in `validation/world-exploration-review/`. The original failed paired
experiment remains under `initial/`. A stopped run with a missing import is also
retained separately; only the final completed test log is qualification evidence.
The paired run uses explicit branches of the same saved continuing history.
Test experiences are not merged into the live individual.

This repairs goal arbitration and completion, not general reflective planning.
The curiosity rule and route planner remain authored. There is no claim that
the creature diagnosed or authored this code change itself. Review of exploration
under genuinely blocked or changed geometry remains a separate development gap.

## Final results

Seventeen focused and regression tests passed in 72.070 seconds. In 256 moments from the same tick-13095 source, V20 never reached the old target and visited zero new cells. V21 reached it at tick 13098 and visited 39 new cells. Both completed three newly initiated familiar activities, produced 16 practice interactions, and took five rest actions. The V21 branch matched a restored continuation exactly for twelve ticks. A separate read-only live upgrade preflight at tick 13413 preserved host, prior events, lineage, and exact restoration.

Live V20 → V21 adoption at tick 13495 preserved history, body, and lineage. Service resumed without reported error and advanced to tick 13547; the one-time migration hook was removed. A fresh Tailscale browser view showed the creature walking and the complete town rendering. The captured overview is `validation/world-exploration-review/live-overview.png`.
