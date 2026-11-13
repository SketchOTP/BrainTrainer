"""Evidence-linked capability inventory for the creature research simulator.

This is an inventory of what the implementation can currently demonstrate,
not an assertion that the creature is conscious or biologically alive. A source
or test file being present is not reported as a test having passed.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Capability:
    key: str
    name: str
    maturity: str
    owns: tuple[str, ...]
    source: tuple[str, ...]
    tests: tuple[str, ...]
    evidence: tuple[str, ...]
    next_gap: str


CAPABILITIES = (
    Capability(
        "reconstructed_brain", "REA-derived genome brain", "modelled",
        ("15-lobe / 29-tract controller", "genome-defined neurons, instincts, and decision output"),
        ("src/creature_brain/neural.py",),
        ("tests/test_neural.py",),
        ("research/docking-station-20261103/resources/chichi-brain-program.json",
         "research/docking-station-20261103/full-creature-native/findings.json"),
        "Qualify additional native pathways and held-out behavior against the installed game.",
    ),
    Capability(
        "genome_body", "Genome-driven body and biochemistry", "modelled",
        ("gene-expressed reactions", "needs, sleep, injury, repair, and energy"),
        ("src/creature_brain/genome_physiology.py", "src/creature_brain/biochemistry.py"),
        ("tests/test_genome_physiology.py", "tests/test_biochemistry.py"),
        ("genome_physiology_receipt.json", "docs/CALIBRATION.md"),
        "Extend developmental stages and compare more interventions against native runtime traces.",
    ),
    Capability(
        "experience", "Memory and learning from outcomes", "partial",
        ("bounded episodes and associations", "host-side learned recall and aversion cues"),
        ("src/creature_brain/experience.py", "src/creature_brain/simulation.py"),
        ("tests/test_experience.py", "tests/test_experience_simulation.py"),
        ("docs/FULL_CREATURE.md",),
        "Measure retained knowledge, reversal, transfer, and forgetting on blinded trials.",
    ),
    Capability(
        "perception", "World perception and action", "partial",
        ("simulated objects, needs, locomotion, and action consequences", "experimental rendered object pixels"),
        ("src/creature_brain/world.py", "src/creature_brain/vision.py"),
        ("tests/test_world.py", "tests/test_interactive_world.py", "tests/test_experience.py"),
        ("docs/FULL_CREATURE.md",),
        "Replace hand-authored cues and isolated object crops with sensor evidence from a simpler body/world.",
    ),
    Capability(
        "self_model", "Self-knowledge and capability review", "partial",
        ("this source-linked inventory", "existing physiology and memory summaries"),
        ("src/creature_brain/self_review.py", "src/creature_brain/simulation.py"),
        ("tests/test_self_review.py",),
        ("docs/SELF_IMPROVEMENT.md",),
        "Track measured competence, uncertainty, failed attempts, and change history in each saved creature.",
    ),
    Capability(
        "self_directed_learning", "Choosing what to learn next", "missing",
        (), (), (), (),
        "Build curiosity around uncertainty and information gain, then evaluate without teacher goals.",
    ),
    Capability(
        "code_growth", "Writing and updating its own implementation", "partial",
        ("external Codex CLI candidate harness", "isolated candidate edits and test runs; explicit promotion"),
        ("scripts/self_improve.py",),
        ("tests/test_self_improve.py",),
        ("docs/SELF_IMPROVEMENT.md",),
        "Add held-out ability evaluations and durable review of candidate changes; the creature itself does not author code.",
    ),
    Capability(
        "development", "Long-term development and new abilities", "missing",
        (), (), (), (),
        "Add persistent developmental stages and new abilities with inherited, testable state transitions.",
    ),
)


def inspect(root: Path, capabilities: Iterable[Capability] = CAPABILITIES) -> dict:
    """Check references and expose declared maturity without claiming execution."""
    root = root.resolve()
    rows = []
    for item in capabilities:
        record = asdict(item)
        for field in ("owns", "source", "tests", "evidence"):
            record[field] = list(record[field])
        record["references"] = {
            field: [
                {"path": value, "exists": (root / value).is_file()}
                for value in record[field]
            ]
            for field in ("source", "tests", "evidence")
        }
        record["missing_references"] = [
            ref["path"]
            for refs in record["references"].values()
            for ref in refs if not ref["exists"]
        ]
        rows.append(record)
    return {
        "model": "creature-capability-review-v1",
        "scope": "source inventory; referenced checks are not executed by this command",
        "capabilities": rows,
        "gaps": [
            {"key": row["key"], "name": row["name"], "next_gap": row["next_gap"]}
            for row in rows if row["maturity"] != "modelled" or row["missing_references"]
        ],
    }


def verify(root: Path, report: dict, timeout: float = 60.0) -> dict:
    """Execute distinct linked local unittest files separately from evidence references."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    root = root.resolve()
    checks = []
    for path in dict.fromkeys(p for row in report["capabilities"] for p in row["tests"]):
        started = time.monotonic()
        check = {"path": path, "status": "error", "returncode": None, "stdout": "", "stderr": ""}
        try:
            relative = Path(path)
            target = (root / relative).resolve()
            if (relative.is_absolute() or ".." in relative.parts
                    or not target.is_relative_to(root / "tests")
                    or not re.fullmatch(r"test_[A-Za-z0-9_]+\.py", target.name)
                    or not target.is_file()):
                raise ValueError("expected an existing local tests/test_*.py file")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(root / "src")
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", str(target.parent),
                 "-p", target.name, "-v"], cwd=root, env=env,
                capture_output=True, text=True, timeout=timeout)
            check.update(status="passed" if result.returncode == 0 else "failed",
                         returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        except subprocess.TimeoutExpired as exc:
            def decoded(value):
                return value.decode(errors="replace") if isinstance(value, bytes) else value or ""
            check.update(status="timeout", stdout=decoded(exc.stdout), stderr=decoded(exc.stderr))
        except (OSError, ValueError) as exc:
            check["stderr"] = str(exc)
        check["elapsed_seconds"] = time.monotonic() - started
        checks.append(check)
    report["verified_checks"] = checks
    report["verification_summary"] = {
        "passed": sum(check["status"] == "passed" for check in checks),
        "failed": sum(check["status"] == "failed" for check in checks),
        "timed_out": sum(check["status"] == "timeout" for check in checks),
        "errored": sum(check["status"] == "error" for check in checks),
        "total_elapsed_seconds": float(sum(check["elapsed_seconds"] for check in checks)),
    }
    report["verification_timeout_seconds"] = timeout
    report["scope"] = "source inventory with explicit local unittest verification; not a competence evaluation"
    return report


def markdown(report: dict) -> str:
    lines = ["# Moss capability review", "",
             "This source inventory does not claim consciousness, life, or general intelligence.",
             "It checks that declared evidence paths exist; it does not run those tests.", "",
             "## Current capabilities", "", "| Area | Status | What exists | Evidence references |",
             "|---|---|---|---|"]
    for row in report["capabilities"]:
        details = "; ".join(row["owns"]) or "No implementation recorded"
        refs = row["source"] + row["tests"] + row["evidence"]
        evidence = ", ".join(f"`{p}`" for p in refs) or "None recorded"
        missing = row["missing_references"]
        if missing:
            evidence += " (missing: " + ", ".join(f"`{p}`" for p in missing) + ")"
        lines.append(f"| {row['name']} | {row['maturity']} | {details} | {evidence} |")
    if "verified_checks" in report:
        lines[3] = "Evidence references record file presence; explicit unittest results appear separately below."
        lines += ["", "## Verified checks", ""]
        summary = report["verification_summary"]
        lines.append("Summary: " + ", ".join(
            f"{field} {summary[field]}" for field in ("passed", "failed", "timed_out", "errored")
        ) + f", total elapsed {summary['total_elapsed_seconds']:.3f}s")
        for check in report["verified_checks"]:
            lines.append(f"- `{check['path']}`: **{check['status']}**, "
                         f"{check['elapsed_seconds']:.3f}s (exit {check['returncode']})")
            for stream in ("stdout", "stderr"):
                if check[stream]:
                    lines.append(f"  {stream}:")
                    lines.extend("    " + line for line in check[stream].splitlines())
        if not report["verified_checks"]:
            lines.append("No linked test files to verify.")
    lines += ["", "## Highest-priority gaps", ""]
    for gap in report["gaps"]:
        lines.append(f"- **{gap['name']}** — {gap['next_gap']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2],
                        help="creature project root")
    parser.add_argument("--json", action="store_true", help="print machine-readable review")
    parser.add_argument("--output", type=Path, help="write the review to a file")
    parser.add_argument("--verify", action="store_true", help="execute linked local unittest files")
    parser.add_argument("--timeout", type=float, default=60.0,
                        help="positive timeout in seconds per file (default: 60)")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")
    report = inspect(args.root)
    if args.verify:
        verify(args.root, report, args.timeout)
    rendered = json.dumps(report, indent=2) + "\n" if args.json else markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.verify and any(c["status"] != "passed" for c in report["verified_checks"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
