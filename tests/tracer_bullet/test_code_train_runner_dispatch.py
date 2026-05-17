
"""Tests for code train runner dispatch."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

POLICY = Path("governance/security/code_train_runner_dispatch_policy_v1.json")

RUNBOOK = Path("docs/runbooks/code_train_runner_dispatch_v1.md")

RUNNER = Path("tools/local_train_runner.py")

QUEUE = Path("governance/local_train/autonomous_code_train_queue_v1.json")

CODE_EXECUTOR = Path("tools/local_code_stage_executor.py")

class CodeTrainRunnerDispatchTests(unittest.TestCase):

    def test_files_exist(self):

        self.assertTrue(POLICY.is_file())

        self.assertTrue(RUNBOOK.is_file())

        self.assertTrue(RUNNER.is_file())

        self.assertTrue(QUEUE.is_file())

        self.assertTrue(CODE_EXECUTOR.is_file())

    def test_policy_is_active(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["policy_name"], "code_train_runner_dispatch_policy_v1")

        self.assertEqual(payload["policy_version"], "v1")

        self.assertEqual(payload["status"], "active")

    def test_policy_allows_verification_and_code_stage_only(self):

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

    def test_policy_requires_dispatch_guards(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        guards = set(payload["required_guards"])

        required = {

            "stage_kind_must_be_known",

            "code_stage_id_required_for_code_stage",

            "suite_required_for_verification",

            "code_stage_dispatched_through_local_executor",

            "verification_dispatched_through_local_runner",

            "stop_on_first_failure",

            "heartbeat_written",

            "resume_marker_written",

            "main_branch_mutation_rejected",

            "cloud_ai_calls_forbidden",

            "secrets_forbidden",

            "merge_forbidden",

            "branch_delete_forbidden",

            "unbounded_generation_forbidden",

        }

        self.assertTrue(required.issubset(guards))

    def test_runner_dispatches_code_stage_kind(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn('stage_kind = str(task.get("stage_kind", "verification"))', source)

        self.assertIn('elif stage_kind == "code_stage":', source)

        self.assertIn('"tools/local_code_stage_executor.py"', source)

        self.assertIn('"--stage-id"', source)

        self.assertIn("code_stage_id_required", source)

    def test_runner_keeps_verification_dispatch_path(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn('if stage_kind == "verification":', source)

        self.assertIn("run_suite(", source)

    def test_runner_rejects_unknown_stage_kind(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn("exit_code = 97", source)

    def test_queue_contains_code_stage_then_verification(self):

        payload = json.loads(QUEUE.read_text(encoding="utf-8"))

        stages = payload["stages"]

        self.assertEqual(stages[0]["stage_kind"], "code_stage")

        self.assertEqual(stages[0]["code_stage_id"], "generate-local-code-stage-example")

        self.assertEqual(stages[1]["stage_kind"], "verification")

        self.assertEqual(stages[1]["suite"], "full")

    def test_runbook_records_dispatch_boundaries(self):

        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("It does not call cloud AI.", text)

        self.assertIn("It does not run freeform shell commands.", text)

        self.assertIn("It does not generate unbounded code.", text)

        self.assertIn("It does not merge main.", text)

        self.assertIn("It does not push main.", text)

        self.assertIn("It does not delete branches.", text)

        self.assertIn("It does not read secrets.", text)

    def test_runbook_records_non_overclaim(self):

        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("This dispatch layer does not authorize freeform coding.", text)

        self.assertIn("It does not authorize cloud AI.", text)

        self.assertIn("It does not replace human merge review.", text)

        self.assertIn("registered local code stages into the existing queue execution path", text)

if __name__ == "__main__":

    unittest.main()

