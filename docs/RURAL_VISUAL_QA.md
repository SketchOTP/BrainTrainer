# Tree and roof visual repair

The v3 visual review was insufficient: 0x016 was used as a complete hedge despite
being a tree bottom, and the border used forest-overlap lower tiles 0x1DC/1DD.
Comparison against original Littleroot and the native General tiles established
the complete 2×2 tree stamp (1D4, 1D5 / 1E4, 1E5) and small tree pair (00E / 016).
The Porymap-authored v4 adds all ten missing small-tree tops and corrects every
border tree. Both 5×5 house footprints, including every roof tile, match the
original Littleroot source house. The earlier clipped v2 workshop roof was
already corrected in v3 and remains complete in v4.

Evidence: validation/rural-visual-fix/source-littleroot.png, Pory readback,
rural-preview.png, tests.log, current-pack-movement.log, and live screenshots.
The preview was inspected at full-map and closer game scale, covering both roofs,
the farm, pond, and all four forest edges. Native-assembly checks compare both
houses against the donor footprint and verify every tree pairing. Current-pack
movement checks cover both doors/returns and farm/pond collision.

v3 remains immutable for history and recovery. An attributed repair-rural-art
map adoption retains identity and history. Only ten previously empty cells now
contain the missing tree tops and block movement. Relocation, if needed, uses
the existing explicit map migration. No learned brain state is replaced.

Canonical authoring tools now generate v4; the v3 recipes are archived with its
validation evidence. Porymap ran only against the isolated project copy/settings.
The same source-native sprite art and palettes are reused, with no generated
replacement artwork. Visual observations do not establish physical-phone testing.

Final live QA additionally found that Overview clipped side trees on a 412-pixel phone viewport because it enforced a minimum 1x zoom. Overview now fits narrow viewports and refits on region changes. Terrain is baked once at native resolution before drawing as one surface, preventing fractional-scale tile seams. Intermediate seam evidence is retained; live-phone-final.png shows the corrected live rendering. Desktop roofs and all edges were checked before this final mobile check. The live individual resumed after an exact-preservation migration at moment 7356; its identity and branch are unchanged.

## Live visual recheck — 2026-11-08

Reopened the private Tailscale habitat and inspected the rendered town at desktop and 412 × 915 browser viewport sizes. Both roofs, the small-tree tops, all four forest borders, pond perimeter and six berry beds are complete in the observed rendering. Overview fits the full town in the narrow viewport. The creature was observed walking; the live state retained identity <record-id>, rural-v4 pack 3319cd07682c2c985b74604e6c9df9731fb63e48c8ead12614a6bf618cef2a38, running=true and error=null. No additional terrain repair was needed in this recheck. Screenshots: validation/rural-visual-fix/live-recheck-desktop.png and live-recheck-phone.png. This remains browser viewport QA, not a physical-phone acceptance test. Prior movement and native tile assembly test receipts were reviewed, not rerun.

## Fresh live QA and camera controls

Rechecked the live Tailscale page after reloading the client. Inspected the settled
Overview at desktop and 412 x 915 viewport sizes: both complete native roofs,
all perimeter trees, small-tree tops, pond perimeter and berry plots are visible
without clipped tile assemblies. Evidence: `latest-desktop.png` and
`latest-phone.png` in `validation/rural-visual-fix/`. This is browser viewport
verification, not physical-phone acceptance.

During inspection, background state processing disabled local camera buttons,
preventing Overview clicks. The HTML now excludes world HUD buttons from the
processing/disconnection disable selector while continuing to disable commands
that change creature state. Verified Overview works and stays enabled while
the live page displays Connected / processing. No service restart or individual
migration was required. Reload existing clients to receive this fix.

Executed `python -m unittest test_rural_visual_fix -v` with project PYTHONPATH:
10 checks passed in 14.832 seconds (`latest-tests.log`), covering native donor
roof/tree assembly, farm/pond collision, door returns, and restoration.
