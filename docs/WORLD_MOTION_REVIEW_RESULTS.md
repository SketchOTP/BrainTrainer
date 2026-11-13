# V22: world movement failure changes behavior

The V21 rural exploration failure probe imposed zero body strength on an explicit
continuing-history test branch. Thirty-two actual exploration actions produced
one unchanged position, with no movement review or assistance request.

V22 reviews matched executed exploration actions and their observed world
positions. Three consecutive attempts without displacement mark movement as
unresolved. The executive then holds between periodic probes, retains the
unfinished destination, and issues one request for that goal. Body versus
environment cause remains unknown. Actual displacement restores ordinary
exploration; observed arrival completes the review. Arrival during another
activity also closes the old failure. Maintenance keeps priority over waiting.

The review is reconstructed from attributed experience and communication events.
Missing or unmatched observations cannot teach failure. Historical pre-V22
experiences are not retrospectively converted into new knowledge. The eight-tick
probe interval and three-failure threshold are authored starting mechanisms, not
self-authored code or learned timing. This is operational self-review, not a
claim of subjective awareness or general causal diagnosis.

## Qualification

Evidence resides in `validation/world-motion-failure/`. Seven initial focused and
related tests passed in 39.467 seconds; four final movement-review tests passed
in 8.308 seconds after adding closure on arrival during another activity.

Two explicit branches of the same blocked checkpoint each ran 32 failure moments.
V21 attempted movement all 32 times. V22 attempted three initial movements and
three later probes, held 26 times, and issued exactly one grounded request.
The source individual was not modified by the experiments. V22's blocked state
and future behavior matched exactly through an eight-tick restored continuation.
After external repair, both branches reached their retained destinations.
V21 took three ticks; V22 took ten. Those recovery timings are separate examples:
V22 received eight extra pre-repair ticks for the restoration test. They are not
a controlled equal-duration latency comparison. Periodic probing intentionally
trades fewer futile attempts for delayed detection of recovery.

A read-only live upgrade preflight at tick 13879 preserved host, lineage, and all
prior events, and restored exactly. The help request and quiet waiting state were
visually inspected in a separately served, paused test branch. The screenshot
`request-preview.png` records that preview; it does not depict a fault in the
continuing live creature. The preview server was stopped after inspection.

General diagnosis, alternate-route learning, and autonomous body repair remain
unfinished. No test experiences or imposed body faults are merged into live state.

Live V21 → V22 adoption at tick 13971 preserved body, lineage, and full prior history. The service resumed and advanced to tick 13994 with no reported error. The one-time migration hook was removed. Before-images and installation receipt are in `live-adoption/`.
