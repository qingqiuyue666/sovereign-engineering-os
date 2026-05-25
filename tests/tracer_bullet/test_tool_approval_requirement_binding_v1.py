"""Tracer-bullet tests for tool approval requirement binding v1."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.runtime.tool_approval_requirement_binding import (
    ApprovalRequirement,
    generate_approval_requirement,
)
from kernel.runtime.tool_manifest_normalizer import normalize_tool_manifest_candidate
from kernel.runtime.tool_manifest_risk_binding import bind_tool_manifest_risk
from kernel.runtime.tool_risk_classifier import ToolRiskDescriptor, classify_tool_risk

POLICY_PATH = Path("governance/approval/tool_approval_requirement_binding_v1.json")
SOURCE_PATH = Path("kernel/runtime/tool_approval_requirement_binding.py")


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


def _manifest_report(**overrides: object):
    return bind_tool_manifest_risk(
        normalize_tool_manifest_candidate(_candidate(**overrides))
    )


def _requirement(**descriptor_overrides: object) -> ApprovalRequirement:
    return generate_approval_requirement(
        classify_tool_risk(_descriptor(**descriptor_overrides))
    )


class ToolApprovalRequirementBindingTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "tool_approval_requirement_binding_v1")
        self.assertTrue(policy["binding_only"])
        self.assertTrue(policy["uses_tool_risk_classifier"])
        self.assertTrue(policy["uses_human_approval_token_concepts"])
        self.assertFalse(policy["accepted_decision_created"])
        self.assertFalse(policy["execution_allowed"])
        self.assertFalse(policy["subprocess_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["credential_storage_allowed"])
        self.assertFalse(policy["dcc_launch_allowed"])
        self.assertFalse(policy["comfyui_launch_allowed"])
        self.assertFalse(policy["mcp_execution_allowed"])
        self.assertFalse(policy["cli_execution_allowed"])
        self.assertFalse(policy["plugin_execution_allowed"])

    def test_read_only_bounded_tool_may_avoid_approval(self):
        requirement = generate_approval_requirement(
            classify_tool_risk(_descriptor()),
            required_scope_id="scope:tool:readonly-metadata",
        )
        self.assertFalse(requirement.approval_required)
        self.assertFalse(requirement.token_required)
        self.assertEqual(requirement.required_action_type, "READ_PATH")
        self.assertTrue(requirement.production_admission_allowed)

    def test_local_file_read_bounded_scope_requires_token_without_explicit_approval(self):
        assessment = classify_tool_risk(
            _descriptor(
                declared_capabilities=("read_only", "local_file_read"),
                filesystem_scope="read",
            )
        )
        requirement = generate_approval_requirement(
            assessment,
            required_scope_id="scope:filesystem:asset-root-001:read",
        )
        self.assertFalse(requirement.approval_required)
        self.assertTrue(requirement.token_required)
        self.assertTrue(requirement.expires_required)
        self.assertTrue(requirement.revocation_required)

    def test_file_write_requires_approval(self):
        requirement = _requirement(
            declared_capabilities=("local_file_write",),
            filesystem_scope="write",
        )
        self.assertTrue(requirement.approval_required)
        self.assertTrue(requirement.token_required)
        self.assertEqual(requirement.required_action_type, "WRITE_PATH")

    def test_process_launch_requires_approval(self):
        requirement = _requirement(
            source_type="local_script",
            declared_capabilities=("process_launch",),
            process_scope="launch",
        )
        self.assertTrue(requirement.approval_required)
        self.assertEqual(requirement.required_action_type, "LAUNCH_PROCESS")

    def test_network_requires_approval(self):
        requirement = _requirement(
            declared_capabilities=("network_access",),
            network_scope="egress",
        )
        self.assertTrue(requirement.approval_required)
        self.assertEqual(requirement.required_action_type, "ACCESS_NETWORK")

    def test_browser_requires_approval(self):
        requirement = _requirement(
            source_type="browser_automation",
            declared_capabilities=("browser_control",),
            browser_scope="control",
        )
        self.assertTrue(requirement.approval_required)
        self.assertEqual(requirement.required_action_type, "BROWSER_CONTROL")

    def test_provider_requires_approval(self):
        requirement = _requirement(
            source_type="provider_api",
            declared_capabilities=("provider_api",),
            provider_scope="api",
        )
        self.assertTrue(requirement.approval_required)
        self.assertEqual(requirement.required_action_type, "CALL_PROVIDER")

    def test_credential_touching_cannot_be_implicitly_approved(self):
        requirement = _requirement(
            declared_capabilities=("credential_touching",),
            credential_scope="secret",
        )
        self.assertTrue(requirement.approval_required)
        self.assertEqual(requirement.risk_class, "HIGH_RISK")
        self.assertFalse(requirement.production_admission_allowed)
        self.assertIn("implicit_approval_forbidden", requirement.reason)

    def test_mcp_tool_requires_approval_unless_bounded_read_only(self):
        report = _manifest_report(source_type="MCP_TOOL")
        unbounded = generate_approval_requirement(report)
        bounded = generate_approval_requirement(
            report,
            required_scope_id="scope:mcp:server:tools:list",
        )
        self.assertTrue(unbounded.approval_required)
        self.assertFalse(bounded.approval_required)
        self.assertTrue(bounded.token_required)
        self.assertEqual(bounded.required_action_type, "CALL_MCP_TOOL")

    def test_dcc_requires_approval_and_no_production_admission(self):
        requirement = generate_approval_requirement(
            _manifest_report(source_type="DCC_APP", dcc_scope="metadata_only")
        )
        self.assertTrue(requirement.approval_required)
        self.assertFalse(requirement.production_admission_allowed)
        self.assertEqual(requirement.required_action_type, "RUN_DCC_APP")

    def test_comfyui_requires_approval_and_no_production_admission(self):
        requirement = generate_approval_requirement(
            _manifest_report(source_type="COMFYUI_WORKFLOW", model_scope="metadata_only")
        )
        self.assertTrue(requirement.approval_required)
        self.assertFalse(requirement.production_admission_allowed)
        self.assertEqual(requirement.required_action_type, "RUN_COMFYUI")

    def test_plugin_requires_sandbox_strategy(self):
        requirement = _requirement(
            source_type="plugin",
            declared_capabilities=("plugin_execution",),
            plugin_scope="sandbox",
        )
        self.assertTrue(requirement.approval_required)
        self.assertTrue(requirement.token_required)
        self.assertEqual(requirement.required_action_type, "RUN_PLUGIN")
        self.assertIn("plugin_sandbox_strategy_required", requirement.reason)

    def test_high_risk_blocks_production_admission(self):
        requirement = _requirement(declared_capabilities=("high_risk",))
        self.assertEqual(requirement.risk_class, "HIGH_RISK")
        self.assertFalse(requirement.production_admission_allowed)

    def test_requirement_hash_deterministic_excluding_observed_at(self):
        assessment = classify_tool_risk(
            _descriptor(declared_capabilities=("network_access",), network_scope="egress")
        )
        first = generate_approval_requirement(
            assessment,
            observed_at="2026-05-25T00:00:00+00:00",
        )
        second = generate_approval_requirement(
            assessment,
            observed_at="2030-01-01T00:00:00+00:00",
        )
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.requirement_id, second.requirement_id)
        self.assertNotEqual(first.observed_at, second.observed_at)

    def test_no_auto_approved_token_generated(self):
        requirement = _requirement(declared_capabilities=("network_access",))
        self.assertIsInstance(requirement, ApprovalRequirement)
        self.assertNotIn("approval_id", requirement.as_dict())
        self.assertNotIn("accepted", requirement.as_dict())
        source = SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("create_human_approval_token", source)
        self.assertNotIn("create_approval_decision", source)

    def test_no_execution_subprocess_network_browser_provider_dcc_or_comfyui_launch(self):
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
