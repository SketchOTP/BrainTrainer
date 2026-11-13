# Persistent individual example

From the project root, run:

```sh
.venv/bin/python examples/persistent_individual/server.py
```

Open <http://127.0.0.1:<port>>. Offer or move food A, food B, or the toy relative to the creature, and observe its attention, action and outcome. The server resumes the same individual from `runs/persistent-individual/individual.json`; `--state PATH` selects another portable checkpoint and `--seed N` selects a new individual's initial seed. Stop with Ctrl-C. The server saves every 20 ticks, on interaction, and on graceful shutdown. Abrupt termination can lose ticks since the last save; the Save button writes immediately. This example is local only and is not a Docking Station archive.

Food effects are hidden from the brain until consumption. Attention and actions originate in the recovered brain; the page only changes objects in the world. The walking adapter and experimental action lifecycle execute the selected action. The room is bounded at positions −20 and +20; that boundary, tick pacing, objects and the action timeout are host design choices, not claimed native parity. An eat action approaches and registers contact before consumption; another selected action interrupts it, a different selected target replaces it, loss of the target fails it, and an action lasting 32 ticks is cancelled. The world and brain do not reset between ticks. Its checkpoint preserves the individual identity, brain and chemistry, body, objects, clock, random state, pending outcome feedback and active action.

The optional retention runner is a scientific experiment separate from the live UI; see its frozen protocol and results in the project docs. It compares ordinary gain-1 against the narrow persistent gene-7 tract freeze, not a whole-brain learning-disabled condition.

## Optional experimental movement self-model

To try the separate experimental individual and checkpoint, run:

```sh
.venv/bin/python examples/persistent_individual/server.py --experimental-motor-model
```

Open <http://127.0.0.1:<port>>. The movement panel shows the last prediction, chosen execution effort, observed result and remaining motor reserve. The body-strength control changes the example body's physical response; the model receives movement outcomes, not the setting. This creates or restores `runs/persistent-individual/motor-individual.json`, separate from the baseline individual's checkpoint. The reserve is not coupled to food or replenished automatically; the panel can restore it. The model does not select the brain's action or target. Its motor reserve, effort costs, movement success threshold and body impairment are experimental host rules, not recovered Docking Station biology. The baseline remains the default when the option is absent.

A separate experimental four-decision recovery-probe individual can be launched with `--experimental-recovery-probe` at <http://127.0.0.1:<port>>. Its checkpoint is `runs/persistent-individual/recovery-individual.json`; it does not replace the original individual or the earlier motor model. This is a research option, not a promoted default. The recovery comparison reports any extra failures during impairment alongside improved recovery.

The separate confirmation candidate can be tried with `--experimental-confirm-recovery` at <http://127.0.0.1:<port>>. Its checkpoint is `runs/persistent-individual/confirmation-individual.json`. It makes one additional real low-effort attempt after a surprising success, rather than receiving a body-recovery signal. This remains experimental; neither the baseline nor the prior motor individual is automatically migrated or replaced.

The confirmation host also supports an explicit programmatic copy from an existing adaptive motor individual using `ConfirmationMotorIndividual.from_baseline(existing)`. The copy preserves identity, brain and body, model evidence, pending attempts and clock; it does not mutate or stop the source. Keep only one active continuation of an individual when using that conversion. A baseline checkpoint cannot be silently loaded as a confirmation checkpoint or vice versa.

## Operational continuity receipts

The server displays its current tick and last durable checkpoint tick. Each successful checkpoint flushes the state file and its containing directory before recording `checkpoint_written` in `<state path>.lifecycle.jsonl`. That log also records startup, requested shutdown and server-side errors; `server_shutdown` cannot observe its own operating-system exit status and labels it unobserved. Logs and checkpoint ticks do not establish that unsaved ticks survived an abrupt interruption.

To record child exit status observed by a parent process, launch through:

```sh
.venv/bin/python examples/persistent_individual/launch_individual.py -- --experimental-confirm-recovery
```

Additional server options can follow the `--`. The launcher appends child-start, forwarded-signal and observed child-exit records to `runs/persistent-individual/process-observations.jsonl`; `--process-log PATH` selects another log. A negative child return code records termination by that signal. If the launcher itself is terminated before it observes the child exit, the missing exit record is unknown, not evidence of a particular exit or of lossless continuation.

## Optional complete-action predictor

The passive action-prediction demonstration is a separate prepared individual and checkpoint:

```sh
.venv/bin/python examples/persistent_individual/launch_individual.py -- --experimental-action-prediction
```

Open <http://127.0.0.1:<port>>. The brain still chooses its action and target, and the current adaptive motor controller still chooses effort. A disposable copy previews a prospective eat-action forecast before the real action executes; a changed scene or body invalidates that preview. Automatic execution holds the preview for about 1.5 seconds, changing wall-clock pace but not the simulation's brain-tick ordering. With `--start-paused`, Step previews a new eat action and Step again executes it. The view then shows the eventual outcome linked to the original action. The contextual evidence label uses a research heuristic: fewer than five context-specific observations is marked limited, not a statistically guaranteed confidence interval.

The saved `action-prediction-individual.json` includes the one-time inherited-preparation receipt, neural and body state, pending action and forecasts, and learned estimates. Each forecast and terminal is also appended to the checkpoint's lifecycle JSONL. Action/model state is checkpointed when such records occur, but the checkpoint and JSONL are separate files, not one atomic transaction: a crash between writes can leave a missing journal event. The last durable checkpoint is the authority for restored state; do not infer that every observed wall-clock event survived a crash. This optional individual does not modify the live baseline checkpoint.
