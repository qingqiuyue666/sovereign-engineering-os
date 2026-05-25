"""Tracer-bullet tests for operator task snapshot binding v1."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.runtime.operator_task_snapshot_binding import (
    ALLOWED_NEXT_ACTIONS,
    FORBIDDEN_NEXT_ACTIONS,
    OperatorTaskSnapshot,
    build_operator_task_snapshot,
)
from kernel.runtime.task_to_workflow_router_skeleton import TaskIntent, route_task_intent
from kernel.runtime.tool_approval_requirement_binding import generate_approval_requirement
from kernel.runtime.tool_manifest_normalizer import normalize_tool_manifest_candidate
from kernel.runtime.workflow_dry_run_plan import create_workflow_dry_run_plan
from kernel.runtime.workflow_risk_approval_binding import bind_workflow_risk_approvals
from kernel.runtime.workflow_tool_requirement_binding import bind_workflow_tool_requirements

POLICY_PATH = Path("governance/operator/operator_task_snapshot_binding_v1.json")
SOURCE_PATH = Path("kernel/runtime/operator_task_snapshot_binding.py")


def _intent() -> TaskIntent:
    return TaskIntent(
        task_id="task-001",
        domain="ASSET_INGESTION",
        objective="Build operator task snapshot.",
        inputs={"assets": ("asset-a",)},
        constraints={"dry_run": True},
        risk_tolerance="LOW",
        desired_outputs=("operator_task_snapshot",),
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


def _successful_chain():
    plan = _plan()
    tool_report = bind_workflow_tool_requirements(plan, list(_manifests()))
    risk_report = bind_workflow_risk_approvals(plan, tool_report, _low_risks())
    return plan, tool_report, risk_report


def _asset():
    return {
        "asset_id": "asset-001",
        "media_class": "TEXT",
        "content_hash": "sha256:" + "1" * 64,
    }


def _journal():
    return {
        "event_id": "event-001",
        "run_id": "run-001",
        "task_id": "task-001",
        "stage": "dry_run_plan",
        "content_hash": "sha256:" + "2" * 64,
    }


class OperatorTaskSnapshotBindingTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "operator_task_snapshot_binding_v1")
        self.assertTrue(policy["snapshot_only"])
        self.assertTrue(policy["read_only"])
        self.assertTrue(policy["advisory_only"])
        self.assertFalse(policy["ui_implementation_allowed"])
        self.assertFalse(policy["execution_authorization_allowed"])
        self.assertFalse(policy["execution_allowed"])
        self.assertFalse(policy["subprocess_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["dcc_launch_allowed"])
        self.assertFalse(policy["comfyui_launch_allowed"])
        self.assertEqual(set(policy["allowed_next_actions"]), ALLOWED_NEXT_ACTIONS)
        self.assertEqual(set(policy["forbidden_next_actions"]), FORBIDDEN_NEXT_ACTIONS)

    def test_aggregate_successful_dry_run_task_snapshot(self):
        plan, tool_report, risk_report = _successful_chain()
        snapshot = build_operator_task_snapshot(
            dry_run_plan=plan,
            tool_binding_report=tool_report,
            risk_approval_report=risk_report,
            asset_inventory_summaries=[_asset()],
            journal_summaries=[_journal()],
        )
        self.assertIsInstance(snapshot, OperatorTaskSnapshot)
        self.assertEqual(snapshot.task_id, "task-001")
        self.assertEqual(snapshot.workflow_id, plan.workflow_id)
        self.assertEqual(snapshot.asset_summary["asset_count"], 1)
        self.assertEqual(snapshot.journal_summary["event_count"], 1)
        self.assertIn("review_dry_run_plan", snapshot.next_actions)
        self.assertIn("inspect_asset_inventory", snapshot.next_actions)
        self.assertFalse(snapshot.operator_state["ui_runtime_present"])
        self.assertFalse(snapshot.operator_state["execution_authorized"])

    def test_aggregate_blocked_task_snapshot(self):
        plan = _plan()
        tool_report = bind_workflow_tool_requirements(plan, [])
        risk_report = bind_workflow_risk_approvals(plan, tool_report, [])
        snapshot = build_operator_task_snapshot(
            dry_run_plan=plan,
            tool_binding_report=tool_report,
            risk_approval_report=risk_report,
        )
        self.assertTrue(snapshot.blockers)
        self.assertIn("workflow_dry_run_admission_blocked", snapshot.blockers)
        self.assertIn("rerun_dry_run_planning", snapshot.next_actions)

    def test_missing_tool_creates_inspect_missing_tool_next_action(self):
        plan = _plan()
        tool_report = bind_workflow_tool_requirements(plan, [])
        risk_report = bind_workflow_risk_approvals(plan, tool_report, [])
        snapshot = build_operator_task_snapshot(
            dry_run_plan=plan,
            tool_binding_report=tool_report,
            risk_approval_report=risk_report,
        )
        self.assertIn("inspect_missing_tool", snapshot.next_actions)

    def test_missing_approval_creates_issue_scoped_approval_next_action(self):
        plan = _plan()
        manifest = _manifest(
            source_type="COMFYUI_WORKFLOW",
            declared_capabilities=["asset_inventory", "comfyui_execution"],
            model_scope="metadata_only",
        )
        tool_report = bind_workflow_tool_requirements(plan, [manifest])
        risk_report = bind_workflow_risk_approvals(
            plan,
            tool_report,
            [_risk(manifest.tool_id, "COMFYUI_EXECUTION", approval_required=True)],
        )
        snapshot = build_operator_task_snapshot(
            dry_run_plan=plan,
            tool_binding_report=tool_report,
            risk_approval_report=risk_report,
        )
        self.assertIn("issue_scoped_approval", snapshot.next_actions)

    def test_high_risk_creates_review_risk_assessment_next_action(self):
        plan, tool_report, _ = _successful_chain()
        manifest = _manifests()[0]
        requirement = generate_approval_requirement(
            _risk(manifest.tool_id, "HIGH_RISK", approval_required=True)
        )
        risk_report = bind_workflow_risk_approvals(
            plan,
            tool_report,
            [_risk(manifest.tool_id, "HIGH_RISK", approval_required=True), *_low_risks()[1:]],
            [requirement],
        )
        snapshot = build_operator_task_snapshot(
            dry_run_plan=plan,
            tool_binding_report=tool_report,
            risk_approval_report=risk_report,
            approval_requirement_summaries=[requirement],
        )
        self.assertIn("review_risk_assessment", snapshot.next_actions)

    def test_forbidden_next_actions_rejected(self):
        plan, tool_report, risk_report = _successful_chain()
        for action in ("execute_raw_command", "launch_dcc", "run_comfyui", "run_cli_tool"):
            with self.subTest(action=action):
                with self.assertRaisesRegex(ValueError, "forbidden_next_actions"):
                    build_operator_task_snapshot(
                        dry_run_plan=plan,
                        tool_binding_report=tool_report,
                        risk_approval_report=risk_report,
                        next_actions=[action],
                    )

    def test_snapshot_hash_deterministic(self):
        plan, tool_report, risk_report = _successful_chain()
        first = build_operator_task_snapshot(
            dry_run_plan=plan,
            tool_binding_report=tool_report,
            risk_approval_report=risk_report,
            generated_at="2026-05-25T00:00:00+00:00",
        )
        second = build_operator_task_snapshot(
            dry_run_plan=plan,
            tool_binding_report=tool_report,
            risk_approval_report=risk_report,
            generated_at="2026-05-25T00:00:00+00:00",
        )
        self.assertEqual(first.snapshot_hash, second.snapshot_hash)
        self.assertEqual(first.snapshot_id, second.snapshot_id)

    def test_generated_at_excluded_from_hash(self):
        plan, tool_report, risk_report = _successful_chain()
        first = build_operator_task_snapshot(
            dry_run_plan=plan,
            tool_binding_report=tool_report,
            risk_approval_report=risk_report,
            generated_at="2026-05-25T00:00:00+00:00",
        )
        second = build_operator_task_snapshot(
            dry_run_plan=plan,
            tool_binding_report=tool_report,
            risk_approval_report=risk_report,
            generated_at="2030-01-01T00:00:00+00:00",
        )
        self.assertEqual(first.snapshot_hash, second.snapshot_hash)
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        self.assertNotEqual(first.generated_at, second.generated_at)

    def test_no_raw_payload_stored(self):
        plan, tool_report, risk_report = _successful_chain()
        with self.assertRaisesRegex(ValueError, "raw_payload"):
            build_operator_task_snapshot(
                dry_run_plan=plan,
                tool_binding_report=tool_report,
                risk_approval_report=risk_report,
                journal_summaries=[{"event_id": "event-001", "raw_payload": "no"}],
            )

    def test_no_credential_material_stored(self):
        plan, tool_report, risk_report = _successful_chain()
        with self.assertRaisesRegex(ValueError, "credential"):
            build_operator_task_snapshot(
                dry_run_plan=plan,
                tool_binding_report=tool_report,
                risk_approval_report=risk_report,
                asset_inventory_summaries=[{"asset_id": "asset-001", "credential": "no"}],
            )

    def test_no_ui_execution_subprocess_network_browser_provider_dcc_or_comfyui_launch(self):
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
