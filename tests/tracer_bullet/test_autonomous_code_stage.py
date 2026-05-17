
"""Tests for autonomous local code stage executor."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

from tools.local_code_stage_executor import (

    ALLOWED_STAGE_TYPES,

    FORBIDDEN_STAGE_TYPES,

    MAX_FILES_CHANGED_PER_STAGE,

    MAX_LINES_ADDED_PER_STAGE,

    find_stage,

    load_registry,

    validate_stage,

)

POLICY = Path("governance/security/autonomous_code_stage_policy_v1.json")

REGISTRY = Path("governance/local_train/code_stage_registry_v1.json")

EXECUTOR = Path("tools/local_code_stage_executor.py")

GENERATOR = Path("tools/local_code_stages/generate_local_code_stage_example.py")

GENERATED_DOC = Path("docs/runbooks/generated_local_code_stage_example_v1.md")

GENERATED_POLICY = Path("governance/local_train/generated_local_code_stage_example_v1.json")

GENERATED_TEST = Path("tests/tracer_bullet/test_generated_local_code_stage_example.py")

class AutonomousCodeStageTests(unittest.TestCase):

    def test_files_exist(self):

        self.assertTrue(POLICY.is_file())

        self.assertTrue(REGISTRY.is_file())

        self.assertTrue(EXECUTOR.is_file())

        self.assertTrue(GENERATOR.is_file())

        self.assertTrue(GENERATED_DOC.is_file())

        self.assertTrue(GENERATED_POLICY.is_file())

        self.assertTrue(GENERATED_TEST.is_file())

    def test_policy_is_active(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["policy_name"], "autonomous_code_stage_policy_v1")

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

    def test_policy_line_budget(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["line_budget"]["max_lines_added_per_stage"], 2000)

        self.assertEqual(payload["line_budget"]["max_files_changed_per_stage"], 12)

        self.assertTrue(payload["line_budget"]["reject_if_unbounded"])

    def test_registry_is_active(self):

        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))

        self.assertEqual(payload["registry_name"], "code_stage_registry_v1")

        self.assertEqual(payload["registry_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertEqual(payload["default_rule"], "predefined_local_code_stages_only")

    def test_registry_forbids_cloud_and_unbounded_generation(self):

        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))

        forbidden = set(payload["forbidden_stage_types"])

        required = {

            "cloud_ai",

            "freeform_shell",

            "production_execution",

            "provider_live_execution",

            "vault_live_write",

            "deployment",

            "unbounded_generation",

        }

        self.assertTrue(required.issubset(forbidden))

    def test_stage_types_declared(self):

        self.assertIn("local_code_generation", ALLOWED_STAGE_TYPES)

        self.assertIn("local_code_patch", ALLOWED_STAGE_TYPES)

        self.assertIn("verification", ALLOWED_STAGE_TYPES)

        self.assertIn("cloud_ai", FORBIDDEN_STAGE_TYPES)

        self.assertIn("freeform_shell", FORBIDDEN_STAGE_TYPES)

        self.assertIn("unbounded_generation", FORBIDDEN_STAGE_TYPES)

    def test_line_budget_constants(self):

        self.assertEqual(MAX_LINES_ADDED_PER_STAGE, 2000)

        self.assertEqual(MAX_FILES_CHANGED_PER_STAGE, 12)

    def test_find_registered_code_stage(self):

        registry = load_registry()

        stage = find_stage("generate-local-code-stage-example", registry)

        self.assertEqual(stage.stage_id, "generate-local-code-stage-example")

        self.assertEqual(stage.stage_type, "local_code_generation")

        self.assertEqual(stage.script_path, "tools/local_code_stages/generate_local_code_stage_example.py")

    def test_registered_code_stage_validates(self):

        registry = load_registry()

        stage = find_stage("generate-local-code-stage-example", registry)

        self.assertEqual(validate_stage(stage), ())

    def test_generated_policy_is_local_only(self):

        payload = json.loads(GENERATED_POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["artifact_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertFalse(payload["cloud_ai_used"])

        self.assertFalse(payload["freeform_shell_used"])

        self.assertFalse(payload["secret_read"])

    def test_executor_source_records_required_outputs(self):

        source = EXECUTOR.read_text(encoding="utf-8")

        self.assertIn("autonomous_code_stage.log", source)

        self.assertIn("autonomous_code_stage_report.md", source)

        self.assertIn("autonomous_code_stage_summary.json", source)

        self.assertIn("autonomous_code_stage_diff.json", source)

    def test_executor_source_forbids_dangerous_surfaces(self):

        source = EXECUTOR.read_text(encoding="utf-8")

        self.assertIn("cloud_ai", source)

        self.assertIn("freeform_shell", source)

        self.assertIn("provider_live_execution", source)

        self.assertIn("vault_live_write", source)

        self.assertIn("production_autonomy", source)

        self.assertNotIn('("git", "merge"', source)

        self.assertNotIn('("git", "branch", "-D"', source)

        self.assertNotIn('("git", "branch", "-d"', source)

    def test_generator_has_static_allowlisted_outputs(self):

        source = GENERATOR.read_text(encoding="utf-8")

        self.assertIn("ALLOWED_OUTPUTS", source)

        self.assertIn("assert_allowed", source)

        self.assertIn("write_path_not_allowlisted", source)

        self.assertIn("cloud_ai_used", source)

    def test_unregistered_stage_rejected(self):

        registry = load_registry()

        with self.assertRaises(ValueError):

            find_stage("missing-code-stage", registry)

if __name__ == "__main__":

    unittest.main()

