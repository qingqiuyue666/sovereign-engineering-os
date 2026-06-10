"""Tracer-bullet tests for workflow dry-run plan v1."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import hashlib
import json
import unittest

from kernel.runtime.task_to_workflow_router_skeleton import (
    TaskIntent,
    route_task_intent,
)
from kernel.runtime.workflow_dry_run_plan import (
    PlanStep,
    WorkflowDryRunPlan,
    create_workflow_dry_run_plan,
)

POLICY_PATH = Path("governance/workflow/workflow_dry_run_plan_v1.json")
SOURCE_PATH = Path("kernel/runtime/workflow_dry_run_plan.py")


def _intent(domain: str = "ASSET_INGESTION") -> TaskIntent:
    return TaskIntent(
        task_id="task-001",
        domain=domain,
        objective="Plan a deterministic dry-run workflow.",
        inputs={"assets": ("asset-a",)},
        constraints={"dry_run": True},
        risk_tolerance="LOW",
        desired_outputs=("dry_run_plan",),
    )


def _workflow(domain: str = "ASSET_INGESTION"):
    return route_task_intent(_intent(domain))


def _descriptor_map_with_hash(descriptor, nodes: list[dict[str, object]]) -> dict[str, object]:
    data = descriptor.as_dict()
    data["nodes"] = nodes
    material = {key: value for key, value in data.items() if key != "graph_hash"}
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    data["graph_hash"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return data


class WorkflowDryRunPlanTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "workflow_dry_run_plan_v1")
        self.assertTrue(policy["planning_only"])
        self.assertTrue(policy["dry_run_only"])
        self.assertFalse(policy["executable"])
        self.assertFalse(policy["workflow_node_execution_allowed"])
        self.assertFalse(policy["subprocess_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["tool_launch_allowed"])
        self.assertFalse(policy["dcc_launch_allowed"])
        self.assertFalse(policy["comfyui_launch_allowed"])

    def test_valid_task_workflow_produces_dry_run_plan(self):
        plan = create_workflow_dry_run_plan(
            _intent(),
            _workflow(),
            asset_summary_refs=[{"asset_id": "asset-a"}],
            tool_manifest_refs=[{"tool_id": "asset_inventory"}],
        )
        self.assertIsInstance(plan, WorkflowDryRunPlan)
        self.assertTrue(plan.plan_id.startswith("workflow_dry_run_plan_"))
        self.assertEqual(plan.task_id, "task-001")
        self.assertEqual(plan.workflow_id, _workflow().workflow_id)
        self.assertEqual(plan.workflow_graph_hash, _workflow().graph_hash)
        self.assertTrue(plan.plan_steps)
        self.assertIn("asset_inventory", plan.required_tools)
        self.assertIn("asset-a", plan.required_assets)

    def test_plan_is_dry_run_only_and_non_executable(self):
        plan = create_workflow_dry_run_plan(_intent(), _workflow())
        self.assertTrue(plan.dry_run_only)
        self.assertFalse(plan.executable)
        for step in plan.plan_steps:
            self.assertIsInstance(step, PlanStep)
            self.assertEqual(step.status, "PLANNED")
            self.assertFalse(step.executable)

    def test_plan_hash_deterministic(self):
        first = create_workflow_dry_run_plan(
            _intent(),
            _workflow(),
            generated_at="2026-05-25T00:00:00+00:00",
        )
        second = create_workflow_dry_run_plan(
            _intent(),
            _workflow(),
            generated_at="2026-05-25T00:00:00+00:00",
        )
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.plan_id, second.plan_id)

    def test_generated_at_excluded_from_hash(self):
        first = create_workflow_dry_run_plan(
            _intent(),
            _workflow(),
            generated_at="2026-05-25T00:00:00+00:00",
        )
        second = create_workflow_dry_run_plan(
            _intent(),
            _workflow(),
            generated_at="2030-01-01T00:00:00+00:00",
        )
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.plan_id, second.plan_id)
        self.assertNotEqual(first.generated_at, second.generated_at)

    def test_missing_rollback_plan_fails(self):
        broken = replace(_workflow(), rollback_plan=())
        with self.assertRaisesRegex(ValueError, "rollback_plan"):
            create_workflow_dry_run_plan(_intent(), broken)

    def test_missing_evaluation_plan_fails(self):
        broken = replace(_workflow(), evaluation_plan=())
        with self.assertRaisesRegex(ValueError, "evaluation_plan"):
            create_workflow_dry_run_plan(_intent(), broken)

    def test_unsupported_domain_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "domain_not_supported"):
            create_workflow_dry_run_plan(replace(_intent(), domain="MAGIC_DOMAIN"))

    def test_high_risk_node_produces_approval_placeholder(self):
        descriptor = _workflow("GIT_CODE_AUDIT")
        nodes = [dict(node) for node in descriptor.nodes]
        nodes[0]["risk_level"] = "HIGH_RISK"
        plan = create_workflow_dry_run_plan(
            _intent("GIT_CODE_AUDIT"),
            _descriptor_map_with_hash(descriptor, nodes),
        )
        self.assertTrue(
            any(
                ref.startswith("approval_requirement_placeholder:")
                for step in plan.plan_steps
                for ref in step.approval_refs
            )
        )

    def test_raw_command_rejected(self):
        descriptor = _workflow().as_dict()
        descriptor["nodes"][0]["raw_command"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "raw_command"):
            create_workflow_dry_run_plan(_intent(), descriptor)

    def test_command_line_rejected(self):
        descriptor = _workflow().as_dict()
        descriptor["nodes"][0]["command_line"] = "tool --run"
        with self.assertRaisesRegex(ValueError, "command_line"):
            create_workflow_dry_run_plan(_intent(), descriptor)

    def test_argv_rejected(self):
        descriptor = _workflow().as_dict()
        descriptor["nodes"][0]["argv"] = ["tool"]
        with self.assertRaisesRegex(ValueError, "argv"):
            create_workflow_dry_run_plan(_intent(), descriptor)

    def test_no_subprocess_network_provider_browser_dcc_or_comfyui_launch(self):
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
