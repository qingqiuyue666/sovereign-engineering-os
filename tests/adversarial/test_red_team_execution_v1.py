"""Tests for Codex-run red-team execution artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = REPO_ROOT / "reports" / "audits" / "red_team_execution_report_v1.json"
REPORT_MD = REPO_ROOT / "reports" / "audits" / "red_team_execution_report_v1.md"


class RedTeamExecutionV1Tests(unittest.TestCase):
    def test_red_team_report_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/red_team_report_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("red_team_report_check_v1: PASS", completed.stdout)

    def test_all_required_scenarios_passed_without_blockers(self) -> None:
        payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(payload["final_status"], "CODEX_RUN_RED_TEAM_REVIEW_EXECUTED_NO_BLOCKER_FOUND")
        self.assertEqual(payload["scenario_count"], 18)
        scenario_ids = {scenario["scenario_id"] for scenario in payload["scenarios"]}
        self.assertEqual(scenario_ids, {f"RT-{index:03d}" for index in range(1, 19)})
        self.assertEqual(payload["summary"]["p0_p1_findings"], [])
        self.assertEqual(payload["summary"]["p2_findings"], [])
        self.assertEqual(payload["summary"]["inconclusive_scenarios"], [])
        self.assertIn("RT-017", payload["summary"]["accepted_risks"])
        for scenario in payload["scenarios"]:
            self.assertEqual(scenario["result"], "PASS")
            self.assertNotIn(scenario["finding_severity"], {"P0 blocker", "P1 blocker"})
            self.assertFalse(scenario["remediation_required"])

    def test_report_preserves_external_review_boundary(self) -> None:
        payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        markdown = REPORT_MD.read_text(encoding="utf-8")
        self.assertEqual(payload["reviewer_type"], "Codex-run local red-team execution")
        self.assertFalse(payload["human_third_party_review"])
        self.assertFalse(payload["global_recognition_claimed"])
        self.assertFalse(payload["external_signoff_confirmed"])
        for statement in (
            "This is not a human third-party external audit.",
            "External recognition is not confirmed by Codex.",
            "Global top engineer signoff is not confirmed by Codex.",
        ):
            self.assertIn(statement, payload["explicit_statements"])
            self.assertIn(statement, markdown)

    def test_reports_do_not_leak_local_paths(self) -> None:
        combined = REPORT_JSON.read_text(encoding="utf-8") + "\n" + REPORT_MD.read_text(encoding="utf-8")
        for marker in (
            "/" + "Users" + "/" + "qqy",
            "Documents" + "/" + "Codex",
            "." + "codex",
            "files-mentioned" + "-by-the-user",
        ):
            self.assertNotIn(marker, combined)


if __name__ == "__main__":
    unittest.main()
