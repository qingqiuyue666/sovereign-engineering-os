"""Build deterministic rerun definitions from failed workflow nodes."""

from __future__ import annotations

from typing import Any

from execution_plane.workflows.definition import WorkflowDefinition


def build_rerun_definition(definition: WorkflowDefinition, failed_node_id: str) -> dict[str, Any]:
    downstream = _downstream_nodes(definition, failed_node_id)
    selected = {failed_node_id, *downstream}
    return {
        **definition.as_dict(),
        "workflow_id": f"{definition.workflow_id}.rerun_from.{failed_node_id}",
        "rerun": {
            "schema_version": "seos.workflow_rerun_plan.v1",
            "failed_node_id": failed_node_id,
            "included_node_ids": sorted(selected),
        },
        "nodes": [node.as_dict() for node in definition.nodes if node.node_id in selected],
        "edges": [
            edge.as_dict()
            for edge in definition.edges
            if edge.from_node in selected and edge.to_node in selected
        ],
    }


def _downstream_nodes(definition: WorkflowDefinition, node_id: str) -> set[str]:
    downstream: set[str] = set()
    changed = True
    while changed:
        changed = False
        for candidate in definition.nodes:
            deps = definition.dependencies_for(candidate.node_id)
            if candidate.node_id not in downstream and deps.intersection({node_id, *downstream}):
                downstream.add(candidate.node_id)
                changed = True
    downstream.discard(node_id)
    return downstream
