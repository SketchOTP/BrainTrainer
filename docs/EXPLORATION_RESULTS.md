# Persistent spatial exploration — v12

The continuing companion can learn movement direction from actual displacement,
set an exploration destination beyond visited space, retain that goal across
restart, and revise it after contradictory movement or three failed attempts.
Unknown causes remain unknown. Missing motion in older records supplies no
geometry. This is an authored curiosity mechanism with learned expectations,
not general planning or a demonstrated personality.

## Evidence

Four paired 320-tick empty-world histories (seeds 161–164) compared v11 and v12.
Each v12 history covered 39.9 position units, completed 37 extensions, and had
nine no-motion outcomes. Control coverage was 23.8, 19.95, 19.95 and 26.6;
control no-motion counts were 15, 47, 41 and zero. Coverage improved in all
four cases; failure count and resource cost did not improve uniformly.
All arms restored at tick 80 and matched subsequent continuation. A separate
real-process restart matched complete state, and 1,280 v12 panel decisions
matched replay through the final exploration owner. Earlier v11 continuation
remained identical. See `validation/exploration/results.json` and `continuity.json`.

The initial broad suite ran 92 tests with ten errors caused by one legacy
compatibility defect: motion observations were assumed present. A class setup
failure also prevented its tests from running. The producing projection now
preserves missing geometry as unknown. Both affected-module reruns passed:
20 tests in 36.352 seconds and 20 in 17.582 seconds, including the previously
skipped class and an explicit missing-motion regression. The earlier corrected
activity/exploration run passed 21 tests in 75.737 seconds. These sets overlap;
they are not a claim that a new full suite passed. Logs retain the initial
failures and final affected-module results.

Related activity fixes preserve nearby familiar opportunities, let an ongoing
exploration goal finish before distant familiar repetition, and only announce
an invitation when that shared goal is actually pursued. Completion tests wait
for actual effects after travel; they do not count arrival or invitations as
successful activity. Feasibility-specific integration remains pinned to v11,
while v12 movement behavior has its own tests.

A separate explicit test branch displayed its actual exploration destination
and movement in the habitat. Its experiences were not merged into the companion.
The main habitat was then upgraded offline and reopened at localhost:46341:
identity <record-id>, unchanged branch, paused tick 93,
107 records. Exact prior event prefix, host state, lineage, skills and teaching
were verified. One external implementation-adoption record was added. This
adoption was developer-directed, not a creature-originated code revision.
All 267 pinned original project files remain unchanged.

## Remaining limits

Exploration is one-dimensional and uses finite authored actions and goal rules.
It does not infer obstacle versus body failure, discover hidden objects, or plan
optimal routes. Blocked-frontier retries can entail substantial travel. Identical
empty-world policies are not individuality evidence. Long-life projection cost
and the 10,000-event capacity remain unresolved. General software improvement,
rich companionship and the full end goal remain incomplete. Partner selection
is not part of this development.
