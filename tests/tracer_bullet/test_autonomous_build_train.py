
"""Tests for autonomous build train policy and plan."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

POLICY = Path("governance/security/autonomous_build_train_policy_v1.json")

PLAN = Path("governance/local_train/autonomous_build_train_plan_v1.json")

RUNBOOK = Path("docs/runbooks/autonomous_build_train_v1.md")

class AutonomousBuildTrainTests(unittest.TestCase):

    def test_files_exist(self):

        self.assertTrue(POLICY.is_file())

        self.assertTrue(PLAN.is_file())

        self.assertTrue(RUNBOOK.is_file())

    def test_policy_is_active(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["policy_name"], "autonomous_build_train_policy_v1")

        self.assertEqual(payload["policy_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertEqual(payload["max_runtime_seconds_default"], 28800)

    def test_policy_forbids_unbounded_and_cloud_ai_actions(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        forbidden = set(payload["forbidden_actions"])

        required = {

            "cloud_ai_api_call",

            "unbounded_code_generation",

            "unbounded_runtime",

            "git_merge",

            "git_push_main",

            "git_branch_delete",

            "main_branch_modification",

            "secret_read",

            "env_read",

            "provider_live_execution",

            "vault_live_write",

            "production_autonomy",

            "deployment",

        }

        self.assertTrue(required.issubset(forbidden))

    def test_policy_requires_core_guards(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        guards = set(payload["required_guards"])

        required = {

            "predefined_stage_queue_required",

            "stop_on_first_failure",

            "max_runtime_enforced",

            "heartbeat_written",

            "resume_marker_written",

            "stage_reports_written",

            "main_branch_mutation_rejected",

            "cloud_ai_calls_forbidden",

            "secrets_forbidden",

            "merge_forbidden",

            "branch_delete_forbidden",

            "unbounded_generation_forbidden",

        }

        self.assertTrue(required.issubset(guards))

    def test_plan_is_active_and_bounded(self):

        payload = json.loads(PLAN.read_text(encoding="utf-8"))

        self.assertEqual(payload["plan_name"], "autonomous_build_train_plan_v1")

        self.assertEqual(payload["plan_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertEqual(payload["train_mode"], "overnight")

        self.assertEqual(payload["max_runtime_seconds"], 28800)

        self.assertTrue(payload["stop_on_first_failure"])

        self.assertIsInstance(payload["stages"], list)

        self.assertGreaterEqual(len(payload["stages"]), 2)

    def test_plan_stages_are_verification_only_v1(self):

        payload = json.loads(PLAN.read_text(encoding="utf-8"))

        for stage in payload["stages"]:

            self.assertEqual(stage["stage_type"], "verification")

            self.assertIn(stage["suite"], {"local-core", "full"})

            self.assertEqual(stage["mode"], "verify")

            self.assertFalse(stage["allow_commit"])

            self.assertFalse(stage["allow_push_feature_branch"])

    def test_plan_stages_have_required_fields(self):

        payload = json.loads(PLAN.read_text(encoding="utf-8"))

        required = {

            "task_id",

            "stage_id",

            "stage_type",

            "suite",

            "mode",

            "commit_message",

            "allow_commit",

            "allow_push_feature_branch",

        }

        for stage in payload["stages"]:

            self.assertTrue(required.issubset(set(stage)))

    def test_runbook_records_local_only_boundaries(self):

        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("It is not a cloud AI agent.", text)

        self.assertIn("It does not design new architecture by itself.", text)

        self.assertIn("It does not generate unbounded code.", text)

        self.assertIn("It does not merge main.", text)

        self.assertIn("It does not push main.", text)

        self.assertIn("It does not delete branches.", text)

        self.assertIn("It does not read secrets.", text)

        self.assertIn("It does not call cloud AI APIs.", text)

    def test_runbook_records_v1_scope(self):

        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("v1 contains verification stages only", text)

        self.assertIn("It does not yet execute code generation stages.", text)

        self.assertIn("It does not replace human merge review.", text)

        self.assertIn("It does not authorize cloud AI to see C-layer protected assets.", text)

if __name__ == "__main__":

    unittest.main()

