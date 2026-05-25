"""Tracer-bullet tests for task-to-workflow router skeleton v1."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import unittest

from kernel.runtime.task_to_workflow_router_skeleton import (
    SUPPORTED_DOMAINS,
    TaskIntent,
    WorkflowGraphDescriptor,
    route_task_intent,
    validate_workflow_graph_descriptor,
)

POLICY_PATH = Path("governance/workflow/task_to_workflow_router_skeleton_v1.json")
SOURCE_PATH = Path("kernel/runtime/task_to_workflow_router_skeleton.py")


def _intent(domain: str = "ASSET_INGESTION") -> TaskIntent:
    return TaskIntent(
        task_id="task-001",
        domain=domain,
        objective="Produce a descriptor-only workflow plan.",
        inputs={"assets": ("asset-a",)},
        constraints={"no_execution": True},
        risk_tolerance="LOW",
        desired_outputs=("workflow_descriptor",),
    )


class TaskToWorkflowRouterSkeletonTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundaries(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "task_to_workflow_router_skeleton_v1")
        self.assertTrue(policy["descriptor_only"])
        self.assertFalse(policy["workflow_execution_allowed"])
        self.assertFalse(policy["subprocess_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["model_calls_allowed"])
        self.assertFalse(policy["tool_launch_allowed"])

    def test_valid_task_intent_routes_to_workflow_graph(self):
        descriptor = route_task_intent(_intent())
        self.assertIsInstance(descriptor, WorkflowGraphDescriptor)
        self.assertEqual(descriptor.workflow_version, "v1")
        self.assertTrue(descriptor.nodes)
        self.assertTrue(descriptor.edges)
        self.assertTrue(descriptor.evaluation_plan)
        self.assertEqual(descriptor.required_assets, ("asset-a",))

    def test_each_supported_domain_has_route_template(self):
        for domain in SUPPORTED_DOMAINS:
            with self.subTest(domain=domain):
                descriptor = route_task_intent(_intent(domain))
                self.assertIn(domain.lower(), descriptor.workflow_id)
                self.assertTrue(descriptor.nodes)

    def test_missing_objective_fails(self):
        with self.assertRaises(ValueError):
            route_task_intent(replace(_intent(), objective=""))

    def test_missing_evaluation_plan_fails(self):
        descriptor = route_task_intent(_intent())
        broken = replace(descriptor, evaluation_plan=())
        failures = validate_workflow_graph_descriptor(broken)
        self.assertIn("evaluation_plan_required", failures)

    def test_high_risk_domain_requires_approval(self):
        descriptor = route_task_intent(_intent("COMFYUI_WORKFLOW"))
        self.assertIn(
            "operator_approval_required_for_high_risk_domain",
            descriptor.approval_requirements,
        )

    def test_graph_hash_deterministic(self):
        first = route_task_intent(_intent("RELEASE_VALIDATION"))
        second = route_task_intent(_intent("RELEASE_VALIDATION"))
        self.assertEqual(first.graph_hash, second.graph_hash)

    def test_no_raw_command_encoded(self):
        descriptor = route_task_intent(_intent("GIT_CODE_AUDIT"))
        encoded = json.dumps(descriptor.as_dict(), sort_keys=True).lower()
        for forbidden in ("raw_command", "command_line", "argv", "shell=true"):
            self.assertNotIn(forbidden, encoded)

    def test_no_direct_execution_encoded(self):
        descriptor = route_task_intent(_intent("VFX"))
        encoded = json.dumps(descriptor.as_dict(), sort_keys=True).lower()
        for forbidden in ("subprocess", "execute_workflow", "direct_launch"):
            self.assertNotIn(forbidden, encoded)

    def test_source_has_no_runtime_execution_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in ("subprocess", "requests", "urllib", "socket", "webbrowser"):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
