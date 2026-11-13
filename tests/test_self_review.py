import tempfile
import contextlib
import io
import unittest
import subprocess
from unittest.mock import patch
from pathlib import Path

from creature_brain.self_review import Capability, inspect, markdown, verify, main


class CapabilityReviewTests(unittest.TestCase):
    def test_review_distinguishes_source_tests_and_missing_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src/brain.py").write_text("brain")
            capability = Capability(
                "brain", "Brain", "modelled", ("decision output",),
                ("src/brain.py",), ("tests/test_brain.py",), (), "compare native traces")
            report = inspect(root, [capability])
        row = report["capabilities"][0]
        self.assertTrue(row["references"]["source"][0]["exists"])
        self.assertFalse(row["references"]["tests"][0]["exists"])
        self.assertEqual(row["missing_references"], ["tests/test_brain.py"])
        self.assertIn("brain", [gap["key"] for gap in report["gaps"]])

    def test_verification_is_explicit_and_records_real_results(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            for name, body in (("pass", "self.assertTrue(True)"),
                               ("fail", "self.fail('deliberate failure')")):
                (root / f"tests/test_{name}.py").write_text(
                    "import unittest\nclass Check(unittest.TestCase):\n"
                    f"    def test_check(self): {body}\n")
            capability = Capability("x", "X", "partial", (), (),
                                    ("tests/test_pass.py", "tests/test_fail.py", "tests/test_pass.py"),
                                    (), "gap")
            with patch("creature_brain.self_review.subprocess.run") as run:
                report = inspect(root, [capability])
                run.assert_not_called()
            self.assertNotIn("verified_checks", report)
            verify(root, report)
            checks = report["verified_checks"]
            self.assertEqual([c["status"] for c in checks], ["passed", "failed"])
            self.assertEqual([c["returncode"] for c in checks], [0, 1])
            self.assertTrue(all(c["elapsed_seconds"] >= 0 for c in checks))
            self.assertIn("deliberate failure", checks[1]["stderr"])
            self.assertIn("## Verified checks", markdown(report))
            self.assertTrue(report["capabilities"][0]["references"]["tests"][0]["exists"])

    def test_timeout_error_and_unsafe_links_are_reported(self):
        root = Path(__file__).resolve().parents[1]
        paths = ("tests/test_self_review.py", "tests/missing.py", "../test_escape.py",
                 str(root / "tests/test_self_review.py"), "src/creature_brain/self_review.py")
        capability = Capability("x", "X", "partial", (), (), paths, (), "gap")
        with patch("creature_brain.self_review.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("unittest", 0.01, stderr=b"partial")) as run:
            report = verify(root, inspect(root, [capability]), 0.01)
        self.assertEqual(run.call_count, 1)
        self.assertEqual([c["status"] for c in report["verified_checks"]],
                         ["timeout", "error", "error", "error", "error"])
        self.assertEqual(report["verification_summary"]["errored"], 4)
        self.assertEqual(report["verification_summary"]["timed_out"], 1)
        self.assertEqual(report["verified_checks"][0]["stderr"], "partial")
        with patch("creature_brain.self_review.subprocess.run", side_effect=OSError("launch failed")):
            report = verify(root, inspect(root, [capability]))
        self.assertIn("launch failed", report["verified_checks"][0]["stderr"])
        for timeout in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                verify(root, report, timeout)

    def test_summary_counts_outcomes_once_and_sums_elapsed_time(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            paths = tuple(f"tests/test_{name}.py" for name in
                          ("pass", "fail", "timeout", "error", "pass"))
            for path in set(paths):
                (root / path).write_text("# placeholder\n")
            capability = Capability("x", "X", "partial", (), (), paths, (), "gap")
            results = [subprocess.CompletedProcess([], 0, "", ""),
                       subprocess.CompletedProcess([], 2, "", "failure"),
                       subprocess.TimeoutExpired([], 1), OSError("launch failed")]
            ticks = iter([0, 1, 4, 5, 8, 9, 12, 14])
            with patch("creature_brain.self_review.subprocess.run", side_effect=results) as run, \
                    patch("creature_brain.self_review.time.monotonic",
                          side_effect=lambda: next(ticks) / 4):
                report = verify(root, inspect(root, [capability]))
        self.assertEqual(run.call_count, 4)
        self.assertEqual(report["verification_summary"], {
            "passed": 1, "failed": 1, "timed_out": 1, "errored": 1,
            "total_elapsed_seconds": 1.25,
        })
        rendered = markdown(report)
        self.assertIn("Summary: passed 1, failed 1, timed_out 1, errored 1", rendered)
        self.assertIn("tests/test_fail.py", rendered)
        self.assertIn("failure", rendered)

    def test_empty_verification_has_zero_summary_and_inventory_omits_it(self):
        root = Path(__file__).resolve().parents[1]
        capability = Capability("x", "X", "partial", (), (), (), (), "gap")
        inventory = inspect(root, [capability])
        with patch("creature_brain.self_review.subprocess.run") as run:
            self.assertNotIn("verification_summary", inventory)
            run.assert_not_called()
            report = verify(root, inventory)
        run.assert_not_called()
        self.assertEqual(report["verification_summary"], {
            "passed": 0, "failed": 0, "timed_out": 0, "errored": 0,
            "total_elapsed_seconds": 0.0,
        })
        self.assertIn("No linked test files", markdown(report))

    def test_cli_failure_exit_and_json_output(self):
        with patch("sys.argv", ["self_review", "--verify", "--json"]), patch(
                "creature_brain.self_review.verify") as run, contextlib.redirect_stdout(io.StringIO()) as output:
            def failed(root, report, timeout):
                report["verified_checks"] = [{"status": "failed"}]
            run.side_effect = failed
            with self.assertRaises(SystemExit) as exit_status:
                main()
            self.assertEqual(exit_status.exception.code, 1)
            self.assertIn('"verified_checks"', output.getvalue())

    def test_default_review_names_learning_gap_and_candidate_harness(self):
        from creature_brain.self_review import CAPABILITIES
        report = inspect(Path(__file__).resolve().parents[1], CAPABILITIES)
        by_key = {row["key"]: row for row in report["capabilities"]}
        self.assertEqual(by_key["code_growth"]["maturity"], "partial")
        self.assertEqual(by_key["self_directed_learning"]["maturity"], "missing")
        self.assertIn("does not run", markdown(report))


if __name__ == "__main__":
    unittest.main()
