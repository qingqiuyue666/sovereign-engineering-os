"""Tests for local core operating foundation."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

from kernel.security.local_core_operating_foundation import (

    validate_cloud_ai_boundary,

    validate_patch_only_intake,

    validate_task_classification,

)

VALID_DIGEST_A = "sha256:" + "a" * 64

VALID_DIGEST_B = "sha256:" + "b" * 64

def valid_task(**overrides):

    payload = {

        "task_id": "task-local-core-001",

        "task_name": "local core task",

        "asset_class": "B",

        "cloud_ai_allowed": True,

        "repository_access_mode": "minimal_snippets",

        "secret_exposure_check": "absent",

        "core_architecture_exposure": "partial_snippets",

        "expected_output_mode": "unified_diff_patch",

        "human_review_required": True,

        "requested_actions": ["draft_patch"],

    }

    payload.update(overrides)

    return payload

def valid_patch(**overrides):

    payload = {

        "patch_id": "patch-local-core-001",

        "task_id": "task-local-core-001",

        "source_snippet_digest": VALID_DIGEST_A,

        "patch_digest": VALID_DIGEST_B,

        "output_mode": "unified_diff_patch",

        "repository_access_mode": "minimal_snippets",

        "cloud_ai_role": "draft_worker_only",

        "human_review_required": True,

        "local_apply_required": True,

        "local_ci_required": True,

        "forbidden_content_flags": [],

    }

    payload.update(overrides)

    return payload

class LocalCoreOperatingFoundationTests(unittest.TestCase):

    def test_policy_files_exist(self):

        for path in (

            "governance/security/task_classification_gate_policy_v1.json",

            "governance/security/cloud_ai_boundary_enforcer_policy_v1.json",

            "governance/security/patch_only_intake_contract_policy_v1.json",

        ):

            self.assertTrue(Path(path).is_file())

    def test_policy_files_are_valid_json(self):

        for path in (

            "governance/security/task_classification_gate_policy_v1.json",

            "governance/security/cloud_ai_boundary_enforcer_policy_v1.json",

            "governance/security/patch_only_intake_contract_policy_v1.json",

        ):

            payload = json.loads(Path(path).read_text(encoding="utf-8"))

            self.assertEqual(payload["policy_version"], "v1")

            self.assertEqual(payload["status"], "active")

    def test_valid_b_layer_task_is_accepted(self):

        receipt = validate_task_classification(valid_task())

        self.assertTrue(receipt.accepted)

        self.assertEqual(receipt.asset_class, "B")

        self.assertEqual(receipt.repository_access_mode, "minimal_snippets")

    def test_c_layer_rejects_cloud_ai(self):

        receipt = validate_task_classification(valid_task(asset_class="C", cloud_ai_allowed=True))

        self.assertFalse(receipt.accepted)

        self.assertIn("c_layer_must_be_local_only", receipt.failures)

    def test_b_layer_rejects_full_repo_mount(self):

        receipt = validate_task_classification(valid_task(repository_access_mode="full_repo_mount"))

        self.assertFalse(receipt.accepted)

        self.assertIn("repository_access_mode_invalid", receipt.failures)

        self.assertIn("b_layer_requires_patch_only", receipt.failures)

    def test_secret_exposure_forbids_cloud_ai(self):

        receipt = validate_task_classification(valid_task(secret_exposure_check="present"))

        self.assertFalse(receipt.accepted)

        self.assertIn("secrets_forbid_cloud_ai", receipt.failures)

    def test_core_full_context_forbids_cloud_ai(self):

        receipt = validate_task_classification(valid_task(core_architecture_exposure="full_context"))

        self.assertFalse(receipt.accepted)

        self.assertIn("core_architecture_full_context_forbids_cloud_ai", receipt.failures)

    def test_boundary_rejects_forbidden_actions(self):

        receipt = validate_cloud_ai_boundary(valid_task(requested_actions=["git_push", "git_merge"]))

        self.assertFalse(receipt.accepted)

        self.assertIn("git_push_forbidden_for_cloud_ai", receipt.failures)

        self.assertIn("git_merge_forbidden_for_cloud_ai", receipt.failures)

    def test_boundary_rejects_forbidden_input_flags(self):

        receipt = validate_cloud_ai_boundary(valid_task(secrets_present=True, tokens_present=True))

        self.assertFalse(receipt.accepted)

        self.assertIn("secrets_present_forbids_cloud_ai", receipt.failures)

        self.assertIn("tokens_present_forbids_cloud_ai", receipt.failures)

    def test_boundary_rejects_c_layer_cloud_ai(self):

        receipt = validate_cloud_ai_boundary(valid_task(asset_class="C", cloud_ai_allowed=True))

        self.assertFalse(receipt.accepted)

        self.assertIn("c_layer_cloud_ai_boundary_violation", receipt.failures)

    def test_patch_only_valid_intake_is_accepted(self):

        receipt = validate_patch_only_intake(valid_patch())

        self.assertTrue(receipt.accepted)

    def test_patch_only_requires_digest_shape(self):

        receipt = validate_patch_only_intake(valid_patch(source_snippet_digest="sha256:bad"))

        self.assertFalse(receipt.accepted)

        self.assertIn("source_snippet_digest_required_sha256_digest", receipt.failures)

    def test_patch_only_rejects_wrong_modes(self):

        receipt = validate_patch_only_intake(valid_patch(repository_access_mode="full_repo_mount"))

        self.assertFalse(receipt.accepted)

        self.assertIn("repository_access_mode_must_be_minimal_snippets", receipt.failures)

    def test_patch_only_rejects_forbidden_content(self):

        receipt = validate_patch_only_intake(valid_patch(forbidden_content_flags=["secrets", "git_push"]))

        self.assertFalse(receipt.accepted)

        self.assertIn("secrets_forbidden_in_patch", receipt.failures)

        self.assertIn("git_push_forbidden_in_patch", receipt.failures)

    def test_non_mapping_payloads_raise(self):

        with self.assertRaises(TypeError):

            validate_task_classification(None)  # type: ignore[arg-type]

        with self.assertRaises(TypeError):

            validate_cloud_ai_boundary(None)  # type: ignore[arg-type]

        with self.assertRaises(TypeError):

            validate_patch_only_intake(None)  # type: ignore[arg-type]

    def test_source_does_not_import_network_or_git_mutation_modules(self):

        source = Path("kernel/security/local_core_operating_foundation.py").read_text(encoding="utf-8")

        forbidden = ("socket", "requests", "urllib", "subprocess", "os.system", "git push", "git merge")

        for item in forbidden:

            self.assertNotIn(item, source)

if __name__ == "__main__":

    unittest.main()

