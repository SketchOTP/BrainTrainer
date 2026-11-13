> Town scope expanded with working interiors: see [LITTLEROOT_INTERIORS.md](LITTLEROOT_INTERIORS.md). The outside boundary remains closed.

# ETCH reference revision and starter-town development habitat

The owner rejected the earlier sprite and supplied `118139.png` as the new
character reference. Three transparent atlases were generated using the built-in
image_gen tool and copied unchanged into
`examples/persistent_individual/assets/creature/etch-v3/`:

- `movement.png`: down, left, right and up; four frames per direction.
- `daily.png`: idle/blink, rest, eating and interaction; four frames each.
- `expressions.png`: thinking/rehearsal, requesting help, pleased/success and
  curious/investigate; four frames each.

48 frames total. The curious/investigate row is available art, not yet mapped to
an asserted cognitive state. Rest, eating, interaction, rehearsal, request and
retained-improvement cues still depend on actual state/evidence. The world now
uses only this new set for the creature; older atlases are retained for recovery.
The reference poster's full list of 36 animation sets is not implemented by these
three sheets. No combat, carrying, drinking or jumping capability is implied.

`manifest.json` records dimensions, hashes, transparency and row assignments.
`prompts.json` retains the exact successful prompt set and tool. The first
movement attempt was rejected by the image service; the simpler peaceful walking
request succeeded. The original reference remains in the owner's attachments.
No generated PNG was resampled or retouched; the renderer samples its 4x4 cells
with image smoothing disabled and a shared standing baseline. Rest has its own
lower body baseline. Browser visual quality remains subject to owner acceptance.

## Starter-town scope

The owner requested only the initial starter town during development. The
continuing individual was moved to **Littleroot Town** at tick 4251 through an
attributed `set-home-town` external intervention. `world.home_region` disables all
map transitions, including doors and route departures. Prior visited locations
remain memories. Archived maps remain available for restoring older checkpoints;
the active creature cannot leave its single town.

The body position and objects were relocated, the current route/exploration goal
was cleared, and any pending action was recorded in the intervention. Identity,
branch, neural state, random state, clock, motor model, object behavior, learned
policies and the exact prior event prefix were checked unchanged. This is an
owner-directed environment change, not a self-improvement claim.

## Verification and recovery

- `validation/etch-v3/town-tests.log`: nine body tests pass, including all town
  gateways in every facing, preserved history, exact 25-moment restored
  continuation, invalid scope-history rejection, and existing practice-code
  self-development with rest.
- `migration-test.log`: an explicit live-state test fork passed migration,
  preserved-state checks, restoration, next action and idempotence.
- `live-adoption/`: full before-image, raw checkpoint, installed candidate and
  receipt. Same individual and branch; prior running intent restored.
- PNG inspection: all three have alpha transparency, 1254x1254 dimensions and
  recorded SHA-256 hashes. Source requested 1024x1024; actual tool output is
  sampled by its dimensions, not an assumed size.
- Renderer JavaScript syntax check passed. New PNG HTTP routes returned 200.
- Deployed HTTPS browser showed ETCH in Littleroot, no console errors, and the
  412x915 layout. Screenshot: `validation/etch-v3/live-phone.png`. This is a
  browser viewport check, not confirmation from the physical phone.

The live URL remains https://<tailnet-host>:46342/ . Refresh to
load the new renderer. The temporary migration service drop-in was removed.
The broader persistent-companion goal is still active and incomplete.
