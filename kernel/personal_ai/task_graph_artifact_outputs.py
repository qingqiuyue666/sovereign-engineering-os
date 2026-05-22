"""Graph-level artifact output binding for local task graph fixtures."""

from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_canonical_json, sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "TASK_GRAPH_ARTIFACT_OUTPUTS_FILE",
    "build_task_graph_artifact_outputs_manifest",
    "task_graph_artifact_outputs_projection_sha256",
    "write_task_graph_artifact_outputs_manifest",
]

TASK_GRAPH_ARTIFACT_OUTPUTS_FILE = "task_graph_artifact_outputs.json"

_MANIFEST_TYPE = "personal_ai_task_graph_artifact_outputs_v1"
_GRAPH_ARTIFACT_NODE_ID = "__task_graph__"
_GRAPH_ARTIFACT_ADAPTER_ID = "task_graph_fixture"
_GRAPH_ARTIFACT_CAPABILITY = "write_task_graph_artifact_outputs"
_LOCAL_ASSET_ADAPTER_ID = "local_asset_runtime"
_LOCAL_ASSET_CAPABILITY = "launch_local_asset_scan"
_LOCAL_ASSET_SMOKE_READINESS_CAPABILITY = "launch_local_asset_smoke_readiness"
_LOCAL_ASSET_HUMAN_SMOKE_CAPABILITY = "launch_local_asset_human_smoke_run"
_DELIVERY_ADAPTER_ID = "runtime_delivery_package"
_DELIVERY_CAPABILITY = "validate_runtime_delivery"

_LOCAL_ASSET_DIRECT_PATH_FIELDS = (
    ("asset_scan_run_receipt", "asset_scan_run_receipt_path"),
    ("asset_scan_failure_bundle", "asset_scan_failure_bundle_path"),
    ("asset_scan_failure_summary", "asset_scan_failure_summary_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
    ("local_asset_sqlite_index", "local_asset_sqlite_index_path"),
    (
        "local_asset_sqlite_index_manifest",
        "local_asset_sqlite_index_manifest_path",
    ),
    ("local_asset_sqlite_query_summary", "local_asset_sqlite_query_summary_path"),
    (
        "local_asset_incremental_scan_plan",
        "local_asset_incremental_scan_plan_path",
    ),
    (
        "local_asset_incremental_scan_manifest",
        "local_asset_incremental_scan_manifest_path",
    ),
    (
        "local_asset_incremental_scan_summary",
        "local_asset_incremental_scan_summary_path",
    ),
    ("asset_manifest", "asset_manifest_path"),
    ("asset_index", "asset_index_path"),
    ("duplicates_report", "duplicates_report_path"),
    ("media_inventory", "media_inventory_path"),
    ("asset_runtime_audit_log", "asset_runtime_audit_log_path"),
    ("asset_runtime_validation_report", "asset_runtime_validation_report_path"),
    ("asset_runtime_quarantine_manifest", "asset_runtime_quarantine_manifest_path"),
    ("launcher_summary", "launcher_summary_path"),
)

_LOCAL_ASSET_OUTPUT_FILE_ROLES = {
    "asset_manifest.json": "asset_manifest",
    "asset_index.json": "asset_index",
    "duplicates_report.json": "duplicates_report",
    "media_inventory.md": "media_inventory",
    "asset_runtime_audit_log.jsonl": "asset_runtime_audit_log",
    "asset_runtime_validation_report.json": "asset_runtime_validation_report",
    "asset_runtime_quarantine_manifest.json": "asset_runtime_quarantine_manifest",
}

_LOCAL_ASSET_SMOKE_READINESS_DIRECT_PATH_FIELDS = (
    (
        "local_asset_smoke_readiness_report",
        "local_asset_smoke_readiness_report_path",
    ),
    (
        "local_asset_smoke_readiness_manifest",
        "local_asset_smoke_readiness_manifest_path",
    ),
    (
        "local_asset_smoke_readiness_summary",
        "local_asset_smoke_readiness_summary_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
    ("launcher_summary", "launcher_summary_path"),
)

_LOCAL_ASSET_HUMAN_SMOKE_DIRECT_PATH_FIELDS = (
    (
        "local_asset_human_smoke_approval",
        "local_asset_human_smoke_approval_path",
    ),
    (
        "local_asset_human_smoke_admission_receipt",
        "local_asset_human_smoke_admission_receipt_path",
    ),
    (
        "local_asset_human_smoke_run_summary",
        "local_asset_human_smoke_run_summary_path",
    ),
    (
        "local_asset_human_smoke_scan_artifact_index",
        "scan_artifact_index_path",
    ),
    (
        "local_asset_human_smoke_scan_artifact_index_manifest",
        "scan_artifact_index_manifest_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_DELIVERY_PATH_FIELDS = (
    ("runtime_delivery_manifest", "runtime_delivery_manifest_path"),
    ("runtime_delivery_validation", "runtime_delivery_validation_path"),
)

_GRAPH_ARTIFACTS = (
    ("task_graph_execution_manifest", "execution_manifest_path"),
    ("task_graph_replay_manifest", "replay_manifest_path"),
    ("task_graph_failure_bundle", "failure_bundle_path"),
)

_ROLE_ARTIFACT_TYPES = {
    "asset_runtime_audit_log": "jsonl",
    "asset_scan_failure_summary": "markdown",
    "launcher_summary": "markdown",
    "local_asset_incremental_scan_summary": "markdown",
    "local_asset_human_smoke_run_summary": "markdown",
    "local_asset_sqlite_query_summary": "markdown",
    "local_asset_smoke_readiness_summary": "markdown",
    "media_inventory": "markdown",
}


def build_task_graph_artifact_outputs_manifest(
    *,
    graph_id: str,
    graph_path: Path,
    graph_sha256: str,
    graph_execution_mode: str,
    graph_success: bool,
    node_order: tuple[str, ...],
    executed_nodes: list[dict],
    output_dir: Path,
    execution_manifest_path: Path,
    replay_manifest_path: Path,
    failure_bundle_path: Path | None,
) -> dict:
    """Build a metadata-only task graph artifact output manifest."""

    output_path = Path(output_dir)
    ordered_nodes = _ordered_nodes(executed_nodes, node_order)
    artifact_candidates = []
    for node in ordered_nodes:
        artifact_candidates.extend(_node_artifact_candidates(node, output_path))
    artifact_candidates.extend(
        _graph_artifact_candidates(
            graph_success=graph_success,
            output_dir=output_path,
            execution_manifest_path=execution_manifest_path,
            replay_manifest_path=replay_manifest_path,
            failure_bundle_path=failure_bundle_path,
        )
    )
    artifacts = _assign_artifact_ids(artifact_candidates)
    node_artifact_counts = {
        node_id: sum(1 for artifact in artifacts if artifact["node_id"] == node_id)
        for node_id in node_order
    }
    failed_node_ids = {
        node["node_id"] for node in ordered_nodes if node.get("status") == "failed"
    }
    failed_node_artifacts = [
        _failed_node_artifact_ref(artifact)
        for artifact in artifacts
        if artifact["node_id"] in failed_node_ids
    ]
    return {
        "manifest_type": _MANIFEST_TYPE,
        "authority": "non_authority",
        "execution_capability": "local_task_graph_fixture_only",
        "graph_id": graph_id,
        "graph_path": Path(graph_path).as_posix(),
        "graph_sha256": graph_sha256,
        "graph_execution_mode": graph_execution_mode,
        "graph_success": graph_success,
        "node_order": list(node_order),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "node_artifact_counts": node_artifact_counts,
        "failed_node_artifacts": failed_node_artifacts,
        "skipped_nodes": _skipped_node_refs(ordered_nodes),
        "input_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_task_graph_artifacts",
    }


def task_graph_artifact_outputs_projection_sha256(manifest: dict) -> str:
    """Hash a non-circular manifest projection for replay binding.

    The final artifact-output manifest includes the replay manifest file hash.
    The replay manifest therefore binds a canonical projection that normalizes
    only that self-referential artifact's file existence, size, and hash.
    """

    projection = json.loads(json.dumps(manifest, sort_keys=True))
    for artifact in projection.get("artifacts", []):
        if (
            artifact.get("node_id") == _GRAPH_ARTIFACT_NODE_ID
            and artifact.get("artifact_role") == "task_graph_replay_manifest"
        ):
            artifact["exists"] = False
            artifact["sha256"] = None
            artifact["size_bytes"] = None
    return sha256_canonical_json(projection)


def write_task_graph_artifact_outputs_manifest(
    output_path: Path,
    manifest: dict,
) -> None:
    output_file = Path(output_path)
    if output_file.exists():
        raise ValueError("task graph artifact outputs already exists")
    write_json_atomically(output_file, manifest)


def _ordered_nodes(executed_nodes, node_order):
    by_id = {node["node_id"]: node for node in executed_nodes}
    return [by_id[node_id] for node_id in node_order if node_id in by_id]


def _node_artifact_candidates(node, output_dir):
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"] == _LOCAL_ASSET_CAPABILITY
    ):
        return _local_asset_artifact_candidates(node, output_dir)
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"] == _LOCAL_ASSET_SMOKE_READINESS_CAPABILITY
    ):
        return _local_asset_smoke_readiness_artifact_candidates(node, output_dir)
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"] == _LOCAL_ASSET_HUMAN_SMOKE_CAPABILITY
    ):
        return _local_asset_human_smoke_artifact_candidates(node, output_dir)
    if (
        node["adapter_id"] == _DELIVERY_ADAPTER_ID
        and node["capability"] == _DELIVERY_CAPABILITY
    ):
        return _delivery_artifact_candidates(node, output_dir)
    return []


def _local_asset_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_ASSET_DIRECT_PATH_FIELDS:
        path_value = node.get(field_name)
        if _add_role_path(role_paths, seen_roles, role, path_value):
            continue
    output_paths = node.get("asset_runtime_output_paths")
    if isinstance(output_paths, dict):
        for file_name in sorted(output_paths):
            role = _LOCAL_ASSET_OUTPUT_FILE_ROLES.get(file_name)
            if role is not None:
                _add_role_path(role_paths, seen_roles, role, output_paths[file_name])
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_smoke_readiness_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_ASSET_SMOKE_READINESS_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_human_smoke_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_ASSET_HUMAN_SMOKE_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _delivery_artifact_candidates(node, output_dir):
    delivery_validation = node.get("delivery_validation")
    if not isinstance(delivery_validation, dict):
        return []
    role_paths = []
    seen_roles = set()
    for role, field_name in _DELIVERY_PATH_FIELDS:
        _add_role_path(
            role_paths,
            seen_roles,
            role,
            delivery_validation.get(field_name),
        )
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _graph_artifact_candidates(
    *,
    graph_success,
    output_dir,
    execution_manifest_path,
    replay_manifest_path,
    failure_bundle_path,
):
    graph_status = "completed" if graph_success else "failed"
    paths_by_name = {
        "execution_manifest_path": execution_manifest_path,
        "replay_manifest_path": replay_manifest_path,
        "failure_bundle_path": failure_bundle_path,
    }
    candidates = []
    for role, path_name in _GRAPH_ARTIFACTS:
        path_value = paths_by_name[path_name]
        if role == "task_graph_failure_bundle" and path_value is None:
            continue
        candidates.append(
            _artifact_record(
                node_id=_GRAPH_ARTIFACT_NODE_ID,
                adapter_id=_GRAPH_ARTIFACT_ADAPTER_ID,
                capability=_GRAPH_ARTIFACT_CAPABILITY,
                node_status=graph_status,
                artifact_role=role,
                path_value=path_value,
                output_dir=output_dir,
            )
        )
    return candidates


def _add_role_path(role_paths, seen_roles, role, path_value):
    if not isinstance(path_value, str) or not path_value:
        return False
    if role in seen_roles:
        return False
    seen_roles.add(role)
    role_paths.append((role, path_value))
    return True


def _artifact_record(
    *,
    node_id,
    adapter_id,
    capability,
    node_status,
    artifact_role,
    path_value,
    output_dir,
):
    path = Path(path_value)
    exists = path.exists() and path.is_file() and not path.is_symlink()
    return {
        "node_id": node_id,
        "adapter_id": adapter_id,
        "capability": capability,
        "node_status": node_status,
        "artifact_role": artifact_role,
        "artifact_type": _artifact_type(artifact_role, path),
        "path": path.as_posix(),
        "relative_path": _relative_path(path, output_dir),
        "sha256": sha256_file(path) if exists else None,
        "size_bytes": path.stat().st_size if exists else None,
        "exists": exists,
        "content_indexed": False,
        "raw_content_copied": False,
        "producer": "task_graph_node_output",
        "required_human_approval": True,
    }


def _assign_artifact_ids(artifact_candidates):
    groups = {}
    for artifact in artifact_candidates:
        base_id = _base_artifact_id(artifact)
        groups.setdefault(base_id, []).append(artifact)

    artifacts = []
    for artifact in artifact_candidates:
        base_id = _base_artifact_id(artifact)
        if len(groups[base_id]) == 1:
            artifact_id = base_id
        else:
            suffix = sha256_canonical_json(
                {
                    "artifact_role": artifact["artifact_role"],
                    "path": artifact["path"],
                }
            )[:12]
            artifact_id = base_id + "::" + suffix
        artifact_with_id = {"artifact_id": artifact_id}
        artifact_with_id.update(artifact)
        artifacts.append(artifact_with_id)
    return artifacts


def _base_artifact_id(artifact):
    return "artifact::" + artifact["node_id"] + "::" + artifact["artifact_role"]


def _artifact_type(role, path):
    if role in _ROLE_ARTIFACT_TYPES:
        return _ROLE_ARTIFACT_TYPES[role]
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix in (".md", ".markdown"):
        return "markdown"
    return suffix[1:] if suffix else "file"


def _relative_path(path, output_dir):
    try:
        return (
            Path(path)
            .resolve(strict=False)
            .relative_to(Path(output_dir).resolve(strict=False))
            .as_posix()
        )
    except (OSError, ValueError):
        return None


def _failed_node_artifact_ref(artifact):
    return {
        "artifact_id": artifact["artifact_id"],
        "node_id": artifact["node_id"],
        "artifact_role": artifact["artifact_role"],
        "path": artifact["path"],
        "sha256": artifact["sha256"],
        "size_bytes": artifact["size_bytes"],
        "exists": artifact["exists"],
    }


def _skipped_node_refs(ordered_nodes):
    return [
        {
            "node_id": node["node_id"],
            "blocked_dependencies": list(node.get("blocked_dependencies", [])),
            "status": node["status"],
        }
        for node in ordered_nodes
        if node.get("status") == "skipped"
    ]
