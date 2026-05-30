"""Tests for Codex-run findings remediation closure artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTER_JSON = REPO_ROOT / "reports" / "audits" / "findings_register_v1.json"
LOG_JSON = REPO_ROOT / "reports" / "audits" / "findings_remediation_log_v1.json"
REGISTER_MD = REPO_ROOT / "reports" / "audits" / "findings_register_v1.md"
FINAL_STATUS = "FINDINGS_REMEDIATION_CLOSED_FOR_CODEX_RUN_VERIFICATION"


class FindingsRegisterV1Tests(unittest.TestCase):
    def test_findings_register_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/findings_register_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("findings_register_check_v1: PASS", completed.stdout)

    def test_register_records_supported_closure_only(self) -> None:
        register = json.loads(REGISTER_JSON.read_text(encoding="utf-8"))
        self.assertEqual(register["summary"]["terminal_status"], FINAL_STATUS)
        self.assertFalse(register["human_third_party_review"])
        self.assertFalse(register["external_signoff_confirmed"])
        self.assertFalse(register["global_recognition_claimed"])
        self.assertEqual(register["summary"]["p0_p1_open"], [])
        self.assertEqual(register["summary"]["p2_open"], [])
        self.assertEqual(register["summary"]["deferred_requires_human"], [])
        self.assertEqual(register["summary"]["accepted_risks"], ["FND-RT-017"])

    def test_source_reports_support_register_counts(self) -> None:
        register = json.loads(REGISTER_JSON.read_text(encoding="utf-8"))
        independent = json.loads(
            (REPO_ROOT / "reports" / "audits" / "independent_verification_execution_v1.json").read_text(
                encoding="utf-8"
            )
        )
        red_team = json.loads(
            (REPO_ROOT / "reports" / "audits" / "red_team_execution_report_v1.json").read_text(
                encoding="utf-8"
            )
        )
        reports = {entry["source"]: entry for entry in register["source_reports"]}
        self.assertEqual(independent["findings"], [])
        self.assertEqual(reports["independent_verification"]["findings_count"], 0)
        self.assertEqual(red_team["summary"]["p0_p1_findings"], [])
        self.assertEqual(red_team["summary"]["p2_findings"], [])
        self.assertEqual(red_team["summary"]["inconclusive_scenarios"], [])
        self.assertEqual(red_team["summary"]["accepted_risks"], ["RT-017"])
        self.assertEqual(reports["red_team_execution"]["accepted_risk_ids"], ["RT-017"])

    def test_remediation_log_does_not_invent_repair_prs(self) -> None:
        log = json.loads(LOG_JSON.read_text(encoding="utf-8"))
        self.assertEqual(log["terminal_status"], FINAL_STATUS)
        self.assertFalse(log["fixes_required"])
        self.assertEqual(log["minimal_repair_prs_created"], [])
        self.assertEqual({entry["finding_id"] for entry in log["entries"]}, {"FND-IV-001", "FND-RT-001", "FND-RT-017"})

    def test_markdown_keeps_external_review_boundary(self) -> None:
        markdown = REGISTER_MD.read_text(encoding="utf-8")
        self.assertIn("External recognition is not confirmed by Codex.", markdown)
        self.assertIn("Global top engineer signoff is not confirmed by Codex.", markdown)
        self.assertIn("Human or independent external review remains required.", markdown)
        self.assertIn("This register does not claim that future external, human, or long-duration", markdown)

    def test_makefile_declares_findings_gate(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("findings-check:", makefile)
        self.assertIn("test-findings-register:", makefile)
        self.assertIn("scripts/findings_register_check_v1.py", makefile)
        self.assertIn("tests.tracer_bullet.test_findings_register_v1", makefile)


if __name__ == "__main__":
    unittest.main()
