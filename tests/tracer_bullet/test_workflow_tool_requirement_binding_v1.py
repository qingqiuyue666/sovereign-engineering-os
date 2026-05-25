"""Tracer-bullet tests for workflow tool requirement binding v1."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.runtime.task_to_workflow_router_skeleton import TaskIntent, route_task_intent
from kernel.runtime.tool_manifest_normalizer import normalize_tool_manifest_candidate
from kernel.runtime.workflow_dry_run_plan import create_workflow_dry_run_plan
from kernel.runtime.workflow_tool_requirement_binding import (
    WorkflowToolRequirementBindingReport,
    bind_workflow_tool_requirements,
)

POLICY_PATH = Path("governance/workflow/workflow_tool_requirement_binding_v1.json")
SOURCE_PATH = Path("kernel/runtime/workflow_tool_requirement_binding.py")


def _intent() -> TaskIntent:
    return TaskIntent(
        task_id="task-001",
        domain="ASSET_INGESTION",
        objective="Bind dry-run tool requirements.",
        inputs={"assets": ("asset-a",)},
        constraints={"dry_run": True},
        risk_tolerance="LOW",
        desired_outputs=("tool_binding_report",),
    )


def _plan():
    return create_workflow_dry_run_plan(_intent(), route_task_intent(_intent()))


def _candidate(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "source_type": "CLI_TOOL",
        "tool_name": "Asset Inventory",
        "declared_capabilities": ["asset_inventory", "read_only"],
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


class WorkflowToolRequirementBindingTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "workflow_tool_requirement_binding_v1")
        self.assertTrue(policy["binding_only"])
        self.assertTrue(policy["advisory_only"])
        self.assertTrue(policy["uses_workflow_dry_run_plan"])
        self.assertTrue(policy["uses_tool_manifest_normalizer"])
        self.assertFalse(policy["automatic_installation_allowed"])
        self.assertFalse(policy["network_lookup_allowed"])
        self.assertFalse(policy["execution_allowed"])
        self.assertFalse(policy["subprocess_allowed"])
        self.assertFalse(policy["mcp_execution_allowed"])
        self.assertFalse(policy["cli_execution_allowed"])
        self.assertFalse(policy["plugin_execution_allowed"])
        self.assertFalse(policy["dcc_launch_allowed"])
        self.assertFalse(policy["comfyui_launch_allowed"])

    def test_valid_plan_binds_matching_tool_manifest(self):
        report = bind_workflow_tool_requirements(
            _plan(),
            [
                _manifest(),
                _manifest(
                    tool_name="Evidence Ledger",
                    declared_capabilities=["evidence_ledger", "read_only"],
                ),
            ],
        )
        self.assertIsInstance(report, WorkflowToolRequirementBindingReport)
        self.assertTrue(report.binding_id.startswith("workflow_tool_binding_"))
        self.assertFalse(report.blockers)
        statuses = {binding.match_status for binding in report.required_tool_bindings}
        self.assertIn("MATCHED", statuses)
        self.assertIn("tool.cli_tool.asset-inventory", {binding.matched_tool_id for binding in report.required_tool_bindings})

    def test_missing_tool_requirement_creates_blocker(self):
        report = bind_workflow_tool_requirements(_plan(), [])
        self.assertIn("asset_inventory", report.missing_tool_requirements)
        self.assertTrue(any(blocker.startswith("missing_tool_requirement:") for blocker in report.blockers))
        self.assertIn("MISSING", {binding.match_status for binding in report.required_tool_bindings})

    def test_incompatible_tool_creates_blocker(self):
        report = bind_workflow_tool_requirements(
            _plan(),
            [_manifest(source_type="DCC_APP", dcc_scope="metadata_only")],
            capability_mapping={
                "asset_inventory": {
                    "capability": "asset_inventory",
                    "allowed_source_types": ["CLI_TOOL"],
                }
            },
        )
        self.assertIn("INCOMPATIBLE", {binding.match_status for binding in report.required_tool_bindings})
        self.assertTrue(report.incompatible_tools)
        self.assertTrue(any(blocker.startswith("incompatible_tool:") for blocker in report.blockers))

    def test_high_risk_tool_requires_approval(self):
        report = bind_workflow_tool_requirements(
            _plan(),
            [
                _manifest(
                    source_type="COMFYUI_WORKFLOW",
                    declared_capabilities=["asset_inventory", "comfyui_execution"],
                    model_scope="metadata_only",
                )
            ],
        )
        self.assertIn("REQUIRES_APPROVAL", {binding.match_status for binding in report.required_tool_bindings})
        self.assertTrue(any(warning.startswith("tool_requires_approval:") for warning in report.warnings))

    def test_mcp_dcc_and_comfyui_candidates_are_metadata_only(self):
        for source_type, scope in (
            ("MCP_TOOL", {}),
            ("DCC_APP", {"dcc_scope": "metadata_only"}),
            ("COMFYUI_WORKFLOW", {"model_scope": "metadata_only"}),
        ):
            with self.subTest(source_type=source_type):
                report = bind_workflow_tool_requirements(
                    _plan(),
                    [_manifest(source_type=source_type, **scope)],
                )
                self.assertTrue(report.candidate_tool_matches)
                self.assertTrue(report.candidate_tool_matches[0]["metadata_only"])
                self.assertFalse(report.candidate_tool_matches[0]["direct_execution_allowed"])
                self.assertFalse(report.candidate_tool_matches[0]["runtime_integration_allowed"])

    def test_no_network_lookup(self):
        report = bind_workflow_tool_requirements(
            _plan(),
            [
                _manifest(
                    source_type="GITHUB_REPO",
                    source_ref="https://github.com/example/metadata-only",
                    network_scope="metadata_only",
                )
            ],
        )
        self.assertTrue(report.candidate_tool_matches[0]["metadata_only"])

    def test_no_execution_subprocess_or_install_vendor_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "requests",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "pip",
            "npm",
            "brew",
            "vendor",
            "bpy",
        ):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)
        self.assertNotIn("shell=True", source)

    def test_binding_hash_deterministic(self):
        first = bind_workflow_tool_requirements(
            _plan(),
            [_manifest()],
            observed_at="2026-05-25T00:00:00+00:00",
        )
        second = bind_workflow_tool_requirements(
            _plan(),
            [_manifest()],
            observed_at="2026-05-25T00:00:00+00:00",
        )
        self.assertEqual(first.binding_hash, second.binding_hash)
        self.assertEqual(first.binding_id, second.binding_id)

    def test_observed_at_excluded_from_deterministic_hash(self):
        first = bind_workflow_tool_requirements(
            _plan(),
            [_manifest()],
            observed_at="2026-05-25T00:00:00+00:00",
        )
        second = bind_workflow_tool_requirements(
            _plan(),
            [_manifest()],
            observed_at="2030-01-01T00:00:00+00:00",
        )
        self.assertEqual(first.binding_hash, second.binding_hash)
        self.assertEqual(first.binding_id, second.binding_id)
        self.assertNotEqual(first.observed_at, second.observed_at)


if __name__ == "__main__":
    unittest.main()
