"""Static tests for Mainline Release Readiness Gate V1."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "governance" / "release" / "mainline_release_readiness_gate_v1.json"
ARTIFACT_PATH = ROOT / "governance" / "release" / "mainline_release_recommendation_artifact_v1.json"
DOC_PATH = ROOT / "docs" / "operator" / "mainline_release_readiness_gate_v1.md"

REQUIRED_MILESTONES = {
    "A1",
    "A2",
    "A3",
    "B1",
    "B2",
    "B3",
    "B4",
    "C1",
    "C2",
    "D1",
    "D2",
    "D3",
    "D4",
    "E1",
}

EXPECTED_COMMANDS = {
    "full_unittest_discover": ["python3", "-m", "unittest", "discover", "tests"],
    "make_ci": ["make", "ci"],
    "diff_check": ["git", "diff", "--check"],
    "status_short": ["git", "status", "--short"],
}

FORBIDDEN_AUTHORITY_FLAGS = {
    "release_automation_authorized",
    "merge_automation_authorized",
    "branch_deletion_authorized",
    "push_to_main_authorized",
    "production_promotion_authorized",
    "runtime_execution_authorized",
    "browser_execution_authorized",
    "network_execution_authorized",
    "provider_api_calls_authorized",
    "credential_storage_authorized",
    "unbounded_daemon_authorized",
    "unbounded_scheduler_authorized",
}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class MainlineReleaseReadinessGateV1Tests(unittest.TestCase):
    def test_gate_descriptor_declares_required_release_evidence(self) -> None:
        gate = load_json(GATE_PATH)
        self.assertEqual(gate["descriptor_type"], "seos_mainline_release_readiness_gate")
        self.assertEqual(gate["version"], "v1")
        self.assertEqual(gate["status"], "contract_only")
        self.assertEqual(gate["default_recommendation"], "DO_NOT_RELEASE")
        self.assertEqual(
            set(gate["allowed_recommendations"]),
            {"RELEASE_ALLOWED", "DO_NOT_RELEASE", "WAITING_FOR_CI", "BLOCKED"},
        )

        milestone_ids = {
            item["milestone_id"] for item in gate["required_milestone_evidence"]
        }
        self.assertEqual(milestone_ids, REQUIRED_MILESTONES)
        for item in gate["required_milestone_evidence"]:
            self.assertIn("github_actions_pass", item["required_evidence"])

    def test_gate_requires_main_validation_and_forbidden_surface_scan(self) -> None:
        gate = load_json(GATE_PATH)
        commands = {item["command_id"]: item["argv"] for item in gate["main_validation_commands"]}
        self.assertEqual(commands, EXPECTED_COMMANDS)
        self.assertTrue(all(item["required"] for item in gate["main_validation_commands"]))

        scan = gate["forbidden_surface_scan_requirement"]
        self.assertTrue(scan["required"])
        self.assertEqual(scan["recommendation_when_missing"], "BLOCKED")
        blocked = set(scan["blocked_surfaces"])
        for surface in (
            "arbitrary_shell_execution",
            "shell_true",
            "network_access",
            "provider_api_live_calls",
            "production_autonomy",
            "direct_push_to_main",
            "merge_automation",
            "branch_deletion",
        ):
            self.assertIn(surface, blocked)

    def test_gate_denies_release_and_runtime_authority(self) -> None:
        gate = load_json(GATE_PATH)
        authority = gate["forbidden_authority"]
        for flag in FORBIDDEN_AUTHORITY_FLAGS:
            self.assertIn(flag, authority)
            self.assertIs(authority[flag], False)

        artifact_contract = gate["release_recommendation_artifact_contract"]
        self.assertFalse(artifact_contract["writes_release"])
        self.assertFalse(artifact_contract["merges_prs"])
        self.assertFalse(artifact_contract["deletes_branches"])
        self.assertFalse(artifact_contract["pushes_main"])

    def test_release_recommendation_artifact_is_advisory_and_blocked_by_default(self) -> None:
        artifact = load_json(ARTIFACT_PATH)
        self.assertEqual(artifact["artifact_type"], "mainline_release_recommendation_artifact_v1")
        self.assertEqual(artifact["version"], "v1")
        self.assertEqual(artifact["target_branch"], "main")
        self.assertEqual(artifact["recommendation"], "DO_NOT_RELEASE")
        self.assertTrue(artifact["operator_review_required"])
        self.assertIn("release_readiness_evidence_not_yet_evaluated", artifact["blockers"])

        authority = artifact["automation_authority"]
        self.assertFalse(authority["writes_release"])
        self.assertFalse(authority["merges_prs"])
        self.assertFalse(authority["deletes_branches"])
        self.assertFalse(authority["pushes_main"])
        self.assertFalse(authority["performs_runtime_execution"])
        self.assertFalse(authority["performs_network_execution"])
        self.assertFalse(authority["performs_browser_execution"])

    def test_operator_doc_records_boundary_and_review_criteria(self) -> None:
        text = DOC_PATH.read_text(encoding="utf-8")
        for heading in (
            "## Scope Summary",
            "## Required Evidence",
            "## Validation Commands",
            "## Recommendation States",
            "## Rollback And Recovery Evidence",
            "## Boundary Statement",
            "## Review Readiness Criteria",
        ):
            self.assertIn(heading, text)

        lower = " ".join(text.lower().split())
        for phrase in (
            "no runtime execution",
            "no browser or network behavior",
            "no provider api calls",
            "no credential storage",
            "no production autonomy",
            "no branch deletion",
            "no push to main",
            "no pr merge",
            "no release automation",
        ):
            self.assertIn(phrase, lower)


if __name__ == "__main__":
    unittest.main()
