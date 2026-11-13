# Experience-grounded animation requests — 2026-11-08

`visual_asset_requests` identifies a missing harvest clip only after an attributed,
completed berry harvest. It verifies executed/outcome action identity and target,
checks the perceived berry type, and compares the existing daily-sheet hash with
its manifest. The request retains individual/branch, source event and event hash,
reference hash, coverage limitation and an explicit bounded ability claim.

The normal detector examines recent experience. A caller can also select a
retained event explicitly; missing or non-harvest evidence does not create an art
request. Requests are deduplicated by individual, branch, intent and reference
version, preserving the original motivating evidence rather than replacing it
with every later harvest. Requests are visual-system records, not invented
experiences inserted into the creature's memory.

## Real candidate

The first recent-history lookup found no recent harvest and correctly did nothing.
The developer then selected already verified live event 27247 (berry-5 harvested)
from the retained history. This invocation is developer initiated, not a claim that
the creature independently requested art. The worker generated four poses using
the exact installed purple-creature daily sheet: reach, pick, lift, hold.

The candidate is at
`runs/habitat-visual-qualification/asset-jobs/75b72e25725131bf28283a700f838bea4c25deb1b4cf4b98062cd0a0ab21a21f/candidate.png`.
Its SHA256 is d32cc6fac95188fac1700f76318d607b37d887ec63a8354f14229f7482b378ab.
The 2172x724 source visually preserves the recognizable character and four distinct
poses. Generation used 55,306 input tokens (34,816 cached) and 484 output tokens.
It is uninstalled; alignment, world-size sampling, palette and actual animation
still require qualification. No image was substituted into the live renderer.

Raw dimensions and partial alpha are not sufficient acceptance criteria. The
existing accepted daily sheet is 1254x1254 with four rows/columns and uses runtime
cell sampling, alpha thresholding and palette conversion. Therefore a large or
non-divisible source size is a reason to qualify sampling and frame registration,
not by itself a permanent rejection. Earlier native-dimension checks remain useful
measurements, but should not replace actual game-size visual evaluation.

## Background integration

`AssetRequestScheduler` runs one candidate worker outside the body thread. The
habitat calls it after saving the actual tick. It records dispatch before starting,
keeps completed receipts, deduplicates later matching activity, and reports recovery
required for an interrupted dispatch rather than silently relaunching. Generation
failures remain separate from bodily activity. Shutdown cancels its owned worker.
Candidate receipt status never grants installation or a new learned ability.

Thirteen request/worker/habitat checks passed in 20.517 seconds. A separate
production-boundary check passed in 3.595 seconds and confirmed that the source
harvest could be read from the saved checkpoint when the worker began. Earlier
eight request/worker checks also passed in 10.608 seconds. Evidence is under
`validation/visual-asset-requests/`.

The live user service now includes `30-asset-generation.conf`, enabling
`--generate-assets` alongside reflection. Restart at tick 28136 preserved the exact
checkpoint bytes (SHA256 1c0672ec9bdd90c4b2cb93fd32a74d1a76c11640ba9bc0bf8197d216b904030d),
identity, branch and model v33. Running state was restored. The initial asset
scheduler status was idle. This proves installation/readback, not a newly observed
autonomous image request after restart; the candidate above predates enablement.

Remaining: in-world frame/animation QA, qualified registration, additional visual
need detectors, environment-object authoring and a complete automatic generation-
to-installation workflow. The single harvest detector is an initial capability,
not the full extensible creature/environment asset agent.

After enablement, a new actual harvest occurred at tick 28197/event 28272. At tick
28225 the live asset status became candidate-awaiting-qualification. The asset-job
inventory still contained exactly the original job and its earlier provider
receipt: the scheduler recognized the existing need without generating a duplicate.
Evidence: `live-status.json` and `live-deduplication.json` under the qualification
directory. The latter reads archived and current records together; inspecting only
the current checkpoint tail would miss this event after history segmentation.
