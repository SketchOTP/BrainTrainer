> Historical first sprite integration. Superseded for the live world by
> [TOPDOWN_WORLD_RESULTS.md](TOPDOWN_WORLD_RESULTS.md); the original sheets remain unchanged.

# Exact supplied creature representation

The four owner-supplied 8 by 8 sprite sheets are preserved unchanged in
`examples/persistent_individual/assets/creature/`. Their source paths and SHA-256
hashes are in `provenance.json`. All 256 frames remain available. No generative
redrawing or image cleanup was performed. The canvas samples frames directly
from those original atlases with smoothing disabled.

Nine clips cover attentive idle, left/right movement, rest, eating, interaction,
rehearsal, retained code improvement, and assistance requests. Actual observed
movement chooses facing. Eating requires completed action and energy gain;
interaction requires activation. Rehearsal and code-improvement cues require
increased recorded counts. Other decorative sheets are retained for future
capabilities, without asserting those capabilities exist. Movement currently
uses the supplied side-facing poses rather than a newly drawn footfall cycle.

Pause freezes animation. An explicit one-step action or rehearsal can play a
brief corresponding sequence; merely reopening a paused checkpoint does not
replay historical actions. Reduced-motion preference preserves state cues with
a static representative frame. Rendering does not write brain state.

`node tests/sprite_animation.cjs` passed action mapping, pause, bounded rehearsal,
revision cue and atlas-bound checks. The browser displayed the exact transparent
character, real movement facing, and rehearsal selected from an actual recorded
rehearsal on an explicit test branch. Not all clips have live behavioral browser
coverage. The test branch is stopped and was not merged.

The main habitat at http://127.0.0.1:<port> now serves these visuals. Its complete
returned state and raw checkpoint hash were identical before/after restart:
paused tick 93, 107 records, same individual and history. The screenshot and
receipt are under `validation/sprite-adoption-before/installed.png` and
`validation/sprite-adoption-receipt.json`.
