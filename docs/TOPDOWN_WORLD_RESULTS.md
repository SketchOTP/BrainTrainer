> Live scope and sprites updated: see [ETCH_SPRITE_AND_STARTER_TOWN.md](ETCH_SPRITE_AND_STARTER_TOWN.md). The active habitat is now Littleroot only.

# Top-down digital embodiment and visual world

## Delivered scope

The same live individual now inhabits a persistent two-axis body. Its position,
facing, visited-cell counts, current exploration destination and route survive
checkpoint restoration. Collision-aware four-neighbor routes lead to actual
object contact. Doors, stairs and connected map boundaries change its location.
Crossings appear in recorded experience. Objects remain in their own region.

The initial six-map private reference world contains Oldale Town, Route 101,
Littleroot Town, an Oldale house and two floors of Brendan's house. A bounded
import copies the owner's Pokémon Digital World atlas and verified map chunks;
it does not modify the donor project, its saves or runtime. Exact source paths,
chunk hashes, source revision and reuse restrictions accompany the pack in
`examples/persistent_individual/assets/world/provenance.json`.

The browser follows actual recorded positions, interpolating recent received
movements. Four-direction footfall cycles come from `walk-v2.png`, generated
from the owner's purple armored creature reference. Original standing poses and
rest, eat, interact, assistance, rehearsal and retained-improvement clips remain
sampled from the four unchanged supplied sheets. Rendering never drives the
brain. Zoom and camera drag do not move the creature. Camera following respects
map edges; the phone layout uses a tall world viewport and wrapped controls.

This is an authored map planner and initial curiosity rule. Visited cells are
experience; the collision map is inherited knowledge. It does not establish
learned geometry, open-ended storytelling, operational code understanding, or
completion of the overall companion goal. Original one-axis motor learning is
retained separately and is not trained on misleading north/south x deltas.

## Evidence

- `validation/world-v1/legacy-tests.log`: 11 existing spatial and habitat tests.
- `validation/world-v1/regressions.log`: 19 tests covering six new body cases,
  familiar activities, shared history and habitat self-development.
- `validation/world-v1/world-learning-test.log`: the top-down body still initiates
  practice-code evaluation, rejects a candidate, retains a useful revision,
  restores it and rests when depleted.
- `validation/world-v1/migration-test.log`: real checkpoint migration preserves
  identity/history, restores, continues and is idempotent.
- `node tests/sprite_animation.cjs`: action mapping, bounded rehearsal, pause,
  disconnect, reconnect and original atlas bounds pass.
- `validation/world-v1/live-branch-receipt.json`: an explicitly forked live
  individual ran 280 moments, used both axes, visited 36 cells and retained the
  complete prefix. Restoration produced identical next 24 moments. That run
  stayed in Oldale; doors/stairs/map boundaries were separately tested.
- Browser: directional walking and responsive 412 × 915 layout observed. A
  separate paused test branch displayed a rehearsal clip following an actual
  recorded rehearsal. Not every expression has live browser coverage.
- `live-world.png` and `mobile-preview.png` under the same evidence directory.

Initial failed tests remain in evidence. One exposed routes traversing a door
as though it were an ordinary cell; gateway cells now terminate local routes.
Other failures were fixture assumptions (nested checkpoint fields and expecting
both axes within the first 30 moments rather than allowing exploration to turn).

## Live adoption and recovery

At tick 3215, individual `<record-id>`, branch
`<record-id>`, adopted `topdown-body-v1`. The neural
state, random state, clock, motor model, personal history, learned policies and
object behaviors remain intact. Body/object coordinates and route implementation
changed explicitly. A pending action, if present, is recorded as cancelled for
migration; this instance had none. No test-branch experience was merged.

`validation/world-v1/live-adoption/` retains the raw prior checkpoint, complete
before-image, candidate and receipt. `migrate_world.py` owns the offline migration
under the existing exclusive store lock. The running service resumed its prior
running intent after exact identity/state and asset checks. The temporary
migration drop-in was removed. The preview service was stopped with its test
checkpoint retained. All 267 files in the original source manifest still match.

The existing private HTTPS endpoint remains:
https://<tailnet-host>:46342/

The HTTPS page and new world assets were verified on the host browser; this does
not establish access from the owner's phone. No public Funnel was added.

## Research references and application

[Porymap](https://huderlem.github.io/porymap/) documents tiles, collisions,
connections and events; [Poryscript](https://github.com/huderlem/poryscript)
provides scripting for generation-three projects. Their map/event organization
informed this bounded map import; neither is installed as the creature's runtime.
[Emerald Expansion](https://github.com/rh-hideout/pokeemerald-expansion) and
[Emerald Arena](https://github.com/GBurgardt/pokemon-emerald-arena) were inspected
as relevant ecosystem references. The actual reused assets come from the owner's
existing Pokémon Digital World pack, not an untracked new ROM download.

The donor actor implementation separates directional frames from world position;
this viewer similarly separates observed movement, facing and animation timing.
Assets remain private, with original artists' rights unchanged. Importing the
pack does not grant redistribution permission.
