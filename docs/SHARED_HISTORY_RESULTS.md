# Relationship history and invitation timing

Candidate v28 makes repeated declined invitations change future invitation timing
through the one existing companion channel. No partner selection, recognition,
emotion inference or fabricated participation is introduced.

After a decline, the next eligible invitation waits 128 moments per consecutive
reported decline, capped at 512. A completed activity with reported participation
ends the decline sequence. Mere availability, silence, expiry, joining without
completion and dreaming do not count as completed shared activity. The individual
continues its own activity during the invitation pause.

The retained timing review names actual supplied-information events, the resulting
interval, and the uncertainty about why the person declined. This is an authored
bounded adaptation rule using relationship history; it is not an inferred personal
preference, a self-written learning rule, or human identity recognition.

Nine tests passed in 38.621 seconds, covering repeated 128/256/384 timing,
completed-participation reset, exact restored continuation, grounded invitations,
independent activity after decline, absence/stale responses, evidence forgery,
pause/dream semantics, and the existing HTTP/process-restart participation flow.
A separate prior-v27 compatibility check passed in 4.195 seconds and retains
fixed 128-moment intervals with no new timing review. Evidence logs are under validation/shared-history.

The rural branch completed 1024 moments with explicitly simulated availability
reports. It initiated one invitation at tick 21746 and set the initial 128-moment
pause after a simulated decline. This exercises ordinary rural integration, not
multiple real-owner declines. Repeated adaptation and successful-participation reset
are established by the separate controlled tests. No simulated reports are merged
into main history. Live adoption and its result are recorded below.

## Live adoption

Adopted at tick 21457. The migration preserved identity, branch, host state
and the entire prior event prefix and verified installed checkpoint readback.
Live shared-invitation history and retained code-revision count remained unchanged;
no test participation was imported. The one-time service hook was removed.
Live v28 resumed at tick 21478 without error with running intent restored.
Actual future owner interaction is still needed for sustained relationship
assessment; controlled tests do not establish that experience.
