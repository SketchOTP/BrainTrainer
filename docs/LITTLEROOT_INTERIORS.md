# Complete enclosed Littleroot habitat

Historical v2 layout. The current owner-requested redesign is documented in [RURAL_HOME.md](RURAL_HOME.md).

The live habitat now uses the complete original Littleroot town layout and all
of its original building interiors from the owner's Pokémon world source pack.
The original town has **three buildings**, not four: Brendan's house, May's house
and Birch's lab. Both houses include their upstairs rooms and stair transitions.
To fulfill the requested four-building habitat, a fourth companion workshop was
added in the southeast using matching house exterior tiles and a separate copy
of the lab interior. This addition is explicitly authored, not claimed original.

Four outdoor doors now connect to six interior maps (two two-floor houses, lab,
workshop). All doorways and stairs have return transitions. The north route is
blocked with existing tree tiles, and every map in the enclosure has no external
connections. Current scope permits the town and its interiors, not Oldale or the
outside routes. `Overview` fits the current map in the viewer; `Follow` returns
the camera to the actual creature. Camera controls do not move the creature.

## Ownership and persistence

`tools/build_littleroot_habitat.py` verifies donor chunk hashes and imports the
whole town and its original interiors. Source metadata and each authored map
change are retained in `assets/world/littleroot-v2-provenance.json`. No donor
source, runtime or saves were changed. These are private reused assets; no
redistribution rights are implied. The existing atlas is unchanged.

The original `maps.json` and its hash remain available. `world_body.pack` selects
the correct immutable map version from persistent body state, allowing old
checkpoints to restore with their original geometry. Expansion changes are
attributed in history; restore rejects mismatched map versions. Past visited
locations remain memories even if a newly placed building or barrier now blocks
the location. Current body/object positions must remain traversable. If expansion
covers a current position, migration relocates it to the nearest traversable cell
and retains the complete before-image.

`open_home_interiors.py` migrated the live individual at tick 5131 with exact
preservation checks for identity, branch, clock, neural state, RNG, learned
policies, object behavior and the full prior event prefix. Route and exploration
destination are cleared to allow the new geometry; any pending action is included
in the explicit change receipt. Previous running intent was restored. The
migration's temporary service drop-in was removed. Test branches are not merged.

## Executed verification

Evidence is under `validation/littleroot-interiors/`:

- `legacy-tests.log`: nine existing body/migration/learning regressions passed.
- `interior-tests-final.log`: four new cases passed: real movement through every
  door and stair in both directions; safe arrival cells; closed external routes;
  exact restored continuation inside every room; preserved history; attributed
  expansion; historical map restoration.
- `reachability-test.log`: every town entrance is reachable from the town's
  center, and every room entrance/stair is reachable from incoming arrival cells.
- `preview-adoption/`: an explicit live-state test fork passed the same migration
  and exact preservation checks before live adoption.
- `live-adoption/`: raw original checkpoint, full before-image, candidate and
  installed receipt.
- `workshop-preview.png`: browser rendering of an explicitly placed test branch
  inside the workshop. Placement is attributed as a visual fixture; this image
  is not autonomous navigation evidence.
- `live-town.png`: actual running individual, full-town Overview, four buildings.
  No browser console errors observed. New map and art served over existing private
  Tailscale HTTPS. Physical phone access is not established by this host check.

The workshop currently provides traversable interior space and supports ordinary
nearby offerings. Its decorative equipment does not yet implement independent
repair, crafting or software-editing affordances. NPC dialogue and original game
story scripting are not ported or represented as creature cognition.
