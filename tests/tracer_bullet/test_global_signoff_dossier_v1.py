"""Tests for the global signoff candidate dossier foundation."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOSSIER_JSON = REPO_ROOT / "reports" / "audits" / "global_top_engineer_signoff_dossier_v1.json"
DOSSIER_MD = REPO_ROOT / "docs" / "audits" / "global_top_engineer_signoff_dossier_v1.md"
FINAL_VERDICT = "GLOBAL_TOP_ENGINEER_SIGNOFF_CANDIDATE_FOUNDATION_READY"


class GlobalSignoffDossierV1Tests(unittest.TestCase):
    def test_global_signoff_dossier_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/global_signoff_dossier_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("global_signoff_dossier_check_v1: PASS", completed.stdout)

    def test_dossier_records_candidate_verdict_only(self) -> None:
        payload = json.loads(DOSSIER_JSON.read_text(encoding="utf-8"))
        self.assertEqual(payload["final_verdict"], FINAL_VERDICT)
        self.assertFalse(payload["global_recognition_confirmed"])
        self.assertFalse(payload["human_external_signoff_confirmed"])
        self.assertFalse(payload["codex_self_certifying_final_signoff"])
        self.assertFalse(payload["human_third_party_review_completed"])
        self.assertFalse(payload["thirty_to_ninety_day_operation_completed"])
        self.assertTrue(payload["conditions_for_candidate_foundation"]["codex_run_independent_verification_executed"])
        self.assertTrue(payload["conditions_for_candidate_foundation"]["red_team_execution_completed"])
        self.assertTrue(payload["conditions_for_candidate_foundation"]["p0_p1_findings_fixed_or_none_found"])
        self.assertTrue(payload["conditions_for_candidate_foundation"]["operation_evidence_program_initialized"])

    def test_dossier_references_required_artifacts(self) -> None:
        payload = json.loads(DOSSIER_JSON.read_text(encoding="utf-8"))
        for ref in payload["required_references"].values():
            self.assertTrue((REPO_ROOT / ref).exists(), ref)
        self.assertEqual(payload["prior_wave_1_to_9_readiness_summary"]["final_prior_pr"], "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/548")

    def test_dossier_lists_current_program_prs_with_ci(self) -> None:
        payload = json.loads(DOSSIER_JSON.read_text(encoding="utf-8"))
        prs = {entry["wave"]: entry for entry in payload["current_program_prs"]}
        self.assertEqual(set(prs), {1, 2, 3, 4})
        self.assertEqual(prs[1]["merge_commit"], "71a9744b2e84595627222c82c8155d2e537977ed")
        self.assertEqual(prs[2]["merge_commit"], "33032ef069830b4023bc994c722d86a087179268")
        self.assertEqual(prs[3]["merge_commit"], "b7a0dce3f33d0ebb33ec8cacc97f1c4a3151f791")
        self.assertEqual(prs[4]["merge_commit"], "0952722911ca880b75511b7ef7718051a060d2de")
        for entry in prs.values():
            self.assertEqual(entry["ci_status"], "canonical-health passed")
            self.assertIn("/actions/runs/", entry["ci_url"])

    def test_markdown_keeps_required_non_claims(self) -> None:
        text = DOSSIER_MD.read_text(encoding="utf-8")
        self.assertIn(FINAL_VERDICT, text)
        self.assertIn("This is not final global recognition.", text)
        self.assertIn("This is not human external signoff confirmed.", text)
        self.assertIn("Human or independent external review remains required.", text)
        self.assertIn("30-90 day real-world operation remains required.", text)
        self.assertIn("Final recognition requires evidence beyond Codex.", text)

    def test_makefile_declares_global_signoff_gates(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("global-signoff-dossier-check:", makefile)
        self.assertIn("test-global-signoff-dossier:", makefile)
        self.assertIn("external-verification-program-check:", makefile)
        self.assertIn("scripts/global_signoff_dossier_check_v1.py", makefile)
        self.assertIn("tests.tracer_bullet.test_global_signoff_dossier_v1", makefile)


if __name__ == "__main__":
    unittest.main()
