"""Tracer-bullet tests for tool risk classifier v1."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.runtime.tool_risk_classifier import (
    HIGH_RISK,
    ToolRiskDescriptor,
    classify_tool_risk,
)

POLICY_PATH = Path("governance/tools/tool_risk_classifier_v1.json")
SOURCE_PATH = Path("kernel/runtime/tool_risk_classifier.py")


def _descriptor(**overrides: object) -> ToolRiskDescriptor:
    fields = {
        "tool_id": "tool.readonly",
        "source_type": "read_only_tool",
        "declared_capabilities": ("read_only",),
        "filesystem_scope": "none",
        "network_scope": "none",
        "process_scope": "none",
        "credential_scope": "none",
        "provider_scope": "none",
        "dcc_scope": "none",
        "model_scope": "none",
        "browser_scope": "none",
        "plugin_scope": "none",
    }
    fields.update(overrides)
    return ToolRiskDescriptor(**fields)


class ToolRiskClassifierTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "tool_risk_classifier_v1")
        self.assertFalse(policy["execution_allowed"])
        self.assertFalse(policy["subprocess_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["credential_storage_allowed"])
        self.assertFalse(policy["dcc_launch_allowed"])
        self.assertFalse(policy["comfyui_launch_allowed"])
        self.assertFalse(policy["production_autonomy_allowed"])
        self.assertIn(HIGH_RISK, policy["risk_classes"])

    def test_read_only_descriptor_classified_low_risk(self):
        assessment = classify_tool_risk(_descriptor())
        self.assertEqual(assessment.risk_classes, ("READ_ONLY",))
        self.assertEqual(assessment.highest_risk, "READ_ONLY")
        self.assertFalse(assessment.approval_required)
        self.assertFalse(assessment.token_required)
        self.assertTrue(assessment.production_admission_allowed)

    def test_local_file_write_escalates(self):
        assessment = classify_tool_risk(
            _descriptor(
                declared_capabilities=("read_only", "local_file_write"),
                filesystem_scope="write",
            )
        )
        self.assertIn("LOCAL_FILE_WRITE", assessment.risk_classes)
        self.assertTrue(assessment.approval_required)
        self.assertFalse(assessment.production_admission_allowed)

    def test_process_launch_escalates(self):
        assessment = classify_tool_risk(
            _descriptor(
                source_type="local_script",
                declared_capabilities=("process_launch",),
                process_scope="launch",
            )
        )
        self.assertIn("PROCESS_LAUNCH", assessment.risk_classes)
        self.assertTrue(assessment.approval_required)

    def test_network_escalates(self):
        assessment = classify_tool_risk(
            _descriptor(declared_capabilities=("network_access",), network_scope="egress")
        )
        self.assertIn("NETWORK_ACCESS", assessment.risk_classes)
        self.assertTrue(assessment.approval_required)

    def test_browser_escalates(self):
        assessment = classify_tool_risk(
            _descriptor(
                source_type="browser_automation",
                declared_capabilities=("browser_control",),
                browser_scope="control",
            )
        )
        self.assertIn("BROWSER_CONTROL", assessment.risk_classes)
        self.assertTrue(assessment.approval_required)

    def test_provider_api_escalates(self):
        assessment = classify_tool_risk(
            _descriptor(
                source_type="provider_api",
                declared_capabilities=("provider_api",),
                provider_scope="api",
            )
        )
        self.assertIn("PROVIDER_API", assessment.risk_classes)
        self.assertTrue(assessment.approval_required)

    def test_credential_touching_becomes_high_risk(self):
        assessment = classify_tool_risk(
            _descriptor(
                declared_capabilities=("credential_touching",),
                credential_scope="secret",
            )
        )
        self.assertIn("CREDENTIAL_TOUCHING", assessment.risk_classes)
        self.assertEqual(assessment.highest_risk, HIGH_RISK)
        self.assertFalse(assessment.production_admission_allowed)

    def test_dcc_control_requires_approval(self):
        assessment = classify_tool_risk(
            _descriptor(
                source_type="dcc_app",
                declared_capabilities=("dcc_control",),
                dcc_scope="houdini",
            )
        )
        self.assertIn("DCC_CONTROL", assessment.risk_classes)
        self.assertTrue(assessment.approval_required)
        self.assertFalse(assessment.production_admission_allowed)

    def test_comfyui_execution_requires_approval(self):
        assessment = classify_tool_risk(
            _descriptor(
                source_type="comfyui_workflow",
                declared_capabilities=("comfyui_execution",),
                process_scope="launch",
            )
        )
        self.assertIn("COMFYUI_EXECUTION", assessment.risk_classes)
        self.assertTrue(assessment.approval_required)
        self.assertFalse(assessment.production_admission_allowed)

    def test_model_execution_requires_approval(self):
        assessment = classify_tool_risk(
            _descriptor(
                source_type="model_runtime",
                declared_capabilities=("model_execution",),
                model_scope="local_model",
            )
        )
        self.assertIn("MODEL_EXECUTION", assessment.risk_classes)
        self.assertTrue(assessment.approval_required)

    def test_mcp_tool_classified_without_execution(self):
        assessment = classify_tool_risk(
            _descriptor(source_type="mcp_server", declared_capabilities=("mcp_tool",))
        )
        self.assertIn("MCP_TOOL", assessment.risk_classes)
        self.assertFalse(assessment.production_admission_allowed)

    def test_plugin_execution_requires_sandbox_strategy(self):
        assessment = classify_tool_risk(
            _descriptor(
                source_type="plugin",
                declared_capabilities=("plugin_execution",),
                plugin_scope="unsandboxed",
            )
        )
        self.assertIn("PLUGIN_EXECUTION", assessment.risk_classes)
        self.assertEqual(assessment.highest_risk, HIGH_RISK)
        self.assertIn("plugin_sandbox_strategy_required", assessment.reasons)

    def test_unknown_capability_fails_closed_high_risk(self):
        assessment = classify_tool_risk(
            _descriptor(declared_capabilities=("unknown_magic",))
        )
        self.assertEqual(assessment.highest_risk, HIGH_RISK)
        self.assertFalse(assessment.production_admission_allowed)

    def test_missing_source_type_fails_closed_high_risk(self):
        assessment = classify_tool_risk(_descriptor(source_type=""))
        self.assertEqual(assessment.highest_risk, HIGH_RISK)
        self.assertIn("source_type_required", assessment.reasons)

    def test_high_risk_cannot_be_production_admitted(self):
        assessment = classify_tool_risk(
            _descriptor(declared_capabilities=("high_risk",))
        )
        self.assertEqual(assessment.highest_risk, HIGH_RISK)
        self.assertFalse(assessment.production_admission_allowed)

    def test_content_hash_deterministic(self):
        first = classify_tool_risk(_descriptor(filesystem_scope="read"))
        second = classify_tool_risk(_descriptor(filesystem_scope="read"))
        self.assertEqual(first.content_hash, second.content_hash)

    def test_no_execution_subprocess_or_network_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "requests",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
        ):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
