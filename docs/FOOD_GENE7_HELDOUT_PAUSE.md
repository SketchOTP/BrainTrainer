# Paused held-out gene-7 test

Paused at the user's request on November 6, 2026. No held-out worker remains running. No intermediate held-out outcomes were inspected or used to modify the predeclared protocol.

The frozen manifest is `runs/food-qualification/gene7-heldout-v1-manifest.json`, SHA-256 `6615d73940082d7d9f7523b60749994c3806c4bb3e8cf825779904110a2b11fb`. It binds the program, sources, analysis, protocol and development diagnostic artifacts. Do not edit those files and then treat the old manifest as valid. Seeds 56–95 are the predeclared held-out set. The in-contact task and 32-tick action lifecycle do not establish native interruption parity or disable whole-brain learning.

Shard 0 completed all 80 cases; its case-file hash and manifest binding were verified against its receipt. Shard 1 was stopped by SIGTERM at the user's request. Its append-only case file contains 48 complete, unique, validated records; 32 remain. Its SHA-256 at pause is `bc987aac30d9dda9127152f08a4d5ab08e5daffb5c959fee7adfa02a3e5faf44`. The shard start receipt matches the frozen manifest and seeds 61–65. A streaming validation checked every retained row, full opportunity histories and checkpoint/control flags, and confirmed no truncated final line. In-flight work was stopped and will be rerun. Shards 2–7 have not started. The complete test requires 640 cases across eight shards; currently 128 completed cases are preserved.

The implementation and validation suite passed 268 tests before the run. The development work established a controlled immediate target effect in some tract-transfer contexts, bounded reversal diagnostics and four independent continuation replays; see `FOOD_TRACT_TRANSFER_DIAGNOSTIC.md`, `FOOD_REVERSAL_DIAGNOSTICS.md`, and `FOOD_INDEPENDENT_REPLAY.md` for exact limits.

## Resume

From `.`, first recheck `run_gene7_heldout.check_manifest` and the shard-0 receipt, then resume the partial shard. The `--resume` guard verifies its start receipt, current manifest, retained records and duplicate keys; it does not automatically repair a truncated line. Preserve the existing raw file before any separate repair.

```bash
.venv/bin/python scripts/run_gene7_heldout.py shard --manifest runs/food-qualification/gene7-heldout-v1-manifest.json --shard 1 --output runs/food-qualification/gene7-heldout-v1-shard-1.json --workers 12 --resume >> runs/food-qualification/gene7-heldout-v1-shard-1.log 2>&1
```

Then run each untouched shard, one at a time in a separate command, using its own receipt and output paths. This example starts shard 2; repeat separately with values 3 through 7:

```bash
.venv/bin/python scripts/run_gene7_heldout.py shard --manifest runs/food-qualification/gene7-heldout-v1-manifest.json --shard 2 --output runs/food-qualification/gene7-heldout-v1-shard-2.json --workers 12 > runs/food-qualification/gene7-heldout-v1-shard-2.log 2>&1
```

For an interrupted shard, use `--resume` and append to its log; each shard process should be managed separately because the previous continuous development process received SIGTERM after roughly an hour. Do not interpret incomplete held-out results. Once all eight receipts exist, run `scripts/analyze_gene7_heldout.py` with the manifest, eight repeated `--shard-report` arguments and a new `--output` path. It validates all 640 keys, full paired initial snapshots, source/receipt hashes and recorded control/checkpoint flags, then calculates the predeclared paired-seed bootstrap and 10-point criteria. Producer checkpoint continuation is checked for every case; only a small development sample was independently replayed. Update the Creatures Brain Notion page with the final outcome and limitations.
