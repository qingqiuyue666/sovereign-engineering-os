"""Tests for Wave 8 reliability and operational stability evidence."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = REPO_ROOT / "reports" / "reliability" / "reliability_benchmark_v1.json"


class OperationalStabilityV1Tests(unittest.TestCase):
    def test_reliability_benchmark_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/reliability_benchmark_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("reliability_benchmark_v1: PASS", completed.stdout)
        self.assertIn("elapsed_seconds=", completed.stdout)
        self.assertIn("flake_rate=0.000000", completed.stdout)

    def test_reliability_report_records_required_targets(self) -> None:
        payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "reliability_benchmark_v1")
        self.assertTrue(payload["external_review_required"])
        self.assertFalse(payload["global_recognition_claimed"])
        self.assertFalse(payload["runtime_expansion_performed"])
        self.assertFalse(payload["network_accessed"])
        self.assertFalse(payload["secret_value_read"])
        self.assertEqual(payload["targets"]["repeated_smoke_loop"], 50)
        self.assertEqual(payload["targets"]["multi_task_batch"], 20)
        self.assertEqual(payload["targets"]["multi_workspace_checks"], 3)
        self.assertEqual(payload["targets"]["approval_reject_run_mixed_flow"], 20)
        self.assertEqual(payload["targets"]["evidence_replay_batch_validation"], 20)
        self.assertEqual(payload["targets"]["failure_path_batch_validation"], 10)
        for result in payload["results"].values():
            self.assertEqual(result["target"], result["completed"])
            self.assertEqual(result["failures"], 0)
        self.assertEqual(payload["flake_rate_recording"]["sample_count"], 123)
        self.assertEqual(payload["flake_rate_recording"]["observed_flake_rate"], 0.0)

    def test_benchmark_does_not_rewrite_tracked_report(self) -> None:
        before = REPORT_PATH.read_text(encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "scripts/reliability_benchmark_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        after = REPORT_PATH.read_text(encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(before, after)

    def test_operations_docs_define_response_boundaries(self) -> None:
        required = {
            "incident_response_v1.md": ("severity", "triage", "containment", "evidence preservation"),
            "rollback_runbook_v1.md": ("rollback trigger", "safe rollback", "no force push"),
            "maintenance_policy_v1.md": ("maintenance window", "dependency review", "validation gate"),
            "workspace_cleanup_policy_v1.md": ("workspace cleanup", "secret material", "git status --short"),
            "interrupted_run_policy_v1.md": ("interrupted run", "resume", "idempotent", "do not invent"),
        }
        operations_root = REPO_ROOT / "docs" / "operations"
        for filename, terms in required.items():
            text = (operations_root / filename).read_text(encoding="utf-8").lower()
            for term in terms:
                self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
