# Recovered brain food-preference benchmark

This independent research benchmark runs the genome-driven `DefaultBrain` with a locally supplied program. It does not load the pet simulation, experience memory, high-level association-based `Brain`, authored survival cues or an action-selection policy. The host maps the two observed categories to `visn`; the brain's actual attention and action determine the target and action. No preferred food or reward information is passed into the observations. Each completed eat action updates the host's energy and hunger; a matched action/target outcome can produce the recovered signed response input to `resp[2]`. All other action/target pairs get no food outcome.

The native-informed sensory route does not establish full native creature physiology or perception. Categories 3 and 8 are benchmark assignments, not a claim that native creatures classify these invented foods this way. Walking and swimming are simple deterministic one-dimensional models. Left/right/approach/retreat update positions differently; the host gives the brain no goal or navigation suggestion. Movement is recorded as `moving` and is not modeled as a completed multistep action; `completed` currently denotes a completed consumption. Other motor actions are recorded but have no modeled physical effect. A two-tick opportunity is an explicit bounded evaluation choice, not a natural Docking Station time unit. Failure to eat or identify a target counts as unsuccessful.

## Control and interpretation

The reconstructed SVRules can modify dendrites and helper state while also producing transient activity. There is not yet a verified gate that blocks **only** persistent learning while leaving all other dynamics untouched. Consequently the control is **feedback withheld**, not learning disabled. Both conditions use the same initialization, physical chemistry and observation rules, but the control omits the response-lobe outcome input. If their choices diverge, their later observations and chemical concentrations can also diverge. The control can still learn through other rules. Any enabled-versus-withheld difference is descriptive, not a qualified comparison against an otherwise identical learning-disabled creature. The planned >=10 percentage point target is **not assessable** against this unqualified control.

For the supplied stage-1 program this is a concrete unresolved boundary: there
are four migratory tracts (genes 7 and 18–20), and the drive-to-combination rule
includes both dendrite-state updates and consolidation opcode 44 in the normal
component schedule. Simply skipping a whole tract or restoring its complete
state after a tick has not been shown to preserve the original transient
computation. No learning-disabled gate is advertised until its affected state
and output semantics can be qualified.

Two observable food-type identities are counterbalanced against outcomes across seeds; the mapping reverses after 40 opportunities. Positions randomize independently. Held-out layout changes distance only in evaluation phases. Appearance labels change in evaluation phases but are deliberately not encoded into the brain; that condition checks only a neutral presentation change, **not visual appearance recognition or appearance generalization**. The novel-identity variant uses different category indices during evaluation; it is exploratory and is not evidence that values generalize to previously unknown identities. The system receives no delayed-credit extension or memory/planning overlay.

The success score means a completed consumption of the currently higher-value
food type. Actual energy change is logged separately and can be zero when the
energy store is already full; scores must not be described as measured energy
restored on every successful interaction.

## Run

```sh
.venv/bin/python -m creature_brain.benchmark.run \
  --program research/docking-station-20261103/resources/chichi-brain-program.json \
  --output runs/food-preference/baseline-v1.json --workers 4
```

Defaults: development seeds 0–15, held-out seeds 16–55, both embodiments, two conditions, four variants, 20 opportunities per phase and a two-tick limit. The phases are initial experience, initial evaluation, reversal experience, and reversal evaluation. Learning continues in the evaluation phases; these are online measurements, not frozen-policy tests. Six of eight successful opportunities meets the rolling-75%-of-eight criterion; `null` means not achieved in the observed segment.

Each completed case is flushed to `baseline-v1.cases.jsonl`; `--resume` reuses only cases with the same program digest, implementation fingerprint and step/opportunity settings. The output report provides raw step events, per-seed results, descriptive paired bootstrap intervals, CPU/wall time, and worker process peak RSS (a cumulative per-worker high-water mark, not per-run allocation). Seed 16 for each body and condition in the training variant round-trips a JSON checkpoint at the midpoint and compares all subsequent events and final state against uninterrupted execution. This portable experiment checkpoint includes brain state, queued feedback, body/world state, RNG, history and schedule; it is not a native archive.

As a reference representation measurement, an initial walking experiment for
seed 16 serialized to 287,609 compact JSON bytes, including a 280,526-byte
brain checkpoint, 815 neurons and 2,639 dendrites. This is serialized size,
not Python heap size, and grows as the experiment history grows.

`scripts/summarize_food_benchmark.py` also computes the first-opportunity rate,
which occurs before any food outcome in that run; the first-five-opportunity
metric in the primary output is an early-experience measure, not a pure
pre-experience test. Its `complete` flag counts cases, not benchmark success.

The baseline manifest is [recovered-v1.json](baselines/recovered-v1.json). Native observations and their limits remain in the [investigation report](../research/docking-station-20261103/brain-connections-20261106/queue-runtime/REPORT.md).

The completed first run and its limitations are in [baseline v1 results](baselines/food-preference-v1-results.md).
