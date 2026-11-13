# Reflective mind, lived learning and expressive growth

The owner-authorized direction combines a persistent embodied individual with
an OAuth-backed LLM reflective component and an extensible sprite generator.
This replaces the proposed fixed-template expansion as the main direction for
candidate generation. The old executable policy remains available for replay.

## Implemented prototype

examples/persistent_individual/llm_reflection.py invokes the installed Codex CLI
using saved ChatGPT authentication. No credentials are read, copied into the
project or printed. The worker receives an attributed bounded memory packet,
returns structured hypotheses and a goal proposal, and retains request/output
hashes, usage and failures. Shell and multi-agent tools are disabled; the CLI
uses read-only mode and no user-config MCP servers. It does not modify the
continuing individual or execute returned code.

Purposes include self-review, analysis, dream and development. These labels do
not yet establish four integrated capabilities. The first successful actual
OAuth run used an explicit qualification branch. Live-history reflection is a
separate read-only observation, not an adopted thought cycle. Reference validity
is checked; a valid citation does not automatically prove semantic truth.

A real live-history response cited an older event referenced by a goal summary
but absent from its evidence packet. It was rejected and retained. An initial repair included up to 96 referenced events plus the latest 32.
That passed citation checks but consumed 133,840 input tokens. The compact
revision supplies the latest 8 events plus up to 24 referenced events, observed
interaction targets, one current observation and compact recent goals, with
explicit citable IDs and coverage. This repairs the producing context, not the validator.

## Remaining integration

1. Trigger reflection from meaningful novelty, unresolved goals or review needs
   without freezing movement or calling an LLM every animation frame.
2. Record reflection as attributed hypotheses, including its source-state version
   and coverage. Revalidate changed circumstances before acting on a proposal.
3. Let the creature select a concrete trial: target, action, expected observation,
   failure observation and a bounded stopping condition. Execute through the
   actual body, then review actual outcomes and retain learning.
4. Dreams may propose or rehearse possibilities, but add no lived success counts.
5. Commission code when the creature's diagnosis justifies it. Record exact source,
   test executable candidates separately for regressions/crashes, then assess
   utility through ordinary life. A coder's assertion of success is not acceptance.
6. Persist unresolved thoughts, selected goals, evidence and results across restart.

## Built-in animation generation

Generation should be a durable job from an unmet visual activity description,
not a hardcoded milestone that swaps art after an arbitrary score. Inputs include
reference sprite assets, actual action/capability, facing, pose transitions, scale,
palette, frame grid, anchor and intended timing. Maintain distinct descriptions
for an attempt, failure, successful use and a learned habit.

The generated sheet must be checked for framing, transparency, consistent design,
foot placement, looping/directional motion and world fit before activating a clip.
The renderer uses an activity-to-clip registry with a clearly provisional fallback
while a new clip is pending. Generation does not change body collision, available
actions or learning records. Actual state determines playback.

No runtime image-generation provider has yet been qualified. Codex OAuth success
for text/code is not evidence of image-generation access. The existing image tool
can author assets during development, but that alone is not a built-in habitat
sprite generator. Provider integration, durable jobs, validation, visual QA and
runtime registration remain required.

## Verified environment

Installed CLI: 0.167.0-alpha.3.2. `codex login status`: logged in using ChatGPT.
Official noninteractive guidance confirms saved authentication, structured output,
JSONL events and read-only execution:
https://learn.chatgpt.com/docs/non-interactive-mode

Evidence: validation/llm-reflection/. The continuing habitat was not restarted or
migrated by this prototype. No LLM proposal has yet become its goal or memory.

## Qualification results

Four boundary tests passed after the compact packet change (2.310s), including
invalid citation/request rejection, preparation preservation, process failure
receipts and owned timeout termination. The tightened 32-record budget check
was also run separately.

Live review 01 was rejected for an unavailable citation. Live review 02 passed
with 133,840 input tokens. Compact live review 03 passed with 33,369 input tokens
and a 44,654-byte persisted request containing 27 evidence records. These were
different live snapshots, not a controlled latency benchmark; observed provider
turn times were about 21 and 20 seconds respectively. Do not claim a speedup.
The runtime service remained on v32, with no reflective proposal applied.

Outstanding: goal admission and actual embodied trial execution, outcome review,
automatic reflection/dream scheduling, code commissioning/adoption, and runtime
sprite-generation provider/jobs/QA. OAuth reflection alone is not these completed
features.

## Later integration status

The earlier prototype limitations above describe that historical stage. Live v33
now schedules OAuth reflection and admits bounded body trials; see
`RURAL_REFLECTION_RESULTS.md`. The OAuth native image path has now produced actual
candidate PNGs through a reusable worker, but they are not visually qualified or
installed; see `RUNTIME_IMAGE_PROVIDER_RESULTS.md`. General self-modification,
full dreaming and autonomous asset authoring remain incomplete.
