"""Tests for Wave 1 public identity and boundary evidence."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = (
    Path("README.md"),
    Path("docs/identity/system_identity_v1.md"),
    Path("docs/identity/non_goals_v1.md"),
    Path("SECURITY.md"),
    Path("CHANGELOG.md"),
    Path("docs/quickstart/local_first_quickstart_v1.md"),
    Path("docs/architecture/seos_control_plane_v1.md"),
    Path("examples/README.md"),
    Path("scripts/identity_boundary_check_v1.py"),
    Path("tests/tracer_bullet/test_identity_boundary_v1.py"),
)

STATUS_ANCHORS = (
    "SYSTEM_LANDED",
    "REAL_OPERATION_OBSERVATION_PERIOD_ACTIVE",
    "LOCAL_REAL_USE_VALIDATED",
    "APPROVAL_GATE_VALIDATED",
    "CLEAN_CLONE_VALIDATED",
    "NO_HARD_EVIDENCE_BLOCKER_RECORDED",
)

NON_GOAL_PHRASES = (
    "not an OS-level sandbox",
    "not RPA",
    "not a computer-control framework",
    "not an autonomous AI executor",
    "not a commercial SaaS platform",
    "not a secret manager",
)

STALE_MARKERS = (
    "Current phase/state: Personal AI Execution OS final product-completion",
    "Current phase: Personal AI Execution OS final product-completion candidate",
    "FINAL_PRODUCT_COMPLETION_READY_FOR_REVIEW",
)


def _read(relative_path: Path) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class IdentityBoundaryV1Tests(unittest.TestCase):
    def test_required_wave_1_files_exist(self) -> None:
        for relative_path in REQUIRED_FILES:
            self.assertTrue(
                (REPO_ROOT / relative_path).exists(),
                f"missing {relative_path.as_posix()}",
            )

    def test_identity_boundary_check_script_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/identity_boundary_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        self.assertIn("identity_boundary_check_v1: PASS", completed.stdout)

    def test_readme_records_current_status_without_stale_state(self) -> None:
        readme = _read(Path("README.md"))
        for anchor in STATUS_ANCHORS:
            self.assertIn(anchor, readme)
        for phrase in NON_GOAL_PHRASES:
            self.assertIn(phrase, readme)
        for marker in STALE_MARKERS:
            self.assertNotIn(marker, readme)

    def test_current_phase_records_observation_mode(self) -> None:
        text = _read(Path("docs/current_phase.md"))
        self.assertIn("REAL_OPERATION_OBSERVATION_PERIOD_ACTIVE", text)
        self.assertIn("v0.1.0-rc3", text)
        self.assertIn("external recognition claim", text)
        for marker in STALE_MARKERS:
            self.assertNotIn(marker, text)

    def test_identity_docs_map_claims_to_evidence(self) -> None:
        for relative_path in (
            Path("docs/identity/system_identity_v1.md"),
            Path("docs/identity/non_goals_v1.md"),
            Path("docs/quickstart/local_first_quickstart_v1.md"),
            Path("docs/architecture/seos_control_plane_v1.md"),
            Path("examples/README.md"),
        ):
            text = _read(relative_path)
            for term in (
                "Claim",
                "Risk",
                "Control",
                "Implementation",
                "Validation command",
                "Gate",
                "Evidence artifact",
                "Residual risk",
            ):
                self.assertIn(term, text, relative_path.as_posix())

    def test_no_local_absolute_path_leaks_in_public_docs(self) -> None:
        forbidden_markers = (
            "/" + "Users" + "/" + "qqy",
            "Documents" + "/" + "Codex",
            "." + "codex",
            "files-mentioned" + "-by-the-user",
        )
        for relative_path in REQUIRED_FILES:
            text = _read(relative_path)
            for marker in forbidden_markers:
                self.assertNotIn(marker, text, relative_path.as_posix())


if __name__ == "__main__":
    unittest.main()
