"""ArtifactRef zero-copy routing helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
import shutil

from creative.common import write_json
from execution_plane.artifacts import ARTIFACT_REF_SCHEMA_VERSION, build_artifact_refs
from execution_plane.permits.builder import stable_id
from execution_plane.runner.path_guard import assert_within_root, validate_relative_output_path
from execution_plane.runner.result_envelope import collect_output_records, utc_now

ARTIFACT_ROUTING_RECEIPT_SCHEMA_VERSION = "seos.artifact_routing_receipt.v1"
VALID_STORAGE_MODES = {"path_ref", "managed_copy", "external_ref"}


def refs_from_outputs(
    *,
    run_id: str,
    node_id: str,
    output_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return build_artifact_refs(run_id=run_id, node_id=node_id, output_records=[dict(item) for item in output_records])


def validate_artifact_ref(ref: Mapping[str, Any]) -> bool:
    required = {
        "artifact_id",
        "producer_run_id",
        "producer_node_id",
        "uri",
        "relative_path",
        "size_bytes",
        "sha256",
        "media_type",
        "storage_mode",
        "copy_policy",
        "lifetime",
    }
    return (
        ref.get("schema_version") == ARTIFACT_REF_SCHEMA_VERSION
        and required.issubset(ref.keys())
        and ref.get("storage_mode") in VALID_STORAGE_MODES
    )


def route_artifacts(
    *,
    artifact_refs: Sequence[Mapping[str, Any]],
    downstream_node_id: str,
    source_root: str | Path | None = None,
    managed_copy_root: str | Path | None = None,
    storage_mode: str = "path_ref",
) -> dict[str, Any]:
    if storage_mode not in VALID_STORAGE_MODES:
        raise ValueError(f"unsupported_storage_mode:{storage_mode}")
    refs = [dict(ref) for ref in artifact_refs]
    for ref in refs:
        if not validate_artifact_ref(ref):
            raise ValueError("invalid_artifact_ref")
    if storage_mode == "path_ref":
        return {
            "schema_version": "seos.artifact_route.v1",
            "downstream_node_id": downstream_node_id,
            "storage_mode": "path_ref",
            "artifact_refs": refs,
            "copied_files": [],
        }
    if storage_mode == "external_ref":
        external_refs = [{**ref, "storage_mode": "external_ref"} for ref in refs]
        return {
            "schema_version": "seos.artifact_route.v1",
            "downstream_node_id": downstream_node_id,
            "storage_mode": "external_ref",
            "artifact_refs": external_refs,
            "copied_files": [],
        }
    if source_root is None or managed_copy_root is None:
        raise ValueError("managed_copy_requires_source_and_destination")
    copied = _managed_copy(refs, source_root=Path(source_root), managed_copy_root=Path(managed_copy_root))
    return {
        "schema_version": "seos.artifact_route.v1",
        "downstream_node_id": downstream_node_id,
        "storage_mode": "managed_copy",
        "artifact_refs": copied["artifact_refs"],
        "copied_files": copied["copied_files"],
    }


def build_routing_receipt(
    *,
    route: Mapping[str, Any],
    receipt_path: str | Path | None = None,
) -> dict[str, Any]:
    receipt = {
        "schema_version": ARTIFACT_ROUTING_RECEIPT_SCHEMA_VERSION,
        "routing_id": stable_id("ROUTE", route.get("downstream_node_id"), utc_now()),
        "created_at": utc_now(),
        "downstream_node_id": route.get("downstream_node_id"),
        "storage_mode": route.get("storage_mode"),
        "artifact_refs": [dict(ref) for ref in route.get("artifact_refs", []) if isinstance(ref, Mapping)],
        "copied_files": [dict(item) for item in route.get("copied_files", []) if isinstance(item, Mapping)],
    }
    if receipt_path is not None:
        write_json(Path(receipt_path), receipt)
    return receipt


def attach_artifacts_to_payload(
    payload: Mapping[str, Any] | None,
    route: Mapping[str, Any],
) -> dict[str, Any]:
    routed = dict(payload or {})
    routed["artifact_refs"] = [dict(ref) for ref in route.get("artifact_refs", []) if isinstance(ref, Mapping)]
    return routed


def _managed_copy(
    refs: Sequence[Mapping[str, Any]],
    *,
    source_root: Path,
    managed_copy_root: Path,
) -> dict[str, Any]:
    copied_files: list[dict[str, Any]] = []
    managed_copy_root.mkdir(parents=True, exist_ok=True)
    for ref in refs:
        relative_path = validate_relative_output_path(str(ref["relative_path"]))
        source_path = assert_within_root(relative_path, source_root)
        destination_path = assert_within_root(relative_path, managed_copy_root)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        copied_files.append(
            {
                "source_relative_path": relative_path,
                "managed_relative_path": destination_path.relative_to(managed_copy_root.resolve()).as_posix(),
            }
        )
    output_records = collect_output_records(managed_copy_root)
    copied_refs = build_artifact_refs(
        run_id=stable_id("MANAGED_COPY", managed_copy_root.as_posix(), len(output_records)),
        node_id="managed_copy",
        output_records=output_records,
        storage_mode="managed_copy",
        copy_policy="managed_copy_requested",
    )
    return {"artifact_refs": copied_refs, "copied_files": copied_files}
