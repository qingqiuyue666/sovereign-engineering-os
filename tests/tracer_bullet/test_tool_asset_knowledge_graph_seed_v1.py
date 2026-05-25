"""Tracer-bullet tests for tool / asset knowledge graph seed v1."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.runtime.tool_asset_knowledge_graph_seed import (
    REQUIRED_CANDIDATE_LINKS,
    REQUIRED_EDGE_TYPES,
    REQUIRED_NODE_TYPES,
    CandidateSubstrateNode,
    ToolNode,
    build_knowledge_graph_seed,
    validate_knowledge_graph_seed,
)

POLICY_PATH = Path("governance/knowledge/tool_asset_knowledge_graph_seed_v1.json")
SOURCE_PATH = Path("kernel/runtime/tool_asset_knowledge_graph_seed.py")


class ToolAssetKnowledgeGraphSeedTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundaries(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "tool_asset_knowledge_graph_seed_v1")
        self.assertFalse(policy["direct_dependency_adoption_allowed"])
        self.assertFalse(policy["runtime_integration_allowed"])
        self.assertFalse(policy["third_party_install_or_vendor_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["credential_storage_allowed"])

    def test_all_required_node_types_present(self):
        seed = build_knowledge_graph_seed()
        node_types = {getattr(node, "node_type", type(node).__name__) for node in seed.nodes}
        self.assertTrue(set(REQUIRED_NODE_TYPES).issubset(node_types))

    def test_all_required_edge_types_present(self):
        seed = build_knowledge_graph_seed()
        edge_types = {edge.edge_type for edge in seed.edges}
        self.assertTrue(set(REQUIRED_EDGE_TYPES).issubset(edge_types))

    def test_required_candidate_links_present(self):
        seed = build_knowledge_graph_seed()
        candidate_urls = {
            node.github_url
            for node in seed.nodes
            if isinstance(node, CandidateSubstrateNode)
        }
        self.assertTrue(set(REQUIRED_CANDIDATE_LINKS.values()).issubset(candidate_urls))

    def test_candidates_are_not_imported_as_dependencies(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        forbidden_imports = (
            "temporalio",
            "nats",
            "lancedb",
            "duckdb",
            "extism",
            "wasmtime",
            "pxr",
            "tauri",
            "semgrep",
            "langgraph",
            "autogen",
            "crewai",
        )
        for forbidden in forbidden_imports:
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)

    def test_candidate_direct_dependency_allowed_now_false(self):
        seed = build_knowledge_graph_seed()
        for node in seed.nodes:
            if isinstance(node, CandidateSubstrateNode):
                self.assertFalse(node.direct_dependency_allowed_now, node.candidate_id)

    def test_candidate_runtime_integration_allowed_now_false(self):
        seed = build_knowledge_graph_seed()
        for node in seed.nodes:
            if isinstance(node, CandidateSubstrateNode):
                self.assertFalse(node.runtime_integration_allowed_now, node.candidate_id)

    def test_executable_tool_nodes_require_risk_edge(self):
        seed = build_knowledge_graph_seed()
        failures = validate_knowledge_graph_seed(seed)
        self.assertFalse(
            [failure for failure in failures if "executable_tool_missing_risk_edge" in failure]
        )
        executable_tools = [
            node for node in seed.nodes if isinstance(node, ToolNode) and node.executable
        ]
        self.assertTrue(executable_tools)

    def test_production_approval_requires_approved_for_edge(self):
        seed = build_knowledge_graph_seed()
        failures = validate_knowledge_graph_seed(seed)
        self.assertFalse(
            [failure for failure in failures if "production_approval_missing_edge" in failure]
        )

    def test_seed_validates(self):
        seed = build_knowledge_graph_seed()
        self.assertEqual(validate_knowledge_graph_seed(seed), ())


if __name__ == "__main__":
    unittest.main()
