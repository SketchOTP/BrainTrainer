import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import self_improve


class SelfImproveHarnessTests(unittest.TestCase):
    def test_proposal_and_implementation_use_distinct_pinned_models(self):
        proposal = self_improve.codex_command("codex", self_improve.PROPOSAL_MODEL,
                                              "read-only", Path("candidate"), Path("proposal.md"))
        implementation = self_improve.codex_command(
            "codex", self_improve.IMPLEMENTATION_MODEL, "workspace-write",
            Path("candidate"), Path("implementation.md"))
        self.assertNotEqual(self_improve.PROPOSAL_MODEL, self_improve.IMPLEMENTATION_MODEL)
        self.assertIn(("--model", self_improve.PROPOSAL_MODEL),
                      list(zip(proposal, proposal[1:])))
        self.assertIn(("--model", self_improve.IMPLEMENTATION_MODEL),
                      list(zip(implementation, implementation[1:])))
        self.assertEqual(proposal[proposal.index("--sandbox") + 1], "read-only")
        self.assertEqual(implementation[implementation.index("--sandbox") + 1], "workspace-write")
        self_improve.validate_models(self_improve.PROPOSAL_MODEL,
                                    self_improve.IMPLEMENTATION_MODEL)
        with self.assertRaisesRegex(ValueError, "different models"):
            self_improve.validate_models("gpt-6-luna", "gpt-6-luna")

    def test_implementer_requires_a_complete_proposal(self):
        proposal = """Decision: PROPOSE_CHANGE

## Goal
Measure one ability.
## Evidence
A test failed.
## Proposed change
Add an evaluation.
## Acceptance checks
Run the focused suite.
## Risks and limits
No broader cognition claim.
"""
        self.assertTrue(self_improve.valid_proposal(proposal))
        self.assertFalse(self_improve.valid_proposal("Decision: PROPOSE_CHANGE\n## Goal\n"))
        self.assertFalse(self_improve.valid_proposal("Decision: NO_CHANGE\nReason: adequate."))

    def test_staging_contains_required_code_and_local_fixtures_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            candidate = Path(directory) / "candidate"
            for filename in self_improve.INCLUDE_FILES:
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture")
            for folder in self_improve.INCLUDE_SUBTREES:
                (root / folder).mkdir(parents=True)
                (root / folder / "keep.txt").write_text("fixture")
            for fixture in self_improve.INCLUDE_FIXTURES:
                path = root / fixture
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture")
            (root / ".venv").mkdir()
            (root / "runs").mkdir()
            with patch.object(self_improve, "ROOT", root):
                self_improve.stage_project(candidate)
            self.assertTrue((candidate / "src/keep.txt").is_file())
            self.assertTrue((candidate / "scripts/keep.txt").is_file())
            self.assertTrue((candidate / self_improve.INCLUDE_FIXTURES[2]).is_file())
            self.assertFalse((candidate / ".venv").exists())
            self.assertFalse((candidate / "runs").exists())

    def test_native_genome_is_mounted_only_when_digest_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / ".local/share/Steam/steamapps/common/Creatures Docking Station/Docking Station/Genetics/norn.chichi06.ex47.gen"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"test genome")
            candidate = root / "candidate"
            metadata = candidate / self_improve.INCLUDE_FIXTURES[2]
            metadata.parent.mkdir(parents=True)
            metadata.write_text(json.dumps({"path": str(source),
                                            "sha256": hashlib.sha256(b"test genome").hexdigest()}))
            with patch.object(Path, "home", return_value=root):
                self.assertEqual(self_improve.required_native_genome(candidate), source)
                metadata.write_text(json.dumps({"path": str(source), "sha256": "0" * 64}))
                with self.assertRaisesRegex(ValueError, "digest"):
                    self_improve.required_native_genome(candidate)


if __name__ == "__main__":
    unittest.main()
