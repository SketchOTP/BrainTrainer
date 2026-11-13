# Controlled transfer of experienced gene-7 tract state

This is an exploratory reconstruction experiment using four development seeds (0–3), walking body, one mirror orientation, and both counterbalanced food-value assignments. It does not use held-out seeds and does not claim native-engine parity. The eight source branches are drawn from the original frozen development run. Starting from their retained initial checkpoints, each branch was replayed through opportunity 60 and every observation, choice, action event and outcome was compared against the retained per-step history. The complete brain states immediately before experience, after 20 initial-experience opportunities and after 20 reversal-experience opportunities were saved in [stage snapshots](../runs/food-qualification/tract-state-transfer-dev-v1.states.jsonl).

For each of the 24 recipient contexts (four seeds × two assignment branches × three recipient stages), the experiment replaces only the gene-7 drive-to-combination tract with a compatible same-seed donor's entire saved tract state: endpoints, all dendrite variables, helper, weak queue and migration count. For a given recipient, all non-target brain fields, neuron states, previously queued lobe inputs and RNG remain identical between donor conditions. Each receives identical visible food categories, hunger input, and a shared chemical vector with hunger chemical 150 set to 0.8. No external pending-outcome event is delivered and no action is executed during the probe. The donor's external outcome queue is not transplanted. Attention is mapped to one of the two visible food targets; eat is action 12.

The 24 contexts are repeated recipients from **four seeds**, not 24 independent experiments. Comparisons are descriptive. Different donor reward assignments also generated different histories of choices and outcomes, so an experienced tract can carry more than an isolated food-value label.

## Opposite-value donors

| Donor stage | Recipient contexts | Opposite donors selected different targets | Both targets matched donor's then-current valuable food | Both targets matched and both actions were eat |
| --- | ---: | ---: | ---: | ---: |
| After initial experience | 24 | 16 | 16 | 9 |
| After reversal experience | 24 | 10 | 7 | 4 |

After initial experience, every target flip observed between opposite-value donors pointed toward the respective donor's valuable food. After reversal, seven flips matched the newly valuable foods and three pointed in the opposite direction. Other contexts had no target flip. These grafts demonstrate that experienced tract state can causally affect an immediate target in the fixed recipient context; directionality is consistent with value-related information for some cases. They do not prove that the tract stores a pure food-value association or that reversal succeeds consistently.

## Pre-experience donors versus experienced donors

For each of 24 recipient contexts and both value assignments, compare the shared same-seed pre-experience donor to the experienced donor (48 correlated comparisons per stage):

| Experienced donor | Target changed relative to pre-experience graft | Experienced target matched donor's then-current valuable food | Experienced choice was eat at that target |
| --- | ---: | ---: | ---: |
| After initial experience | 16/48 | 40/48 | 23/48 |
| After reversal experience | 10/48 | 28/48 | 16/48 |

The post-experience target-match totals include unchanged targets and thus are not counts of newly acquired preferences. For initial-experience donors, target changes from the pre-experience graft occurred in 2, 3, 5 and 6 comparisons for seeds 0, 1, 2 and 3 respectively; after reversal the counts were 3, 2, 4 and 1. See [sham verification](../runs/food-qualification/tract-state-transfer-sham-dev-v1.json) for all per-seed counts.

## Controls and evidence

For all 24 recipient contexts, a sham graft of the recipient's own tract reproduced the direct ungrafted tick's attention, decision, action and complete post-tick brain-state digest; it also matched the corresponding saved transfer probe. The graft implementation rejects mismatched genome, seed, age stage and sex and validates donor tract endpoint, helper and queue state. It checks that the recipient snapshot is identical outside the transplanted tract. Tests verify the full state copy, validation and no mutation of input snapshots.

The [transfer result](../runs/food-qualification/tract-state-transfer-dev-v1.json) records all probe choices, state hashes, source digests and limitations; the independent sham verifier rechecked every recorded source digest and the stage-snapshot digest. The original raw-case file's SHA-256 was independently recomputed as `c4e867666aa360cc52a94825e3a3e5340c7165c0f93de0ff0b42f54643b04864`, matching the recovered development analysis. The stage snapshots were produced by exact history replay, not directly saved phase-boundary checkpoints. No full-world native validation is implied.
