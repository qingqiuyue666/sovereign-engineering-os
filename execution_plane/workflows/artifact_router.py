"""Workflow-level ArtifactRef handoff helpers."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from execution_plane.runtime.artifact_router import (
    attach_artifacts_to_payload,
    build_routing_receipt,
    route_artifacts,
)
from execution_plane.workflows.definition import WorkflowDefinition
from execution_plane.workflows.node import WorkflowNode


def routed_payload_for_node(
    *,
    definition: WorkflowDefinition,
    node: WorkflowNode,
    node_results: Mapping[str, Mapping[str, Any]],
    workflow_output_root: Path,
) -> dict[str, Any]:
    upstream_refs: list[dict[str, Any]] = []
    upstream_roots: list[str] = []
    for upstream_node_id in sorted(definition.dependencies_for(node.node_id)):
        result = node_results.get(upstream_node_id, {})
        upstream_refs.extend(
            dict(ref)
            for ref in result.get("artifact_refs", [])
            if isinstance(ref, Mapping)
        )
        output_root = result.get("output_root")
        if output_root:
            upstream_roots.append(str(output_root))
    if not upstream_refs:
        return dict(node.payload)
    route_kwargs: dict[str, Any] = {
        "artifact_refs": upstream_refs,
        "downstream_node_id": node.node_id,
        "storage_mode": node.artifact_mode,
    }
    if node.artifact_mode == "managed_copy" and upstream_roots:
        route_kwargs["source_root"] = upstream_roots[0]
        route_kwargs["managed_copy_root"] = workflow_output_root / node.node_id / "managed_inputs"
    route = route_artifacts(**route_kwargs)
    build_routing_receipt(route=route, receipt_path=workflow_output_root / node.node_id / "artifact_routing_receipt.json")
    return attach_artifacts_to_payload(node.payload, route)
