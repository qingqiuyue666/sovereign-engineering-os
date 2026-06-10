"""Workflow node model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    adapter: str
    action: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    artifact_mode: str = "path_ref"

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, index: int) -> "WorkflowNode":
        node_id = str(payload.get("node_id") or f"node_{index + 1}")
        adapter = str(payload.get("adapter") or "")
        action = str(payload.get("action") or "")
        if not node_id:
            raise ValueError("workflow_node_id_required")
        if not adapter:
            raise ValueError(f"workflow_node_adapter_required:{node_id}")
        if not action:
            raise ValueError(f"workflow_node_action_required:{node_id}")
        depends = payload.get("depends_on", ())
        if isinstance(depends, str):
            depends_on = (depends,)
        elif isinstance(depends, list):
            depends_on = tuple(str(item) for item in depends)
        else:
            depends_on = ()
        raw_payload = payload.get("payload")
        node_payload = dict(raw_payload) if isinstance(raw_payload, Mapping) else {}
        artifact_mode = str(payload.get("artifact_mode") or "path_ref")
        return cls(
            node_id=node_id,
            adapter=adapter,
            action=action,
            payload=node_payload,
            depends_on=depends_on,
            artifact_mode=artifact_mode,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "adapter": self.adapter,
            "action": self.action,
            "payload": dict(self.payload),
            "depends_on": list(self.depends_on),
            "artifact_mode": self.artifact_mode,
        }
