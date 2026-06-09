"""Workflow edge model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowEdge:
    from_node: str
    to_node: str
    mode: str = "artifact_refs"

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "WorkflowEdge":
        from_node = str(payload.get("from") or payload.get("from_node") or "")
        to_node = str(payload.get("to") or payload.get("to_node") or "")
        if not from_node or not to_node:
            raise ValueError("workflow_edge_requires_from_and_to")
        return cls(from_node=from_node, to_node=to_node, mode=str(payload.get("mode") or "artifact_refs"))

    def as_dict(self) -> dict[str, Any]:
        return {"from": self.from_node, "to": self.to_node, "mode": self.mode}
