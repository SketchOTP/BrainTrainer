# Reviewing executable changes against subsequent experience

V29 adds an explicit follow-up for newly installed practice policies. The record
binds the installation event, selected policy digest, request and resumed goal to
its actual starting counters. Branch-test success leaves the record awaiting
experience. Dreams and mere restoration do not supply successful outcomes.
Actual matched interactions update trial/change counts and a terminal goal records
either completion or unresolved experience, with its event provenance.

The review does not attribute success or failure exclusively to code. Its scope
is the resumed goal and its cause remains unestablished. In particular, a changed
environment can invalidate a tested prediction without making the code defective.
No automatic rollback or general claim of improvement is inferred.

The review affects action: if a resumed goal stops with no further observed effect,
the creature does not use its pre-installation effect as justification for another
patch evaluation. It can request help with a grounded message about trying the
revised rule. Later new effects can justify another improvement request; repeated
and timing-sensitive improvement scenarios remain supported. An unrelated goal is
not blocked by this review.

Qualification:
- Initial two focused checks passed (13.014 seconds).
- Eight broader checks ran: seven passed, one older test crashed because it
  unpacked exactly two candidates. A source-version comparison confirmed v28 and
  v29 generate the same three candidates. The test now selects the accepted
  candidate by selected_sha256 and the rejected uniform policy by its declared
  counter, retaining all coverage and behavioral assertions.
- Four final checks passed in 29.510 seconds: real completion, post-install no-
  effect help-seeking, prior-version repeated evaluation, and two useful changes
  with preserved history/prior skill. Five other regression checks passed in the
  earlier broader run. Logs retain the original failure.
- The controlled failure changes the test device to inert between installation
  and the next world step. V28 launches another evaluation; v29 keeps the one
  completed evaluation and requests help. Neither claims to know the failure cause.
- Exact restoration of derived reviews and later ticks passed.

This is an authored self-review mechanism, not self-written review code. It applies
to installations after v29 adoption; older installations are not silently given
new contemporaneous reviews. Existing live code/history remains preserved. Test
branches and simulated environmental changes are never merged into main state.
Full developmental-process improvement and general software self-understanding
remain incomplete. Live adoption details follow below.

## Live adoption

V29 was adopted at tick 21898 with exact prior event-prefix, identity,
branch and host-state preservation and installed-checkpoint readback. Existing
shared-invitation history and code-revision count were unchanged. The one-time
service hook was removed and prior running intent restored. Live tick 21921
is running without error. No new executable revision has yet occurred under this
capability, so real-world follow-up behavior remains controlled-test evidence.
