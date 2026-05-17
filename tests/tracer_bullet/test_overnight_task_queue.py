
"""Tests for overnight task queue extension."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

RUNNER = Path("tools/local_train_runner.py")

POLICY = Path("governance/security/overnight_task_queue_policy_v1.json")

QUEUE = Path("governance/local_train/overnight_task_queue_v1.json")

RUNBOOK = Path("docs/runbooks/overnight_task_queue_v1.md")

class OvernightTaskQueueTests(unittest.TestCase):

    def test_files_exist(self):

        self.assertTrue(RUNNER.is_file())

        self.assertTrue(POLICY.is_file())

        self.assertTrue(QUEUE.is_file())

        self.assertTrue(RUNBOOK.is_file())

    def test_policy_is_active(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["policy_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertEqual(payload["max_runtime_seconds_default"], 28800)

    def test_policy_forbids_high_risk_actions(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        forbidden = set(payload["forbidden_actions"])

        required = {

            "git_merge",

            "git_push_main",

            "git_branch_delete",

            "main_branch_modification",

            "secret_read",

            "env_read",

            "cloud_ai_api_call",

            "provider_live_execution",

            "vault_live_write",

            "production_autonomy",

            "deployment",

            "unbounded_runtime",

        }

        self.assertTrue(required.issubset(forbidden))

    def test_policy_requires_overnight_outputs(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        outputs = set(payload["required_outputs"])

        required = {

            "outputs/logs/overnight_task_queue.log",

            "outputs/reports/overnight_task_queue_report.md",

            "outputs/reports/overnight_task_queue_summary.json",

            "outputs/reports/overnight_task_queue_index.json",

            "outputs/state/overnight_task_queue_resume.json",

            "outputs/state/overnight_task_queue_heartbeat.json",

        }

        self.assertTrue(required.issubset(outputs))

    def test_queue_is_active_and_bounded(self):

        payload = json.loads(QUEUE.read_text(encoding="utf-8"))

        self.assertEqual(payload["queue_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertEqual(payload["queue_mode"], "overnight")

        self.assertEqual(payload["max_runtime_seconds"], 28800)

        self.assertTrue(payload["stop_on_first_failure"])

        self.assertIsInstance(payload["tasks"], list)

        self.assertGreaterEqual(len(payload["tasks"]), 2)

    def test_queue_tasks_have_required_fields(self):

        payload = json.loads(QUEUE.read_text(encoding="utf-8"))

        required = {

            "task_id",

            "stage_id",

            "suite",

            "mode",

            "commit_message",

            "allow_commit",

            "allow_push_feature_branch",

        }

        for task in payload["tasks"]:

            self.assertTrue(required.issubset(set(task)))

            self.assertIn(task["suite"], {"local-core", "full"})

            self.assertIn(task["mode"], {"verify", "overnight", "commit", "commit-push"})

    def test_runner_defines_overnight_output_paths(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn("OVERNIGHT_LOG_PATH", source)

        self.assertIn("OVERNIGHT_REPORT_PATH", source)

        self.assertIn("OVERNIGHT_SUMMARY_PATH", source)

        self.assertIn("OVERNIGHT_INDEX_PATH", source)

        self.assertIn("OVERNIGHT_RESUME_PATH", source)

        self.assertIn("OVERNIGHT_HEARTBEAT_PATH", source)

    def test_runner_writes_heartbeat_resume_and_reports(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn("def write_overnight_state", source)

        self.assertIn("def write_overnight_reports", source)

        self.assertIn("OVERNIGHT_HEARTBEAT_PATH.write_text", source)

        self.assertIn("OVERNIGHT_RESUME_PATH.write_text", source)

        self.assertIn("OVERNIGHT_SUMMARY_PATH.write_text", source)

        self.assertIn("OVERNIGHT_INDEX_PATH.write_text", source)

        self.assertIn("OVERNIGHT_REPORT_PATH.write_text", source)

    def test_runner_queue_records_stage_status(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn("stage_index", source)

        self.assertIn("stage_count", source)

        self.assertIn("stage_id", source)

        self.assertIn("task_id", source)

        self.assertIn("completed_stage_count", source)

        self.assertIn("stop on first failure", RUNBOOK.read_text(encoding="utf-8"))

    def test_runner_keeps_forbidden_main_controls(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn("push_main_forbidden", source)

        self.assertIn("main_branch_mutation_forbidden", source)

        self.assertNotIn('("git", "merge"', source)

        self.assertNotIn('("git", "branch", "-D"', source)

        self.assertNotIn('("git", "branch", "-d"', source)

    def test_runbook_records_non_overclaim(self):

        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("It does not call cloud AI.", text)

        self.assertIn("It does not merge main.", text)

        self.assertIn("It does not push main.", text)

        self.assertIn("It does not delete branches.", text)

        self.assertIn("It does not replace human merge review.", text)

        self.assertIn("It does not complete the system by itself.", text)

if __name__ == "__main__":

    unittest.main()

