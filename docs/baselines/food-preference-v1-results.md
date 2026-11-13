# Food-preference benchmark: baseline v1

The 896-case protocol completed with 16 development and 40 held-out seeds for each embodiment, four variants and two feedback conditions. Every case used 20 opportunities in each of four phases and a two-tick maximum per opportunity. The [protocol and qualifications](../FOOD_PREFERENCE_BENCHMARK.md) are part of this result. Source/program fingerprints, full per-step events, per-seed results and paired bootstrap intervals are in `runs/food-preference/baseline-v1.json`; the per-case JSONL is retained alongside it. `baseline-v1-analysis.json` adds first-opportunity rates and cost summaries. Earlier preliminary cases use superseded fingerprints and are not included.

The required learning-disabled control is **not qualified**. The available comparison withholds response feedback; it is not an otherwise identical brain with plasticity disabled. The 10-percentage-point learning criterion is therefore **unassessable**, regardless of the descriptive differences below. These results do not establish a learned preference, nor do they prove the recovered brain cannot learn one in other settings.

## Held-out training-layout results

Rates count unsuccessful or unfinished interactions in the denominator. Both movement adapters produced the same aggregate rates in this particular setup; they have different movement physics, but this result does not establish different behavioral competence.

| Phase | Feedback | Feedback withheld | Paired difference, 95% bootstrap interval |
| --- | ---: | ---: | ---: |
| First opportunity before food feedback | 0 / 40 (0%) | 0 / 40 (0%) | — |
| Initial evaluation | 60 / 800 (7.5%) | 18 / 800 (2.25%) | +5.25 pp [1.5, 10.125] pp |
| Reversal evaluation | 43 / 800 (5.375%) | 9 / 800 (1.125%) | +4.25 pp [1.5, 7.875] pp |

During initial evaluation only 67 / 800 feedback opportunities and 43 / 800 feedback-withheld opportunities completed consumption. During reversal evaluation the corresponding counts were 51 and 25. Thus overall choice success is dominated by failure to complete an interaction under this bounded adapter; selection quality conditional on eating must not be confused with the primary score. Evaluation itself continues learning. In the feedback condition, 8 / 40 held-out seeds ever reached six successes in a rolling eight-opportunity window during initial experience/evaluation, and 4 / 40 did so after reversal; seeds that did not reach the criterion are censored, not assigned a learning time.

In held-out layout evaluations, feedback successes were 0 / 800 initially and 2 / 800 after reversal for each embodiment. The altered distance starts the objects outside contact and the brain has only two ticks per opportunity, so this result confounds navigation and the opportunity limit with preference. The appearance variant changed a label that was never encoded and reproduced training-layout rates; it does not test appearance generalization. The novel-identity variant changed category indices during evaluation and is an exploratory unfamiliar-identity test: feedback success was 46 / 800 initially and 58 / 800 after reversal per embodiment. No unseen identity is assumed to have a knowable value.

## Continuation and cost

At the midpoint of held-out seed 16, each embodiment and condition was checkpointed and resumed. All four resumed runs matched every remaining recorded event and the final complete portable experiment state of the uninterrupted run. Separate focused tests exercise a checkpoint with pending feedback. This is controlled portable-checkpoint evidence, not equivalence to a native Docking Station save.

The run executed 139,642 brain ticks over 71,680 opportunities, with 4,060 completed consumptions, across 896 cases. Elapsed wall time was approximately 726 seconds with six workers; summed per-case process CPU time was approximately 1.20 hours. The maximum reported cumulative per-worker peak RSS was 25,740 KiB. This is not total process-family peak memory, and per-worker peak RSS is a cumulative high-water mark rather than a separate measurement of each run. `runtime-v1.json` records the local runtime.

## Next measured limitation

The clearest immediate limitation is the low completion rate in a two-tick, one-dimensional environment and the absence of a qualified learning-disabled control. The first follow-up should qualify the control and investigate whether the brain can perceive and complete useful object interactions under less restrictive but still neutral, matched timing. Do not infer that adding memory, delayed credit or planning would solve these observed failures without separate tests.
