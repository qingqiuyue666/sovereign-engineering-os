"""Build a public-safe SEOS knowledge graph from workspace artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import json

from kernel.knowledge.object_model import KnowledgeObject, KnowledgeRelation, digest_payload, now_utc, safe_id
from kernel.knowledge.redaction import public_path_ref

__all__ = ["build_workspace_graph", "write_workspace_graph"]


def build_workspace_graph(workspace: str | Path, *, public: bool = True) -> dict[str, object]:
    """Build a relation graph from SEOS task and receipt artifacts.

    The graph is a mirror artifact: it summarizes objects and relationships for
    human review and UI tools. It does not introduce approvals, permits, or
    execution authority.
    """

    workspace_root = Path(workspace).resolve()
    seos_root = workspace_root / ".seos"
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []

    task_ids: set[str] = set()
    for task_path in _iter_json(seos_root / "tasks"):
        task = _read_json(task_path)
        task_id = safe_id(task.get("task_id") or task_path.stem, fallback=task_path.stem)
        task_ids.add(task_id)
        task_object = KnowledgeObject(
            "seos.task",
            task_id,
            "mirror",
            title=str(task.get("title") or task_id),
            properties={
                "status": task.get("status"),
                "task_type": task.get("task_type"),
                "classification": task.get("classification"),
                "approval_required": task.get("approval_required"),
                "requested_capabilities": task.get("requested_capabilities", []),
                "source_refs": task.get("source_refs", []),
                "path_ref": public_path_ref(task_path, root=workspace_root) if public else task_path.as_posix(),
            },
            public=public,
            local_path_redacted=public,
        )
        nodes.append(task_object.as_dict(include_digest=True))
        for evidence_ref in task.get("evidence_refs", []) if isinstance(task.get("evidence_refs", []), list) else []:
            evidence_id = safe_id(f"{task_id}:{evidence_ref}", fallback=f"{task_id}:evidence")
            edges.append(_edge("seos.task", task_id, "has_evidence_ref", "seos.evidence_ref", evidence_id))
            nodes.append(
                KnowledgeObject(
                    "seos.evidence_ref",
                    evidence_id,
                    "mirror",
                    title=f"Evidence reference for {task_id}",
                    properties={"task_id": task_id, "ref": str(evidence_ref)},
                    relations=(KnowledgeRelation("supports", "seos.task", task_id),),
                    public=public,
                    local_path_redacted=public,
                ).as_dict(include_digest=True)
            )

    for receipt_path in _iter_json(seos_root / "receipts"):
        receipt = _read_json(receipt_path)
        task_id = safe_id(receipt.get("task_id"), fallback="unknown_task")
        receipt_type = safe_id(receipt.get("receipt_type"), fallback="receipt")
        digest = str(receipt.get("digest") or digest_payload(receipt))
        receipt_id = safe_id(f"{task_id}:{receipt_type}:{digest[-16:]}", fallback=receipt_path.stem)
        receipt_object = KnowledgeObject(
            "seos.receipt",
            receipt_id,
            "receipt",
            title=f"{receipt_type} receipt for {task_id}",
            properties={
                "task_id": task_id,
                "receipt_type": receipt.get("receipt_type"),
                "created_at": receipt.get("created_at"),
                "approved": receipt.get("approved"),
                "dry_run": receipt.get("dry_run"),
                "execution_performed": receipt.get("execution_performed"),
                "result": receipt.get("result"),
                "digest": receipt.get("digest"),
                "path_ref": public_path_ref(receipt_path, root=workspace_root) if public else receipt_path.as_posix(),
            },
            relations=(KnowledgeRelation("for_task", "seos.task", task_id),),
            public=public,
            local_path_redacted=public,
        )
        nodes.append(receipt_object.as_dict(include_digest=True))
        edges.append(_edge("seos.receipt", receipt_id, "for_task", "seos.task", task_id))
        if task_id in task_ids:
            edges.append(_edge("seos.task", task_id, "has_receipt", "seos.receipt", receipt_id))

    graph = {
        "schema": "seos_knowledge_graph_v1",
        "created_at": now_utc(),
        "workspace_ref": public_path_ref(workspace_root) if public else workspace_root.as_posix(),
        "public": public,
        "local_path_redacted": public,
        "authority": "mirror",
        "execution_authority_granted": False,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }
    graph["digest"] = digest_payload({"nodes": nodes, "edges": edges})
    return graph


def write_workspace_graph(workspace: str | Path, output: str | Path, *, public: bool = True) -> dict[str, object]:
    graph = build_workspace_graph(workspace, public=public)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "graph": graph, "path": output_path.as_posix()}


def _iter_json(path: Path) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.json") if item.is_file())


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _edge(source_type: str, source_id: str, relation_type: str, target_type: str, target_id: str) -> dict[str, str]:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "relation_type": relation_type,
        "target_type": target_type,
        "target_id": target_id,
    }
