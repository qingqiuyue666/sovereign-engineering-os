"""Anytype object-bundle mirror adapter for SEOS.

This adapter intentionally exports SEOS objects into a neutral JSON bundle rather
than depending on Anytype source code or runtime APIs. It preserves the useful
object/type/relation shape while keeping SEOS as the authority layer.
"""

from __future__ import annotations

from pathlib import Path
import json

from kernel.knowledge.graph import build_workspace_graph
from kernel.knowledge.object_model import digest_payload, now_utc
from kernel.knowledge.redaction import public_path_ref

__all__ = ["export_anytype_object_bundle", "import_anytype_object_bundle"]


def export_anytype_object_bundle(workspace: str | Path, output: str | Path, *, public: bool = True) -> dict[str, object]:
    """Write a neutral Anytype-style object bundle from a SEOS workspace graph."""

    workspace_root = Path(workspace).resolve()
    graph = build_workspace_graph(workspace_root, public=public)
    objects = []
    for node in graph["nodes"]:
        properties = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
        objects.append(
            {
                "object_type": node.get("object_type"),
                "object_id": node.get("object_id"),
                "name": node.get("title") or node.get("object_id"),
                "authority": node.get("authority"),
                "source": "seos",
                "properties": properties,
                "relations": node.get("relations", []),
                "digest": node.get("digest"),
                "execution_authority_granted": False,
            }
        )
    bundle = {
        "schema": "seos_anytype_object_bundle_v1",
        "created_at": now_utc(),
        "workspace_ref": public_path_ref(workspace_root) if public else workspace_root.as_posix(),
        "public": public,
        "authority": "mirror",
        "execution_authority_granted": False,
        "object_count": len(objects),
        "objects": objects,
        "relations": graph["edges"],
        "license_boundary": "neutral_export_no_anytype_source_dependency",
    }
    bundle["digest"] = digest_payload({"objects": objects, "relations": graph["edges"]})
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "bundle": bundle, "path": output_path.as_posix()}


def import_anytype_object_bundle(source: str | Path, output: str | Path, *, public: bool = True) -> dict[str, object]:
    """Validate a neutral Anytype-style object bundle as non-authority intent.

    Import means "record a reviewable object-model proposal." It never creates
    SEOS tasks, approvals, permits, receipts, or execution authority.
    """

    source_path = Path(source).expanduser().resolve()
    output_path = Path(output)
    try:
        bundle = json.loads(source_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"ok": False, "error": "anytype_bundle_not_found", "path": source_path.as_posix()}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": "anytype_bundle_invalid_json", "message": str(exc)}

    objects = bundle.get("objects", [])
    relations = bundle.get("relations", [])
    problems: list[str] = []
    if not isinstance(objects, list):
        problems.append("objects_must_be_list")
        objects = []
    if not isinstance(relations, list):
        problems.append("relations_must_be_list")
        relations = []
    for index, item in enumerate(objects):
        if not isinstance(item, dict):
            problems.append(f"object_{index}_must_be_object")
            continue
        if item.get("execution_authority_granted") is True:
            problems.append(f"object_{index}_claims_execution_authority")
        if item.get("authority") not in {None, "proposal", "mirror", "receipt", "invalid"}:
            problems.append(f"object_{index}_invalid_authority")

    record = {
        "schema": "seos_anytype_import_record_v1",
        "created_at": now_utc(),
        "source_ref": public_path_ref(source_path) if public else source_path.as_posix(),
        "source_digest": digest_payload(bundle),
        "public": public,
        "authority": "proposal",
        "accepted_as": "object_model_proposal_only",
        "execution_authority_granted": False,
        "task_created": False,
        "approval_created": False,
        "permit_created": False,
        "network_call_performed": False,
        "object_count": len(objects),
        "relation_count": len(relations),
        "problems": problems,
        "objects": [
            {
                "object_type": item.get("object_type"),
                "object_id": item.get("object_id"),
                "name": item.get("name"),
                "authority": item.get("authority", "proposal"),
                "digest": item.get("digest") or digest_payload(item),
                "execution_authority_granted": False,
            }
            for item in objects
            if isinstance(item, dict)
        ],
    }
    record["digest"] = digest_payload(record)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": not problems, "record": record, "path": output_path.as_posix()}
