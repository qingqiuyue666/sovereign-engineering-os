"""Static validation for End-to-End Acceptance Matrix V1."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


MATRIX_MD = Path("governance/acceptance/e2e_acceptance_matrix_v1.md")
MATRIX_JSON = Path("governance/acceptance/e2e_acceptance_matrix_v1.json")


class E2EAcceptanceMatrixV1Tests(unittest.TestCase):
    def test_required_acceptance_areas_are_present_in_markdown_and_json(self):
        markdown = MATRIX_MD.read_text(encoding="utf-8").lower()
        matrix = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
        areas = {item["id"] for item in matrix["acceptance_items"]}

        required_ids = {
            "metadata_chain",
            "real_local_runner",
            "token_lifecycle",
            "job_queue",
            "replay",
            "worker_registry",
            "pr_audit",
            "artifact_ledger",
            "dashboard_model",
            "domain_adapter_foundation",
            "forbidden_surfaces",
            "mainline_release_readiness",
        }
        self.assertEqual(areas, required_ids)
        for phrase in (
            "metadata chain",
            "real local runner",
            "token lifecycle",
            "job queue",
            "replay",
            "worker registry",
            "pr audit",
            "artifact ledger",
            "dashboard model",
            "domain adapter foundation",
            "forbidden surfaces",
            "mainline release readiness",
        ):
            self.assertIn(phrase, markdown)

    def test_matrix_requires_global_validation_and_audit_packet(self):
        markdown = MATRIX_MD.read_text(encoding="utf-8")
        matrix = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))

        for command in (
            "python3 -m unittest discover tests",
            "make ci",
            "git diff --check",
            "GitHub Actions",
        ):
            self.assertIn(command, markdown)
            self.assertIn(command, matrix["global_validation_commands"])
        for field in (
            "milestone",
            "branch",
            "PR URL",
            "head SHA",
            "changed files",
            "GitHub Actions run URL",
            "forbidden-surface confirmation",
        ):
            self.assertIn(field, markdown)

    def test_matrix_does_not_grant_runtime_merge_or_release_authority(self):
        matrix = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
        markdown = MATRIX_MD.read_text(encoding="utf-8").lower()

        self.assertFalse(matrix["runtime_behavior_introduced"])
        self.assertFalse(matrix["production_execution_allowed"])
        self.assertFalse(matrix["merge_automation_allowed"])
        self.assertFalse(matrix["release_automation_allowed"])
        for forbidden in (
            "auto-merge",
            "direct push to main",
            "branch deletion",
            "production autonomy",
            "provider api live calls",
            "credential storage",
        ):
            self.assertIn(forbidden, markdown)
            self.assertIn(forbidden, [item.lower() for item in matrix["forbidden_surface_rules"]])

    def test_each_acceptance_item_has_evidence_and_merge_signal(self):
        matrix = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))

        for item in matrix["acceptance_items"]:
            self.assertTrue(item["id"])
            self.assertTrue(item["area"])
            self.assertGreaterEqual(len(item["required_evidence"]), 3)
            self.assertTrue(item["merge_readiness_signal"])


if __name__ == "__main__":
    unittest.main()
