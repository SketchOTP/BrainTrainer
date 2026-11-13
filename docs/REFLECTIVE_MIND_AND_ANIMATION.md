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
continuing individual or execute returned code. For a development-purpose
reflection, the habitat may pass one returned practice-policy source to the
separate bounded evaluator; the model cannot write files or install code.

Purposes include self-review, analysis, dream and development. A development
request now carries the individual's current lived practice limitation and can
choose code, another embodied trial, or no change. A code proposal is restricted
to the existing small `PracticePolicy` language. The evaluator runs branch
regressions before installation; the same continuing body then exercises the
candidate. A later real effect marks it retained, while a no-effect unresolved
goal restores the previous policy and keeps the failed attempt in history. This
does not yet permit general repository edits or arbitrary code generation.
These labels do not establish four complete integrated capabilities. The
continuing individual has completed four live self-review → body-trial cycles,
then an owner-requested post-update self-review at event 114492 that declined
another redundant trial. Its prior identical body trials and subsequent berry
outcomes were supplied as evidence; the review added no body outcome. Reference
validity is checked; a valid citation does not automatically prove semantic
truth, and one review does not establish improved general learning.

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
5. Expand beyond the current practice-policy program: let the creature diagnose
   implementation limits across its body and memory, propose an appropriate code
   change, and qualify it against acquired abilities and unfamiliar situations.
   Then test the exact candidate in ordinary life and retain, revise, reject or
   roll it back from observed consequences.
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

## Rest-linked reflective dreaming

The continuing individual's host can request an LLM dream from a cited completed
rest action, after at least 256 world ticks since its prior reflection request.
This is a bounded asynchronous thought cycle: the body continues during provider
latency, returned ideas are stored as hypotheses, and the dream event adds no
experience or world action. If the proposed method is practice and includes a
valid plan, the existing scheduler may admit a bounded trial that the actual body
must execute. Rest is not evidence of sleep or subjective dreaming. Non-practice
goal proposals remain hypotheses until their body-side goal methods are built.

The feature is recorded as a developer-authored implementation change for the
same live individual. On 2026-11-13, its OAuth reflection produced a dream event
citing completed rest event 110437, then proposed a one-attempt action-1 trial
on berry-3. The continuing body reached contact and harvested it: event 110474
records the appearance changing from `berry:pecha:state=1` to
`berry:pecha:state=0`. The body later completed a berry-2 trial; a subsequent
berry-4 trial was incomplete. The dream itself added zero outcomes and advanced
zero world ticks. The dream and berry-3 result remained after checkpoint restore
with the same identity and branch. This is one narrow live result, not evidence
of repeatable generalization, subjective dreaming, creature-initiated software
changes, or improved self-modification.

After that restore, a later LLM review used the continuing event history to set
a bounded workshop-lantern practice goal. The body tried action 1 five times;
the fifth completed interaction changed the observed lantern state from 1 to 0,
and the trial recorded `observed-success` (event 110894). The preceding four
completed activations left the appearance unchanged. This shows the actual
review-to-goal-to-body loop and a state-dependent outcome in this environment;
it does not establish that the lantern rule generalizes to other objects. See
`validation/rest-linked-dream-adoption-2026-11-13/followup-practice-after-restore.json`.

The implementation receipt and hash-verified runtime event observation are under
`validation/rest-linked-dream-adoption-2026-11-13/`.

## Post-update review and executable-development decision

After the v2 novelty update, the owner requested a fresh self-review. The same
individual recorded it at event 114492 with purpose `self-review`. It compared
the repeated lantern outcomes with the later berry-1 and berry-3 appearance
changes and declined another identical trial. This is an observed review
decision grounded in cited experience; it does not show that v2 caused those
berry outcomes or establish generalized improvement.

At implementation event 114510, the continuing individual was enabled to ask
for bounded LLM-directed executable development when its own practice review
produces an unresolved, evidence-backed stopping limitation. The proposed
`PracticePolicy` is parsed in a finite language, exercised against isolated
regression branches, then resumed in the real body's unfinished goal. Retention
requires a further observed body effect; after at least one actual post-install
trial, an unresolved goal with no further effect restores the previous policy.
Missing or unavailable body trials alone do not count as failure. The later
rest-linked dreams at events 114978, 115239, 115505 and 115768 cited additional berry
and lantern outcomes and declined duplicate trials. A post-v10 live observation
recorded the same identity and branch running on the new map, with reflection
idle and no eligible practice limitation; no executable proposal was pending.
The timestamped snapshot is
`validation/lived-self-review-novelty-2026-11-13/post-v10-live-observation-115790.json`.
The
deterministic-provider regression covers proposal, branch evaluation, body
follow-up, retention and rollback; a live OAuth code change remains unobserved.
The live observation and owner review receipts are in
`validation/lived-self-review-novelty-2026-11-13/`; current world continuity is
in `validation/pond-trail-v10-2026-11-13/`.
