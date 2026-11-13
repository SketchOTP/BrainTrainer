# Responding to unresolved investigations — v31

The live v30 individual can request investigation after supplied practice advice
fails. It has no useful response path yet. Candidate v31 adds attributed replies
at the continuing-companion API and habitat command boundary:

- `not-responsive`: set the unresolved goal aside on a report. This is not an
  observed fact about the object and does not modify its implementation.
- `changed`: reopen that goal for a bounded recheck. The allowance uses the
  previously observed gap plus one, bounded to three through eight attempts.
  This rule is authored; it is not a demonstrated learned investigation policy.

Reports are supplied-information events, carry a source, and preserve the goal's
actual trial/change counters. Rechecks record actual subsequent experience and
stop with an observed effect or no effect within the allowance. Neither result
establishes the cause of the object's behavior. A failed recheck can later be
revisited on another report; a pending recheck rejects duplicate extensions.
The earlier failed advice remains failed, rather than gaining retrospective
credit from a later repair. All earlier model versions retain their capability
sets; v30 rejects the new command.

Qualification is in tests/test_investigation_response.py. Separate explicit test
branches compare a reported change alone against an actual switch repair. Tests
cover set-aside behavior, bounded recheck, actual outcome attribution, exact
restore/continuation, invalid-reply atomicity, version gating and habitat command
persistence. No test reports or repairs were sent to the continuing individual.

Status: adopted after backend checks and browser UI qualification. Reply controls
and a revisitable activity history are available in the habitat. No claim of complete
self-diagnosis or general self-directed improvement is established here.

Receipts: validation/investigation-response/. Initial tests.log records an
indentation error introduced while editing and corrected before testing.
tests-corrected.log records nine passing new/assisted-learning checks. The
integration-tests.log records the additional habitat persistence check and
implementation-followup regressions.


## UI and live adoption

An explicit fork of the earlier assistance preview exercised the actual HTTP
reply controls: set-aside removed the outstanding request, kept moment 28,
recorded supplied information and exposed a recheck button. Clicking recheck
created an awaiting-experience report with three allowed attempts. The 412 x 915
phone viewport was visually inspected; preview-phone.png is test-branch evidence.
The preview service was stopped after QA.

Live adoption completed at moment 23191. The upgrade receipt verifies the
original event prefix, identity, lineage, neural/body state and installed readback.
The prior running intent was restored and the one-time hook removed. The live
Tailscale page was reloaded and visibly showed the existing investigation request
with both new reply controls while the creature continued walking. No reply was
sent to the live individual; live-resumed-state.json confirms its investigation
reports remain empty. Physical-phone interaction is not yet observed.
