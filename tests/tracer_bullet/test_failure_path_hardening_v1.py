"""Tests for Wave 4 fail-closed smoke evidence."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_CASE_IDS = {
    "missing_task",
    "bad_workspace",
    "duplicate_task_id",
    "missing_approval",
    "rejected_task_cannot_run",
    "corrupted_receipt",
    "corrupted_observation_json",
    "missing_evidence",
    "replay_impossible_not_reconstructable",
    "tag_mismatch",
    "network_failure_no_pass",
    "interrupted_script_no_success_marker",
    "invalid_cli_args",
    "fake_pass_log_rejected",
    "path_leak",
    "shell_metacharacters",
    "path_traversal",
    "unicode_emoji_long_fields",
    "prompt_injection_no_authority",
}

REQUIRED_FILES = (
    Path("scripts/failure_path_smoke_v1.sh"),
    Path("scripts/adversarial_smoke_v1.py"),
    Path("tests/tracer_bullet/test_failure_path_hardening_v1.py"),
    Path("tests/adversarial/test_adversarial_inputs_v1.py"),
    Path("reports/failure_path/failure_path_baseline_v1.md"),
    Path("reports/failure_path/failure_path_baseline_v1.json"),
)


def _read(relative_path: Path) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class FailurePathHardeningV1Tests(unittest.TestCase):
    def test_required_wave_4_files_exist(self) -> None:
        for relative_path in REQUIRED_FILES:
            self.assertTrue((REPO_ROOT / relative_path).exists(), relative_path.as_posix())

    def test_failure_path_smoke_script_passes(self) -> None:
        completed = subprocess.run(
            ["bash", "scripts/failure_path_smoke_v1.sh"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("failure_path_smoke_v1: PASS", completed.stdout)

    def test_shell_smoke_is_fail_closed(self) -> None:
        text = _read(Path("scripts/failure_path_smoke_v1.sh"))
        self.assertTrue(text.startswith("#!/usr/bin/env bash\n"))
        self.assertIn("set -euo pipefail", text)
        self.assertIn("trap cleanup EXIT INT TERM", text)
        self.assertIn("failed command printed PASSED", text)
        self.assertIn("interrupted child left success marker", text)

    def test_baseline_covers_required_cases(self) -> None:
        payload = json.loads(
            (REPO_ROOT / "reports/failure_path/failure_path_baseline_v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(payload["schema_version"], "failure_path_baseline_v1")
        self.assertIs(payload["global_recognition_claimed"], False)
        covered = {item["case_id"] for item in payload["cases"]}
        self.assertTrue(REQUIRED_CASE_IDS.issubset(covered))

    def test_adversarial_runner_lists_required_cases(self) -> None:
        text = _read(Path("scripts/adversarial_smoke_v1.py"))
        for case_id in REQUIRED_CASE_IDS:
            self.assertIn(case_id, text)


if __name__ == "__main__":
    unittest.main()
