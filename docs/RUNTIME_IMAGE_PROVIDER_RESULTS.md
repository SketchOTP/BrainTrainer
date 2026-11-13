# Runtime image-generation provider qualification — 2026-11-08

The installed Codex CLI advertises the stable image_generation feature. The
native tool is also described in OpenAI's source:
https://github.com/openai/codex/blob/main/codex-rs/ext/image-generation/imagegen_description.md
Feature advertisement alone was not treated as a working provider.

## Actual OAuth runs

An isolated CLI probe invoked the native image-generation path using saved OAuth,
with shell and multi-agent tools disabled and no ambient API-key override. It
returned a PNG under its own generated_images thread directory. The file decoded
as RGBA at 2048x768. Visual inspection found a soft halo; alpha extrema were 0–254.
It did not meet the requested 128x48 native dimensions and was not installed.
Evidence: `validation/runtime-image-provider/probe-01/`.

A second generation ran through the new reusable `asset_generation` worker with
copied, hashed native berry references and four named visual states. It returned
an actual PNG at 1774x887. The artifact was copied non-destructively into the job,
hashed, and marked candidate-awaiting-qualification. Usage: 33,188 input tokens,
15,104 cached input tokens, 478 output tokens. Evidence: `worker-01/` under the same
validation directory, including request, prompt, provider response and receipt.

The second image's visible halo improved, but raster inspection found 215,151
partially transparent pixels, only 1,766 fully opaque pixels and a width not
divisible by four. It therefore remains unqualified for installation. Its native
pixel grid, frame registration, palette and actual game-size appearance still
need work. No current sprite, map, collision or world interaction was replaced.

## Implemented worker boundary

`asset_generation.prepare` persists the asset owner, requirement, logical cell
size, named states and copied reference hashes. Exclusive job creation prevents
replacement. `run` invokes native image generation through OAuth and retains
terminal receipts. Returned files must belong to that CLI thread's generated-image
directory, fit the byte limit and have a PNG header. Successful generation becomes
a candidate, never an installed asset or a learned ability. Full decoding and
visual checks are explicitly outside that lightweight collection boundary.

`codex_process.execute` now owns the shared child lifetime for reflection and image
workers, including timeout, cancellation, process-group termination/reaping,
output capture and OAuth environment selection. No credential values are logged.
Sixteen asset/reflection/scheduler tests passed in 7.219 seconds, including foreign
or absent artifact rejection, reference preservation, no-overwrite behavior,
provider failure, timeout and cancellation. The main service has not been
restarted for this worker/refactor; generation is not automatically scheduled by
the continuing creature yet.

Provenance limitation: this CLI JSONL stream omitted native image tool-call events.
The retained result is an actual decoded image in the matching returned thread
directory, plus the model's generation response and terminal turn. Do not claim a
complete provider tool transcript beyond what those artifacts show.

Remaining: native-grid/alpha/frame qualification, visual acceptance, durable
creature/environment demand scheduling, scene trials and versioned installation.
The reusable generation worker is functional; the full built-in sprite and
environment agents are not finished.
