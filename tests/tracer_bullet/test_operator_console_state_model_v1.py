"""Tracer-bullet tests for operator console state model v1."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.runtime.operator_console_state_model import (
    ALLOWED_UI_ACTION_TYPES,
    REQUIRED_PANELS,
    build_operator_console_state,
    validate_console_action,
)

POLICY_PATH = Path("governance/operator/operator_console_state_model_v1.json")
SOURCE_PATH = Path("kernel/runtime/operator_console_state_model.py")


class OperatorConsoleStateModelTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundaries(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "operator_console_state_model_v1")
        self.assertTrue(policy["state_model_only"])
        self.assertFalse(policy["ui_runtime_present"])
        self.assertFalse(policy["tauri_dependency_added"])
        self.assertFalse(policy["web_server_added"])
        self.assertFalse(policy["frontend_runtime_added"])
        self.assertFalse(policy["production_autonomy_allowed"])

    def test_all_required_panels_present(self):
        state = build_operator_console_state()
        panel_ids = {panel.panel_id for panel in state.panels}
        self.assertTrue(set(REQUIRED_PANELS).issubset(panel_ids))

    def test_dangerous_action_requires_approval(self):
        rejected = validate_console_action(
            {"action_type": "command_id", "command_id": "diff_check"}
        )
        self.assertFalse(rejected.accepted)
        self.assertTrue(rejected.approval_required)
        self.assertIn("approval_required_for_dangerous_action", rejected.failures)

        accepted = validate_console_action(
            {
                "action_type": "command_id",
                "command_id": "diff_check",
                "approval_decision": "APPROVED",
            }
        )
        self.assertTrue(accepted.accepted)

    def test_ui_action_cannot_include_raw_command(self):
        result = validate_console_action(
            {"action_type": "task_intent", "raw_command": "rm -rf"}
        )
        self.assertFalse(result.accepted)
        self.assertIn("raw_command_forbidden", result.failures)

    def test_ui_action_cannot_include_arbitrary_argv(self):
        result = validate_console_action(
            {"action_type": "task_intent", "payload": {"argv": ["python3"]}}
        )
        self.assertFalse(result.accepted)
        self.assertIn("argv_forbidden", result.failures)

    def test_ui_action_cannot_include_command_line(self):
        result = validate_console_action(
            {"action_type": "task_intent", "command_line": "python3 -m unittest"}
        )
        self.assertFalse(result.accepted)
        self.assertIn("command_line_forbidden", result.failures)

    def test_ui_can_only_submit_allowed_action_types(self):
        for action_type in ALLOWED_UI_ACTION_TYPES:
            with self.subTest(action_type=action_type):
                payload = {"action_type": action_type}
                if action_type == "command_id":
                    payload["approval_decision"] = "APPROVED"
                self.assertNotIn(
                    "action_type_not_allowed",
                    validate_console_action(payload).failures,
                )
        result = validate_console_action({"action_type": "raw_command"})
        self.assertFalse(result.accepted)
        self.assertIn("action_type_not_allowed", result.failures)

    def test_tauri_listed_as_candidate_only(self):
        state = build_operator_console_state()
        tauri = [shell for shell in state.candidate_ui_shells if shell.candidate_id == "tauri"]
        self.assertEqual(len(tauri), 1)
        self.assertFalse(tauri[0].direct_dependency_allowed_now)
        self.assertFalse(tauri[0].runtime_integration_allowed_now)

    def test_no_ui_dependency_added(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        forbidden_imports = (
            "tauri",
            "electron",
            "PySide6",
            "PyQt",
            "flask",
            "fastapi",
            "uvicorn",
            "django",
            "streamlit",
        )
        for forbidden in forbidden_imports:
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
