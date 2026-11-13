#!/usr/bin/env python3
"""Run a two-model Codex growth cycle in a disposable candidate copy.

The live source tree and pet checkpoint are never passed as the writable
workspace. A run produces a candidate diff, Codex report, and test log. It does
not promote candidate code into the running project.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from creature_brain.self_review import inspect, markdown


ROOT = Path(__file__).resolve().parents[1]
INCLUDE_FILES = ("README.md", "pyproject.toml", "RESEARCH_RECEIPT.json",
                 "genome_physiology_receipt.json", "full_creature_receipt.json",
                 ".gitignore")
INCLUDE_SUBTREES = ("src", "tests", "docs", "scripts")
NATIVE_GENOME_METADATA = "research/docking-station-20261103/resources/norn.chichi06.ex47-genome.json"
INCLUDE_FIXTURES = (
    "research/docking-station-20261103/resources/chichi-brain-program.json",
    "research/docking-station-20261103/resources/chichi-genome.json",
    NATIVE_GENOME_METADATA,
    "research/docking-station-20261103/runtime-calibration/captured/stage1-child-live.json",
    "research/docking-station-20261103/runtime-calibration/findings.json",
    "research/docking-station-20261103/runtime-calibration/captures/20261103T204404Z-age1-female-full/logs/calibration.json",
)
IGNORE_NAMES = {"__pycache__", "*.pyc", "*.pyo"}
PROPOSAL_MODEL = "gpt-6.1-sol"
IMPLEMENTATION_MODEL = "gpt-6-luna"


def copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(*IGNORE_NAMES))


def stage_project(candidate: Path) -> None:
    candidate.mkdir(parents=True)
    for filename in INCLUDE_FILES:
        source = ROOT / filename
        if source.is_file():
            shutil.copy2(source, candidate / filename)
    for folder in INCLUDE_SUBTREES:
        source = ROOT / folder
        if source.is_dir():
            copy_tree(source, candidate / folder)
    for relative in INCLUDE_FIXTURES:
        source = ROOT / relative
        if source.is_file():
            destination = candidate / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def required_native_genome(candidate: Path) -> Path | None:
    """Return the single recorded game file needed by native-data tests."""
    metadata = json.loads((candidate / NATIVE_GENOME_METADATA).read_text(encoding="utf-8"))
    source = Path(metadata["path"])
    expected = metadata["sha256"]
    game_genetics = Path.home() / ".local/share/Steam/steamapps/common/Creatures Docking Station/Docking Station/Genetics"
    if source.parent != game_genetics or source.name != "norn.chichi06.ex47.gen":
        raise ValueError("native test input points outside the declared game genetics folder")
    if not source.is_file():
        return None
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("installed game genome digest differs from the recorded fixture")
    return source


def codex_command(codex: str, model: str, sandbox: str, candidate: Path,
                  last_message: Path) -> list[str]:
    return [codex, "exec", "--model", model, "--sandbox", sandbox,
            "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
            "--cd", str(candidate), "--output-last-message", str(last_message), "-"]


def valid_proposal(text: str) -> bool:
    headings = ("## Goal", "## Evidence", "## Proposed change",
                "## Acceptance checks", "## Risks and limits")
    text = text.lstrip()
    first = text.splitlines()[0].strip() if text.splitlines() else ""
    return first == "Decision: PROPOSE_CHANGE" and all(h in text for h in headings)


def validate_models(proposal_model: str, implementation_model: str) -> None:
    if not proposal_model.strip() or not implementation_model.strip():
        raise ValueError("both Codex model names are required")
    if proposal_model == implementation_model:
        raise ValueError("proposal and implementation stages must use different models")


def run(args: argparse.Namespace) -> int:
    codex = shutil.which(args.codex)
    if not codex:
        raise SystemExit(f"Codex CLI not found: {args.codex}")
    bwrap = shutil.which("bwrap")
    python = shutil.which("python3")
    if not bwrap or not python:
        raise SystemExit("A Linux bubblewrap sandbox and python3 are required for candidate checks")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = (args.output or ROOT / "runs/self-improvement").resolve() / stamp
    candidate = destination / "candidate"
    destination.mkdir(parents=True, exist_ok=False)
    stage_project(candidate)

    review = inspect(ROOT)
    report_text = markdown(review)
    (destination / "capability-review.md").write_text(report_text, encoding="utf-8")
    (candidate / "CAPABILITY_REVIEW.md").write_text(report_text, encoding="utf-8")

    init = subprocess.run(["git", "init", "-q", str(candidate)],
                          text=True, capture_output=True)
    if init.returncode:
        raise RuntimeError(f"Could not initialize candidate history: {init.stderr.strip()}")
    for command in (
        ["git", "-C", str(candidate), "add", "-A"],
        ["git", "-C", str(candidate), "-c", "user.name=Moss Candidate Harness",
         "-c", "user.email=moss-candidate@localhost", "commit", "-qm", "candidate baseline"],
    ):
        result = subprocess.run(command, text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(f"Could not prepare candidate history: {result.stderr.strip()}")

    task = args.task.strip() if args.task else (
        "Choose the smallest high-value change for the highest-priority capability gap in "
        "CAPABILITY_REVIEW.md. Keep the REA-derived genome brain as the base. Propose "
        "one bounded step that can be implemented and measured. Do not claim consciousness, "
        "native parity, or abilities that were not measured."
    )
    proposal_prompt = f"""You are the proposal reviewer for the Digital Creature Brain project.

Task: {task}

Read CAPABILITY_REVIEW.md, README.md, and docs/SELF_IMPROVEMENT.md. Do not edit
files or implement code. Return either `Decision: NO_CHANGE` with a short reason,
or `Decision: PROPOSE_CHANGE` followed by exactly these sections:

## Goal
## Evidence
## Proposed change
## Acceptance checks
## Risks and limits

Keep the proposal narrow, source-grounded, testable, and suitable for a separate
implementation model. Distinguish recovered behavior from host adaptations.
Do not claim consciousness, native parity, or unmeasured abilities. Do not
recommend unrestricted host access or edits to the live pet/checkpoint.
"""
    proposal_path = destination / "proposal.md"
    proposal_log = destination / "proposal.log"
    proposal_prompt_path = destination / "proposal-prompt.txt"
    proposal_prompt_path.write_text(proposal_prompt, encoding="utf-8")
    proposal_command = codex_command(codex, args.proposal_model, "read-only",
                                     candidate, proposal_path)
    with proposal_log.open("w", encoding="utf-8") as log:
        proposal_result = subprocess.run(
            proposal_command, input=proposal_prompt, text=True, stdout=log,
            stderr=subprocess.STDOUT, timeout=args.timeout, check=False, close_fds=True)

    proposal_text = proposal_path.read_text(encoding="utf-8") if proposal_path.is_file() else ""
    if proposal_result.returncode != 0 or not proposal_text:
        result_record = {
            "model": "two-model-growth-cycle-v1", "status": "proposal-failed",
            "proposal_model": args.proposal_model,
            "proposal_exit_code": proposal_result.returncode,
            "implementation_model": args.implementation_model,
            "implementation_status": "not-run",
            "proposal_path": str(proposal_path), "proposal_log_path": str(proposal_log),
            "candidate_path": str(candidate), "promoted": False,
        }
        (destination / "result.json").write_text(json.dumps(result_record, indent=2) + "\n",
                                                  encoding="utf-8")
        print(json.dumps(result_record, indent=2))
        return 1
    if proposal_text.splitlines()[0].strip() == "Decision: NO_CHANGE":
        result_record = {
            "model": "two-model-growth-cycle-v1", "status": "no-change-proposed",
            "proposal_model": args.proposal_model,
            "proposal_exit_code": proposal_result.returncode,
            "implementation_model": args.implementation_model,
            "implementation_status": "not-run",
            "proposal_path": str(proposal_path), "proposal_log_path": str(proposal_log),
            "candidate_path": str(candidate), "promoted": False,
        }
        (destination / "result.json").write_text(json.dumps(result_record, indent=2) + "\n",
                                                  encoding="utf-8")
        print(json.dumps(result_record, indent=2))
        return 0
    if not valid_proposal(proposal_text):
        result_record = {
            "model": "two-model-growth-cycle-v1", "status": "invalid-proposal",
            "proposal_model": args.proposal_model,
            "proposal_exit_code": proposal_result.returncode,
            "implementation_model": args.implementation_model,
            "implementation_status": "not-run",
            "proposal_path": str(proposal_path), "proposal_log_path": str(proposal_log),
            "candidate_path": str(candidate), "promoted": False,
        }
        (destination / "result.json").write_text(json.dumps(result_record, indent=2) + "\n",
                                                  encoding="utf-8")
        print(json.dumps(result_record, indent=2))
        return 1

    implementation_prompt = f"""You are the implementation model for the Digital Creature Brain project.

Implement the following proposal in this disposable candidate copy:

{proposal_text}

Read CAPABILITY_REVIEW.md, README.md, and docs/SELF_IMPROVEMENT.md first. Make
only the proposed change. Add focused regression tests and update documentation
where needed. Do not access files outside this working directory, the network,
credentials, or the live pet. Preserve existing behavior unless the proposal
requires a change. Do not update or replace any live process or checkpoint.
Run the focused checks you can, and report exactly what changed and what ran.
"""
    implementation_path = destination / "implementation-result.txt"
    implementation_log = destination / "implementation.log"
    implementation_prompt_path = destination / "implementation-prompt.txt"
    implementation_prompt_path.write_text(implementation_prompt, encoding="utf-8")
    implementation_command = codex_command(codex, args.implementation_model,
                                           "workspace-write", candidate,
                                           implementation_path)
    with implementation_log.open("w", encoding="utf-8") as log:
        implementation_result = subprocess.run(
            implementation_command, input=implementation_prompt, text=True,
            stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout,
            check=False, close_fds=True)

    subprocess.run(["git", "-C", str(candidate), "add", "-N", "."],
                   text=True, capture_output=True, check=False)
    diff = subprocess.run(["git", "-C", str(candidate), "diff", "--no-ext-diff",
                           "--no-color"], text=True, capture_output=True, check=False)
    (destination / "candidate.patch").write_text(diff.stdout, encoding="utf-8")
    status = subprocess.run(["git", "-C", str(candidate), "status", "--short"],
                            text=True, capture_output=True, check=False)

    native_genome = required_native_genome(candidate)
    sandbox = [bwrap, "--die-with-parent", "--unshare-net", "--unshare-pid", "--unshare-uts",
         "--unshare-ipc", "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
         "--ro-bind-try", "/lib64", "/lib64", "--ro-bind", "/etc", "/etc",
         "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
         "--bind", str(candidate), "/candidate", "--chdir", "/candidate",
         "--setenv", "HOME", "/candidate", "--setenv", "PATH", "/usr/bin:/bin",
         "--setenv", "PYTHONPATH", "/candidate/src"]
    if native_genome is None:
        checks = subprocess.CompletedProcess(
            args=sandbox, returncode=2, stdout="",
            stderr="Required installed-game genome fixture is unavailable; candidate tests not run.\n")
    else:
        for directory in reversed(native_genome.parents):
            if directory != Path("/"):
                sandbox.extend(["--dir", str(directory)])
        sandbox.extend(["--ro-bind", str(native_genome), str(native_genome), python,
                        "-m", "unittest", "discover", "-s", "tests"])
        checks = subprocess.run(
            sandbox, cwd=candidate, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=args.test_timeout, check=False,
            close_fds=True)
    (destination / "tests.log").write_text(checks.stdout, encoding="utf-8")
    result_record = {
        "model": "two-model-growth-cycle-v1",
        "status": "implemented-and-tested" if implementation_result.returncode == 0 and checks.returncode == 0 else "candidate-check-failed",
        "proposal_model": args.proposal_model,
        "proposal_exit_code": proposal_result.returncode,
        "implementation_model": args.implementation_model,
        "implementation_exit_code": implementation_result.returncode,
        "checks_exit_code": checks.returncode,
        "candidate_changed": bool(diff.stdout or status.stdout.strip()),
        "candidate_test_sandbox": "bubblewrap with network disabled, candidate writable, and only the digest-checked game genome mounted read-only",
        "candidate_path": str(candidate),
        "patch_path": str(destination / "candidate.patch"),
        "proposal_path": str(proposal_path),
        "proposal_log_path": str(proposal_log),
        "implementation_report_path": str(implementation_path),
        "implementation_log_path": str(implementation_log),
        "checks_log_path": str(destination / "tests.log"),
        "promoted": False,
    }
    (destination / "result.json").write_text(json.dumps(result_record, indent=2) + "\n",
                                              encoding="utf-8")
    print(json.dumps(result_record, indent=2))
    return 0 if implementation_result.returncode == 0 and checks.returncode == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", help="one focused improvement; otherwise choose from the review")
    parser.add_argument("--codex", default="codex", help="Codex CLI executable")
    parser.add_argument("--proposal-model", default=PROPOSAL_MODEL)
    parser.add_argument("--implementation-model", default=IMPLEMENTATION_MODEL)
    parser.add_argument("--output", type=Path, help="candidate output directory")
    parser.add_argument("--timeout", type=int, default=1200, help="Codex run timeout in seconds")
    parser.add_argument("--test-timeout", type=int, default=900, help="test timeout in seconds")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 3600 or not 1 <= args.test_timeout <= 3600:
        parser.error("timeouts must be between 1 and 3600 seconds")
    try:
        validate_models(args.proposal_model, args.implementation_model)
    except ValueError as error:
        parser.error(str(error))
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()
