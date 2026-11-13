# V16: route-aware review and rural preference adaptation

The new rural preference probe first failed on V15. After familiar play became
inert, the creature did sometimes select another activity, but abandoned its
journey before demonstrating that alternative. Actual event records showed the
body advancing east around a house while straight-line target distance grew.
Three such observations were incorrectly classified as a stalled approach.
The original failure and full checkpoint remain under validation/world-preference/
with the v15-failure prefix.

V16 records remaining distance along the actual inherited collision-map route
before and after movement. The curriculum uses this evidence only for the
matching executing action and target. It labels the basis as inherited map
support; this is not learned geometry or an assertion that moving directly away
from an object always helps. Stationary movement remains a stall, and an
unmatched route is not credited as route progress. Earlier executive versions
keep their prior review semantics.

Two additional movement defects were exposed by the eastern-town regression:

- The individual wrapper applied the old linear-room x <= 20 clamp after the
  2D route owner had already moved the body. That clamp now applies only to the
  linear body; the world's collision map owns the 2D bounds.
- Floating-point arrival could leave a waypoint at the body's exact position.
  The next step calculated zero distance and never removed it. Waypoint
  completion now uses actual position within 1e-9 cells, and already reached
  waypoints are consumed before movement. The body snaps only this numerical
  residue to its grid waypoint.

These body corrections affect future movement under all executive versions.
Recorded history is unchanged. Route-feedback consumption is explicitly V16.
The original source tree and map assets were not changed.

The probe uses explicit test branches from the same initial individual. Different
experienced object response histories must produce different voluntary returns.
After changing the preferred object to inert, it requires a recorded failed
return, selection of the alternative, and actual successful interaction. No
commands select the creature's activity. The offered objects and their response
changes are externally arranged. This establishes a bounded learned activity
preference and adaptation, not the complete personality or relationship goal.

Initial focused-test failures included two fixture timing assumptions; the
fixture now includes the initial discovery step. A mistakenly overlapping log
write was preserved separately and is not used as final validation evidence.
Final checks use a fresh output file after both earlier processes terminated.

## Final executed evidence and adoption

Eighteen focused and related tests passed in 63.337 seconds, and ten rural map/body tests passed in 14.752 seconds. Final logs are validation/route-review/tests-final.log and rural-tests.log. Both externally arranged preference histories passed on the final movement code, including actual alternative interaction and sixteen-tick exact restored continuations. Full test checkpoints and results are in validation/world-preference/.

The continuing live individual adopted V16 at tick 9723. Exact host, lineage and prior event-prefix preservation passed, with portable before/candidate images retained. The temporary startup hook was removed, the previous running intent restored, and advancing ticks with no error verified. The private Tailscale browser reconnected and visibly showed the creature walking in the complete rural town. This was desktop browser observation, not a new physical-phone test.

The live executable revision count remains zero. These changes are externally authored improvements to embodied self-review and movement; the preference probes are separate test histories. The full end goal remains incomplete.
