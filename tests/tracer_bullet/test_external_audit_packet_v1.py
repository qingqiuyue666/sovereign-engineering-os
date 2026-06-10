"""Tests for Wave 9 external audit packet."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKET_JSON = REPO_ROOT / "reports" / "audits" / "external_audit_packet_v1.json"
PACKET_MD = REPO_ROOT / "docs" / "audits" / "external_audit_packet_v1.md"
FINAL_VERDICT = "GLOBAL_RECOGNITION_READINESS_READY_FOR_EXTERNAL_REVIEW"


class ExternalAuditPacketV1Tests(unittest.TestCase):
    def test_external_audit_packet_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/external_audit_packet_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("external_audit_packet_check_v1: PASS", completed.stdout)

    def test_packet_contains_required_final_verdict_and_caveats(self) -> None:
        payload = json.loads(PACKET_JSON.read_text(encoding="utf-8"))
        markdown = PACKET_MD.read_text(encoding="utf-8")
        self.assertEqual(payload["final_verdict"], FINAL_VERDICT)
        self.assertIn(FINAL_VERDICT, markdown)
        self.assertFalse(payload["global_recognition_claimed"])
        self.assertFalse(payload["external_recognition_confirmed"])
        self.assertTrue(payload["external_verification_required"])
        self.assertFalse(payload["codex_self_certifying_final_signoff"])
        for statement in (
            "External recognition has not yet been confirmed.",
            "External verification is still required.",
            "Real-world 30-90 day operation evidence is still required for global recognition.",
            "Codex is not self-certifying final signoff.",
        ):
            self.assertIn(statement, payload["explicit_statements"])
            self.assertIn(statement, markdown)

    def test_packet_lists_all_wave_prs(self) -> None:
        payload = json.loads(PACKET_JSON.read_text(encoding="utf-8"))
        wave_prs = {entry["wave"]: entry for entry in payload["wave_prs"]}
        self.assertEqual(set(wave_prs), set(range(1, 10)))
        for wave, pr_number in {
            1: 540,
            2: 541,
            3: 542,
            4: 543,
            5: 544,
            6: 545,
            7: 546,
            8: 547,
            9: 548,
        }.items():
            self.assertEqual(wave_prs[wave]["pr_number"], pr_number)
            self.assertIn(f"/pull/{pr_number}", wave_prs[wave]["pr_url"])

    def test_risk_and_blocker_reports_keep_external_review_boundary(self) -> None:
        accepted = json.loads((REPO_ROOT / "reports" / "audits" / "accepted_risk_register_v1.json").read_text(encoding="utf-8"))
        residual = json.loads((REPO_ROOT / "reports" / "audits" / "residual_risk_register_v1.json").read_text(encoding="utf-8"))
        blockers = json.loads((REPO_ROOT / "reports" / "audits" / "final_blocker_table_v1.json").read_text(encoding="utf-8"))
        self.assertTrue(accepted["external_review_required"])
        self.assertTrue(residual["external_review_required"])
        self.assertEqual(blockers["final_verdict"], FINAL_VERDICT)
        self.assertEqual(blockers["blockers_for_external_review_packet"], [])
        self.assertGreaterEqual(len(blockers["blockers_for_final_recognition_analysis"]), 3)
        for risk in accepted["risks"]:
            self.assertTrue(risk["not_accepted_for_final_recognition"])
        for risk in residual["risks"]:
            self.assertEqual(risk["status"], "open_for_external_review")


if __name__ == "__main__":
    unittest.main()
