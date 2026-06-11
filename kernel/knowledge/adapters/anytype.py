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

__all__ = ["export_anytype_object_bundle"]


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
