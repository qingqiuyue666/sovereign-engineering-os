"""Tracer-bullet tests for workflow risk approval binding v1."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.runtime.task_to_workflow_router_skeleton import TaskIntent, route_task_intent
from kernel.runtime.tool_approval_requirement_binding import generate_approval_requirement
from kernel.runtime.tool_manifest_normalizer import normalize_tool_manifest_candidate
from kernel.runtime.tool_manifest_risk_binding import bind_tool_manifest_risk
from kernel.runtime.workflow_dry_run_plan import create_workflow_dry_run_plan
from kernel.runtime.workflow_risk_approval_binding import (
    WorkflowRiskApprovalBindingReport,
    bind_workflow_risk_approvals,
)
from kernel.runtime.workflow_tool_requirement_binding import bind_workflow_tool_requirements

POLICY_PATH = Path("governance/workflow/workflow_risk_approval_binding_v1.json")
SOURCE_PATH = Path("kernel/runtime/workflow_risk_approval_binding.py")


def _intent() -> TaskIntent:
    return TaskIntent(
        task_id="task-001",
        domain="ASSET_INGESTION",
        objective="Bind workflow risk approvals.",
        inputs={"assets": ("asset-a",)},
        constraints={"dry_run": True},
        risk_tolerance="LOW",
        desired_outputs=("risk_approval_report",),
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


def _manifests():
    return (
        _manifest(),
        _manifest(
            tool_name="Evidence Ledger",
            declared_capabilities=["evidence_ledger", "read_only"],
        ),
    )


def _binding_report(manifests=None):
    return bind_workflow_tool_requirements(_plan(), list(manifests or _manifests()))


def _risk(tool_id: str, *risk_classes: str, approval_required: bool = False):
    highest = risk_classes[-1] if risk_classes else "READ_ONLY"
    return {
        "tool_id": tool_id,
        "risk_classes": list(risk_classes or ("READ_ONLY",)),
        "highest_risk": highest,
        "approval_required": approval_required,
        "token_required": approval_required,
        "production_admission_allowed": not approval_required,
        "content_hash": "sha256:" + (tool_id.encode("utf-8").hex()[:64]).ljust(64, "0"),
    }


def _low_risks():
    return tuple(_risk(manifest.tool_id, "READ_ONLY") for manifest in _manifests())


class WorkflowRiskApprovalBindingTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "workflow_risk_approval_binding_v1")
        self.assertTrue(policy["binding_only"])
        self.assertTrue(policy["uses_tool_manifest_risk_binding"])
        self.assertTrue(policy["uses_tool_approval_requirement_binding"])
        self.assertFalse(policy["accepted_approval_token_creation_allowed"])
        self.assertFalse(policy["production_admission_allowed"])
        self.assertFalse(policy["execution_allowed"])
        self.assertFalse(policy["subprocess_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["dcc_launch_allowed"])
        self.assertFalse(policy["comfyui_launch_allowed"])

    def test_low_risk_workflow_dry_run_admission_allowed(self):
        report = bind_workflow_risk_approvals(_plan(), _binding_report(), _low_risks())
        self.assertIsInstance(report, WorkflowRiskApprovalBindingReport)
        self.assertFalse(report.production_admission_allowed)
        self.assertTrue(report.dry_run_admission_allowed)
        self.assertFalse(report.blockers)
        self.assertEqual(report.highest_risk, "READ_ONLY")

    def test_missing_approval_blocks_dry_run_when_required(self):
        comfy = _manifest(
            source_type="COMFYUI_WORKFLOW",
            declared_capabilities=["asset_inventory", "comfyui_execution"],
            model_scope="metadata_only",
        )
        report = bind_workflow_risk_approvals(
            _plan(),
            _binding_report([comfy]),
            [bind_tool_manifest_risk(comfy)],
        )
        self.assertFalse(report.dry_run_admission_allowed)
        self.assertIn(comfy.tool_id, report.missing_approvals)
        self.assertTrue(any(blocker.startswith("approval_requirement_missing:") for blocker in report.blockers))

    def test_high_risk_blocks_production_admission(self):
        manifest = _manifests()[0]
        requirement = generate_approval_requirement(
            {
                "tool_id": manifest.tool_id,
                "manifest_id": manifest.manifest_id,
                "source_type": manifest.source_type,
                "risk_classes": ["HIGH_RISK"],
                "highest_risk": "HIGH_RISK",
                "approval_required": True,
                "production_admission_allowed": False,
            }
        )
        report = bind_workflow_risk_approvals(
            _plan(),
            _binding_report(),
            [_risk(manifest.tool_id, "HIGH_RISK", approval_required=True), *_low_risks()[1:]],
            [requirement],
        )
        self.assertFalse(report.production_admission_allowed)
        self.assertEqual(report.highest_risk, "HIGH_RISK")

    def test_dcc_blocks_production_admission(self):
        report = bind_workflow_risk_approvals(
            _plan(),
            _binding_report(),
            [_risk(_manifests()[0].tool_id, "DCC_CONTROL", approval_required=True), *_low_risks()[1:]],
            [generate_approval_requirement(_risk(_manifests()[0].tool_id, "DCC_CONTROL", approval_required=True))],
        )
        self.assertFalse(report.production_admission_allowed)
        self.assertIn("DCC_CONTROL", report.step_risk_summary[0]["risk_classes"])

    def test_comfyui_blocks_production_admission(self):
        report = bind_workflow_risk_approvals(
            _plan(),
            _binding_report(),
            [_risk(_manifests()[0].tool_id, "COMFYUI_EXECUTION", approval_required=True), *_low_risks()[1:]],
            [generate_approval_requirement(_risk(_manifests()[0].tool_id, "COMFYUI_EXECUTION", approval_required=True))],
        )
        self.assertFalse(report.production_admission_allowed)
        self.assertIn("COMFYUI_EXECUTION", report.step_risk_summary[0]["risk_classes"])

    def test_browser_provider_blocks_production_admission(self):
        for risk_class in ("BROWSER_CONTROL", "PROVIDER_API"):
            with self.subTest(risk_class=risk_class):
                report = bind_workflow_risk_approvals(
                    _plan(),
                    _binding_report(),
                    [_risk(_manifests()[0].tool_id, risk_class, approval_required=True), *_low_risks()[1:]],
                    [generate_approval_requirement(_risk(_manifests()[0].tool_id, risk_class, approval_required=True))],
                )
                self.assertFalse(report.production_admission_allowed)
                self.assertIn(risk_class, report.step_risk_summary[0]["risk_classes"])

    def test_credential_touching_blocks_admission(self):
        report = bind_workflow_risk_approvals(
            _plan(),
            _binding_report(),
            [_risk(_manifests()[0].tool_id, "CREDENTIAL_TOUCHING", approval_required=True), *_low_risks()[1:]],
            [generate_approval_requirement(_risk(_manifests()[0].tool_id, "CREDENTIAL_TOUCHING", approval_required=True))],
        )
        self.assertFalse(report.production_admission_allowed)
        self.assertFalse(report.dry_run_admission_allowed)
        self.assertTrue(any(blocker.startswith("credential_touching_blocks_admission:") for blocker in report.blockers))

    def test_approval_requirement_does_not_create_approval_token(self):
        requirement = generate_approval_requirement(
            _risk(_manifests()[0].tool_id, "DCC_CONTROL", approval_required=True)
        )
        report = bind_workflow_risk_approvals(
            _plan(),
            _binding_report(),
            [_risk(_manifests()[0].tool_id, "DCC_CONTROL", approval_required=True), *_low_risks()[1:]],
            [requirement],
        )
        encoded = json.dumps(report.as_dict(), sort_keys=True)
        self.assertIn("requirement_id", encoded)
        self.assertNotIn("approval_id", encoded)
        self.assertNotIn("accepted", encoded.lower())

    def test_report_hash_deterministic(self):
        first = bind_workflow_risk_approvals(
            _plan(),
            _binding_report(),
            _low_risks(),
            observed_at="2026-05-25T00:00:00+00:00",
        )
        second = bind_workflow_risk_approvals(
            _plan(),
            _binding_report(),
            _low_risks(),
            observed_at="2026-05-25T00:00:00+00:00",
        )
        self.assertEqual(first.report_hash, second.report_hash)
        self.assertEqual(first.report_id, second.report_id)

    def test_observed_at_excluded_from_deterministic_hash(self):
        first = bind_workflow_risk_approvals(
            _plan(),
            _binding_report(),
            _low_risks(),
            observed_at="2026-05-25T00:00:00+00:00",
        )
        second = bind_workflow_risk_approvals(
            _plan(),
            _binding_report(),
            _low_risks(),
            observed_at="2030-01-01T00:00:00+00:00",
        )
        self.assertEqual(first.report_hash, second.report_hash)
        self.assertEqual(first.report_id, second.report_id)
        self.assertNotEqual(first.observed_at, second.observed_at)

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
