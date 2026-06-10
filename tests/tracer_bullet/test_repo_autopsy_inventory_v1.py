"""Tracer-bullet tests for Repo Autopsy Inventory V1."""

from __future__ import annotations

from dataclasses import replace
import json
import unittest
from pathlib import Path

from kernel.audit.repo_autopsy_inventory import (
    AUTOPSY_CATEGORIES,
    SCORE_VALUES,
    RepoAutopsyRecord,
    record_content_hash,
    validate_repo_autopsy_record,
)


POLICY_PATH = Path("governance/audit/repo_autopsy_inventory_v1.json")
SOURCE_PATH = Path("kernel/audit/repo_autopsy_inventory.py")


def _record(**overrides: object) -> RepoAutopsyRecord:
    base = RepoAutopsyRecord(
        record_id="autopsy_core_runtime_001",
        path="kernel/runtime/runner.py",
        module_name="kernel.runtime.runner",
        category="CORE_RUNTIME",
        execution_value="HIGH",
        evidence_value="MEDIUM",
        risk_reduction_value="MEDIUM",
        use_case_ids=("uc_002_local_test_receipt",),
        runtime_pressure="HIGH",
        test_pressure="HIGH",
        external_pressure="LOW",
        prune_candidate=False,
        archive_candidate=False,
        keep_reason="Core runtime dry-run receipt behavior is actively tested.",
        prune_reason="",
        owner_layer="kernel.runtime",
        last_reviewed_at="2026-05-25T00:00:00Z",
    )
    record = replace(base, **overrides)
    return replace(record, content_hash=record_content_hash(record))


class RepoAutopsyInventoryTests(unittest.TestCase):
    def test_policy_declares_classification_model(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["object_type"], "RepoAutopsyInventoryPolicy")
        self.assertEqual(set(policy["categories"]), set(AUTOPSY_CATEGORIES))
        self.assertEqual(set(policy["score_values"]), set(SCORE_VALUES))
        self.assertFalse(policy["mutates_files"])
        self.assertFalse(policy["deletes_files"])
        self.assertFalse(policy["moves_files"])

    def test_valid_core_runtime_record_accepted(self):
        result = validate_repo_autopsy_record(_record())
        self.assertTrue(result.accepted, result.failures)
        self.assertFalse(result.review_required)

    def test_evidence_spine_requires_evidence_value(self):
        result = validate_repo_autopsy_record(_record(category="EVIDENCE_SPINE", evidence_value="NONE"))
        self.assertFalse(result.accepted)
        self.assertIn("evidence_spine_requires_evidence_value", result.failures)

    def test_risk_boundary_requires_risk_reduction_value(self):
        result = validate_repo_autopsy_record(_record(category="RISK_BOUNDARY", risk_reduction_value="NONE"))
        self.assertFalse(result.accepted)
        self.assertIn("risk_boundary_requires_risk_reduction_value", result.failures)

    def test_prune_candidate_cannot_silently_be_core_runtime(self):
        result = validate_repo_autopsy_record(_record(prune_candidate=True))
        self.assertFalse(result.accepted)
        self.assertIn("core_runtime_prune_conflict_requires_reviewer_marked_conflict", result.failures)

    def test_archive_candidate_requires_reason(self):
        result = validate_repo_autopsy_record(
            _record(
                category="ARCHIVE_CANDIDATE",
                execution_value="NONE",
                archive_candidate=True,
                keep_reason="",
                prune_reason="",
                archive_reason="",
            )
        )
        self.assertFalse(result.accepted)
        self.assertIn("archive_candidate_requires_reason", result.failures)

    def test_orphaned_record_flagged_for_review(self):
        result = validate_repo_autopsy_record(
            _record(
                category="UNKNOWN",
                execution_value="NONE",
                use_case_ids=(),
                runtime_pressure="NONE",
            )
        )
        self.assertTrue(result.accepted, result.failures)
        self.assertTrue(result.review_required)

    def test_content_hash_deterministic_excluding_last_reviewed_at(self):
        first = _record(last_reviewed_at="2026-05-25T00:00:00Z")
        second = _record(last_reviewed_at="2030-01-01T00:00:00Z")
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.content_hash, record_content_hash(first))

    def test_no_file_deletion_or_move_behavior_exists(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for marker in ("unlink(", "rmdir(", "remove(", "removedirs(", "renames(", "shutil", "archive_move"):
            self.assertNotIn(marker, source)

    def test_no_subprocess_network_provider_browser_dcc_or_comfyui_launch(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for marker in (
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "openai",
            "anthropic",
            "bpy",
            "comfyui",
            "shell=True",
        ):
            self.assertNotIn(marker, source.lower())


if __name__ == "__main__":
    unittest.main()
