"""ArtifactRef helpers for zero-copy path-reference handoff."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from execution_plane.permits.builder import stable_id

ARTIFACT_REF_SCHEMA_VERSION = "seos.artifact_ref.v1"


def build_artifact_refs(
    *,
    run_id: str,
    node_id: str,
    output_records: list[Mapping[str, Any]],
    storage_mode: str = "path_ref",
    copy_policy: str = "zero_copy_reference",
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for record in output_records:
        relative_path = str(record.get("relative_path", ""))
        if not relative_path:
            continue
        artifact_id = stable_id("ART", run_id, node_id, relative_path, record.get("sha256", ""))
        refs.append(
            {
                "schema_version": ARTIFACT_REF_SCHEMA_VERSION,
                "artifact_id": artifact_id,
                "producer_run_id": run_id,
                "producer_node_id": node_id,
                "uri": f"seos://run/{run_id}/{relative_path}",
                "relative_path": relative_path,
                "size_bytes": int(record.get("size_bytes", 0)),
                "sha256": str(record.get("sha256", "")),
                "media_type": media_type_for_path(relative_path),
                "storage_mode": storage_mode,
                "copy_policy": copy_policy,
                "lifetime": "managed_by_run_package",
            }
        )
    return refs


def media_type_for_path(relative_path: str) -> str:
    suffix = relative_path.rsplit(".", 1)[-1].lower() if "." in relative_path else ""
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "json": "application/json",
        "txt": "text/plain",
        "log": "text/plain",
        "exr": "image/aces",
        "bgeo": "application/x-bgeo",
        "sc": "application/x-bgeo-sc",
    }.get(suffix, "application/octet-stream")
