
"""Tests for local train runner."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

RUNNER = Path("tools/local_train_runner.py")

POLICY = Path("governance/security/local_train_runner_policy_v1.json")

RUNBOOK = Path("docs/runbooks/local_train_runner_v1.md")

QUEUE = Path("governance/local_train/task_queue_v1.json")

class LocalTrainRunnerTests(unittest.TestCase):

    def test_files_exist(self):

        self.assertTrue(RUNNER.is_file())

        self.assertTrue(POLICY.is_file())

        self.assertTrue(RUNBOOK.is_file())

        self.assertTrue(QUEUE.is_file())

    def test_policy_is_active_and_local_only(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["policy_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertEqual(payload["authority_model"]["cloud_ai_role"], "none")

        self.assertTrue(payload["authority_model"]["local_terminal_remains_authority"])

    def test_policy_forbids_high_risk_actions(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        forbidden = set(payload["forbidden_actions"])

        required = {

            "git_merge",

            "git_push_main",

            "git_branch_delete",

            "secret_read",

            "env_read",

            "cloud_ai_api_call",

            "provider_live_execution",

            "vault_live_write",

            "production_autonomy",

            "deployment",

        }

        self.assertTrue(required.issubset(forbidden))

    def test_runner_has_required_modes_and_suites(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn('"verify"', source)

        self.assertIn('"commit"', source)

        self.assertIn('"commit-push"', source)

        self.assertIn('"overnight"', source)

        self.assertIn('"local-core"', source)

        self.assertIn('"full"', source)

    def test_runner_blocks_main_branch_mutation(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn("push_main_forbidden", source)

        self.assertIn("main_branch_mutation_forbidden", source)

        self.assertIn("is_main_branch", source)

    def test_runner_does_not_contain_merge_or_branch_delete_commands(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertNotIn('("git", "merge"', source)

        self.assertNotIn('("git", "branch", "-D"', source)

        self.assertNotIn('("git", "branch", "-d"', source)

    def test_runner_writes_reports_and_logs(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn("outputs/logs/local_train_runner.log", source)

        self.assertIn("outputs/reports/local_train_runner_report.md", source)

        self.assertIn("outputs/reports/local_train_runner_summary.json", source)

    def test_runner_records_dirty_worktree_and_first_failure(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn("dirty_worktree", source)

        self.assertIn("first_failure", source)

        self.assertIn("git_status_short", source)

    def test_runner_supports_queue_execution(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn("def run_queue", source)

        self.assertIn("def load_queue", source)

        self.assertIn("--queue", source)

    def test_queue_is_valid(self):

        payload = json.loads(QUEUE.read_text(encoding="utf-8"))

        self.assertEqual(payload["queue_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertIsInstance(payload["tasks"], list)

        self.assertGreaterEqual(len(payload["tasks"]), 1)

    def test_runbook_records_forbidden_actions(self):

        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("no cloud AI API calls", text)

        self.assertIn("no merge", text)

        self.assertIn("no push to main", text)

        self.assertIn("no branch deletion", text)

        self.assertIn("no secret reads", text)

    def test_runner_py_compile_target_is_present(self):

        source = RUNNER.read_text(encoding="utf-8")

        self.assertIn("if __name__ == \"__main__\":", source)

        self.assertIn("raise SystemExit(main())", source)

if __name__ == "__main__":

    unittest.main()

