"""Tests for real-world operation evidence program initialization."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_JSON = REPO_ROOT / "reports" / "operations" / "real_world_operation_evidence_index_v1.json"
DAY0_JSON = REPO_ROOT / "reports" / "operations" / "operation_day_000_initialization_v1.json"
PROGRAM_MD = REPO_ROOT / "docs" / "operations" / "real_world_operation_evidence_program_v1.md"
PROGRAM_STATUS = "REAL_WORLD_OPERATION_EVIDENCE_PROGRAM_INITIALIZED"


class RealWorldOperationEvidenceProgramV1Tests(unittest.TestCase):
    def test_operation_evidence_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/real_world_operation_evidence_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("real_world_operation_evidence_check_v1: PASS", completed.stdout)

    def test_index_records_initialization_without_completion_claim(self) -> None:
        index = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
        self.assertEqual(index["program_status"], PROGRAM_STATUS)
        self.assertEqual(index["current_day_count"], 0)
        self.assertFalse(index["minimum_window_satisfied"])
        self.assertFalse(index["stronger_window_satisfied"])
        self.assertFalse(index["global_recognition_claimed"])
        self.assertFalse(index["external_signoff_confirmed"])
        self.assertFalse(index["human_third_party_review"])
        self.assertEqual(index["current_evidence_counts"]["observation_days_recorded"], 0)

    def test_program_defines_required_future_evidence(self) -> None:
        index = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
        requirements = index["minimum_future_evidence_requirements"]
        self.assertEqual(requirements["real_seos_governed_tasks"], 10)
        self.assertEqual(requirements["real_prs_governed_by_seos"], 5)
        self.assertEqual(requirements["failure_or_exception_cases"], 3)
        self.assertEqual(requirements["rollback_or_recovery_drills"], 1)
        self.assertEqual(requirements["dependency_update_or_release_drills"], 1)
        self.assertTrue(requirements["repeated_verification_checks_over_time"])

    def test_day_000_records_only_real_current_run_prs(self) -> None:
        day0 = json.loads(DAY0_JSON.read_text(encoding="utf-8"))
        operations = {entry["operation_id"]: entry for entry in day0["real_operations_recorded_current_run"]}
        self.assertEqual(set(operations), {"OP-PR-549", "OP-PR-550", "OP-PR-551"})
        self.assertEqual(operations["OP-PR-549"]["merge_commit"], "71a9744b2e84595627222c82c8155d2e537977ed")
        self.assertEqual(operations["OP-PR-550"]["merge_commit"], "33032ef069830b4023bc994c722d86a087179268")
        self.assertEqual(operations["OP-PR-551"]["merge_commit"], "b7a0dce3f33d0ebb33ec8cacc97f1c4a3151f791")
        for entry in operations.values():
            self.assertIn("https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/", entry["pr_url"])
            self.assertIn("canonical-health passed", entry["validation_summary"])

    def test_program_document_contains_required_schemas_and_boundaries(self) -> None:
        text = PROGRAM_MD.read_text(encoding="utf-8")
        for term in (
            "Task Evidence Schema",
            "PR Evidence Schema",
            "Failure Evidence Schema",
            "Incident Evidence Schema",
            "Rollback/Recovery Drill Schema",
            "Dependency/Update Drill Schema",
            "Validation Command Schema",
            "Daily/Weekly Rollup Schema",
            "Stop Conditions",
            "Escalation Conditions",
            "Final Operation Evidence Report Requirements",
        ):
            self.assertIn(term, text)
        self.assertIn("Current day count at initialization: 0.", text)
        self.assertIn("External recognition is not confirmed by Codex.", text)
        self.assertIn("It does not satisfy the 30-day or 90-day observation windows.", text)

    def test_makefile_declares_operation_evidence_gate(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("operation-evidence-check:", makefile)
        self.assertIn("test-real-world-operation-evidence-program:", makefile)
        self.assertIn("scripts/real_world_operation_evidence_check_v1.py", makefile)
        self.assertIn("tests.tracer_bullet.test_real_world_operation_evidence_program_v1", makefile)


if __name__ == "__main__":
    unittest.main()
