"""Tests for Real Operation Observation Period V1 deliverables."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = (
    Path("docs/runbooks/real_operation_observation_period_v1.md"),
    Path("reports/observation/real_operation_observation_log_v1.md"),
    Path("reports/observation/real_operation_observation_log_v1.json"),
    Path("governance/policy/observation_period_change_policy_v1.md"),
    Path("scripts/observation_check_v1.py"),
    Path("tests/tracer_bullet/test_real_operation_observation_period_v1.py"),
)

REQUIRED_JSON_KEYS = (
    "schema_version",
    "observation_period_id",
    "start_state",
    "main_head",
    "release_candidate_tag",
    "mode",
    "active_development_allowed",
    "allowed_change_classes",
    "forbidden_change_classes",
    "hard_evidence_blocker_types",
    "observations",
    "current_verdict",
)

MAIN_HEAD = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"
RELEASE_CANDIDATE_TAG = "v0.1.0-rc3"
SECURITY_BOUNDARY = (
    "SEOS is a governance-level control plane, not an OS-level sandbox, "
    "container, VM, EDR, filesystem permission boundary, RPA system, "
    "computer-control system, or secret manager."
)


def _read(relative_path: Path) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class RealOperationObservationPeriodV1Tests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        for relative_path in REQUIRED_FILES:
            self.assertTrue(
                (REPO_ROOT / relative_path).exists(),
                f"missing {relative_path.as_posix()}",
            )

    def test_observation_json_parses_and_has_required_keys(self) -> None:
        payload = json.loads(
            _read(Path("reports/observation/real_operation_observation_log_v1.json"))
        )
        for key in REQUIRED_JSON_KEYS:
            self.assertIn(key, payload)
        self.assertEqual(payload["mode"], "real_operation_observation")
        self.assertFalse(payload["active_development_allowed"])
        self.assertEqual(
            payload["current_verdict"], "NO_HARD_EVIDENCE_BLOCKER_RECORDED"
        )

    def test_observation_check_script_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/observation_check_v1.py"],
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

    def test_no_forbidden_local_absolute_path_leaks(self) -> None:
        forbidden_markers = (
            "/" + "Users" + "/" + "qqy",
            "/" + "Users" + "/",
            "Documents" + "/" + "Codex",
            "." + "codex",
            "files-mentioned" + "-by-the-user",
        )
        for relative_path in REQUIRED_FILES:
            text = _read(relative_path)
            for marker in forbidden_markers:
                self.assertNotIn(marker, text, relative_path.as_posix())

    def test_policy_and_runbook_include_no_expansion_rule(self) -> None:
        for relative_path in (
            Path("docs/runbooks/real_operation_observation_period_v1.md"),
            Path("governance/policy/observation_period_change_policy_v1.md"),
        ):
            text = _read(relative_path)
            self.assertIn("feature expansion", text)
            self.assertIn("multi-agent expansion", text)
            self.assertIn("speculative V2/V3", text)

    def test_policy_and_runbook_include_no_item_28_rule(self) -> None:
        for relative_path in (
            Path("docs/runbooks/real_operation_observation_period_v1.md"),
            Path("governance/policy/observation_period_change_policy_v1.md"),
        ):
            text = _read(relative_path)
            self.assertIn("item 28+", text)
            self.assertIn("no item 28+", text.lower())

    def test_policy_and_runbook_include_blocker_only_exception_rule(self) -> None:
        for relative_path in (
            Path("docs/runbooks/real_operation_observation_period_v1.md"),
            Path("governance/policy/observation_period_change_policy_v1.md"),
        ):
            text = _read(relative_path).lower()
            self.assertIn("blocker", text)
            self.assertIn("hard evidence", text)
            self.assertIn("smallest", text)

    def test_security_boundary_wording_is_present(self) -> None:
        combined = "\n".join(_read(path) for path in REQUIRED_FILES)
        self.assertIn(SECURITY_BOUNDARY, combined)

    def test_current_main_head_and_release_candidate_anchors_are_present(self) -> None:
        combined = "\n".join(_read(path) for path in REQUIRED_FILES)
        self.assertIn(MAIN_HEAD, combined)
        self.assertIn(RELEASE_CANDIDATE_TAG, combined)


if __name__ == "__main__":
    unittest.main()
