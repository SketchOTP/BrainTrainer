# Fresh-seed half-gain comparison

The fresh-seed study completed all **256 cases** using seeds 96–111, both bodies, both mirrors, both food-value assignments and paired baseline versus the fixed half-strength positive hunger-training response. These seeds were outside the documented development 0–15 and prior gene-7 held-out 56–95 sets. A later bounded scan of earlier JSON records below 4 MB found no explicit 96–111 seed entries; this is not a claim that no unrelated experiment anywhere ever used those numbers. The [protocol](FOOD_HALF_GAIN_FRESH_PROTOCOL.md) and [manifest](../runs/food-qualification/half-gain-fresh-v1-manifest.json) were frozen before these cases ran.

There are 16 independent seeds per body, with four correlated mirror/value branches per seed and condition; each body/condition/phase has 1,280 opportunities. The predeclared primary score is the proportion of opportunities ending in consumption of the currently more valuable food; non-completions count as failures. Differences are half-gain minus recovered baseline. Intervals are 10,000-resample paired-seed percentile bootstrap intervals after averaging each seed's four branches.

| Body and phase | Baseline | Half gain | Difference | Paired 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Walking, initial evaluation | 29.06% | 29.14% | +0.08 pp | −0.31 to +0.70 pp |
| Walking, reversal experience | 22.03% | 23.13% | +1.09 pp | −0.86 to +2.97 pp |
| Walking, reversal evaluation | 18.28% | 19.38% | +1.09 pp | −0.31 to +2.81 pp |
| Swimming, initial evaluation | 28.13% | 28.36% | +0.23 pp | 0.00 to +0.63 pp |
| Swimming, reversal experience | 21.02% | 22.19% | +1.17 pp | −0.16 to +2.73 pp |
| Swimming, reversal evaluation | 17.42% | 19.53% | +2.11 pp | +0.23 to +4.38 pp |

**The predeclared overall capability target was not met.** Early reversal was required to improve by at least five percentage points with an interval above zero in each body; neither body met that requirement. The earlier four-seed development improvements did not replicate at that size. Initial evaluation, later reversal evaluation and matched-needs post-reversal probe each met the study's operational non-inferiority rule in both bodies: a nonnegative mean difference and interval lower bound above −5 points. This does not prove absence of all harm. Swimming's later evaluation interval was above zero, but the predefined early-reversal and overall target still failed; do not promote the candidate on one endpoint.

Completed interactions during reversal experience were 370 baseline versus 398 half-gain walking and 355 versus 379 swimming, out of 1,280 opportunities per cell. Higher-value completions were 282 versus 296 and 269 versus 284 respectively. Among completed interactions only, those correspond to 76.2% versus 74.4% walking and 75.8% versus 74.9% swimming. These conditional rates omit failures and are secondary diagnostics, not the primary score.

## Retention and checkpoint continuation

After initial experience, both conditions chose eat at the higher-value target in the matched-needs clone in 44/64 walking and 41/64 swimming branch probes. After reversal experience, the baseline versus half-gain counts were 36/64 versus 40/64 walking, and 30/64 versus 39/64 swimming. The paired-seed difference intervals after reversal were −3.13 to +18.75 percentage points walking and 0.00 to +29.69 swimming. The 64 probes per body and condition share 16 seeds; they do not establish a statistically clear retention improvement. Probes clear pending outcomes only in a clone, normalize visible needs and geometry and deliver no new outcome. Other retained neurons, chemistry and RNG remain, so a probe is not an isolated tract-state transplant.

All 256 cases passed the producer's midpoint JSON save/reload continuation comparison, including subsequent events and complete final snapshot; each matched and unmodified-needs probe was repeated from a separately restored clone with identical result and post-probe brain digest. The [combined analysis](../runs/food-qualification/half-gain-fresh-v1-analysis.json) checked all shard receipts and file hashes, expected unique keys, every opportunity, complete paired initial snapshots apart from the intentional extension marker and the per-case continuation flags. The original per-case midpoint objects were not saved.

Four predetermined fresh cases—seed 96 walking and seed 111 swimming, one baseline and one half-gain each—were separately re-executed from their seeds. Their constructed initial checkpoints, all recorded events, pending deliveries, phase tract snapshots, probe outcomes and complete final brain states matched the retained cases. Their newly reconstructed midpoint save/reload continuations also matched. [Replay receipt](../runs/food-qualification/half-gain-fresh-v1-independent-replay-v2.json). This is a separate re-execution using the **same implementation**, not an independent implementation, a replay of a retained original midpoint, or native Docking Station verification. The earlier replay receipt without the `-v2` suffix used an imprecise description of starting from the saved checkpoint; its numerical matches are preserved but this report relies on the corrected v2 wording.

## Scope and resource limits

The intervention is an optional host-interface gain on already-attributed worsening hunger input; it changes neither the recorded outcomes and chemistry nor the recovered neural kernel. It can influence transient activity as well as learning. The test uses the experimental in-contact action lifecycle whose interruption rule remains unverified against native brain-selected interruption. The present result therefore does not establish general failure of the brain to adapt, native parity, or lack of any effect in other environments.

Four shard receipts bind the raw cases to the frozen manifest. They report approximately 3,138 seconds summed shard wall time (sequential shard invocations, excluding gaps and analysis) and 34,703 summed case CPU seconds. Maximum cumulative per-worker peak RSS was 65,644 KiB; process-family peak memory was not measured. The [analysis artifact](../runs/food-qualification/half-gain-fresh-v1-analysis.json) preserves per-opportunity curves, seed differences, action and target counts, non-completions, conditional scores and first-success times including censored branches. No defaults were changed.

After the study and replay, the complete local unittest suite passed **278 tests**. The frozen manifest and its source/program digests still matched.
