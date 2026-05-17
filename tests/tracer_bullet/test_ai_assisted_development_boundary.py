"""Tests for AI-assisted development boundary policy."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

POLICY_PATH = Path("governance/security/ai_assisted_development_boundary_policy_v1.json")

RUNBOOK_PATH = Path("docs/runbooks/ai_assisted_development_boundary_v1.md")

class AiAssistedDevelopmentBoundaryTests(unittest.TestCase):

    def setUp(self):

        self.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

        self.runbook = RUNBOOK_PATH.read_text(encoding="utf-8")

    def test_policy_and_runbook_exist(self):

        self.assertTrue(POLICY_PATH.is_file())

        self.assertTrue(RUNBOOK_PATH.is_file())

    def test_cloud_ai_is_draft_worker_not_authority(self):

        authority = self.policy["authority_model"]

        self.assertEqual(authority["cloud_ai_role"], "draft_worker_only")

        self.assertTrue(authority["cloud_ai_may_not_be_authority"])

        self.assertEqual(authority["local_terminal_role"], "authority_for_git_ci_merge_push")

        self.assertTrue(authority["human_review_required"])

    def test_c_layer_is_local_only(self):

        modes = self.policy["required_work_modes"]

        self.assertEqual(modes["C_layer"], "local_only_no_cloud_ai")

        c_assets = set(self.policy["asset_classes"]["C_local_only"])

        required = {

            "system_architecture_core",

            "runtime_spine_design",

            "provider_architecture",

            "replay_architecture",

            "evidence_vault_architecture",

            "osint_asset_mapping_architecture",

            "decision_engine",

            "real_provider_implementation",

            "real_strategy_parameters",

            "real_execution_logic",

            "secrets_env_tokens_cookies_sessions",

        }

        self.assertTrue(required.issubset(c_assets))

    def test_b_layer_requires_patch_only(self):

        modes = self.policy["required_work_modes"]

        self.assertEqual(modes["B_layer"], "patch_only_minimal_snippets")

        self.assertIn("unified_diff_patch_draft", self.policy["allowed_cloud_ai_outputs"])

    def test_cloud_ai_forbidden_inputs_include_secrets_and_core_context(self):

        forbidden = set(self.policy["forbidden_cloud_ai_inputs"])

        self.assertIn("secrets", forbidden)

        self.assertIn("env_files", forbidden)

        self.assertIn("api_keys", forbidden)

        self.assertIn("github_tokens", forbidden)

        self.assertIn("core_architecture_full_context", forbidden)

        self.assertIn("production_execution_context", forbidden)

    def test_cloud_ai_forbidden_actions_include_git_and_live_surfaces(self):

        forbidden = set(self.policy["forbidden_cloud_ai_actions"])

        self.assertIn("git_push", forbidden)

        self.assertIn("git_merge", forbidden)

        self.assertIn("git_branch_delete", forbidden)

        self.assertIn("main_branch_modification", forbidden)

        self.assertIn("secret_read", forbidden)

        self.assertIn("env_read", forbidden)

        self.assertIn("provider_live_execution", forbidden)

        self.assertIn("vault_live_write", forbidden)

        self.assertIn("autonomous_deployment", forbidden)

    def test_task_intake_requires_asset_class_and_cloud_ai_boundary(self):

        required = set(self.policy["task_intake_required_fields"])

        self.assertIn("task_name", required)

        self.assertIn("asset_class", required)

        self.assertIn("cloud_ai_allowed", required)

        self.assertIn("repository_access_mode", required)

        self.assertIn("secret_exposure_check", required)

        self.assertIn("human_review_required", required)

    def test_runbook_records_non_overclaim_boundary(self):

        self.assertIn("cloud AI tools as draft workers only", self.runbook)

        self.assertIn("C Layer: Local-Only", self.runbook)

        self.assertIn("Patch-Only Workflow", self.runbook)

        self.assertIn("does not claim cloud AI is private", self.runbook)

if __name__ == "__main__":

    unittest.main()

