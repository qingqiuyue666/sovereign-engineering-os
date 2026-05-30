"""Tests for Codex-run independent verification execution artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = REPO_ROOT / "reports" / "audits" / "independent_verification_execution_v1.json"
REPORT_MD = REPO_ROOT / "reports" / "audits" / "independent_verification_execution_v1.md"


class IndependentVerificationExecutionV1Tests(unittest.TestCase):
    def test_independent_verification_report_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/independent_verification_report_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("independent_verification_report_check_v1: PASS", completed.stdout)

    def test_report_records_codex_run_boundary(self) -> None:
        payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        markdown = REPORT_MD.read_text(encoding="utf-8")
        self.assertEqual(payload["reviewer_type"], "Codex-run local independent verification")
        self.assertFalse(payload["human_third_party_audit"])
        self.assertFalse(payload["external_signoff_confirmed"])
        self.assertFalse(payload["global_recognition_claimed"])
        self.assertFalse(payload["global_recognition_confirmed_by_codex"])
        self.assertIn("This is not a human third-party external audit.", payload["explicit_statements"])
        self.assertIn("External recognition is not confirmed by Codex.", markdown)

    def test_report_records_clean_reproduction_invariants(self) -> None:
        payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(payload["repository"]["target_head"], "2f46520b9aa107d83689b86d3314919ad4bca7b8")
        self.assertEqual(payload["repository"]["observed_head"], "2f46520b9aa107d83689b86d3314919ad4bca7b8")
        self.assertEqual(payload["release_candidate_tag"]["name"], "v0.1.0-rc3")
        self.assertEqual(
            payload["release_candidate_tag"]["observed_target"],
            "9a363f95b85602ffc598db463dc6181a9bbbdf3c",
        )
        self.assertFalse(payload["release_candidate_tag"]["moved_or_recreated_by_this_execution"])
        self.assertTrue(payload["environment_summary"]["clean_clone"])
        self.assertTrue(payload["environment_summary"]["fresh_venv"])
        self.assertFalse(payload["environment_summary"]["temp_workspace_path_recorded"])

    def test_report_commands_all_passed(self) -> None:
        payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        commands = {entry["id"]: entry for entry in payload["commands"]}
        for command_id in (
            "git_clone",
            "checkout_expected_head",
            "verify_starting_head",
            "verify_rc3_tag",
            "create_fresh_venv",
            "install_project",
            "clean_install_artifacts_after_install",
            "cli_help_seos",
            "cli_help_seos_local",
            "external_audit_packet_check",
            "observation_check",
            "failure_path_smoke",
            "adversarial_smoke",
            "make_verify",
            "clean_install_artifacts_before_ci",
            "make_ci",
        ):
            self.assertIn(command_id, commands)
            self.assertEqual(commands[command_id]["result"], "PASS")
            self.assertEqual(commands[command_id]["exit_code"], 0)
        self.assertEqual(payload["final_status"], "CODEX_RUN_INDEPENDENT_VERIFICATION_EXECUTED")
        self.assertEqual(payload["findings"], [])

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
