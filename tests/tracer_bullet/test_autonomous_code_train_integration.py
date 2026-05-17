
"""Tests for autonomous code train integration."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

POLICY = Path("governance/security/autonomous_code_train_integration_policy_v1.json")

QUEUE = Path("governance/local_train/autonomous_code_train_queue_v1.json")

RUNBOOK = Path("docs/runbooks/autonomous_code_train_integration_v1.md")

CODE_STAGE_REGISTRY = Path("governance/local_train/code_stage_registry_v1.json")

CODE_STAGE_EXECUTOR = Path("tools/local_code_stage_executor.py")

LOCAL_TRAIN_RUNNER = Path("tools/local_train_runner.py")

class AutonomousCodeTrainIntegrationTests(unittest.TestCase):

    def test_files_exist(self):

        self.assertTrue(POLICY.is_file())

        self.assertTrue(QUEUE.is_file())

        self.assertTrue(RUNBOOK.is_file())

        self.assertTrue(CODE_STAGE_REGISTRY.is_file())

        self.assertTrue(CODE_STAGE_EXECUTOR.is_file())

        self.assertTrue(LOCAL_TRAIN_RUNNER.is_file())

    def test_policy_is_active(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["policy_name"], "autonomous_code_train_integration_policy_v1")

        self.assertEqual(payload["policy_version"], "v1")

        self.assertEqual(payload["status"], "active")

    def test_policy_allows_only_verification_and_code_stage(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(set(payload["allowed_stage_kinds"]), {"verification", "code_stage"})

    def test_policy_forbids_high_risk_actions(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        forbidden = set(payload["forbidden_actions"])

        required = {

            "cloud_ai_api_call",

            "freeform_shell_execution",

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

    def test_policy_requires_verification_after_code_stage(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        guards = set(payload["required_guards"])

        self.assertIn("code_stage_must_be_registered", guards)

        self.assertIn("verification_after_code_stage_required", guards)

        self.assertIn("stop_on_first_failure", guards)

        self.assertIn("diff_report_written", guards)

        self.assertIn("unbounded_generation_forbidden", guards)

    def test_queue_is_active_and_bounded(self):

        payload = json.loads(QUEUE.read_text(encoding="utf-8"))

        self.assertEqual(payload["queue_name"], "autonomous_code_train_queue_v1")

        self.assertEqual(payload["queue_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertEqual(payload["train_mode"], "overnight")

        self.assertEqual(payload["max_runtime_seconds"], 28800)

        self.assertTrue(payload["stop_on_first_failure"])

        self.assertIsInstance(payload["stages"], list)

        self.assertGreaterEqual(len(payload["stages"]), 2)

    def test_queue_contains_code_stage_then_verification(self):

        payload = json.loads(QUEUE.read_text(encoding="utf-8"))

        stages = payload["stages"]

        self.assertEqual(stages[0]["stage_kind"], "code_stage")

        self.assertEqual(stages[0]["code_stage_id"], "generate-local-code-stage-example")

        self.assertEqual(stages[1]["stage_kind"], "verification")

        self.assertEqual(stages[1]["suite"], "full")

    def test_queue_stages_have_required_fields(self):

        payload = json.loads(QUEUE.read_text(encoding="utf-8"))

        for stage in payload["stages"]:

            required = {

                "task_id",

                "stage_id",

                "stage_kind",

                "mode",

                "commit_message",

                "allow_commit",

                "allow_push_feature_branch",

            }

            self.assertTrue(required.issubset(set(stage)))

            self.assertIn(stage["stage_kind"], {"code_stage", "verification"})

            self.assertFalse(stage["allow_commit"])

            self.assertFalse(stage["allow_push_feature_branch"])

    def test_code_stage_reference_is_registered(self):

        queue = json.loads(QUEUE.read_text(encoding="utf-8"))

        registry = json.loads(CODE_STAGE_REGISTRY.read_text(encoding="utf-8"))

        registered = {stage["stage_id"] for stage in registry["stages"]}

        code_stage_ids = {

            stage["code_stage_id"]

            for stage in queue["stages"]

            if stage["stage_kind"] == "code_stage"

        }

        self.assertTrue(code_stage_ids.issubset(registered))

    def test_runbook_records_boundaries(self):

        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("It remains local-only.", text)

        self.assertIn("It does not call cloud AI.", text)

        self.assertIn("It does not run freeform shell commands.", text)

        self.assertIn("It does not generate unbounded code.", text)

        self.assertIn("It does not merge main.", text)

        self.assertIn("It does not push main.", text)

        self.assertIn("It does not delete branches.", text)

        self.assertIn("It does not read secrets.", text)

    def test_runbook_records_non_overclaim(self):

        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("This integration does not allow freeform coding.", text)

        self.assertIn("It does not authorize cloud AI.", text)

        self.assertIn("It does not replace human merge review.", text)

        self.assertIn("predefined local code stages and verification stages", text)

if __name__ == "__main__":

    unittest.main()

