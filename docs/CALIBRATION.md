# Docking Station timing and physiology calibration

The original installed engine was executed only inside a separately copied game and fresh 32-bit Wine prefix in a bubblewrap namespace. The namespace had no network route and could not see the real home, Steam installation or saved worlds. Original installation and save hashes were unchanged, and all owned game processes were closed. Exact setup, commands, observations and limitations are in the [runtime findings](../research/docking-station-20261103/runtime-calibration/findings.json).

## Clock

The engine's initialized default world interval is 50 ms. Its creature agent updates the active faculties every fourth own update; Brain precedes Biochemistry in that callback. In the isolated run, the engine reported BUZZ=50 ms and RACE around 50–51 ms. Over the no-food sample, 163 world ticks and 40 biochemical callbacks elapsed over approximately 8.125 seconds; the subsequent fed window measured 41 callbacks over approximately 8.122 seconds. Native fade and fast modes can change the interval; individual loaded worlds and computers can run slower. Static REA evidence is retained in [timing findings](../research/docking-station-20261103/timing-native/findings.json).

The default `docking-nominal` model profile now advances one brain and biochemical update per 0.2 simulated seconds. This matches the measured rate in this bounded isolated run, not every runtime condition. Older schema1 biochemistry checkpoints lacking a cadence field retain their prior 1-second interval; explicitly choose `--timing legacy --dt 1` for the earlier comparison schedule. A checkpoint records its own cadence.

## Native chemistry comparison

A female Chichi test creature, CAGE1 (child), was placed in an isolated neutral room with no food. Two recorded native runs sampled 15 chemicals over a no-food period, followed by an atomic STIM79 at strength0.125 and further observations. The reference executes the same genotype and compares samples at the recorded TAGE-derived biochemical tick counts.

- Across 35 later samples × 15 chemicals, the largest absolute difference was **0.000008855**.
- At the full native baseline, all 256 chemicals matched within **0.000000479**.
- The 22 organ receptor/emitter/reaction counts matched; the maximum displayed energy-cost difference was **0.000000491**.
- The native food stimulus changed chemicals10,12,149,151; the model matched the recorded trajectory after that same intervention.

CAOS values are printed to six decimal places. These results are a narrow, measured validation of this one life stage, isolated setup and short no-food/food-stimulus trajectory. They do not establish bitwise floating-point parity, full-world behavior, every age/sex, the original game's social behavior, or biological realism. The stage3 request was deferred by the native game; it was not silently reported as a stage3 calibration. The game-generated genome file had a different whole-file digest due to parental-name bytes and opaque trailing data; selected brain and biochemical gene records through `gend` were separately checked against the supplied template.

Run `.venv/bin/python scripts/compare_native_physiology.py` to reproduce the comparison from preserved captures. See [machine-readable comparisons](../runs/nominal-survival/native-physiology-comparison.json).

## Autonomous survival

The [nominal-timing fed/depleted comparison](../runs/nominal-survival/REPORT.md) used two full-brain creatures in each condition without rescue or teacher commands. Both deprived creatures died at 1,890.2 and 1,931.6 simulated seconds; both fed controls survived to 2,100 seconds. Restored checkpoints matched continuation. These are standalone simulation outcomes at one seed, not a live-game survival comparison.
