"""Notion read-only dashboard payload builder for SEOS.

This module does not call the Notion API. It creates a public-safe JSON payload
that a separate operator-owned publishing step may review. SEOS stays local-first
and authoritative.
"""

from __future__ import annotations

from pathlib import Path
import json

from kernel.knowledge.graph import build_workspace_graph
from kernel.knowledge.object_model import digest_payload, now_utc
from kernel.knowledge.redaction import public_path_ref

__all__ = ["build_notion_readonly_dashboard", "build_notion_readonly_source_mirror"]


def build_notion_readonly_dashboard(workspace: str | Path, output: str | Path, *, public: bool = True) -> dict[str, object]:
    """Build a public-safe dashboard payload for optional team review."""

    workspace_root = Path(workspace).resolve()
    graph = build_workspace_graph(workspace_root, public=public)
    tasks = []
    receipts = []
    for node in graph["nodes"]:
        properties = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
        if node.get("object_type") == "seos.task":
            tasks.append(
                {
                    "task_id": node.get("object_id"),
                    "title": node.get("title"),
                    "status": properties.get("status"),
                    "classification": properties.get("classification"),
                    "approval_required": properties.get("approval_required"),
                    "digest": node.get("digest"),
                }
            )
        if node.get("object_type") == "seos.receipt":
            receipts.append(
                {
                    "receipt_id": node.get("object_id"),
                    "task_id": properties.get("task_id"),
                    "receipt_type": properties.get("receipt_type"),
                    "created_at": properties.get("created_at"),
                    "dry_run": properties.get("dry_run"),
                    "execution_performed": properties.get("execution_performed"),
                    "digest": properties.get("digest") or node.get("digest"),
                }
            )
    dashboard = {
        "schema": "seos_notion_readonly_dashboard_v1",
        "created_at": now_utc(),
        "workspace_ref": public_path_ref(workspace_root) if public else workspace_root.as_posix(),
        "mode": "readonly_mirror_payload",
        "public": public,
        "authority": "mirror",
        "execution_authority_granted": False,
        "network_call_performed": False,
        "credential_required_by_this_step": False,
        "task_count": len(tasks),
        "receipt_count": len(receipts),
        "tasks": tasks,
        "receipts": receipts,
        "notion_boundary": "optional_operator_review_payload_not_source_of_truth",
    }
    dashboard["digest"] = digest_payload({"tasks": tasks, "receipts": receipts})
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "dashboard": dashboard, "path": output_path.as_posix()}


def build_notion_readonly_source_mirror(source: str | Path, output: str | Path, *, public: bool = True) -> dict[str, object]:
    """Build a reviewed Notion mirror payload from an existing public JSON source.

    This is a local packaging step only. It does not call Notion, read tokens, or
    make the source a SEOS authority layer.
    """

    source_path = Path(source).expanduser().resolve()
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"ok": False, "error": "notion_source_not_found", "path": source_path.as_posix()}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": "notion_source_invalid_json", "message": str(exc)}

    if not isinstance(payload, dict):
        return {"ok": False, "error": "notion_source_must_be_object"}

    mirror = {
        "schema": "seos_notion_readonly_source_mirror_v1",
        "created_at": now_utc(),
        "source_ref": public_path_ref(source_path) if public else source_path.as_posix(),
        "source_schema": payload.get("schema") or payload.get("kind", "unknown"),
        "source_digest": digest_payload(payload),
        "mode": "readonly_mirror_payload",
        "public": public,
        "authority": "mirror",
        "execution_authority_granted": False,
        "network_call_performed": False,
        "credential_required_by_this_step": False,
        "task_created": False,
        "approval_created": False,
        "permit_created": False,
        "allowed_fields": _public_summary(payload),
        "notion_boundary": "operator_may_review_and_publish_manually_not_source_of_truth",
    }
    mirror["digest"] = digest_payload(mirror)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(mirror, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "dashboard": mirror, "path": output_path.as_posix()}


def _public_summary(payload: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key in (
        "schema",
        "kind",
        "inspection_status",
        "pressure_status",
        "hardening_status",
        "operation_status",
        "read_only",
        "ready_for_execution",
        "spine_id",
    ):
        if key in payload:
            result[key] = payload[key]
    for key in ("action_summary", "asset_summary", "tool_health_summary"):
        value = payload.get(key)
        if isinstance(value, dict):
            result[key] = value
    return result
