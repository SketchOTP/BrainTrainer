# Environment-agent foundation

The owner requires an environment agent capable of adding and updating native-style
interactable assets. It must coordinate with the reflective creature and extensible
animation generator. This document distinguishes the implemented contract from the
agent still to be built.

## Existing world behavior verified

Garden harvesting is already consequential: contact and ripe state are required;
a successful interaction removes ripe berries, adds one berry to the matching
basket and starts an 80-world-tick regrowth clock. Pauses do not grow berries.
The existing renderer uses native frame 3 for recovering plots and frame 5 for
fruiting plots. No new image or map edit was needed for that example.

## New source implementation

`garden.visual_state` projects validated state into native asset URL, frame,
frame dimensions, anchor, harvest availability and remaining world ticks.
`garden.environment_contract` describes plot identity/position, interaction
requirements and effects, failures, regrowth and walkability. Habitat state now
projects these descriptions as `environment_objects` in source; the running v32
service has not been restarted to expose this additional field yet. The live
renderer is unchanged and still uses its existing berry mapping.

The contract is display/authoring information, not hidden knowledge automatically
supplied to the creature. The brain must continue learning from perception and
outcomes. An unknown object has no qualified visual state by default.

Two developer qualification tests passed in 3.878 seconds. An autonomous harvest
in the fixture produced matching depleted art state and inventory; explicit world
clock advancement reached regrowth; restoring and reading projections did not
advance time. Invalid states/clocks were rejected. These are implementation checks,
not experiences imported into the continuing individual.

## Agent still required

The environment agent should consume unmet interaction/visual requirements and
current world contracts, commission native-style assets and object definitions,
then qualify their transitions and appearance before registering them. Preserve
source asset provenance, door/collision connectivity, spacing and individual/world
history during updates. Include a visual preview and actual interaction trial for
each new object. Neither object capabilities nor harvested resources may be
invented by an image generator or a retrospective success description.

Remaining: generation provider, durable asset jobs, extensible object registry,
creature/environment coordination, visual QA and qualified live installation.
The contract is foundation work; it is not a finished environment agent.

## Renderer connection (2026-11-08)

The renderer now consumes `environment_objects` directly, including the asset,
frame, dimensions, anchor and world position. It no longer separately derives berry
frames from raw objects or assumes an absent plot is ripe. Native artwork is
unchanged. Six garden/contract tests passed (12.454 seconds); a paused explicit
test branch after an actual autonomous harvest was inspected in the browser.
The screenshot is `validation/environment-renderer/depleted-preview.png`.

The environment agent's future authoring role is distinct from world simulation:
create a coherent object package with interactions, resource effects, collision,
state transitions and matching native art; qualify that package; install it with
provenance. Installed rules handle harvesting and regrowth without an LLM deciding
each tick. Creature requests can motivate a new object, but installing an object
must never count as the creature having learned to use it. The creature must try
it through its body, observe success or failure, and retain those experiences.

Installed by habitat-service restart at live tick 25761, still executive v32 with
reflection disabled. Full restored checkpoint equality, identity, branch and tick
were checked before resuming. The initial nine-second readiness probe expired;
the service then became ready and passed those checks without another restart.
The Tailscale live page was visually inspected after resuming: six plots, complete
buildings and forest borders, and a walking creature were visible. Evidence:
`validation/environment-renderer/receipt.json` and `live-garden.png`. No test-branch
experience was imported.

## Environment authoring package (2026-11-08)

`environment_agent.prepare_environment` now connects an explicit behavior proposal
with the existing OAuth image-generation worker. A package names its visual
states, contact/action requirements, failure behavior, resource effects, collision
behavior and world-tick transitions. Invalid or incomplete transitions are rejected
before an asset job is created. The job preserves the reference image, package
hash and artwork request identity together; its output remains uninstalled.

The proposed package must still be implemented by the world simulation, visually
inspected at native town scale, and tried through actual interactions. This API
does not yet autonomously choose new objects, install executable behaviors, or
qualify generated art. Existing berry art should be reused: it already represents
the required depleted and fruiting states. No new imagery or live-world change was
needed for this addition.
