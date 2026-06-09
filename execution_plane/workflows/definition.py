"""Workflow definition loading and validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from creative.common import load_json
from execution_plane.permits.builder import stable_id
from execution_plane.runner.result_envelope import utc_now
from execution_plane.workflows.edge import WorkflowEdge
from execution_plane.workflows.node import WorkflowNode

WORKFLOW_DEFINITION_SCHEMA_VERSION = "seos.cross_software_workflow.v1"


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    nodes: tuple[WorkflowNode, ...]
    edges: tuple[WorkflowEdge, ...] = ()
    runtime_token: Mapping[str, Any] = field(default_factory=dict)
    output_root: Path = Path("work/rpc/workflow")
    failure_policy: Mapping[str, Any] = field(default_factory=dict)
    source_path: str | None = None

    def node_ids(self) -> set[str]:
        return {node.node_id for node in self.nodes}

    def node_by_id(self) -> dict[str, WorkflowNode]:
        return {node.node_id: node for node in self.nodes}

    def dependencies_for(self, node_id: str) -> set[str]:
        node_map = self.node_by_id()
        deps = set(node_map[node_id].depends_on)
        deps.update(edge.from_node for edge in self.edges if edge.to_node == node_id)
        return deps

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": WORKFLOW_DEFINITION_SCHEMA_VERSION,
            "workflow_id": self.workflow_id,
            "source_path": self.source_path,
            "output_root": self.output_root.as_posix(),
            "runtime_token": dict(self.runtime_token),
            "failure_policy": dict(self.failure_policy),
            "nodes": [node.as_dict() for node in self.nodes],
            "edges": [edge.as_dict() for edge in self.edges],
        }


def load_workflow_definition(params: Mapping[str, Any]) -> WorkflowDefinition:
    if not isinstance(params, Mapping):
        raise ValueError("workflow_params_must_be_mapping")
    source_path: str | None = None
    definition_payload: dict[str, Any] = dict(params)
    workflow_path = params.get("workflow_path")
    if workflow_path:
        path = Path(str(workflow_path))
        loaded = load_json(path)
        definition_payload = _deep_merge(dict(loaded), dict(params))
        source_path = path.as_posix()
    workflow_id = str(definition_payload.get("workflow_id") or stable_id("WORKFLOW", utc_now()))
    output_root = Path(str(params.get("output_root") or definition_payload.get("output_root") or "work/rpc/workflow"))
    runtime_token = definition_payload.get("runtime_token") if isinstance(definition_payload.get("runtime_token"), Mapping) else {}
    failure_policy = (
        definition_payload.get("failure_policy")
        if isinstance(definition_payload.get("failure_policy"), Mapping)
        else {"stop_downstream_on_failure": True}
    )
    nodes_raw = definition_payload.get("nodes")
    if not isinstance(nodes_raw, list) or not nodes_raw:
        raise ValueError("workflow_nodes_required")
    nodes = tuple(
        WorkflowNode.from_mapping(raw_node if isinstance(raw_node, Mapping) else {}, index=index)
        for index, raw_node in enumerate(nodes_raw)
    )
    node_ids = [node.node_id for node in nodes]
    if len(set(node_ids)) != len(node_ids):
        raise ValueError("workflow_node_ids_must_be_unique")
    edges_raw = definition_payload.get("edges", [])
    if not isinstance(edges_raw, list):
        raise ValueError("workflow_edges_must_be_list")
    edges = tuple(WorkflowEdge.from_mapping(raw_edge if isinstance(raw_edge, Mapping) else {}) for raw_edge in edges_raw)
    ids = set(node_ids)
    for edge in edges:
        if edge.from_node not in ids or edge.to_node not in ids:
            raise ValueError(f"workflow_edge_references_missing_node:{edge.from_node}->{edge.to_node}")
    for node in nodes:
        for dep in node.depends_on:
            if dep not in ids:
                raise ValueError(f"workflow_dependency_references_missing_node:{node.node_id}:{dep}")
    return WorkflowDefinition(
        workflow_id=workflow_id,
        nodes=nodes,
        edges=edges,
        runtime_token=dict(runtime_token),
        output_root=output_root,
        failure_policy=dict(failure_policy),
        source_path=source_path,
    )


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if key == "workflow_path":
            continue
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(dict(merged[key]), dict(value))
        elif value not in (None, "", [], {}):
            merged[key] = value
    return merged
