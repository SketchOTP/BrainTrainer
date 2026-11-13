# Food-preference benchmark qualification

This development investigation qualifies the next experiment without changing the recovered `DefaultBrain` or overwriting v1 evidence. [Baseline v1](baselines/food-preference-v1-results.md) remains the prior measured result. No memory, delayed-credit layer, planning system or substitute action policy is used.

## Tasks and interaction trace

`QualificationExperiment` uses the existing structured contract and the same brain for both body adapters. `single_contact` presents one food at distance 0.5, and `single_distance` presents one at 1.2. `preference` presents both foods at equal distance 0.5; `embodied` presents both at 1.2. Both configurations use mirrored branches for each seed. The brain's attention supplies the target and its decision supplies the action. The host does not recommend a food or force an action in the measured trials.

The [single-food capture](../runs/food-qualification/single-food-traces.json) records observations, actual brain input, attention, action, target, movement, outcome, pending response, selected neuron variables and all changed drive-to-combination records. In sampled seed 0/category 3 at contact, both bodies selected eat on tick 2; on the next tick the matched outcome supplied response input -0.25, drive-2 variable 3 became -0.25, and one connection moved from drive 0→comb 103 to drive 2→comb 163 with variable 0 about 0.23609. The other six sampled cases did not complete within 32 ticks. The category-8 examples used a different seed, so they do not establish that category as the cause. These are reconstructed brain observations, not fresh native-engine behavior.

The [counterbalance and accessibility check](../runs/food-qualification/counterbalance-accessibility.json) checks identical pre-outcome observations when the hidden good-food assignment is flipped, for every development seed and both tasks/bodies with mirrored positions. It separately uses explicitly instrumented host movement and eat commands to prove each physical target can be reached and consumed under either outcome assignment. Those forced checks are not brain-selected behavior and do not establish learning.

## Timing protocol

`scripts/qualify_food_benchmark.py` runs development seeds 0–15 with budgets 2, 4, 8, 16, and 32 ticks, each body, preference/embodied task and both mirrored layouts. A case stops at its first completed consumption or after 20 opportunities; unsuccessful cases are right-censored. The rate is the proportion of seeds completing at least one consumption within that bound, not the fraction of all opportunities completed. Choose the shortest budget for which at least 13/16 seeds complete in **every** body/task/mirror cell. This is stricter than aggregating across bodies or mirrored sides. All observations and decisions remain in the retained per-case JSONL. Existing v1 held-out seeds are not used for qualification.

The completed 640-case sweep selected **no budget** under that mirrored-cell
rule. Counts below are completed seeds out of 16; the two numbers are the two
mirrored layouts. At 16 ticks both preference cells qualified, while no
embodied cell did. Even at 32, embodied cells remained below 13/16.

| Budget | Walking preference | Swimming preference | Walking embodied | Swimming embodied |
| --- | --- | --- | --- | --- |
| 2 | 5, 5 | 5, 5 | 2, 1 | 0, 0 |
| 4 | 7, 7 | 7, 7 | 4, 1 | 1, 0 |
| 8 | 11, 12 | 11, 13 | 8, 7 | 7, 6 |
| 16 | 13, 14 | 13, 14 | 9, 7 | 7, 7 |
| 32 | 15, 15 | 14, 14 | 12, 8 | 10, 9 |

The mirrored-cell threshold is stricter than counting a seed as completed when
**either** of its mirrored branches completes. At 32 ticks, the latter counts
are 16/16 walking preference, 15/16 swimming preference, 15/16 walking
embodied, and 13/16 swimming embodied. It would meet an aggregate 80% seed
gate, but masks the side-specific failures shown above. The stricter rule was
recorded before the sweep; both interpretations are retained for review.

The [calibration report](../runs/food-qualification/development-calibration-v2.json)
retains completion and censoring for all budgets. The [action analysis](../runs/food-qualification/development-calibration-v2-analysis.json)
separately counts attention, targets, motor actions, eating attempts, completed
targets, high/low food outcomes and observed energy changes. For example, at
32 ticks walking/embodied/mirror 0 selected eat 184 times across all recorded
steps but completed 12 consumptions before cases stopped. Per-step counts and
conditional completion counts are descriptive; this is not a preference or
learning test. The calibration took about 462 seconds wall time with six workers.
It executed 85,455 brain ticks, used about 2,747 summed worker CPU seconds,
and reported a maximum cumulative per-worker peak RSS of 21,416 KiB. The RSS
is not a process-family peak or an independent memory measurement per case.

## Small counterbalanced diagnostic

A separate [development-only diagnostic](../runs/food-qualification/diagnostic-v2.json)
used seeds 0–3, both bodies, both tasks and mirrored layouts. For each identical
seed it ran both hidden outcome assignments and both feedback conditions, with
eight opportunities and a 16-tick limit. It is exploratory; the 16-tick choice
does not select a confirmatory budget. The outcome is applied by the environment
after a brain-chosen completed consumption. Target and eat-action counts are
per tick; completed consumption and high-value counts are per opportunity.

| Body and task | Feedback | Opportunities | Target 0 / 1 selections | Eat-action ticks | Completed | Higher-value completions |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| Walking preference | supplied | 128 | 836 / 725 | 51 | 37 | 30 |
| Walking preference | withheld | 128 | 902 / 744 | 50 | 32 | 16 |
| Swimming preference | supplied | 128 | 836 / 722 | 48 | 38 | 31 |
| Swimming preference | withheld | 128 | 896 / 744 | 44 | 34 | 17 |
| Walking embodied | supplied | 128 | 1052 / 957 | 222 | 5 | 3 |
| Walking embodied | withheld | 128 | 1040 / 972 | 68 | 4 | 2 |
| Swimming embodied | supplied | 128 | 1069 / 969 | 138 | 4 | 2 |
| Swimming embodied | withheld | 128 | 1040 / 998 | 68 | 4 | 2 |

The diagnostic records actual energy deltas in its raw events. Counts among
completed interactions are selected outcomes, not proof of preference. With
the control unqualified and only four development seeds, none of these
comparisons establishes learning or reversal. The difference between selected
eat actions and completed consumption in the embodied task identifies a
concrete interaction bottleneck under this particular geometry and schedule.

## Learning-control audit

The candidate `suppress_drive_comb_migration` context suppresses only migration of the gene-7 drive-to-combination tract; it clears the consumed weak queue and lets the ordinary tract rules, weight updates, consolidation, reinforcement and other tracts run. It is a host-side experimental ablation and must be reapplied after restoring a checkpoint. It does not alter the `DefaultBrain` implementation, native archives or default checkpoint format.

The [controlled audit](../runs/food-qualification/migration-control-audit.json) and focused regressions compare the complete reconstructed brain state immediately before the first eligible migration and find it identical between the ordinary and ablated runs. The ordinary run migrates two endpoints; the ablated one does not. In a no-eligible-migration case the entire next tick matches, and reapplying the ablation after checkpoint restoration preserves its continuation. These results qualify the ablation only for the stated structural intervention and tested states. They do not prove that every transient effect is preserved after the point of a withheld migration.

The supplied stage-1 program has four migratory tracts, including gene 7 and genes 18–20. Gene 7 also executes dendrite update and consolidation rules; reward/punishment helper channels can affect weights when their gates allow. In a separate partially reconstructed captured-state replay, four weight-state pairs changed despite the migration ablation. Other retained neuron, dendrite, helper and queue state also remains active. Thus the ablation is **not a learning-disabled control** and cannot isolate the complete tested learning pathway. The feedback-withheld condition remains a separate unqualified comparison. Without a suitably scoped learning control, the planned confirmatory preference/reversal claim must not be made.

## Held-out boundary

Fresh seeds 56–95 are reserved for the confirmatory two-task evaluation and have not been used in this package. Run it only if both the timing threshold and an adequate learning control qualify. Retain the original >=10 percentage point and paired 95% bootstrap criterion, with non-completion in the denominator. Current checks and reports do not establish a food preference, adaptation or natural-world competence.

The [frozen qualification status](baselines/food-qualification-v2-protocol.json)
records program/source digests, geometry, seeds, thresholds and the explicit
unqualified status. Full unittest discovery passed 237 tests after the changes;
the retained original-engine replay tests remain available and passed as part
of that run. The diagnostic package did not run the native engine again.
