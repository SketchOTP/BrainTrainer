# Runtime asset agents: integration requirements

The environment and animation generators are tools for the continuing creature's
life. Their outputs do not establish knowledge, skills or successful interaction.
The authoritative world and experience log retain that responsibility.

## Shared asset request

Each persistent request must identify the motivating activity or environment
requirement; its source experience/hypothesis; owner (creature animation or world
object); reference images and hashes; logical cell dimensions, frame count and
anchor; required states/clips; and intended transition meanings. A generating
worker may return candidate images and metadata, not grant itself installation
or invent outcomes. Missing provider access remains unavailable, not a fake asset.

The native Codex image-generation tool is being qualified through the owner-
authorized OAuth CLI. Its installed feature advertisement is insufficient proof.
The development-time conversation image tool is not itself a runtime integration.
No API-key fallback is configured or implied by this qualification.

## Candidate-to-world path

1. Persist the request and source hashes before invoking generation.
2. Retain provider events, failure or completion receipt, candidate image and hash.
3. Verify actual raster format, dimensions, transparency, frame layout and anchor.
4. Inspect the result against native art references at its intended game size.
5. Bind named states to real rules and interactions. Harvest removes available
   fruit and adds inventory; regrowth follows world ticks. Neither animation nor
   generation adds resources or changes collision by itself.
6. Exercise the actual object transitions through the body in a qualified test
   branch, while preserving the distinction from the continuing individual's life.
7. Install a versioned asset/object package with provenance and preserved world
   state. The continuing individual must still try and learn its affordances.

The renderer's environment contract already selects the native garden art from
actual world state. New generated environment packages must implement equally
explicit semantics. Ordinary regrowth runs without an LLM per tick. Novel creature
clips must correspond to actual attention/action/outcome rather than merely to a
model's description of having learned something.

Outstanding: qualifying the provider's returned image, durable production worker,
automatic asset requests, image/animation QA, new object definitions and registration.
The exploratory provider probe is under `validation/runtime-image-provider/`.
