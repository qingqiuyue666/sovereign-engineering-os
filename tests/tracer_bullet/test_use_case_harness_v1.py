"""Tracer-bullet tests for Use Case Harness V1."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


POLICY_PATH = Path("governance/use_cases/use_case_harness_v1.json")
USE_CASE_ROOT = Path("use_cases")
USE_CASE_IDS = (
    "uc_001_codex_pr_preflight",
    "uc_002_local_test_receipt",
    "uc_003_github_pr_audit",
    "uc_004_comfyui_workflow_static_check",
    "uc_005_creative_tool_inventory",
)
REQUIRED_FILES = (
    "problem.md",
    "input_example.json",
    "expected_output.json",
    "acceptance.md",
    "manual_baseline.md",
    "automation_gain.md",
    "failure_modes.md",
)


def _policy() -> dict[str, object]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _expected_output(use_case_id: str) -> dict[str, object]:
    path = USE_CASE_ROOT / use_case_id / "expected_output.json"
    return json.loads(path.read_text(encoding="utf-8"))


class UseCaseHarnessV1Tests(unittest.TestCase):
    def test_all_required_use_case_directories_exist(self):
        for use_case_id in USE_CASE_IDS:
            with self.subTest(use_case_id=use_case_id):
                self.assertTrue((USE_CASE_ROOT / use_case_id).is_dir())

    def test_each_use_case_has_required_files(self):
        for use_case_id in USE_CASE_IDS:
            for filename in REQUIRED_FILES:
                with self.subTest(use_case_id=use_case_id, filename=filename):
                    self.assertTrue((USE_CASE_ROOT / use_case_id / filename).is_file())

    def test_each_input_example_json_parses(self):
        for use_case_id in USE_CASE_IDS:
            path = USE_CASE_ROOT / use_case_id / "input_example.json"
            with self.subTest(path=str(path)):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data["use_case_id"], use_case_id)

    def test_each_expected_output_json_parses(self):
        for use_case_id in USE_CASE_IDS:
            data = _expected_output(use_case_id)
            with self.subTest(use_case_id=use_case_id):
                self.assertEqual(data["use_case_id"], use_case_id)

    def test_policy_lists_exactly_the_five_use_cases(self):
        policy_ids = tuple(item["use_case_id"] for item in _policy()["use_cases"])
        self.assertEqual(policy_ids, USE_CASE_IDS)

    def test_no_use_case_implies_execution(self):
        policy = _policy()
        self.assertFalse(policy["execution_allowed"])
        self.assertFalse(policy["runner_allowed"])
        self.assertFalse(policy["network_allowed"])
        for use_case_id in USE_CASE_IDS:
            output = _expected_output(use_case_id)
            with self.subTest(use_case_id=use_case_id):
                self.assertFalse(output["execution_allowed"])
                self.assertFalse(output["runner_required"])
                self.assertFalse(output["network_required"])

    def test_comfyui_use_case_is_static_check_only(self):
        output = _expected_output("uc_004_comfyui_workflow_static_check")
        self.assertTrue(output["static_check_only"])
        self.assertFalse(output["comfyui_launch_allowed"])
        self.assertFalse(output["dcc_launch_allowed"])

    def test_creative_tool_inventory_is_inventory_only_no_control(self):
        output = _expected_output("uc_005_creative_tool_inventory")
        self.assertTrue(output["inventory_only"])
        self.assertFalse(output["tool_control_allowed"])
        self.assertFalse(output["dcc_launch_allowed"])
        self.assertFalse(output["asset_mutation_allowed"])

    def test_github_pr_audit_uses_supplied_snapshot_only(self):
        output = _expected_output("uc_003_github_pr_audit")
        self.assertFalse(output["github_api_call_allowed"])
        self.assertEqual(output["merge_readiness"], "derived_from_supplied_snapshot")

    def test_future_module_admission_requires_at_least_one_use_case_id(self):
        admission = _policy()["future_module_admission"]
        self.assertTrue(admission["requires_use_case_id"])
        self.assertEqual(admission["minimum_use_case_ids"], 1)
        self.assertEqual(admission["accepted_field"], "use_case_ids")


if __name__ == "__main__":
    unittest.main()
