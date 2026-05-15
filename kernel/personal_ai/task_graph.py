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
    failure_bundle_path = output_path / _FAILURE_BUNDLE_FILE
    _require_no_overwrite(execution_manifest_path)
    _require_no_overwrite(replay_manifest_path)
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
            failure_bundle_path=failure_bundle_path,
            success=False,
            node_order=(),
            required_human_approval=True,
        )

    graph_hash = sha256_file(graph_file)
    execution_manifest = {
        "manifest_type": "personal_ai_execution_os_unified_task_graph_execution_v1",
        "authority": "non_authority",
        "execution_capability": "local_task_graph_fixture_only",
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
        "replay_requires_same_graph_sha256": True,
        "required_human_approval": True,
    }
    write_json_atomically(execution_manifest_path, execution_manifest)
    write_json_atomically(replay_manifest_path, replay_manifest)
    return TaskGraphResult(
        graph_path=graph_file,
        output_dir=output_path,
        execution_manifest_path=execution_manifest_path,
        replay_manifest_path=replay_manifest_path,
        failure_bundle_path=None,
        success=True,
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
    for node_id in _topological_order(nodes_by_id):
        node = nodes_by_id[node_id]
        delivery_result = (
            None
            if graph_execution_mode == "dry_run_plan"
            else _run_delivery_node_if_requested(node)
        )
        executed.append(
            {
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
                "delivery_validation": delivery_result,
                "status": "planned"
                if graph_execution_mode == "dry_run_plan"
                else "completed",
                "required_human_approval": True,
            }
        )
    return executed


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


def _write_failure_bundle(graph_file, failure_path, error):
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
    write_json_atomically(failure_path, payload)
