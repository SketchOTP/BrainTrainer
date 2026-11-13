# Self-review and growth boundary

Moss is currently a genome-brain research simulation with host-authored body,
world, memory, and sensing adapters. The brain is derived from REA findings;
the project is not evidence that Moss is conscious, biologically alive, or
generally intelligent. The habitat is only one adapter and should not define the
project's research priorities.

## What Moss can currently know

Run a source-linked capability review:

```bash
.venv/bin/python -m creature_brain.self_review
.venv/bin/python -m creature_brain.self_review --json
.venv/bin/python -m creature_brain.self_review --verify --output runs/self-review.md
```

The review distinguishes modeled, partial, and missing capabilities. It checks
whether linked source, test, and evidence files exist. It does not claim those
tests passed or infer ability from a file name. The report identifies
self-directed learning, persistent in-creature self-knowledge, and development
as missing or partial. External Codex-assisted candidate generation exists, but
Moss itself does not write code or promote it.

`--verify` explicitly runs each distinct linked `tests/test_*.py` file in a
separate Python process and records status, runtime, exit code, and output.
The default report remains read-only and does not launch tests. These tests run
with the invoking user's permissions; use the Codex candidate harness below
when evaluating generated code.

An explicit verification report includes a `verification_summary` with file
counts for `passed`, `failed`, `timed_out`, and `errored`, plus
`total_elapsed_seconds`. Counts describe linked files, not individual unittest
cases. The elapsed total sums each file's recorded duration, including path
validation and process-launch overhead; it is not the command's full wall time.
The summary appears only with `--verify`, alongside the retained per-file
results. These outcomes measure test execution, not creature competence.

## Code change loop

The creature brain must not be confused with the coding agent. Codex CLI is an
external development tool, not an internal lobe or evidence of self-awareness.
A useful growth cycle is:

1. Record a capability question and a measurable baseline.
2. Run a blinded evaluation without teacher goals; retain the complete result.
3. Compare performance, failures, uncertainty, and regressions against the
   prior baseline.
4. Ask Codex to propose one focused change tied to the observed gap.
5. Evaluate that candidate in an isolated project copy; retain its diff, tests,
   and trial report.
6. Promote a passing candidate into the running project deliberately, preserve
   the prior checkpoint, and repeat the same held-out evaluation.

Run one isolated Codex growth cycle:

```bash
.venv/bin/python scripts/self_improve.py
.venv/bin/python scripts/self_improve.py --task "Add a held-out test for memory reversal"
```

Each call stages a bounded source, docs, tests, and fixture copy under
`runs/self-improvement/<UTC timestamp>/candidate/`. GPT-6.1 Sol first reads the
capability review and writes a proposal in a read-only session. GPT-6 Luna then
receives that proposal and implements it in the candidate copy. Its patch and
report are saved separately from the proposal. The candidate suite runs in a
local bubblewrap sandbox with network disabled. The live program, pet save,
shell profile, credentials, and unrelated files stay outside the writable
workspace. Candidate checks require Linux `bwrap`. The harness does not promote
the patch. A generated patch is a candidate, not proof of new ability.

The local user timer runs this two-model cycle every day at midnight, 8:00 a.m.,
and 4:00 p.m. Eastern. It catches up after the computer was off at a scheduled
time. Results include
the proposal, implementation-model report, candidate patch, and test log under
`runs/self-improvement/`; no candidate is applied to the live project.
Manage it with `systemctl --user status moss-self-improve.timer` and
`systemctl --user disable --now moss-self-improve.timer`.

No unrestricted self-modification mode is provided. Allowing generated code to
execute with unrestricted access to the user's machine could overwrite data,
expose credentials, or alter unrelated software. The project can still run
frequent autonomous capability evaluations and create candidate improvements
without giving the creature arbitrary control of the host.

## Research priorities

1. Make perception, action, and consequences measurable with a compact body and
   world interface.
2. Test memory, reversal, generalization, uncertainty, and novelty with held-out
   objects and no scripted goals.
3. Add an explicit self-model of body state, available actions, learned skills,
   uncertainty, and failed attempts.
4. Add self-directed learning based on uncertainty and information gain.
5. Use the external candidate harness to evolve code against repeatable,
   held-out evaluations while preserving the REA-derived brain as the base.

Each priority needs a clear separation between REA-recovered behavior, an
original host adaptation, and a hypothesis about creature-like competence.
