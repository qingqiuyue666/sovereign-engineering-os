"""Unified local task graph fixture for Personal AI Execution OS."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.adapters.adapter_contract import AdapterCapabilityRequest
from kernel.personal_ai.adapters.adapter_registry import (
    admit_adapter_capability,
    find_adapter_entry,
)
from kernel.personal_ai.hash_utils import sha256_canonical_json, sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_delivery_package import validate_runtime_delivery_package
from kernel.personal_ai.task_graph_artifact_outputs import (
    TASK_GRAPH_ARTIFACT_OUTPUTS_FILE,
    build_task_graph_artifact_outputs_manifest,
    task_graph_artifact_outputs_projection_sha256,
    write_task_graph_artifact_outputs_manifest,
)

__all__ = [
    "TaskGraphResult",
    "run_local_task_graph_fixture",
]

_EXECUTION_MANIFEST_FILE = "task_graph_execution_manifest.json"
_REPLAY_MANIFEST_FILE = "task_graph_replay_manifest.json"
_FAILURE_BUNDLE_FILE = "task_graph_failure_bundle.json"
_GRAPH_TYPE = "personal_ai_execution_os_unified_task_graph_v1"
_DELIVERY_ADAPTER_ID = "runtime_delivery_package"
_DELIVERY_CAPABILITY = "validate_runtime_delivery"
_LOCAL_ASSET_ADAPTER_ID = "local_asset_runtime"
_LOCAL_ASSET_CAPABILITY = "launch_local_asset_scan"
_LOCAL_ASSET_SMOKE_READINESS_CAPABILITY = "launch_local_asset_smoke_readiness"
_RUNTIME_ADMISSION_DECISION_TYPE = "personal_ai_runtime_admission_decision_v1"
_GRAPH_EXECUTION_MODES = ("fixture_execution", "dry_run_plan")
_NODE_EXECUTION_MODES = ("fixture", "mock", "dry_run", "real_runtime")
_REAL_RUNTIME_CLASSES = (
    "live_model_provider",
    "external_browser",
    "comfyui_endpoint",
    "blender_runtime",
    "creative_external_tool",
    "unrestricted_network",
    "unrestricted_subprocess",
)
_HUMAN_ACTIVATION_SOURCES = ("human_approval_artifact", "human_review")


@dataclass(frozen=True)
class TaskGraphResult:
    graph_path: Path
    output_dir: Path
    execution_manifest_path: Path | None
    replay_manifest_path: Path | None
    artifact_outputs_manifest_path: Path | None
    failure_bundle_path: Path | None
    success: bool
    node_order: tuple[str, ...]
    required_human_approval: bool


def run_local_task_graph_fixture(
    graph_path: Path,
    output_dir: Path,
) -> TaskGraphResult:
    graph_file = Path(graph_path)
    output_path = Path(output_dir)
    _validate_output_dir(output_path)
    execution_manifest_path = output_path / _EXECUTION_MANIFEST_FILE
    replay_manifest_path = output_path / _REPLAY_MANIFEST_FILE
    artifact_outputs_manifest_path = output_path / TASK_GRAPH_ARTIFACT_OUTPUTS_FILE
    failure_bundle_path = output_path / _FAILURE_BUNDLE_FILE
    _require_no_overwrite(execution_manifest_path)
    _require_no_overwrite(replay_manifest_path)
    _require_no_overwrite(artifact_outputs_manifest_path)
    _require_no_overwrite(failure_bundle_path)

    try:
        graph = _read_graph(graph_file)
        node_records, node_order = _validate_graph(graph)
        graph_execution_mode = graph.get("execution_mode", "fixture_execution")
        executed_nodes = _execute_graph_nodes(node_records, graph_execution_mode)
    except ValueError as error:
        _write_failure_bundle(graph_file, failure_bundle_path, error)
        return TaskGraphResult(
            graph_path=graph_file,
            output_dir=output_path,
            execution_manifest_path=None,
            replay_manifest_path=None,
            artifact_outputs_manifest_path=None,
            failure_bundle_path=failure_bundle_path,
            success=False,
            node_order=(),
            required_human_approval=True,
        )

    graph_hash = sha256_file(graph_file)
    graph_success = _graph_execution_succeeded(executed_nodes)
    planned_artifact_outputs = build_task_graph_artifact_outputs_manifest(
        graph_id=graph["graph_id"],
        graph_path=graph_file,
        graph_sha256=graph_hash,
        graph_execution_mode=graph_execution_mode,
        graph_success=graph_success,
        node_order=node_order,
        executed_nodes=executed_nodes,
        output_dir=output_path,
        execution_manifest_path=execution_manifest_path,
        replay_manifest_path=replay_manifest_path,
        failure_bundle_path=failure_bundle_path if not graph_success else None,
    )
    execution_manifest = {
        "manifest_type": "personal_ai_execution_os_unified_task_graph_execution_v1",
        "authority": "non_authority",
        "execution_capability": "local_task_graph_fixture_only",
        "success": graph_success,
        "status": "completed" if graph_success else "failed",
        "graph_path": graph_file.as_posix(),
        "graph_sha256": graph_hash,
        "graph_id": graph["graph_id"],
        "graph_execution_mode": graph_execution_mode,
        "dry_run_planning_mode": graph_execution_mode == "dry_run_plan",
        "fixture_mock_execution_mode": graph_execution_mode == "fixture_execution",
        "node_order": list(node_order),
        "nodes": executed_nodes,
        "approval_checkpoints": [
            {
                "node_id": node["node_id"],
                "checkpoint_id": node["approval_checkpoint_id"],
                "required_human_approval": True,
            }
            for node in executed_nodes
        ],
        "failure_quarantine_required": True,
        "delivery_package_integration": any(
            node["adapter_id"] == _DELIVERY_ADAPTER_ID for node in executed_nodes
        ),
        "runtime_admission_decisions": [
            node["runtime_admission_decision"]
            for node in executed_nodes
            if node["runtime_admission_decision"]["decision_path"] is not None
        ],
        "task_graph_artifact_outputs_path": (
            artifact_outputs_manifest_path.as_posix()
        ),
        "task_graph_artifact_outputs_written": True,
        "task_graph_artifact_count": planned_artifact_outputs["artifact_count"],
        "runtime_activation_performed": False,
        "real_runtime_activation_allowed": False,
        "task_graph_can_activate_real_runtime_without_admission": False,
        "input_mutation_performed": False,
        "overwrite_performed": False,
        "network_runtime_allowed": False,
        "subprocess_runtime_allowed": False,
        "browser_runtime_allowed": False,
        "model_api_runtime_allowed": False,
        "creative_runtime_allowed": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(execution_manifest_path, execution_manifest)
    if not graph_success:
        _write_failure_bundle(
            graph_file,
            failure_bundle_path,
            ValueError(_graph_execution_failure_message(executed_nodes)),
            node_order=node_order,
            executed_nodes=executed_nodes,
        )
    pre_replay_artifact_outputs = build_task_graph_artifact_outputs_manifest(
        graph_id=graph["graph_id"],
        graph_path=graph_file,
        graph_sha256=graph_hash,
        graph_execution_mode=graph_execution_mode,
        graph_success=graph_success,
        node_order=node_order,
        executed_nodes=executed_nodes,
        output_dir=output_path,
        execution_manifest_path=execution_manifest_path,
        replay_manifest_path=replay_manifest_path,
        failure_bundle_path=failure_bundle_path if not graph_success else None,
    )
    artifact_outputs_projection_sha256 = (
        task_graph_artifact_outputs_projection_sha256(pre_replay_artifact_outputs)
    )
    replay_manifest = {
        "manifest_type": "personal_ai_execution_os_unified_task_graph_replay_v1",
        "authority": "non_authority",
        "execution_capability": "local_task_graph_fixture_only",
        "graph_sha256": graph_hash,
        "graph_execution_mode": graph_execution_mode,
        "node_order_sha256": sha256_canonical_json(list(node_order)),
        "node_route_sha256": sha256_canonical_json(
            [
                {
                    "adapter_id": node["adapter_id"],
                    "capability": node["capability"],
                    "node_id": node["node_id"],
                }
                for node in executed_nodes
            ]
        ),
        "execution_manifest_sha256": sha256_canonical_json(execution_manifest),
        "runtime_admission_decisions_sha256": sha256_canonical_json(
            execution_manifest["runtime_admission_decisions"]
        ),
        "node_output_refs_sha256": sha256_canonical_json(
            _node_output_refs(executed_nodes)
        ),
        "local_asset_scan_receipts_sha256": sha256_canonical_json(
            _local_asset_scan_receipt_refs(executed_nodes)
        ),
        "local_asset_scan_failure_refs_sha256": sha256_canonical_json(
            _local_asset_scan_failure_refs(executed_nodes)
        ),
        "task_graph_artifact_outputs_path": (
            artifact_outputs_manifest_path.as_posix()
        ),
        "task_graph_artifact_outputs_sha256": artifact_outputs_projection_sha256,
        "task_graph_artifact_outputs_sha256_scope": (
            "canonical_manifest_projection_excluding_task_graph_replay_manifest_"
            "file_hash"
        ),
        "task_graph_artifact_outputs_manifest_bound": True,
        "task_graph_artifact_outputs_binding_strategy": (
            "artifact_outputs_hashes_replay_manifest_file; replay_manifest_hashes_"
            "artifact_outputs_projection_without_replay_file_hash"
        ),
        "replay_requires_same_graph_sha256": True,
        "required_human_approval": True,
    }
    write_json_atomically(replay_manifest_path, replay_manifest)
    artifact_outputs = build_task_graph_artifact_outputs_manifest(
        graph_id=graph["graph_id"],
        graph_path=graph_file,
        graph_sha256=graph_hash,
        graph_execution_mode=graph_execution_mode,
        graph_success=graph_success,
        node_order=node_order,
        executed_nodes=executed_nodes,
        output_dir=output_path,
        execution_manifest_path=execution_manifest_path,
        replay_manifest_path=replay_manifest_path,
        failure_bundle_path=failure_bundle_path if not graph_success else None,
    )
    write_task_graph_artifact_outputs_manifest(
        artifact_outputs_manifest_path,
        artifact_outputs,
    )
    return TaskGraphResult(
        graph_path=graph_file,
        output_dir=output_path,
        execution_manifest_path=execution_manifest_path,
        replay_manifest_path=replay_manifest_path,
        artifact_outputs_manifest_path=artifact_outputs_manifest_path,
        failure_bundle_path=None if graph_success else failure_bundle_path,
        success=graph_success,
        node_order=node_order,
        required_human_approval=True,
    )


def _validate_output_dir(output_path):
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")


def _require_no_overwrite(path):
    if Path(path).exists():
        raise ValueError("task graph output already exists")


def _read_graph(graph_file):
    if not graph_file.exists() or not graph_file.is_file():
        raise ValueError("graph_path is missing")
    if graph_file.is_symlink():
        raise ValueError("graph_path must not be a symlink")
    try:
        graph = json.loads(graph_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("task graph JSON is malformed") from error
    if not isinstance(graph, dict):
        raise ValueError("task graph must be an object")
    if graph.get("graph_type") != _GRAPH_TYPE:
        raise ValueError("task graph type mismatch")
    if not isinstance(graph.get("graph_id"), str) or not graph["graph_id"]:
        raise ValueError("task graph graph_id is missing")
    execution_mode = graph.get("execution_mode", "fixture_execution")
    if execution_mode not in _GRAPH_EXECUTION_MODES:
        raise ValueError("task graph execution_mode is invalid")
    if graph.get("authority") != "non_authority":
        raise ValueError("task graph authority mismatch")
    if graph.get("required_human_approval") is not True:
        raise ValueError("task graph must require human approval")
    if not isinstance(graph.get("nodes"), list) or not graph["nodes"]:
        raise ValueError("task graph nodes are malformed")
    return graph


def _validate_graph(graph):
    nodes_by_id = {}
    for index, node in enumerate(graph["nodes"]):
        record = _validate_node_shape(node, index)
        if record["node_id"] in nodes_by_id:
            raise ValueError("task graph duplicate node_id")
        nodes_by_id[record["node_id"]] = record
    _validate_dependencies_exist(nodes_by_id)
    node_order = _topological_order(nodes_by_id)
    ordered_nodes = [nodes_by_id[node_id] for node_id in node_order]
    _attach_runtime_admission_decisions(ordered_nodes)
    _validate_adapter_routes(ordered_nodes, graph.get("execution_mode", "fixture_execution"))
    return nodes_by_id, node_order


def _validate_node_shape(node, index):
    if not isinstance(node, dict):
        raise ValueError("task graph node is malformed")
    for field_name in ("node_id", "adapter_id", "capability"):
        if not isinstance(node.get(field_name), str) or not node[field_name]:
            raise ValueError("task graph node " + field_name + " is missing")
    depends_on = node.get("depends_on", [])
    if not isinstance(depends_on, list) or not all(
        isinstance(item, str) and item for item in depends_on
    ):
        raise ValueError("task graph node dependencies are malformed")
    inputs = node.get("inputs", {})
    if not isinstance(inputs, dict):
        raise ValueError("task graph node inputs are malformed")
    execution_mode = node.get("execution_mode", "fixture")
    if execution_mode not in _NODE_EXECUTION_MODES:
        raise ValueError("task graph node execution_mode is invalid")
    runtime_class = node.get("runtime_class")
    if runtime_class is not None and (
        not isinstance(runtime_class, str) or not runtime_class
    ):
        raise ValueError("task graph node runtime_class is malformed")
    admission_decision_path = node.get("runtime_admission_decision_path")
    if admission_decision_path is not None and (
        not isinstance(admission_decision_path, str) or not admission_decision_path
    ):
        raise ValueError("task graph node runtime admission decision path is malformed")
    if node.get("approval_checkpoint_required") is not True:
        raise ValueError("task graph node must require approval checkpoint")
    return {
        "index": index,
        "node_id": node["node_id"],
        "adapter_id": node["adapter_id"],
        "capability": node["capability"],
        "depends_on": tuple(depends_on),
        "inputs": dict(inputs),
        "execution_mode": execution_mode,
        "runtime_class": runtime_class,
        "runtime_admission_decision_path": admission_decision_path,
        "runtime_admission_decision": None,
        "approval_checkpoint_id": node.get(
            "approval_checkpoint_id",
            node["node_id"] + ":human_review",
        ),
    }


def _validate_dependencies_exist(nodes_by_id):
    for node in nodes_by_id.values():
        for dependency in node["depends_on"]:
            if dependency not in nodes_by_id:
                raise ValueError("task graph dependency is not registered")


def _topological_order(nodes_by_id):
    permanent = set()
    temporary = set()
    order = []

    def visit(node_id):
        if node_id in permanent:
            return
        if node_id in temporary:
            raise ValueError("task graph dependency cycle detected")
        temporary.add(node_id)
        for dependency in sorted(nodes_by_id[node_id]["depends_on"]):
            visit(dependency)
        temporary.remove(node_id)
        permanent.add(node_id)
        order.append(node_id)

    for node_id in sorted(nodes_by_id):
        visit(node_id)
    return tuple(order)


def _attach_runtime_admission_decisions(node_records):
    for node in node_records:
        node["runtime_admission_decision"] = _runtime_admission_decision_summary(node)


def _runtime_admission_decision_summary(node):
    decision_path_value = node["runtime_admission_decision_path"]
    if decision_path_value is None:
        if node["execution_mode"] == "real_runtime":
            raise ValueError("task graph runtime admission decision is required")
        if node["runtime_class"] in _REAL_RUNTIME_CLASSES:
            raise ValueError("task graph runtime admission decision is required")
        return {
            "required": False,
            "decision_path": None,
            "decision_sha256": None,
            "admitted": False,
            "activation_allowed": False,
            "dry_run": node["execution_mode"] == "dry_run",
            "runtime_class": node["runtime_class"],
            "manifest_hash_bound": False,
            "reason_codes": [],
            "activation_sources": [],
        }

    decision_path = Path(decision_path_value)
    decision = _read_runtime_admission_decision(decision_path)
    _validate_runtime_admission_decision(node, decision)
    return {
        "required": True,
        "decision_path": decision_path.as_posix(),
        "decision_sha256": sha256_file(decision_path),
        "admitted": decision["admitted"],
        "activation_allowed": decision["activation_allowed"],
        "dry_run": decision["dry_run"],
        "runtime_class": decision["runtime_class"],
        "manifest_hash_bound": decision["manifest_hash_bound"],
        "reason_codes": list(decision.get("reason_codes", [])),
        "activation_sources": list(decision.get("activation_sources", [])),
    }


def _read_runtime_admission_decision(decision_path):
    if not decision_path.exists() or not decision_path.is_file():
        raise ValueError("task graph runtime admission decision is missing")
    if decision_path.is_symlink():
        raise ValueError("task graph runtime admission decision must not be a symlink")
    try:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("task graph runtime admission decision is malformed") from error
    if not isinstance(decision, dict):
        raise ValueError("task graph runtime admission decision is malformed")
    return decision


def _validate_runtime_admission_decision(node, decision):
    if decision.get("decision_type") != _RUNTIME_ADMISSION_DECISION_TYPE:
        raise ValueError("task graph runtime admission decision type mismatch")
    if decision.get("adapter_id") != node["adapter_id"]:
        raise ValueError("task graph runtime admission adapter mismatch")
    if decision.get("capability") != node["capability"]:
        raise ValueError("task graph runtime admission capability mismatch")
    if node["runtime_class"] and decision.get("runtime_class") != node["runtime_class"]:
        raise ValueError("task graph runtime admission runtime_class mismatch")
    if decision.get("required_human_approval") is not True:
        raise ValueError("task graph runtime admission must require human approval")
    if decision.get("manifest_hash_bound") is not True:
        raise ValueError("task graph runtime admission manifest hash binding failed")
    if decision.get("admitted") is not True:
        raise ValueError("task graph runtime admission decision is denied")
    activation_sources = decision.get("activation_sources", [])
    if not isinstance(activation_sources, list) or not any(
        source in _HUMAN_ACTIVATION_SOURCES for source in activation_sources
    ):
        raise ValueError("task graph runtime admission lacks human approval source")
    if decision.get("dry_run") is not True and node["execution_mode"] == "dry_run":
        raise ValueError("task graph runtime admission dry_run mismatch")
    if node["execution_mode"] == "real_runtime" and decision.get(
        "activation_allowed"
    ) is not True:
        raise ValueError("task graph real runtime activation is not admitted")
    if (
        node["execution_mode"] != "real_runtime"
        and decision.get("runtime_class") in _REAL_RUNTIME_CLASSES
        and decision.get("activation_allowed") is True
    ):
        raise ValueError("task graph dry-run plan must not activate real runtime")


def _validate_adapter_routes(node_records, graph_execution_mode):
    for node in node_records:
        if (
            node["adapter_id"] == _DELIVERY_ADAPTER_ID
            and node["capability"] == _DELIVERY_CAPABILITY
        ):
            continue
        try:
            entry = find_adapter_entry(node["adapter_id"])
        except ValueError as error:
            raise ValueError("task graph adapter route is not registered") from error
        decision = admit_adapter_capability(
            AdapterCapabilityRequest(
                adapter_id=entry.adapter_id,
                capability=node["capability"],
                mode=entry.mode,
                risk_class=entry.risk_class,
            )
        )
        if not decision.admitted and not _route_is_safe_dry_run_plan(
            node,
            decision.reason_codes,
            graph_execution_mode,
        ):
            raise ValueError(
                "task graph adapter route is not admitted: "
                + ",".join(decision.reason_codes)
            )


def _route_is_safe_dry_run_plan(node, reason_codes, graph_execution_mode):
    return (
        graph_execution_mode == "dry_run_plan"
        and node["execution_mode"] == "dry_run"
        and node["runtime_admission_decision"]["admitted"] is True
        and tuple(reason_codes) == ("adapter_not_admitted",)
    )


def _execute_graph_nodes(nodes_by_id, graph_execution_mode):
    executed = []
    status_by_node_id = {}
    for node_id in _topological_order(nodes_by_id):
        node = nodes_by_id[node_id]
        record = _base_node_execution_record(node, graph_execution_mode)
        blocked_dependencies = [
            dependency
            for dependency in sorted(node["depends_on"])
            if status_by_node_id.get(dependency) in ("failed", "skipped")
        ]
        if blocked_dependencies:
            record.update(_skipped_node_result(blocked_dependencies))
        elif graph_execution_mode == "dry_run_plan":
            record["status"] = "planned"
        else:
            local_asset_result = _run_local_asset_node_if_requested(node)
            if local_asset_result is not None:
                record.update(local_asset_result)
            else:
                record["delivery_validation"] = _run_delivery_node_if_requested(node)
                record["status"] = "completed"
        status_by_node_id[node_id] = record["status"]
        executed.append(record)
    return executed


def _base_node_execution_record(node, graph_execution_mode):
    return {
        "node_id": node["node_id"],
        "adapter_id": node["adapter_id"],
        "capability": node["capability"],
        "depends_on": list(node["depends_on"]),
        "execution_mode": node["execution_mode"],
        "runtime_class": node["runtime_class"],
        "approval_checkpoint_required": True,
        "approval_checkpoint_id": node["approval_checkpoint_id"],
        "adapter_route_admitted": True,
        "adapter_route_policy": "local_delivery_integration"
        if node["adapter_id"] == _DELIVERY_ADAPTER_ID
        else _adapter_route_policy(node, graph_execution_mode),
        "runtime_admission_decision": node["runtime_admission_decision"],
        "runtime_activation_performed": False,
        "delivery_validation": None,
        "status": "planned"
        if graph_execution_mode == "dry_run_plan"
        else "completed",
        "required_human_approval": True,
    }


def _skipped_node_result(blocked_dependencies):
    return {
        "status": "skipped",
        "skipped_due_to_failed_dependencies": True,
        "blocked_dependencies": list(blocked_dependencies),
        "failure_stage": "dependency_failed",
        "safe_to_retry": False,
        "replay_hint": (
            "Review and rerun the failed dependency before executing this node."
        ),
        "required_human_approval": True,
    }


def _adapter_route_policy(node, graph_execution_mode):
    if (
        graph_execution_mode == "dry_run_plan"
        and node["runtime_admission_decision"]["decision_path"] is not None
    ):
        return "runtime_admission_dry_run_plan"
    return "registry_admitted"


def _run_delivery_node_if_requested(node):
    if node["adapter_id"] != _DELIVERY_ADAPTER_ID:
        return None
    if node["capability"] != _DELIVERY_CAPABILITY:
        raise ValueError("task graph delivery capability is not registered")
    inputs = node["inputs"]
    package_dir = inputs.get("package_dir")
    output_path = inputs.get("output_path")
    if not isinstance(package_dir, str) or not package_dir:
        raise ValueError("task graph delivery package_dir is missing")
    if not isinstance(output_path, str) or not output_path:
        raise ValueError("task graph delivery output_path is missing")
    raw_sentinels = inputs.get("raw_sentinel_values", [])
    if not isinstance(raw_sentinels, list) or not all(
        isinstance(value, str) for value in raw_sentinels
    ):
        raise ValueError("task graph delivery raw_sentinel_values malformed")
    result = validate_runtime_delivery_package(
        Path(package_dir),
        Path(output_path),
        raw_sentinel_values=raw_sentinels,
    )
    return {
        "complete": result.complete,
        "runtime_delivery_manifest_path": (
            result.runtime_delivery_manifest_path.as_posix()
        ),
        "runtime_delivery_validation_path": (
            result.runtime_delivery_validation_path.as_posix()
        ),
        "packaged_artifacts": list(result.packaged_artifacts),
        "raw_value_leakage_detected": result.raw_value_leakage_detected,
    }


def _run_local_asset_node_if_requested(node):
    if node["adapter_id"] != _LOCAL_ASSET_ADAPTER_ID:
        return None
    if node["capability"] != _LOCAL_ASSET_CAPABILITY:
        if node["capability"] == _LOCAL_ASSET_SMOKE_READINESS_CAPABILITY:
            return _run_local_asset_smoke_readiness_node(node)
        raise ValueError("task graph local asset scan capability is not registered")
    return _run_local_asset_scan_node(node)


def _run_local_asset_scan_node(node):
    inputs = node["inputs"]
    input_dir = _required_string_input(inputs, "input_dir", "local asset scan")
    output_dir = _required_string_input(inputs, "output_dir", "local asset scan")
    recursive = _optional_bool_input(inputs, "recursive", False)
    include_hidden = _optional_bool_input(inputs, "include_hidden", False)
    previous_scan_output_dir = inputs.get("previous_scan_output_dir")
    if previous_scan_output_dir is not None and (
        not isinstance(previous_scan_output_dir, str) or not previous_scan_output_dir
    ):
        raise ValueError(
            "task graph local asset scan previous_scan_output_dir is malformed"
        )
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError("task graph local asset scan project_id is malformed")

    from kernel.personal_ai.local_launcher import run_local_asset_scan_launcher

    result = run_local_asset_scan_launcher(
        Path(input_dir),
        Path(output_dir),
        recursive=recursive,
        include_hidden=include_hidden,
        project_id=project_id,
        previous_scan_output_dir=None
        if previous_scan_output_dir is None
        else Path(previous_scan_output_dir),
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "previous_scan_output_dir": payload.get("previous_scan_output_dir"),
        "local_asset_scan_complete": complete,
        "launcher_summary_path": result.summary_path.as_posix() if complete else None,
        "asset_scan_run_receipt_path": payload.get("asset_scan_run_receipt_path"),
        "asset_scan_failure_bundle_path": payload.get("failure_bundle_path"),
        "asset_scan_failure_summary_path": payload.get("failure_summary_path"),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "local_asset_sqlite_index_path": payload.get(
            "local_asset_sqlite_index_path"
        ),
        "local_asset_sqlite_index_manifest_path": payload.get(
            "local_asset_sqlite_index_manifest_path"
        ),
        "local_asset_sqlite_query_summary_path": payload.get(
            "local_asset_sqlite_query_summary_path"
        ),
        "local_asset_incremental_scan_plan_path": payload.get(
            "local_asset_incremental_scan_plan_path"
        ),
        "local_asset_incremental_scan_manifest_path": payload.get(
            "local_asset_incremental_scan_manifest_path"
        ),
        "local_asset_incremental_scan_summary_path": payload.get(
            "local_asset_incremental_scan_summary_path"
        ),
        "local_asset_incremental_plan_mode": payload.get(
            "local_asset_incremental_plan_mode"
        ),
        "incremental_cache_execution_performed": False,
        "incremental_automatic_skip_performed": False,
        "asset_manifest_path": payload.get("asset_manifest_path"),
        "asset_index_path": payload.get("asset_index_path"),
        "duplicates_report_path": payload.get("duplicates_report_path"),
        "media_inventory_path": payload.get("media_inventory_path"),
        "asset_runtime_audit_log_path": payload.get("asset_runtime_audit_log_path"),
        "asset_runtime_validation_report_path": (
            payload.get("asset_runtime_validation_report_path")
        ),
        "asset_runtime_quarantine_manifest_path": (
            payload.get("asset_runtime_quarantine_manifest_path")
        ),
        "asset_runtime_output_paths": payload.get("asset_runtime_output_paths"),
        "indexed_artifacts": payload.get("indexed_artifacts"),
        "quarantined_paths": payload.get("quarantined_paths"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "safe_to_retry": payload.get("safe_to_retry"),
        "replay_hint": payload.get("replay_hint"),
        "recommended_next_action": payload.get("recommended_next_action"),
        "required_human_approval": True,
        "input_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "desktop_ui_added": False,
        "browser_runtime_invoked": False,
        "comfyui_runtime_invoked": False,
        "blender_runtime_invoked": False,
        "houdini_runtime_invoked": False,
        "after_effects_runtime_invoked": False,
        "davinci_runtime_invoked": False,
        "external_runtime_invoked": False,
    }


def _run_local_asset_smoke_readiness_node(node):
    inputs = node["inputs"]
    candidate_input_dir = _required_string_input(
        inputs,
        "candidate_input_dir",
        "local asset smoke readiness",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local asset smoke readiness",
    )
    recursive = _optional_bool_input(inputs, "recursive", False)
    include_hidden = _optional_bool_input(inputs, "include_hidden", False)
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError(
            "task graph local asset smoke readiness project_id is malformed"
        )
    max_entries = _optional_int_input(
        inputs,
        "max_entries",
        50000,
        "local asset smoke readiness",
    )
    max_depth = _optional_int_input(
        inputs,
        "max_depth",
        20,
        "local asset smoke readiness",
    )
    max_total_bytes = _optional_int_input(
        inputs,
        "max_total_bytes",
        500000000000,
        "local asset smoke readiness",
    )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_smoke_readiness_launcher,
    )

    result = run_local_asset_smoke_readiness_launcher(
        Path(candidate_input_dir),
        Path(output_dir),
        recursive=recursive,
        include_hidden=include_hidden,
        project_id=project_id,
        max_entries=max_entries,
        max_depth=max_depth,
        max_total_bytes=max_total_bytes,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "local_asset_smoke_readiness_complete": complete,
        "launcher_summary_path": result.summary_path.as_posix() if complete else None,
        "local_asset_smoke_readiness_report_path": payload.get(
            "local_asset_smoke_readiness_report_path"
        ),
        "local_asset_smoke_readiness_manifest_path": payload.get(
            "local_asset_smoke_readiness_manifest_path"
        ),
        "local_asset_smoke_readiness_summary_path": payload.get(
            "local_asset_smoke_readiness_summary_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "readiness_status": payload.get("readiness_status"),
        "readiness_decision": payload.get("readiness_decision"),
        "candidate_input_dir": payload.get("candidate_input_dir"),
        "project_id": payload.get("project_id"),
        "recursive": payload.get("recursive"),
        "include_hidden": payload.get("include_hidden"),
        "max_entries": payload.get("max_entries"),
        "max_depth": payload.get("max_depth"),
        "max_total_bytes": payload.get("max_total_bytes"),
        "inspected_entry_count": payload.get("inspected_entry_count"),
        "inspected_file_count": payload.get("inspected_file_count"),
        "inspected_directory_count": payload.get("inspected_directory_count"),
        "estimated_total_size_bytes": payload.get("estimated_total_size_bytes"),
        "secret_looking_path_count": payload.get("secret_looking_path_count"),
        "symlink_count": payload.get("symlink_count"),
        "unsafe_directory_count": payload.get("unsafe_directory_count"),
        "hidden_path_count": payload.get("hidden_path_count"),
        "unreadable_entry_count": payload.get("unreadable_entry_count"),
        "limit_exceeded": payload.get("limit_exceeded"),
        "indexed_artifacts": payload.get("indexed_artifacts"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "safe_to_retry": payload.get("safe_to_retry"),
        "replay_hint": payload.get("replay_hint"),
        "required_human_approval": True,
        "real_scan_performed": False,
        "file_hashing_performed": False,
        "raw_content_read": False,
        "raw_content_copied": False,
        "thumbnail_generation_performed": False,
        "preview_generation_performed": False,
        "input_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
    }


def _required_string_input(inputs, field_name, node_label):
    value = inputs.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError("task graph " + node_label + " " + field_name + " is missing")
    return value


def _optional_bool_input(inputs, field_name, default):
    value = inputs.get(field_name, default)
    if not isinstance(value, bool):
        raise ValueError("task graph local asset scan " + field_name + " is malformed")
    return value


def _optional_int_input(inputs, field_name, default, node_label):
    value = inputs.get(field_name, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(
            "task graph " + node_label + " " + field_name + " is malformed"
        )
    return value


def _graph_execution_succeeded(executed_nodes):
    return all(node["status"] in ("completed", "planned") for node in executed_nodes)


def _graph_execution_failure_message(executed_nodes):
    failed_nodes = [node for node in executed_nodes if node["status"] == "failed"]
    if failed_nodes:
        failed = failed_nodes[0]
        return "task graph node failed: " + failed["node_id"]
    skipped_nodes = [node for node in executed_nodes if node["status"] == "skipped"]
    if skipped_nodes:
        skipped = skipped_nodes[0]
        return "task graph node skipped after dependency failure: " + skipped["node_id"]
    return "task graph execution failed"


def _node_output_refs(executed_nodes):
    refs = []
    for node in executed_nodes:
        node_refs = {
            "node_id": node["node_id"],
            "adapter_id": node["adapter_id"],
            "capability": node["capability"],
            "status": node["status"],
        }
        if node.get("delivery_validation") is not None:
            node_refs["delivery_validation"] = {
                key: _path_ref(value) if key.endswith("_path") else value
                for key, value in sorted(node["delivery_validation"].items())
            }
        if (
            node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
            and node["capability"] == _LOCAL_ASSET_CAPABILITY
        ):
            node_refs["local_asset_scan"] = {
                "output_dir": node.get("output_dir"),
                "previous_scan_output_dir": node.get("previous_scan_output_dir"),
                "asset_scan_run_receipt": _path_ref(
                    node.get("asset_scan_run_receipt_path")
                ),
                "asset_scan_failure_bundle": _path_ref(
                    node.get("asset_scan_failure_bundle_path")
                ),
                "asset_scan_failure_summary": _path_ref(
                    node.get("asset_scan_failure_summary_path")
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "local_asset_sqlite_index": _path_ref(
                    node.get("local_asset_sqlite_index_path")
                ),
                "local_asset_sqlite_index_manifest": _path_ref(
                    node.get("local_asset_sqlite_index_manifest_path")
                ),
                "local_asset_sqlite_query_summary": _path_ref(
                    node.get("local_asset_sqlite_query_summary_path")
                ),
                "local_asset_incremental_scan_plan": _path_ref(
                    node.get("local_asset_incremental_scan_plan_path")
                ),
                "local_asset_incremental_scan_manifest": _path_ref(
                    node.get("local_asset_incremental_scan_manifest_path")
                ),
                "local_asset_incremental_scan_summary": _path_ref(
                    node.get("local_asset_incremental_scan_summary_path")
                ),
                "asset_manifest": _path_ref(node.get("asset_manifest_path")),
                "asset_index": _path_ref(node.get("asset_index_path")),
                "duplicates_report": _path_ref(node.get("duplicates_report_path")),
                "media_inventory": _path_ref(node.get("media_inventory_path")),
                "asset_runtime_audit_log": _path_ref(
                    node.get("asset_runtime_audit_log_path")
                ),
                "asset_runtime_validation_report": _path_ref(
                    node.get("asset_runtime_validation_report_path")
                ),
                "asset_runtime_quarantine_manifest": _path_ref(
                    node.get("asset_runtime_quarantine_manifest_path")
                ),
                "launcher_summary": _path_ref(node.get("launcher_summary_path")),
                "asset_runtime_outputs": _path_refs_by_name(
                    node.get("asset_runtime_output_paths")
                ),
                "indexed_artifacts": node.get("indexed_artifacts"),
                "quarantined_paths": node.get("quarantined_paths"),
                "local_asset_incremental_plan_mode": node.get(
                    "local_asset_incremental_plan_mode"
                ),
                "incremental_cache_execution_performed": node.get(
                    "incremental_cache_execution_performed"
                ),
                "incremental_automatic_skip_performed": node.get(
                    "incremental_automatic_skip_performed"
                ),
                "failure_stage": node.get("failure_stage"),
            }
        if (
            node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
            and node["capability"] == _LOCAL_ASSET_SMOKE_READINESS_CAPABILITY
        ):
            node_refs["local_asset_smoke_readiness"] = {
                "output_dir": node.get("output_dir"),
                "candidate_input_dir": node.get("candidate_input_dir"),
                "report": _path_ref(
                    node.get("local_asset_smoke_readiness_report_path")
                ),
                "manifest": _path_ref(
                    node.get("local_asset_smoke_readiness_manifest_path")
                ),
                "summary": _path_ref(
                    node.get("local_asset_smoke_readiness_summary_path")
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "readiness_status": node.get("readiness_status"),
                "readiness_decision": node.get("readiness_decision"),
                "real_scan_performed": node.get("real_scan_performed"),
                "file_hashing_performed": node.get("file_hashing_performed"),
                "raw_content_read": node.get("raw_content_read"),
                "required_human_approval": node.get("required_human_approval"),
                "failure_stage": node.get("failure_stage"),
            }
        refs.append(node_refs)
    return refs


def _local_asset_scan_receipt_refs(executed_nodes):
    return [
        {
            "node_id": node["node_id"],
            "asset_scan_run_receipt": _path_ref(
                node.get("asset_scan_run_receipt_path")
            ),
        }
        for node in executed_nodes
        if node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node.get("asset_scan_run_receipt_path") is not None
    ]


def _local_asset_scan_failure_refs(executed_nodes):
    return [
        {
            "node_id": node["node_id"],
            "failure_stage": node.get("failure_stage"),
            "asset_scan_failure_bundle": _path_ref(
                node.get("asset_scan_failure_bundle_path")
            ),
            "asset_scan_failure_summary": _path_ref(
                node.get("asset_scan_failure_summary_path")
            ),
        }
        for node in executed_nodes
        if node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and (
            node.get("asset_scan_failure_bundle_path") is not None
            or node.get("asset_scan_failure_summary_path") is not None
        )
    ]


def _path_refs_by_name(paths_by_name):
    if not isinstance(paths_by_name, dict):
        return {}
    return {
        name: _path_ref(path)
        for name, path in sorted(paths_by_name.items())
        if isinstance(name, str)
    }


def _path_ref(path_value):
    if not isinstance(path_value, str) or not path_value:
        return None
    path = Path(path_value)
    return {
        "path": path.as_posix(),
        "sha256": sha256_file(path)
        if path.exists() and path.is_file() and not path.is_symlink()
        else None,
    }


def _write_failure_bundle(
    graph_file,
    failure_path,
    error,
    *,
    node_order=(),
    executed_nodes=(),
):
    payload = {
        "failure_type": "personal_ai_task_graph_failure_bundle_v1",
        "authority": "non_authority",
        "execution_capability": "local_task_graph_fixture_only",
        "graph_path": graph_file.as_posix(),
        "graph_sha256": sha256_file(graph_file)
        if graph_file.exists() and graph_file.is_file() and not graph_file.is_symlink()
        else None,
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "failure_quarantine_required": True,
        "input_mutation_performed": False,
        "overwrite_performed": False,
        "network_runtime_allowed": False,
        "subprocess_runtime_allowed": False,
        "browser_runtime_allowed": False,
        "model_api_runtime_allowed": False,
        "creative_runtime_allowed": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    if node_order:
        payload["node_order"] = list(node_order)
    failed_nodes = _failure_node_summaries(executed_nodes, "failed")
    skipped_nodes = _failure_node_summaries(executed_nodes, "skipped")
    if failed_nodes:
        payload["failed_node_id"] = failed_nodes[0]["node_id"]
        payload["failure_stage"] = failed_nodes[0].get("failure_stage")
        payload["failed_nodes"] = failed_nodes
    if skipped_nodes:
        payload["skipped_nodes"] = skipped_nodes
    write_json_atomically(failure_path, payload)


def _failure_node_summaries(executed_nodes, status):
    summaries = []
    for node in executed_nodes:
        if node.get("status") != status:
            continue
        summaries.append(
            {
                "node_id": node["node_id"],
                "adapter_id": node["adapter_id"],
                "capability": node["capability"],
                "status": node["status"],
                "failure_stage": node.get("failure_stage"),
                "blocked_dependencies": list(node.get("blocked_dependencies", [])),
                "asset_scan_failure_bundle_path": node.get(
                    "asset_scan_failure_bundle_path"
                ),
                "asset_scan_failure_summary_path": node.get(
                    "asset_scan_failure_summary_path"
                ),
                "safe_to_retry": node.get("safe_to_retry"),
                "replay_hint": node.get("replay_hint"),
                "required_human_approval": True,
            }
        )
    return summaries
