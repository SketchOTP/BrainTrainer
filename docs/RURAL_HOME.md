# Rural Littleroot home

The owner-directed rural map is `assets/world/rural-v3.json`: 26 × 24 native
16-pixel metatiles, up from 20 × 20. Brendan's starter home (both floors) and the
companion workshop remain. The former guest-house site contains six walkable
berry beds (18 soil cells); the former laboratory site contains a 35-cell pond.
Every pond cell is non-traversable. Two outdoor doors, their interior returns,
and the home stairs remain functional. Forest boundaries close every outer edge.

Wider connected paths, flower borders, low hedges and a southern stone garden
use the same General/Petalburg assets as the original town. The workshop now
has its complete original roof. Native Oran and Pecha tree sprites are displayed
at 16 × 32 pixels. These are decorative farm plots: harvesting, watering and
crop growth are not implemented by this visual change. Water uses the native
static reflective-water tiles; no simulated water mechanics are implied.

## Porymap authoring

`tools/pory-project` is a separate, ordinary-file copy of the exact Heart & Soul
source revision used by the existing habitat pack. The donor is not the working
project. `tools/plan_rural_town.py` produces an explicit native-block plan and a
Porymap script. Porymap 6.3.1 applies `setDimensions`, `setBlock`, `commit`, then
reads every block back with `getBlock`. `tools/export_rural_town.py` verifies that
readback against the plan, writes the native map.bin/layout dimensions and
builds the private habitat atlas and JSON. This is actual Porymap map editing
through its scripting API, not a claim that a GUI Save button was used.

Run Porymap only with `QT_QPA_PLATFORM=offscreen` and the project-local
`XDG_DATA_HOME=tools/pory-isolated` (use an absolute path). Its isolated config
opens only this copy. The script is attached in porymap.user.cfg. Retained
`validation/rural-town/pory-readback.json` and logs establish the applied blocks.
Porymap warns on an unsigned Pokémon object-graphics macro in this newer donor;
terrain readback is verified independently. This is not a qualified ROM build.

An initial `porymap --help` invocation unexpectedly opened the recent COA project
because that Porymap executable does not implement that option. It was stopped
without an explicit map edit. COA's Porymap config timestamps changed; absence
of before hashes prevents claiming unchanged config contents. See the retained
incident note. Subsequent authoring used only the isolated copy/settings.

## Continuity and verification

The old packs and atlas remain immutable and restorable. A separate attributed
`make-rural-home` implementation event adopts this map; old visited cells remain
valid historical memories, including the removed rooms. Removed-room occupants
return to the central green. Newly blocked positions move to the nearest valid
cell; pending routes/actions are explicitly cleared. Identity, branch, tick,
neural state, object behavior, and the earlier event prefix are preserved.

`make_rural_home.py` performs offline migration under the store lock, saves a full
before image, checks allowed differences, and verifies exact save/restore before
installation. `test_rural_home` exercises actual steps across farm beds, around
the pond, through both doors and all interior exits, closed boundaries, old/new
restoration, and attributed migration. The initial test run exposed two test
fixture mistakes (arrival visit count and a blocked guest-room fixture position);
failed logs are retained and the corrected four-test suite passes.

Desktop and 412 × 915 browser viewport previews were inspected. This is browser
viewport evidence, not a physical-phone test. Original source manifest checked:
267 files unchanged. Assets remain private owner-authorized reuse, with no
redistribution license inferred. Asset hashes are in rural-v3-provenance.json.

Live adoption completed at moment 6957. Identity and branch unchanged; the prior running intent was restored. The private Tailscale page was observed living and moving after deployment. Full before/candidate snapshots and receipt are retained in `validation/rural-town/live-adoption/`.

## Current active town and companion state (2026-11-13)

The active world is now the 26 × 24 Littleroot pack `worldpacks/rural-v10.json` (SHA-256 `e47e7035b5b6b69028f01240640b5ae3a45f7b9d43bf7e6216850e2499bd219a`). The same two buildings remain active: the starter house and companion workshop. Six berry trees, the 35-cell blocked pond and the full perimeter tree border remain. A v9 preview exposed a detached pond-side trail where water had removed its connecting tiles. V10 moves that walk to land: its 44 path cells form one connected component, pass through both building doors and reach the pond bank without making pond tiles walkable. The v9-to-v10 implementation event is 115391.

The live v10 desktop and stable 412 × 915 viewport captures are `validation/pond-trail-v10-2026-11-13/stable-town-v10.png` and `validation/pond-trail-v10-2026-11-13/stable-town-phone-v10-final.png`. These are local headless-browser captures, not physical-phone acceptance. The migration receipt verifies the same identity and branch, unchanged tick and history prefix, preserved garden state, and the in-progress body route. The receipt and before/candidate snapshots are under `validation/pond-trail-v10-2026-11-13/`; the prior v8 and v9 map packs remain available for replay.

## Lived self-review

The same continuing individual adopted `llm-lived-self-review-v1` at event 112097, tick 111967. Four self-review → embodied-goal → body-outcome cycles followed on the workshop lantern; each five-interaction sequence ended with a visible state change. The repeated identical goal exposed a novelty weakness. At event 112676, `llm-lived-self-review-v2` added a prompt and scheduler guard that requires a new target or appearance prediction after repeated success. The owner-requested post-update `self-review` completed at event 114492 and declined another duplicate trial using the lantern and berry outcomes. At implementation event 114510, bounded LLM-directed executable development was enabled for evidence-backed practice limitations selected by the creature's own activity. Later rest-linked dreams reviewed additional berry and lantern outcomes and again proposed no duplicate trial. A dream can admit a real body trial when it chooses practice and provides a validated plan; the latest dreams at events 116030 and 116287 chose observation/rest review instead. These records do not establish subjective dreaming or that the v2 update caused the berry outcomes. The post-v10 live observation confirms the same running individual, with reflection idle and no active practice limitation at capture; therefore no live LLM-generated executable candidate was appropriate at that point. Deterministic-provider tests cover candidate validation, branch regressions and actual body follow-up; no live OAuth-generated code change has been observed. Receipts are under `validation/lived-self-review-adoption-2026-11-13/`, `validation/lived-self-review-novelty-2026-11-13/` and `validation/pond-trail-v10-2026-11-13/`.
