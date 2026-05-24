"""Integrity tests for the machine-readable milestone dependency graph."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = REPO_ROOT / "governance" / "delivery" / "milestone_dependency_graph_v1.json"
SCHEMA_PATH = (
    REPO_ROOT / "governance" / "delivery" / "milestone_dependency_graph_v1.schema.json"
)


class MilestoneDependencyGraphV1Tests(unittest.TestCase):
    def load_graph(self) -> dict[str, object]:
        return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))

    def test_graph_and_schema_exist_with_non_authority_flags(self) -> None:
        graph = self.load_graph()
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(graph["graph_type"], "sovereign_os_milestone_dependency_graph_v1")
        self.assertEqual(graph["version"], "v1")
        self.assertEqual(
            schema["properties"]["graph_type"]["const"],
            "sovereign_os_milestone_dependency_graph_v1",
        )
        for field in (
            "runtime_authority_granted",
            "merge_automation_granted",
            "branch_deletion_granted",
            "direct_main_push_granted",
        ):
            self.assertIs(graph[field], False)

    def test_required_milestones_are_present_with_branch_and_pr_contracts(self) -> None:
        graph = self.load_graph()
        milestones = {entry["id"]: entry for entry in graph["milestones"]}  # type: ignore[index]

        self.assertEqual(
            set(milestones),
            {
                "A1",
                "A2",
                "A3",
                "B1",
                "B2",
                "B3",
                "B4",
                "C1",
                "C2",
                "D1",
                "D2",
                "D3",
                "D4",
                "E1",
                "E2",
            },
        )
        for entry in milestones.values():
            self.assertTrue(entry["branch"].startswith("feat/"))
            self.assertTrue(entry["pr_title"].startswith("feat: "))
            self.assertIsInstance(entry["priority_order"], int)

    def test_dependencies_reference_existing_nodes_and_are_acyclic(self) -> None:
        graph = self.load_graph()
        milestones = {entry["id"]: entry for entry in graph["milestones"]}  # type: ignore[index]

        for entry in milestones.values():
            for dependency in entry["dependencies"]:
                self.assertIn(dependency, milestones, entry["id"])

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise AssertionError(f"dependency cycle at {node_id}")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dependency_id in milestones[node_id]["dependencies"]:
                visit(dependency_id)
            visiting.remove(node_id)
            visited.add(node_id)

        for milestone_id in milestones:
            visit(milestone_id)

    def test_blocked_by_merge_flags_match_known_dependent_milestones(self) -> None:
        graph = self.load_graph()
        milestones = {entry["id"]: entry for entry in graph["milestones"]}  # type: ignore[index]

        for blocked_id in ("B2", "B3", "B4"):
            self.assertIs(milestones[blocked_id]["blocked_by_merge"], True)
            self.assertEqual(
                milestones[blocked_id]["blocked_state"],
                "WAITING_FOR_PREVIOUS_PR_MERGE",
            )
            self.assertIs(milestones[blocked_id]["can_merge_independently"], False)

        for blocked_id in ("D3", "D4"):
            self.assertIs(milestones[blocked_id]["blocked_by_merge"], True)
            self.assertEqual(
                milestones[blocked_id]["blocked_state"],
                "WAITING_FOR_DOMAIN_ADAPTER_FOUNDATION_MERGE",
            )

        for independent_id in ("A1", "A2", "A3", "C1", "C2", "D1", "D2", "E1", "E2"):
            self.assertIs(milestones[independent_id]["blocked_by_merge"], False)
            self.assertIs(milestones[independent_id]["can_merge_independently"], True)

    def test_forbidden_surface_policy_denies_runtime_and_merge_authority(self) -> None:
        graph = self.load_graph()
        policy = graph["forbidden_surface_policy"]

        for field in (
            "no_runtime_execution",
            "no_auto_merge",
            "no_branch_deletion",
            "no_direct_main_push",
            "no_browser_or_network",
            "no_provider_live_calls",
            "no_production_autonomy",
        ):
            self.assertIs(policy[field], True)

        denied = set(policy["denied_surfaces"])
        for surface in (
            "shell=True",
            "arbitrary argv",
            "network access",
            "browser opening",
            "provider API live calls",
            "production autonomy",
            "direct push to main",
            "auto-merge",
            "branch deletion",
        ):
            self.assertIn(surface, denied)

        merge_readiness = graph["merge_readiness"]
        self.assertIs(merge_readiness["auto_merge_permitted"], False)
        self.assertIs(merge_readiness["requires_human_merge"], True)


if __name__ == "__main__":
    unittest.main()
