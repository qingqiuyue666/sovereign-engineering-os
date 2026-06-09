"""Topological workflow scheduler."""

from __future__ import annotations

from execution_plane.workflows.definition import WorkflowDefinition
from execution_plane.workflows.node import WorkflowNode


def topological_layers(definition: WorkflowDefinition) -> list[list[WorkflowNode]]:
    remaining = definition.node_by_id()
    completed: set[str] = set()
    layers: list[list[WorkflowNode]] = []
    while remaining:
        ready = [
            node
            for node_id, node in sorted(remaining.items())
            if definition.dependencies_for(node_id).issubset(completed)
        ]
        if not ready:
            cycle_nodes = ",".join(sorted(remaining))
            raise ValueError(f"workflow_cycle_detected:{cycle_nodes}")
        layers.append(ready)
        for node in ready:
            completed.add(node.node_id)
            remaining.pop(node.node_id)
    return layers
