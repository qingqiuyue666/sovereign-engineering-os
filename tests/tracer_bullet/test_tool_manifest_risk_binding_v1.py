"""Tracer-bullet tests for tool manifest risk binding v1."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.runtime.tool_manifest_normalizer import normalize_tool_manifest_candidate
from kernel.runtime.tool_manifest_risk_binding import bind_tool_manifest_risk

POLICY_PATH = Path("governance/tools/tool_manifest_risk_binding_v1.json")
SOURCE_PATH = Path("kernel/runtime/tool_manifest_risk_binding.py")


def _candidate(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "source_type": "CLI_TOOL",
        "tool_name": "Read Only Tool",
        "declared_capabilities": ["read_only"],
        "declared_inputs": {"schema": "metadata"},
        "declared_outputs": {"schema": "metadata"},
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
    return fields


def _manifest(**overrides: object):
    return normalize_tool_manifest_candidate(_candidate(**overrides))


class ToolManifestRiskBindingTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "tool_manifest_risk_binding_v1")
        self.assertTrue(policy["binding_only"])
        self.assertTrue(policy["uses_tool_manifest_normalizer"])
        self.assertTrue(policy["uses_tool_risk_classifier"])
        self.assertFalse(policy["duplicates_classifier_logic"])
        self.assertFalse(policy["execution_allowed"])
        self.assertFalse(policy["subprocess_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["dcc_launch_allowed"])
        self.assertFalse(policy["comfyui_launch_allowed"])

    def test_mcp_tool_manifest_produces_mcp_tool_risk(self):
        report = bind_tool_manifest_risk(
            _manifest(source_type="MCP_TOOL", declared_capabilities=["read_only"])
        )
        self.assertIn("MCP_TOOL", report.risk_classes)
        self.assertEqual(report.source_type, "MCP_TOOL")

    def test_cli_read_only_manifest_low_risk(self):
        report = bind_tool_manifest_risk(_manifest())
        self.assertEqual(report.risk_classes, ("READ_ONLY",))
        self.assertEqual(report.highest_risk, "READ_ONLY")
        self.assertFalse(report.approval_required)
        self.assertFalse(report.production_admission_allowed)

    def test_local_script_with_process_scope_escalates(self):
        report = bind_tool_manifest_risk(
            _manifest(
                source_type="LOCAL_SCRIPT",
                declared_capabilities=["read_only"],
                process_scope="launch",
            )
        )
        self.assertIn("PROCESS_LAUNCH", report.risk_classes)
        self.assertTrue(report.approval_required)

    def test_dcc_app_escalates_and_requires_approval(self):
        report = bind_tool_manifest_risk(
            _manifest(
                source_type="DCC_APP",
                tool_name="Houdini",
                declared_capabilities=["read_only"],
                dcc_scope="metadata_only",
            )
        )
        self.assertIn("DCC_CONTROL", report.risk_classes)
        self.assertTrue(report.approval_required)

    def test_comfyui_workflow_escalates_and_requires_approval(self):
        report = bind_tool_manifest_risk(
            _manifest(
                source_type="COMFYUI_WORKFLOW",
                declared_capabilities=["read_only"],
                model_scope="metadata_only",
            )
        )
        self.assertIn("COMFYUI_EXECUTION", report.risk_classes)
        self.assertIn("MODEL_EXECUTION", report.risk_classes)
        self.assertTrue(report.approval_required)

    def test_browser_automation_escalates_and_requires_approval(self):
        report = bind_tool_manifest_risk(
            _manifest(
                source_type="BROWSER_AUTOMATION_TOOL",
                declared_capabilities=["read_only"],
            )
        )
        self.assertIn("BROWSER_CONTROL", report.risk_classes)
        self.assertTrue(report.approval_required)

    def test_provider_api_escalates_and_requires_approval(self):
        report = bind_tool_manifest_risk(
            _manifest(
                source_type="API_ADAPTER",
                declared_capabilities=["read_only"],
                provider_scope="metadata_only",
            )
        )
        self.assertIn("PROVIDER_API", report.risk_classes)
        self.assertTrue(report.approval_required)

    def test_credential_scope_becomes_high_risk(self):
        report = bind_tool_manifest_risk(
            _manifest(credential_scope="metadata_only", declared_capabilities=["read_only"])
        )
        self.assertIn("CREDENTIAL_TOUCHING", report.risk_classes)
        self.assertEqual(report.highest_risk, "HIGH_RISK")

    def test_unknown_manifest_source_fails_closed_high_risk(self):
        report = bind_tool_manifest_risk(
            _manifest(source_type="NOT_A_SOURCE", declared_capabilities=["read_only"])
        )
        self.assertEqual(report.source_type, "UNKNOWN")
        self.assertEqual(report.highest_risk, "HIGH_RISK")
        self.assertTrue(report.approval_required)

    def test_production_admission_false_for_high_risk(self):
        report = bind_tool_manifest_risk(
            _manifest(source_type="DCC_APP", dcc_scope="metadata_only")
        )
        self.assertFalse(report.production_admission_allowed)

    def test_binding_hash_deterministic(self):
        manifest = _manifest(source_type="API_ADAPTER", provider_scope="metadata_only")
        first = bind_tool_manifest_risk(
            manifest, observed_at="2026-05-25T00:00:00+00:00"
        )
        second = bind_tool_manifest_risk(
            manifest, observed_at="2030-01-01T00:00:00+00:00"
        )
        self.assertEqual(first.binding_hash, second.binding_hash)
        self.assertNotEqual(first.observed_at, second.observed_at)

    def test_no_execution_subprocess_network_browser_provider_or_dcc_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "requests",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "bpy",
        ):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
