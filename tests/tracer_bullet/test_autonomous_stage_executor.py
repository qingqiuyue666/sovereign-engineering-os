
"""Tests for autonomous local stage executor."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

from tools.local_stage_executor import (

    FORBIDDEN_STAGE_TYPES,

    find_script,

    load_registry,

    validate_script,

)

POLICY = Path("governance/security/autonomous_stage_executor_policy_v1.json")

REGISTRY = Path("governance/local_train/stage_script_registry_v1.json")

RUNBOOK = Path("docs/runbooks/autonomous_stage_executor_v1.md")

EXECUTOR = Path("tools/local_stage_executor.py")

VERIFY_LOCAL_CORE = Path("tools/local_stage_scripts/verify_local_core.py")

VERIFY_FULL = Path("tools/local_stage_scripts/verify_full.py")

class AutonomousStageExecutorTests(unittest.TestCase):

    def test_files_exist(self):

        self.assertTrue(POLICY.is_file())

        self.assertTrue(REGISTRY.is_file())

        self.assertTrue(RUNBOOK.is_file())

        self.assertTrue(EXECUTOR.is_file())

        self.assertTrue(VERIFY_LOCAL_CORE.is_file())

        self.assertTrue(VERIFY_FULL.is_file())

    def test_policy_is_active(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["policy_name"], "autonomous_stage_executor_policy_v1")

        self.assertEqual(payload["policy_version"], "v1")

        self.assertEqual(payload["status"], "active")

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

    def test_registry_is_active_and_allowlisted(self):

        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))

        self.assertEqual(payload["registry_name"], "stage_script_registry_v1")

        self.assertEqual(payload["registry_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertEqual(payload["default_rule"], "allowlisted_local_scripts_only")

        self.assertIsInstance(payload["scripts"], list)

        self.assertGreaterEqual(len(payload["scripts"]), 2)

    def test_registry_forbids_cloud_and_production_stage_types(self):

        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))

        forbidden = set(payload["forbidden_stage_types"])

        required = {

            "cloud_ai",

            "freeform_shell",

            "production_execution",

            "provider_live_execution",

            "vault_live_write",

            "deployment",

        }

        self.assertTrue(required.issubset(forbidden))

    def test_find_registered_scripts(self):

        registry = load_registry()

        local_core = find_script("verify-local-core", registry)

        full = find_script("verify-full", registry)

        self.assertEqual(local_core.script_path, "tools/local_stage_scripts/verify_local_core.py")

        self.assertEqual(full.script_path, "tools/local_stage_scripts/verify_full.py")

    def test_registered_scripts_validate(self):

        registry = load_registry()

        for script_id in ("verify-local-core", "verify-full"):

            script = find_script(script_id, registry)

            self.assertEqual(validate_script(script), ())

    def test_unregistered_script_rejected(self):

        registry = load_registry()

        with self.assertRaises(ValueError):

            find_script("missing-script", registry)

    def test_forbidden_stage_types_are_declared(self):

        self.assertIn("cloud_ai", FORBIDDEN_STAGE_TYPES)

        self.assertIn("freeform_shell", FORBIDDEN_STAGE_TYPES)

        self.assertIn("production_execution", FORBIDDEN_STAGE_TYPES)

        self.assertIn("provider_live_execution", FORBIDDEN_STAGE_TYPES)

        self.assertIn("vault_live_write", FORBIDDEN_STAGE_TYPES)

        self.assertIn("deployment", FORBIDDEN_STAGE_TYPES)

    def test_executor_source_has_safety_outputs(self):

        source = EXECUTOR.read_text(encoding="utf-8")

        self.assertIn("autonomous_stage_executor.log", source)

        self.assertIn("autonomous_stage_executor_report.md", source)

        self.assertIn("autonomous_stage_executor_summary.json", source)

        self.assertIn("push_main_forbidden", source)

        self.assertIn("no freeform shell", source)

    def test_executor_does_not_contain_merge_or_branch_delete_commands(self):

        source = EXECUTOR.read_text(encoding="utf-8")

        self.assertNotIn('("git", "merge"', source)

        self.assertNotIn('("git", "branch", "-D"', source)

        self.assertNotIn('("git", "branch", "-d"', source)

    def test_runbook_records_boundaries(self):

        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("It does not call cloud AI.", text)

        self.assertIn("It does not run freeform shell commands.", text)

        self.assertIn("It does not merge main.", text)

        self.assertIn("It does not push main.", text)

        self.assertIn("It does not delete branches.", text)

        self.assertIn("It does not read secrets.", text)

    def test_stage_scripts_compile_target_present(self):

        local_core = VERIFY_LOCAL_CORE.read_text(encoding="utf-8")

        full = VERIFY_FULL.read_text(encoding="utf-8")

        self.assertIn('if __name__ == "__main__":', local_core)

        self.assertIn('if __name__ == "__main__":', full)

        self.assertIn("raise SystemExit(main())", local_core)

        self.assertIn("raise SystemExit(main())", full)

if __name__ == "__main__":

    unittest.main()

