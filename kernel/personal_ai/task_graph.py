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
_LOCAL_ASSET_HUMAN_SMOKE_CAPABILITY = "launch_local_asset_human_smoke_run"
_LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_CAPABILITY = (
    "launch_local_asset_bounded_smoke_iteration"
)
_LOCAL_ASSET_SMOKE_REVIEW_PACKET_CAPABILITY = (
    "launch_local_asset_smoke_review_packet"
)
_LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_CAPABILITY = (
    "launch_local_asset_smoke_iteration_review_packet"
)
_LOCAL_ASSET_SMOKE_PROMOTION_GATE_CAPABILITY = (
    "launch_local_asset_smoke_promotion_gate"
)
_LOCAL_ASSET_ITERATION_PROMOTION_GATE_CAPABILITY = (
    "launch_local_asset_iteration_promotion_gate"
)
_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_CAPABILITY = (
    "launch_local_asset_bounded_smoke_cycle_contract"
)
_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CAPABILITY = (
    "launch_local_asset_bounded_smoke_cycle_human_review"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_admission"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_execution_request"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_runner_admission"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_runner"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_run_review_packet"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_run_promotion_gate"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_FROM_RUN_PROMOTION_GATE_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_HUMAN_REVIEW_FROM_RUN_PROMOTION_GATE_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate"
)
_GITHUB_CAPABILITY_ADAPTER_ID = "github_capability_intake_packet"
_GITHUB_CAPABILITY_INTAKE_PACKET_CAPABILITY = (
    "launch_github_capability_intake_packet"
)
_PLAYWRIGHT_SMOKE_ADAPTER_ID = "playwright_local_fixture_sandbox_smoke"
_PLAYWRIGHT_SMOKE_CAPABILITY = "launch_playwright_local_fixture_sandbox_smoke"
_BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_ID = "bounded_playwright_worker_adapter_draft"
_BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_CAPABILITY = (
    "launch_bounded_playwright_worker_adapter_draft"
)
_OPERATOR_PLAYWRIGHT_RECEIPT_ADAPTER_ID = (
    "operator_provided_playwright_execution_receipt"
)
_OPERATOR_PLAYWRIGHT_RECEIPT_CAPABILITY = (
    "launch_operator_provided_playwright_execution_receipt"
)
_LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_ADAPTER_ID = (
    "local_fixture_playwright_adapter_admission_gate"
)
_LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_CAPABILITY = (
    "launch_local_fixture_playwright_adapter_admission_gate"
)
_LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ADAPTER_ID = (
    "local_only_playwright_fixture_scenario_suite"
)
_LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CAPABILITY = (
    "launch_local_only_playwright_fixture_scenario_suite"
)
_PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ADAPTER_ID = (
    "playwright_local_admission_receipt_aggregation"
)
_PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CAPABILITY = (
    "launch_playwright_local_admission_receipt_aggregation"
)
_ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ADAPTER_ID = (
    "admission_gated_local_adapter_registry_promotion"
)
_ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CAPABILITY = (
    "launch_admission_gated_local_adapter_registry_promotion"
)
_LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ADAPTER_ID = (
    "local_fixture_adapter_usage_receipt"
)
_LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CAPABILITY = (
    "launch_local_fixture_adapter_usage_receipt"
)
_LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_ADAPTER_ID = (
    "local_fixture_adapter_dry_run_invocation_plan"
)
_LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_CAPABILITY = (
    "launch_local_fixture_adapter_dry_run_invocation_plan"
)
_LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ADAPTER_ID = (
    "local_fixture_adapter_execution_gate_plan"
)
_LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CAPABILITY = (
    "launch_local_fixture_adapter_execution_gate_plan"
)
_LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ADAPTER_ID = (
    "local_fixture_human_approval_artifact"
)
_LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CAPABILITY = (
    "launch_local_fixture_human_approval_artifact"
)
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
        if (
            not decision.admitted
            and not _route_is_safe_dry_run_plan(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
            and not _route_is_safe_adapter_draft_fixture(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
            and not _route_is_safe_operator_playwright_receipt_fixture(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
            and not _route_is_safe_local_fixture_playwright_admission_gate_fixture(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
            and not _route_is_safe_local_only_playwright_fixture_scenario_suite_fixture(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
            and not _route_is_safe_playwright_local_admission_receipt_aggregation_fixture(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
            and not _route_is_safe_admission_gated_local_adapter_registry_promotion_fixture(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
            and not _route_is_safe_local_fixture_adapter_usage_receipt_fixture(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
            and not _route_is_safe_local_fixture_adapter_dry_run_invocation_plan_fixture(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
            and not _route_is_safe_local_fixture_adapter_execution_gate_plan_fixture(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
            and not _route_is_safe_local_fixture_human_approval_artifact_fixture(
                node,
                decision.reason_codes,
                graph_execution_mode,
            )
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


def _route_is_safe_adapter_draft_fixture(node, reason_codes, graph_execution_mode):
    return (
        graph_execution_mode == "fixture_execution"
        and node["execution_mode"] == "fixture"
        and node["adapter_id"] == _BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_ID
        and node["capability"] == _BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_CAPABILITY
        and tuple(reason_codes) == ("adapter_not_admitted",)
    )


def _route_is_safe_operator_playwright_receipt_fixture(
    node,
    reason_codes,
    graph_execution_mode,
):
    return (
        graph_execution_mode == "fixture_execution"
        and node["execution_mode"] == "fixture"
        and node["adapter_id"] == _OPERATOR_PLAYWRIGHT_RECEIPT_ADAPTER_ID
        and node["capability"] == _OPERATOR_PLAYWRIGHT_RECEIPT_CAPABILITY
        and tuple(reason_codes) == ("adapter_not_admitted",)
    )


def _route_is_safe_local_fixture_playwright_admission_gate_fixture(
    node,
    reason_codes,
    graph_execution_mode,
):
    return (
        graph_execution_mode == "fixture_execution"
        and node["execution_mode"] == "fixture"
        and node["adapter_id"] == _LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_ADAPTER_ID
        and node["capability"] == _LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_CAPABILITY
        and tuple(reason_codes) == ("adapter_not_admitted",)
    )


def _route_is_safe_local_only_playwright_fixture_scenario_suite_fixture(
    node,
    reason_codes,
    graph_execution_mode,
):
    return (
        graph_execution_mode == "fixture_execution"
        and node["execution_mode"] == "fixture"
        and node["adapter_id"] == _LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ADAPTER_ID
        and node["capability"] == _LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CAPABILITY
        and tuple(reason_codes) == ("adapter_not_admitted",)
    )


def _route_is_safe_playwright_local_admission_receipt_aggregation_fixture(
    node,
    reason_codes,
    graph_execution_mode,
):
    return (
        graph_execution_mode == "fixture_execution"
        and node["execution_mode"] == "fixture"
        and node["adapter_id"]
        == _PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ADAPTER_ID
        and node["capability"]
        == _PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CAPABILITY
        and tuple(reason_codes) == ("adapter_not_admitted",)
    )


def _route_is_safe_admission_gated_local_adapter_registry_promotion_fixture(
    node,
    reason_codes,
    graph_execution_mode,
):
    return (
        graph_execution_mode == "fixture_execution"
        and node["execution_mode"] == "fixture"
        and node["adapter_id"]
        == _ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ADAPTER_ID
        and node["capability"]
        == _ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CAPABILITY
        and tuple(reason_codes) == ("adapter_not_admitted",)
    )


def _route_is_safe_local_fixture_adapter_usage_receipt_fixture(
    node,
    reason_codes,
    graph_execution_mode,
):
    return (
        graph_execution_mode == "fixture_execution"
        and node["execution_mode"] == "fixture"
        and node["adapter_id"] == _LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ADAPTER_ID
        and node["capability"] == _LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CAPABILITY
        and tuple(reason_codes) == ("adapter_not_admitted",)
    )


def _route_is_safe_local_fixture_adapter_dry_run_invocation_plan_fixture(
    node,
    reason_codes,
    graph_execution_mode,
):
    return (
        graph_execution_mode == "fixture_execution"
        and node["execution_mode"] == "fixture"
        and node["adapter_id"]
        == _LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_ADAPTER_ID
        and node["capability"]
        == _LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_CAPABILITY
        and tuple(reason_codes) == ("adapter_not_admitted",)
    )


def _route_is_safe_local_fixture_adapter_execution_gate_plan_fixture(
    node,
    reason_codes,
    graph_execution_mode,
):
    return (
        graph_execution_mode == "fixture_execution"
        and node["execution_mode"] == "fixture"
        and node["adapter_id"]
        == _LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ADAPTER_ID
        and node["capability"]
        == _LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CAPABILITY
        and tuple(reason_codes) == ("adapter_not_admitted",)
    )


def _route_is_safe_local_fixture_human_approval_artifact_fixture(
    node,
    reason_codes,
    graph_execution_mode,
):
    return (
        graph_execution_mode == "fixture_execution"
        and node["execution_mode"] == "fixture"
        and node["adapter_id"]
        == _LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ADAPTER_ID
        and node["capability"]
        == _LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CAPABILITY
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
            aggregation_result = (
                _run_playwright_local_admission_receipt_aggregation_node_if_requested(
                    node
                )
            )
            if aggregation_result is not None:
                record.update(aggregation_result)
            else:
                scenario_suite_result = (
                    _run_local_only_playwright_fixture_scenario_suite_node_if_requested(
                        node
                    )
                )
                if scenario_suite_result is not None:
                    record.update(scenario_suite_result)
                else:
                    admission_gate_result = (
                        _run_local_fixture_playwright_admission_gate_node_if_requested(
                            node
                        )
                    )
                    if admission_gate_result is not None:
                        record.update(admission_gate_result)
                    else:
                        operator_playwright_receipt_result = (
                            _run_operator_playwright_receipt_node_if_requested(node)
                        )
                        if operator_playwright_receipt_result is not None:
                            record.update(operator_playwright_receipt_result)
                        else:
                            bounded_playwright_draft_result = (
                                _run_bounded_playwright_adapter_draft_node_if_requested(
                                    node
                                )
                            )
                            if bounded_playwright_draft_result is not None:
                                record.update(bounded_playwright_draft_result)
                            else:
                                playwright_smoke_result = _run_playwright_smoke_node_if_requested(
                                    node
                                )
                                if playwright_smoke_result is not None:
                                    record.update(playwright_smoke_result)
                                else:
                                    github_intake_result = _run_github_capability_intake_node_if_requested(
                                        node
                                    )
                                    if github_intake_result is not None:
                                        record.update(github_intake_result)
                                    else:
                                        local_asset_result = _run_local_asset_node_if_requested(
                                            node
                                        )
                                        if local_asset_result is not None:
                                            record.update(local_asset_result)
                                        else:
                                            record["delivery_validation"] = (
                                                _run_delivery_node_if_requested(node)
                                            )
                                            record["status"] = "completed"
        if (
            not blocked_dependencies
            and graph_execution_mode != "dry_run_plan"
        ):
            registry_promotion_result = (
                _run_admission_gated_local_adapter_registry_promotion_node_if_requested(
                    node
                )
            )
            if registry_promotion_result is not None:
                record.update(registry_promotion_result)
            usage_receipt_result = (
                _run_local_fixture_adapter_usage_receipt_node_if_requested(node)
            )
            if usage_receipt_result is not None:
                record.update(usage_receipt_result)
            dry_run_plan_result = (
                _run_local_fixture_adapter_dry_run_invocation_plan_node_if_requested(
                    node
                )
            )
            if dry_run_plan_result is not None:
                record.update(dry_run_plan_result)
            execution_gate_plan_result = (
                _run_local_fixture_adapter_execution_gate_plan_node_if_requested(
                    node
                )
            )
            if execution_gate_plan_result is not None:
                record.update(execution_gate_plan_result)
            approval_artifact_result = (
                _run_local_fixture_human_approval_artifact_node_if_requested(
                    node
                )
            )
            if approval_artifact_result is not None:
                record.update(approval_artifact_result)
        status_by_node_id[node_id] = record["status"]
        executed.append(record)
    return executed


def _base_node_execution_record(node, graph_execution_mode):
    record = {
        "node_id": node["node_id"],
        "adapter_id": node["adapter_id"],
        "capability": node["capability"],
        "depends_on": list(node["depends_on"]),
        "execution_mode": node["execution_mode"],
        "runtime_class": node["runtime_class"],
        "approval_checkpoint_required": True,
        "approval_checkpoint_id": node["approval_checkpoint_id"],
        "adapter_route_admitted": node["adapter_id"]
        not in (
            _LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_ADAPTER_ID,
            _BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_ID,
            _OPERATOR_PLAYWRIGHT_RECEIPT_ADAPTER_ID,
            _LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ADAPTER_ID,
            _PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ADAPTER_ID,
            _ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ADAPTER_ID,
            _LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ADAPTER_ID,
            _LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_ADAPTER_ID,
            _LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ADAPTER_ID,
            _LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ADAPTER_ID,
        ),
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
    if node["adapter_id"] == _LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_ADAPTER_ID:
        from kernel.capabilities.local_fixture_playwright_adapter_admission_gate import (
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS,
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS,
        )

        record.update(dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS))
        record.update(
            dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS)
        )
    if node["adapter_id"] == _PLAYWRIGHT_SMOKE_ADAPTER_ID:
        from kernel.capabilities.playwright_local_fixture_sandbox_smoke import (
            PLAYWRIGHT_BOUNDARY_FALSE_FIELDS,
        )

        record.update(dict(PLAYWRIGHT_BOUNDARY_FALSE_FIELDS))
    if node["adapter_id"] == _BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_ID:
        from kernel.capabilities.bounded_playwright_worker_adapter_draft import (
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS,
        )

        record.update(
            dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS)
        )
    if node["adapter_id"] == _OPERATOR_PLAYWRIGHT_RECEIPT_ADAPTER_ID:
        from kernel.capabilities.operator_provided_playwright_execution_receipt import (
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS,
        )

        record.update(
            dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS)
        )
    if node["adapter_id"] == _LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ADAPTER_ID:
        from kernel.capabilities.local_only_playwright_fixture_scenario_suite import (
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS,
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS,
        )

        record.update(
            dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS)
        )
        record.update(
            dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS)
        )
    if node["adapter_id"] == _PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ADAPTER_ID:
        from kernel.capabilities.playwright_local_admission_receipt_aggregation import (
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS,
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS,
        )

        record.update(
            dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS)
        )
        record.update(
            dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS)
        )
    if (
        node["adapter_id"]
        == _ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ADAPTER_ID
    ):
        from kernel.capabilities.admission_gated_local_adapter_registry_promotion import (
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS,
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS,
        )

        record.update(dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS))
        record.update(
            dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS)
        )
    if node["adapter_id"] == _LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ADAPTER_ID:
        from kernel.capabilities.local_fixture_adapter_usage_receipt import (
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS,
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS,
        )

        record.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS
            }
        )
        record.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS
            }
        )
    if (
        node["adapter_id"]
        == _LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_ADAPTER_ID
    ):
        from kernel.capabilities.local_fixture_adapter_dry_run_invocation_plan import (
            LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_DENIED_ADMISSION_FIELDS,
            LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_FORBIDDEN_PERFORMED_FIELDS,
            LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_MATERIALIZED_FALSE_FIELDS,
        )

        record.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_DENIED_ADMISSION_FIELDS
            }
        )
        record.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_FORBIDDEN_PERFORMED_FIELDS
            }
        )
        record.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_MATERIALIZED_FALSE_FIELDS
            }
        )
        record["future_invocation_requires_separate_execution_gate"] = True
        record["future_execution_requires_human_approval"] = True
    if (
        node["adapter_id"]
        == _LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ADAPTER_ID
    ):
        from kernel.capabilities.local_fixture_adapter_execution_gate_plan import (
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS,
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS,
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS,
        )

        record.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS
            }
        )
        record.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS
            }
        )
        record.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS
            }
        )
        record["approval_token_issued"] = False
        record["auto_approval_performed"] = False
        record["runnable_job_created"] = False
        record["execution_runner_created"] = False
        record["future_execution_requires_separate_human_approval_artifact"] = True
        record["future_execution_requires_separate_execution_runner_pr"] = True
    if (
        node["adapter_id"]
        == _LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ADAPTER_ID
    ):
        from kernel.capabilities.local_fixture_human_approval_artifact import (
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_REQUIRED_SOURCE_FALSE_FIELDS,
        )

        record.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_REQUIRED_SOURCE_FALSE_FIELDS
            }
        )
        record["approval_token_issued"] = False
        record["execution_token_issued"] = False
        record["runner_created"] = False
        record["runnable_job_created"] = False
        record["adapter_execution_performed"] = False
        record["playwright_execution_performed"] = False
        record["browser_open_performed"] = False
        record["network_access_performed"] = False
        record["live_website_access_performed"] = False
        record["autonomous_execution_performed"] = False
        record["production_promotion_granted"] = False
        record["metadata_only"] = True
        record["future_runner_requires_separate_pr"] = True
        record["future_execution_requires_separate_runner_receipt"] = True
        record["future_execution_requires_explicit_local_fixture_runner_gate"] = True
    return record


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
    if node["adapter_id"] == _LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_ADAPTER_ID:
        return "local_fixture_playwright_admission_gate_only_not_production_admitted"
    if node["adapter_id"] == _LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ADAPTER_ID:
        return "local_only_playwright_fixture_scenario_suite_not_production_admitted"
    if node["adapter_id"] == _PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ADAPTER_ID:
        return "playwright_local_admission_receipt_aggregation_not_production_admitted"
    if (
        node["adapter_id"]
        == _ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ADAPTER_ID
    ):
        return "admission_gated_local_adapter_registry_promotion_not_production_admitted"
    if node["adapter_id"] == _LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ADAPTER_ID:
        return "local_fixture_adapter_usage_receipt_not_production_admitted"
    if (
        node["adapter_id"]
        == _LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_ADAPTER_ID
    ):
        return "local_fixture_adapter_dry_run_invocation_plan_not_production_admitted"
    if (
        node["adapter_id"]
        == _LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ADAPTER_ID
    ):
        return "local_fixture_adapter_execution_gate_plan_not_production_admitted"
    if (
        node["adapter_id"]
        == _LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ADAPTER_ID
    ):
        return "local_fixture_human_approval_artifact_not_production_admitted"
    if node["adapter_id"] == _OPERATOR_PLAYWRIGHT_RECEIPT_ADAPTER_ID:
        return "operator_provided_local_fixture_receipt_only_not_production_admitted"
    if node["adapter_id"] == _BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_ID:
        return "adapter_draft_local_fixture_only_not_production_admitted"
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


def _run_github_capability_intake_node_if_requested(node):
    if node["adapter_id"] != _GITHUB_CAPABILITY_ADAPTER_ID:
        return None
    if node["capability"] != _GITHUB_CAPABILITY_INTAKE_PACKET_CAPABILITY:
        raise ValueError("task graph github capability intake capability is not registered")
    inputs = node["inputs"]
    candidate_manifest = _required_string_input(
        inputs,
        "candidate_manifest",
        "github capability intake packet",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "github capability intake packet",
    )
    intake_id = _required_string_input(
        inputs,
        "intake_id",
        "github capability intake packet",
    )
    candidate_repo_dir = _optional_nonempty_string_input(
        inputs,
        "candidate_repo_dir",
        "github capability intake packet",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "github capability intake packet",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "github capability intake packet",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "github capability intake packet",
    )

    from kernel.capabilities.github_capability_intake_packet import (
        NO_SCOPE_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_github_capability_intake_packet_launcher,
    )

    result = run_github_capability_intake_packet_launcher(
        Path(candidate_manifest),
        Path(output_dir),
        intake_id,
        candidate_repo_dir=None
        if candidate_repo_dir is None
        else Path(candidate_repo_dir),
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "github_capability_intake_packet_complete": complete,
        "github_capability_intake_packet_path": payload.get(
            "github_capability_intake_packet_path"
        ),
        "github_capability_intake_packet_manifest_path": payload.get(
            "github_capability_intake_packet_manifest_path"
        ),
        "github_capability_intake_packet_summary_path": payload.get(
            "github_capability_intake_packet_summary_path"
        ),
        "github_capability_intake_packet_checklist_path": payload.get(
            "github_capability_intake_packet_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "intake_id": payload.get("intake_id"),
        "project_id": payload.get("project_id"),
        "reviewer_id": payload.get("reviewer_id"),
        "candidate_manifest_path": payload.get("candidate_manifest_path"),
        "candidate_manifest_sha256": payload.get("candidate_manifest_sha256"),
        "candidate_repo_dir": payload.get("candidate_repo_dir"),
        "candidate_repo_dir_provided": payload.get("candidate_repo_dir_provided"),
        "candidate_id": payload.get("candidate_id"),
        "candidate_name": payload.get("candidate_name"),
        "repo_full_name": payload.get("repo_full_name"),
        "intended_use": payload.get("intended_use"),
        "capability_domains": payload.get("capability_domains"),
        "local_repo_evidence_file_count": payload.get(
            "local_repo_evidence_file_count"
        ),
        "local_repo_evidence_total_bytes": payload.get(
            "local_repo_evidence_total_bytes"
        ),
        "local_repo_symlink_evidence_detected": payload.get(
            "local_repo_symlink_evidence_detected"
        ),
        "declared_network_risk": payload.get("declared_network_risk"),
        "declared_secret_risk": payload.get("declared_secret_risk"),
        "declared_filesystem_risk": payload.get("declared_filesystem_risk"),
        "declared_execution_risk": payload.get("declared_execution_risk"),
        "declared_installation_risk": payload.get("declared_installation_risk"),
        "declared_license_risk": payload.get("declared_license_risk"),
        "license_review_required": payload.get("license_review_required"),
        "security_review_required": payload.get("security_review_required"),
        "sandbox_review_required": payload.get("sandbox_review_required"),
        "adapter_generation_allowed": payload.get("adapter_generation_allowed"),
        "auto_adoption_allowed": payload.get("auto_adoption_allowed"),
        "intake_status": payload.get("intake_status"),
        "intake_decision": payload.get("intake_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "error_message": None if complete else payload.get("error_message"),
        "safe_to_retry": not complete,
        "replay_hint": "Fix intake preflight inputs and rerun the same node."
        if not complete
        else "Review packet before selecting a bounded sandbox smoke.",
        "required_human_approval": True,
        "required_human_review": True,
        **dict(NO_SCOPE_FALSE_FIELDS),
    }


def _run_local_only_playwright_fixture_scenario_suite_node_if_requested(node):
    if node["adapter_id"] != _LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ADAPTER_ID:
        return None
    if node["capability"] != _LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CAPABILITY:
        raise ValueError(
            "task graph local-only Playwright fixture scenario suite capability is not registered"
        )
    inputs = node["inputs"]
    selection_matrix = _required_string_input(
        inputs,
        "selection_matrix",
        "local-only Playwright fixture scenario suite",
    )
    candidate_manifest = _required_string_input(
        inputs,
        "playwright_candidate_manifest",
        "local-only Playwright fixture scenario suite",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local-only Playwright fixture scenario suite",
    )
    suite_id = _required_string_input(
        inputs,
        "suite_id",
        "local-only Playwright fixture scenario suite",
    )
    node_command = _required_string_input(
        inputs,
        "node_command",
        "local-only Playwright fixture scenario suite",
    )
    runner_script = _required_string_input(
        inputs,
        "runner_script",
        "local-only Playwright fixture scenario suite",
    )
    operator_attestation = _required_string_input(
        inputs,
        "operator_attestation",
        "local-only Playwright fixture scenario suite",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "local-only Playwright fixture scenario suite",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "local-only Playwright fixture scenario suite",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "local-only Playwright fixture scenario suite",
    )
    expected_node_version = _optional_nonempty_string_input(
        inputs,
        "expected_node_version",
        "local-only Playwright fixture scenario suite",
    )
    expected_playwright_source = _optional_nonempty_string_input(
        inputs,
        "expected_playwright_source",
        "local-only Playwright fixture scenario suite",
    )
    scenario_set = _optional_nonempty_string_input(
        inputs,
        "scenario_set",
        "local-only Playwright fixture scenario suite",
    ) or "core"
    plan_only = _optional_bool_input(inputs, "plan_only", False)

    from kernel.capabilities.local_only_playwright_fixture_scenario_suite import (
        LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS,
        LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_local_only_playwright_fixture_scenario_suite_launcher,
    )

    result = run_local_only_playwright_fixture_scenario_suite_launcher(
        Path(selection_matrix),
        Path(candidate_manifest),
        Path(output_dir),
        suite_id,
        node_command=Path(node_command),
        runner_script=Path(runner_script),
        operator_attestation=operator_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        expected_node_version=expected_node_version,
        expected_playwright_source=expected_playwright_source,
        scenario_set=scenario_set,
        plan_only=plan_only,
    )
    payload = result.payload
    complete = bool(result.complete)
    false_fields = dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS)
    false_fields.update(
        dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS)
    )
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "local_only_playwright_fixture_scenario_suite_complete": complete,
        "local_only_playwright_fixture_scenario_suite_plan_path": payload.get(
            "local_only_playwright_fixture_scenario_suite_plan_path"
        ),
        "local_only_playwright_fixture_scenario_suite_manifest_path": payload.get(
            "local_only_playwright_fixture_scenario_suite_manifest_path"
        ),
        "local_only_playwright_fixture_scenario_suite_summary_path": payload.get(
            "local_only_playwright_fixture_scenario_suite_summary_path"
        ),
        "local_only_playwright_fixture_scenario_suite_checklist_path": payload.get(
            "local_only_playwright_fixture_scenario_suite_checklist_path"
        ),
        "local_only_playwright_fixture_scenario_suite_result_path": payload.get(
            "local_only_playwright_fixture_scenario_suite_result_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "scenarios_dir": payload.get("scenarios_dir"),
        "scenario_result_paths": payload.get("scenario_result_paths"),
        "suite_id": payload.get("suite_id"),
        "scenario_set": payload.get("scenario_set"),
        "scenario_count_planned": payload.get("scenario_count_planned"),
        "scenario_count_executed": payload.get("scenario_count_executed"),
        "scenario_count_passed": payload.get("scenario_count_passed"),
        "scenario_count_failed": payload.get("scenario_count_failed"),
        "suite_success": payload.get("suite_success"),
        "suite_status": payload.get("suite_status"),
        "suite_decision": payload.get("suite_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "selection_matrix_path": payload.get("selection_matrix_path"),
        "selection_matrix_sha256": payload.get("selection_matrix_sha256"),
        "playwright_candidate_manifest_path": payload.get(
            "playwright_candidate_manifest_path"
        ),
        "playwright_candidate_manifest_sha256": payload.get(
            "playwright_candidate_manifest_sha256"
        ),
        "node_command_path": payload.get("node_command_path"),
        "node_command_sha256": payload.get("node_command_sha256"),
        "runner_script_path": payload.get("runner_script_path"),
        "runner_script_sha256": payload.get("runner_script_sha256"),
        "candidate_id": payload.get("candidate_id"),
        "selected_candidate_id": payload.get("selected_candidate_id"),
        "repo_full_name": payload.get("repo_full_name"),
        "local_execution_scope": payload.get("local_execution_scope"),
        "fixture_url_scheme": payload.get("fixture_url_scheme"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "error_message": None if complete else payload.get("error_message"),
        "safe_to_retry": not complete,
        "replay_hint": (
            "Fix local-only Playwright fixture scenario suite inputs or failed receipt evidence and rerun this node."
        )
        if not complete
        else "Review suite evidence; success is local-fixture-only and not production admission.",
        "required_human_approval": True,
        "required_human_review": True,
        **false_fields,
    }


def _run_playwright_local_admission_receipt_aggregation_node_if_requested(node):
    if node["adapter_id"] != _PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ADAPTER_ID:
        return None
    if node["capability"] != _PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CAPABILITY:
        raise ValueError(
            "task graph Playwright local admission receipt aggregation capability is not registered"
        )
    inputs = node["inputs"]
    suite_run_dirs_manifest = _required_string_input(
        inputs,
        "suite_run_dirs",
        "Playwright local admission receipt aggregation",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "Playwright local admission receipt aggregation",
    )
    aggregation_id = _required_string_input(
        inputs,
        "aggregation_id",
        "Playwright local admission receipt aggregation",
    )
    review_attestation = _required_string_input(
        inputs,
        "review_attestation",
        "Playwright local admission receipt aggregation",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "Playwright local admission receipt aggregation",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "Playwright local admission receipt aggregation",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "Playwright local admission receipt aggregation",
    )
    minimum_suite_runs = _optional_int_input(
        inputs,
        "minimum_suite_runs",
        2,
        "Playwright local admission receipt aggregation",
    )
    minimum_pass_rate_bps = _optional_int_input(
        inputs,
        "minimum_pass_rate_bps",
        10000,
        "Playwright local admission receipt aggregation",
    )
    maximum_flaky_rate_bps = _optional_int_input(
        inputs,
        "maximum_flaky_rate_bps",
        0,
        "Playwright local admission receipt aggregation",
    )
    maximum_evidence_age_days = _optional_int_input(
        inputs,
        "maximum_evidence_age_days",
        30,
        "Playwright local admission receipt aggregation",
    )
    plan_only = _optional_bool_input(inputs, "plan_only", False)

    from kernel.capabilities.playwright_local_admission_receipt_aggregation import (
        PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS,
        PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_playwright_local_admission_receipt_aggregation_launcher,
    )

    result = run_playwright_local_admission_receipt_aggregation_launcher(
        Path(suite_run_dirs_manifest),
        Path(output_dir),
        aggregation_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        minimum_suite_runs=minimum_suite_runs,
        minimum_pass_rate_bps=minimum_pass_rate_bps,
        maximum_flaky_rate_bps=maximum_flaky_rate_bps,
        maximum_evidence_age_days=maximum_evidence_age_days,
        plan_only=plan_only,
    )
    payload = result.payload
    complete = bool(result.complete)
    false_fields = dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS)
    false_fields.update(
        dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS)
    )
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "playwright_local_admission_receipt_aggregation_complete": complete,
        "playwright_local_admission_receipt_aggregation_plan_path": payload.get(
            "playwright_local_admission_receipt_aggregation_plan_path"
        ),
        "playwright_local_admission_receipt_aggregation_manifest_path": payload.get(
            "playwright_local_admission_receipt_aggregation_manifest_path"
        ),
        "playwright_local_admission_receipt_aggregation_summary_path": payload.get(
            "playwright_local_admission_receipt_aggregation_summary_path"
        ),
        "playwright_local_admission_receipt_aggregation_checklist_path": payload.get(
            "playwright_local_admission_receipt_aggregation_checklist_path"
        ),
        "playwright_local_admission_receipt_aggregation_result_path": payload.get(
            "playwright_local_admission_receipt_aggregation_result_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "suite_run_dirs_manifest_path": payload.get("suite_run_dirs_manifest_path"),
        "suite_run_dirs_manifest_sha256": payload.get(
            "suite_run_dirs_manifest_sha256"
        ),
        "aggregation_id": payload.get("aggregation_id"),
        "suite_run_count_planned": payload.get("suite_run_count_planned"),
        "suite_run_count_evaluated": payload.get("suite_run_count_evaluated"),
        "suite_run_count_passed": payload.get("suite_run_count_passed"),
        "suite_run_count_failed": payload.get("suite_run_count_failed"),
        "suite_run_count_rejected": payload.get("suite_run_count_rejected"),
        "scenario_count_total": payload.get("scenario_count_total"),
        "scenario_count_passed": payload.get("scenario_count_passed"),
        "scenario_count_failed": payload.get("scenario_count_failed"),
        "pass_rate_bps": payload.get("pass_rate_bps"),
        "flaky_rate_bps": payload.get("flaky_rate_bps"),
        "flaky_scenario_ids": payload.get("flaky_scenario_ids"),
        "regression_detected": payload.get("regression_detected"),
        "stale_evidence_detected": payload.get("stale_evidence_detected"),
        "missing_coverage_detected": payload.get("missing_coverage_detected"),
        "aggregate_success": payload.get("aggregate_success"),
        "local_fixture_aggregation_passed": payload.get(
            "local_fixture_aggregation_passed"
        ),
        "aggregation_status": payload.get("aggregation_status"),
        "aggregation_decision": payload.get("aggregation_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "candidate_id": payload.get("candidate_id"),
        "selected_candidate_id": payload.get("selected_candidate_id"),
        "repo_full_name": payload.get("repo_full_name"),
        "local_execution_scope": payload.get("local_execution_scope"),
        "fixture_url_scheme": payload.get("fixture_url_scheme"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "error_message": None if complete else payload.get("error_message"),
        "safe_to_retry": not complete,
        "replay_hint": (
            "Fix Playwright local admission receipt aggregation inputs or rejected suite evidence and rerun this node."
        )
        if not complete
        else "Review aggregation evidence; success is local-fixture-only and not production admission.",
        "required_human_approval": True,
        "required_human_review": True,
        **false_fields,
    }


def _run_admission_gated_local_adapter_registry_promotion_node_if_requested(node):
    if (
        node["adapter_id"]
        != _ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ADAPTER_ID
    ):
        return None
    if node["capability"] != _ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CAPABILITY:
        raise ValueError(
            "task graph admission-gated local adapter registry promotion capability is not registered"
        )
    inputs = node["inputs"]
    admission_gate_decision = _required_string_input(
        inputs,
        "admission_gate_decision",
        "admission-gated local adapter registry promotion",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "admission-gated local adapter registry promotion",
    )
    promotion_id = _required_string_input(
        inputs,
        "promotion_id",
        "admission-gated local adapter registry promotion",
    )
    review_attestation = _required_string_input(
        inputs,
        "review_attestation",
        "admission-gated local adapter registry promotion",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "admission-gated local adapter registry promotion",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "admission-gated local adapter registry promotion",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "admission-gated local adapter registry promotion",
    )
    registry_output = _optional_nonempty_string_input(
        inputs,
        "registry_output",
        "admission-gated local adapter registry promotion",
    )

    from kernel.capabilities.admission_gated_local_adapter_registry_promotion import (
        LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS,
        LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_admission_gated_local_adapter_registry_promotion_launcher,
    )

    result = run_admission_gated_local_adapter_registry_promotion_launcher(
        Path(admission_gate_decision),
        Path(output_dir),
        promotion_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        registry_output=None if registry_output is None else Path(registry_output),
    )
    payload = result.payload
    complete = bool(result.complete)
    false_fields = dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS)
    false_fields.update(
        dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS)
    )
    false_fields["local_fixture_admission_granted"] = payload.get(
        "local_fixture_admission_granted",
        False,
    )
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "admission_gated_local_adapter_registry_promotion_complete": complete,
        "admission_gated_local_adapter_registry_promotion_plan_path": payload.get(
            "admission_gated_local_adapter_registry_promotion_plan_path"
        ),
        "admission_gated_local_adapter_registry_promotion_result_path": payload.get(
            "admission_gated_local_adapter_registry_promotion_result_path"
        ),
        "admission_gated_local_adapter_registry_promotion_manifest_path": payload.get(
            "admission_gated_local_adapter_registry_promotion_manifest_path"
        ),
        "admission_gated_local_adapter_registry_promotion_summary_path": payload.get(
            "admission_gated_local_adapter_registry_promotion_summary_path"
        ),
        "admission_gated_local_adapter_registry_promotion_checklist_path": payload.get(
            "admission_gated_local_adapter_registry_promotion_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "registry_output_path": payload.get("registry_output_path"),
        "promotion_id": payload.get("promotion_id"),
        "promotion_status": payload.get("promotion_status"),
        "promotion_decision": payload.get("promotion_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "source_gate_decision_path": payload.get("source_gate_decision_path"),
        "source_gate_decision_sha256": payload.get("source_gate_decision_sha256"),
        "source_gate_decision_type": payload.get("source_gate_decision_type"),
        "source_gate_passed": payload.get("source_gate_passed"),
        "aggregation_bound": payload.get("aggregation_bound"),
        "regression_bound": payload.get("regression_bound"),
        "registry_promotion_granted": payload.get("registry_promotion_granted"),
        "production_promotion_granted": payload.get("production_promotion_granted"),
        "local_fixture_only": payload.get("local_fixture_only"),
        "non_production": payload.get("non_production"),
        "production_adapter": payload.get("production_adapter"),
        "allowed_scope": payload.get("allowed_scope"),
        "denied_scope": payload.get("denied_scope"),
        "rejection_reasons": payload.get("rejection_reasons"),
        "failure_stage": None if complete else "registry_promotion_rejected",
        "error_message": None
        if complete
        else ",".join(str(reason) for reason in payload.get("rejection_reasons", [])),
        "safe_to_retry": not complete,
        "replay_hint": (
            "Fix the #427 admission gate decision evidence and rerun the promotion node."
        )
        if not complete
        else "Use the promoted registry record only in the local-fixture lane under human review.",
        "required_human_approval": True,
        "required_human_review": True,
        **false_fields,
    }


def _run_local_fixture_adapter_usage_receipt_node_if_requested(node):
    if node["adapter_id"] != _LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ADAPTER_ID:
        return None
    if node["capability"] != _LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CAPABILITY:
        raise ValueError(
            "task graph local-fixture adapter usage receipt capability is not registered"
        )
    inputs = node["inputs"]
    promotion_result = _required_string_input(
        inputs,
        "promotion_result",
        "local-fixture adapter usage receipt",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local-fixture adapter usage receipt",
    )
    usage_receipt_id = _required_string_input(
        inputs,
        "usage_receipt_id",
        "local-fixture adapter usage receipt",
    )
    review_attestation = _required_string_input(
        inputs,
        "review_attestation",
        "local-fixture adapter usage receipt",
    )
    local_fixture_reference = _required_string_input(
        inputs,
        "local_fixture_reference",
        "local-fixture adapter usage receipt",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "local-fixture adapter usage receipt",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "local-fixture adapter usage receipt",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "local-fixture adapter usage receipt",
    )
    registry_entry = _optional_nonempty_string_input(
        inputs,
        "registry_entry",
        "local-fixture adapter usage receipt",
    )

    from kernel.capabilities.local_fixture_adapter_usage_receipt import (
        LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS,
        LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_local_fixture_adapter_usage_receipt_launcher,
    )

    result = run_local_fixture_adapter_usage_receipt_launcher(
        Path(promotion_result),
        Path(output_dir),
        usage_receipt_id,
        review_attestation=review_attestation,
        local_fixture_reference=local_fixture_reference,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        registry_entry=None if registry_entry is None else Path(registry_entry),
    )
    payload = result.payload
    complete = bool(result.complete)
    false_fields = {
        field_name: False
        for field_name in LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS
    }
    false_fields.update(
        {
            field_name: False
            for field_name in LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS
        }
    )
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "local_fixture_adapter_usage_receipt_complete": complete,
        "local_fixture_adapter_usage_receipt_plan_path": payload.get(
            "local_fixture_adapter_usage_receipt_plan_path"
        ),
        "local_fixture_adapter_usage_receipt_result_path": payload.get(
            "local_fixture_adapter_usage_receipt_result_path"
        ),
        "local_fixture_adapter_usage_receipt_manifest_path": payload.get(
            "local_fixture_adapter_usage_receipt_manifest_path"
        ),
        "local_fixture_adapter_usage_receipt_summary_path": payload.get(
            "local_fixture_adapter_usage_receipt_summary_path"
        ),
        "local_fixture_adapter_usage_receipt_checklist_path": payload.get(
            "local_fixture_adapter_usage_receipt_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "usage_receipt_id": payload.get("usage_receipt_id"),
        "usage_receipt_granted": payload.get("usage_receipt_granted"),
        "promotion_status": payload.get("promotion_status"),
        "promotion_decision": payload.get("promotion_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "promotion_result_path": payload.get("promotion_result_path"),
        "promotion_result_sha256": payload.get("promotion_result_sha256"),
        "promotion_validated": payload.get("promotion_validated"),
        "registry_entry_validated": payload.get("registry_entry_validated"),
        "registry_entry_path": payload.get("registry_entry_path"),
        "registry_entry_sha256": payload.get("registry_entry_sha256"),
        "source_gate_decision_type": payload.get("source_gate_decision_type"),
        "source_gate_decision_sha256": payload.get("source_gate_decision_sha256"),
        "source_gate_passed": payload.get("source_gate_passed"),
        "aggregation_bound": payload.get("aggregation_bound"),
        "regression_bound": payload.get("regression_bound"),
        "local_fixture_only": payload.get("local_fixture_only"),
        "one_usage_receipt_only": payload.get("one_usage_receipt_only"),
        "local_fixture_reference": payload.get("local_fixture_reference"),
        "local_fixture_reference_scheme": payload.get(
            "local_fixture_reference_scheme"
        ),
        "local_fixture_path": payload.get("local_fixture_path"),
        "local_fixture_sha256": payload.get("local_fixture_sha256"),
        "local_fixture_exists": payload.get("local_fixture_exists"),
        "local_fixture_regular_file": payload.get("local_fixture_regular_file"),
        "local_fixture_symlink_detected": payload.get(
            "local_fixture_symlink_detected"
        ),
        "local_fixture_under_allowed_root": payload.get(
            "local_fixture_under_allowed_root"
        ),
        "promoted_adapter_id": payload.get("adapter_id"),
        "candidate_id": payload.get("candidate_id"),
        "repo_full_name": payload.get("repo_full_name"),
        "non_production": payload.get("non_production"),
        "production_adapter": payload.get("production_adapter"),
        "rejection_reasons": payload.get("rejection_reasons"),
        "failure_stage": None if complete else "usage_receipt_rejected",
        "error_message": None
        if complete
        else ",".join(str(reason) for reason in payload.get("rejection_reasons", [])),
        "safe_to_retry": not complete,
        "replay_hint": (
            "Fix the #428 promotion result or local fixture metadata and rerun the usage receipt node."
        )
        if not complete
        else "Review the usage receipt before any separate execution proposal.",
        "required_human_approval": True,
        "required_human_review": True,
        **false_fields,
    }


def _run_local_fixture_adapter_dry_run_invocation_plan_node_if_requested(node):
    if (
        node["adapter_id"]
        != _LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_ADAPTER_ID
    ):
        return None
    if node["capability"] != _LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_CAPABILITY:
        raise ValueError(
            "task graph local-fixture adapter dry-run invocation plan capability is not registered"
        )
    inputs = node["inputs"]
    usage_receipt = _required_string_input(
        inputs,
        "usage_receipt",
        "local-fixture adapter dry-run invocation plan",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local-fixture adapter dry-run invocation plan",
    )
    invocation_plan_id = _required_string_input(
        inputs,
        "invocation_plan_id",
        "local-fixture adapter dry-run invocation plan",
    )
    review_attestation = _required_string_input(
        inputs,
        "review_attestation",
        "local-fixture adapter dry-run invocation plan",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "local-fixture adapter dry-run invocation plan",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "local-fixture adapter dry-run invocation plan",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "local-fixture adapter dry-run invocation plan",
    )

    from kernel.capabilities.local_fixture_adapter_dry_run_invocation_plan import (
        LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_DENIED_ADMISSION_FIELDS,
        LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_FORBIDDEN_PERFORMED_FIELDS,
        LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_MATERIALIZED_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_local_fixture_adapter_dry_run_invocation_plan_launcher,
    )

    result = run_local_fixture_adapter_dry_run_invocation_plan_launcher(
        Path(usage_receipt),
        Path(output_dir),
        invocation_plan_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
    )
    payload = result.payload
    complete = bool(result.complete)
    false_fields = {
        field_name: False
        for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_DENIED_ADMISSION_FIELDS
    }
    false_fields.update(
        {
            field_name: False
            for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_FORBIDDEN_PERFORMED_FIELDS
        }
    )
    false_fields.update(
        {
            field_name: False
            for field_name in LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_MATERIALIZED_FALSE_FIELDS
        }
    )
    false_fields["future_invocation_requires_separate_execution_gate"] = True
    false_fields["future_execution_requires_human_approval"] = True
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "local_fixture_adapter_dry_run_invocation_plan_complete": complete,
        "local_fixture_adapter_dry_run_invocation_plan_plan_path": payload.get(
            "local_fixture_adapter_dry_run_invocation_plan_plan_path"
        ),
        "local_fixture_adapter_dry_run_invocation_plan_result_path": payload.get(
            "local_fixture_adapter_dry_run_invocation_plan_result_path"
        ),
        "local_fixture_adapter_dry_run_invocation_plan_manifest_path": payload.get(
            "local_fixture_adapter_dry_run_invocation_plan_manifest_path"
        ),
        "local_fixture_adapter_dry_run_invocation_plan_summary_path": payload.get(
            "local_fixture_adapter_dry_run_invocation_plan_summary_path"
        ),
        "local_fixture_adapter_dry_run_invocation_plan_checklist_path": payload.get(
            "local_fixture_adapter_dry_run_invocation_plan_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "invocation_plan_id": payload.get("invocation_plan_id"),
        "invocation_plan_status": payload.get("invocation_plan_status"),
        "invocation_plan_decision": payload.get("invocation_plan_decision"),
        "invocation_plan_granted": payload.get("invocation_plan_granted"),
        "usage_receipt_path": payload.get("usage_receipt_path"),
        "usage_receipt_sha256": payload.get("usage_receipt_sha256"),
        "usage_receipt_type": payload.get("usage_receipt_type"),
        "usage_receipt_validated": payload.get("usage_receipt_validated"),
        "usage_receipt_granted": payload.get("usage_receipt_granted"),
        "promotion_type": payload.get("promotion_type"),
        "promotion_result_sha256": payload.get("promotion_result_sha256"),
        "source_gate_decision_type": payload.get("source_gate_decision_type"),
        "source_gate_decision_sha256": payload.get("source_gate_decision_sha256"),
        "source_gate_passed": payload.get("source_gate_passed"),
        "registry_promotion_granted": payload.get("registry_promotion_granted"),
        "aggregation_bound": payload.get("aggregation_bound"),
        "regression_bound": payload.get("regression_bound"),
        "local_fixture_only": payload.get("local_fixture_only"),
        "one_usage_receipt_bound": payload.get("one_usage_receipt_bound"),
        "dry_run_plan_only": payload.get("dry_run_plan_only"),
        "local_fixture_reference": payload.get("local_fixture_reference"),
        "local_fixture_reference_scheme": payload.get(
            "local_fixture_reference_scheme"
        ),
        "local_fixture_path": payload.get("local_fixture_path"),
        "local_fixture_sha256": payload.get("local_fixture_sha256"),
        "local_fixture_revalidated": payload.get("local_fixture_revalidated"),
        "local_fixture_exists": payload.get("local_fixture_exists"),
        "local_fixture_regular_file": payload.get("local_fixture_regular_file"),
        "local_fixture_symlink_detected": payload.get(
            "local_fixture_symlink_detected"
        ),
        "local_fixture_under_allowed_root": payload.get(
            "local_fixture_under_allowed_root"
        ),
        "promoted_adapter_id": payload.get("adapter_id"),
        "candidate_id": payload.get("candidate_id"),
        "repo_full_name": payload.get("repo_full_name"),
        "non_production": payload.get("non_production"),
        "production_adapter": payload.get("production_adapter"),
        "rejection_reasons": payload.get("rejection_reasons"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "failure_stage": None if complete else "dry_run_invocation_plan_rejected",
        "error_message": None
        if complete
        else ",".join(str(reason) for reason in payload.get("rejection_reasons", [])),
        "safe_to_retry": not complete,
        "replay_hint": (
            "Fix the #429 usage receipt result or local fixture metadata and rerun the dry-run plan node."
        )
        if not complete
        else "Review the dry-run invocation plan before any separate execution gate.",
        "required_human_approval": True,
        "required_human_review": True,
        **false_fields,
    }


def _run_local_fixture_adapter_execution_gate_plan_node_if_requested(node):
    if (
        node["adapter_id"]
        != _LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ADAPTER_ID
    ):
        return None
    if node["capability"] != _LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CAPABILITY:
        raise ValueError(
            "task graph local-fixture adapter execution-gate plan capability is not registered"
        )
    inputs = node["inputs"]
    dry_run_plan = _required_string_input(
        inputs,
        "dry_run_plan",
        "local-fixture adapter execution-gate plan",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local-fixture adapter execution-gate plan",
    )
    execution_gate_plan_id = _required_string_input(
        inputs,
        "execution_gate_plan_id",
        "local-fixture adapter execution-gate plan",
    )
    review_attestation = _required_string_input(
        inputs,
        "review_attestation",
        "local-fixture adapter execution-gate plan",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "local-fixture adapter execution-gate plan",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "local-fixture adapter execution-gate plan",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "local-fixture adapter execution-gate plan",
    )

    from kernel.capabilities.local_fixture_adapter_execution_gate_plan import (
        LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS,
        LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS,
        LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_local_fixture_adapter_execution_gate_plan_launcher,
    )

    result = run_local_fixture_adapter_execution_gate_plan_launcher(
        Path(dry_run_plan),
        Path(output_dir),
        execution_gate_plan_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
    )
    payload = result.payload
    complete = bool(result.complete)
    false_fields = {
        field_name: False
        for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS
    }
    false_fields.update(
        {
            field_name: False
            for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS
        }
    )
    false_fields.update(
        {
            field_name: False
            for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS
        }
    )
    false_fields["approval_token_issued"] = False
    false_fields["auto_approval_performed"] = False
    false_fields["runnable_job_created"] = False
    false_fields["execution_runner_created"] = False
    false_fields["future_execution_requires_separate_human_approval_artifact"] = True
    false_fields["future_execution_requires_separate_execution_runner_pr"] = True
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "local_fixture_adapter_execution_gate_plan_complete": complete,
        "local_fixture_adapter_execution_gate_plan_plan_path": payload.get(
            "local_fixture_adapter_execution_gate_plan_plan_path"
        ),
        "local_fixture_adapter_execution_gate_plan_result_path": payload.get(
            "local_fixture_adapter_execution_gate_plan_result_path"
        ),
        "local_fixture_adapter_execution_gate_plan_manifest_path": payload.get(
            "local_fixture_adapter_execution_gate_plan_manifest_path"
        ),
        "local_fixture_adapter_execution_gate_plan_human_approval_request_path": payload.get(
            "local_fixture_adapter_execution_gate_plan_human_approval_request_path"
        ),
        "local_fixture_adapter_execution_gate_plan_summary_path": payload.get(
            "local_fixture_adapter_execution_gate_plan_summary_path"
        ),
        "local_fixture_adapter_execution_gate_plan_checklist_path": payload.get(
            "local_fixture_adapter_execution_gate_plan_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "execution_gate_plan_id": payload.get("execution_gate_plan_id"),
        "execution_gate_plan_status": payload.get("execution_gate_plan_status"),
        "execution_gate_plan_decision": payload.get("execution_gate_plan_decision"),
        "execution_gate_plan_granted": payload.get("execution_gate_plan_granted"),
        "dry_run_plan_path": payload.get("dry_run_plan_path"),
        "dry_run_plan_sha256": payload.get("dry_run_plan_sha256"),
        "dry_run_plan_type": payload.get("dry_run_plan_type"),
        "dry_run_plan_validated": payload.get("dry_run_plan_validated"),
        "invocation_plan_granted": payload.get("invocation_plan_granted"),
        "usage_receipt_type": payload.get("usage_receipt_type"),
        "usage_receipt_sha256": payload.get("usage_receipt_sha256"),
        "promotion_type": payload.get("promotion_type"),
        "promotion_result_sha256": payload.get("promotion_result_sha256"),
        "source_gate_decision_type": payload.get("source_gate_decision_type"),
        "source_gate_decision_sha256": payload.get("source_gate_decision_sha256"),
        "source_gate_passed": payload.get("source_gate_passed"),
        "registry_promotion_granted": payload.get("registry_promotion_granted"),
        "aggregation_bound": payload.get("aggregation_bound"),
        "regression_bound": payload.get("regression_bound"),
        "local_fixture_only": payload.get("local_fixture_only"),
        "one_usage_receipt_bound": payload.get("one_usage_receipt_bound"),
        "dry_run_plan_bound": payload.get("dry_run_plan_bound"),
        "execution_gate_plan_only": payload.get("execution_gate_plan_only"),
        "human_approval_request_only": payload.get(
            "human_approval_request_only"
        ),
        "local_fixture_reference": payload.get("local_fixture_reference"),
        "local_fixture_reference_scheme": payload.get(
            "local_fixture_reference_scheme"
        ),
        "local_fixture_path": payload.get("local_fixture_path"),
        "local_fixture_sha256": payload.get("local_fixture_sha256"),
        "local_fixture_revalidated": payload.get("local_fixture_revalidated"),
        "local_fixture_exists": payload.get("local_fixture_exists"),
        "local_fixture_regular_file": payload.get("local_fixture_regular_file"),
        "local_fixture_symlink_detected": payload.get(
            "local_fixture_symlink_detected"
        ),
        "local_fixture_under_allowed_root": payload.get(
            "local_fixture_under_allowed_root"
        ),
        "promoted_adapter_id": payload.get("adapter_id"),
        "candidate_id": payload.get("candidate_id"),
        "repo_full_name": payload.get("repo_full_name"),
        "non_production": payload.get("non_production"),
        "production_adapter": payload.get("production_adapter"),
        "rejection_reasons": payload.get("rejection_reasons"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "failure_stage": None if complete else "execution_gate_plan_rejected",
        "error_message": None
        if complete
        else ",".join(str(reason) for reason in payload.get("rejection_reasons", [])),
        "safe_to_retry": not complete,
        "replay_hint": (
            "Fix the #430 dry-run invocation plan result or local fixture metadata and rerun the execution-gate plan node."
        )
        if not complete
        else "Human review is required before any separate execution runner proposal.",
        "required_human_approval": True,
        "required_human_review": True,
        **false_fields,
    }


def _run_local_fixture_human_approval_artifact_node_if_requested(node):
    if (
        node["adapter_id"]
        != _LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ADAPTER_ID
    ):
        return None
    if node["capability"] != _LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CAPABILITY:
        raise ValueError(
            "task graph local-fixture human approval artifact capability is not registered"
        )
    inputs = node["inputs"]
    execution_gate_plan = _required_string_input(
        inputs,
        "execution_gate_plan",
        "local-fixture human approval artifact",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local-fixture human approval artifact",
    )
    approval_artifact_id = _required_string_input(
        inputs,
        "approval_artifact_id",
        "local-fixture human approval artifact",
    )
    reviewer_id = _required_string_input(
        inputs,
        "reviewer_id",
        "local-fixture human approval artifact",
    )
    approval_attestation = _required_string_input(
        inputs,
        "approval_attestation",
        "local-fixture human approval artifact",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "local-fixture human approval artifact",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "local-fixture human approval artifact",
    )

    from kernel.capabilities.local_fixture_human_approval_artifact import (
        LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_REQUIRED_SOURCE_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_local_fixture_human_approval_artifact_launcher,
    )

    result = run_local_fixture_human_approval_artifact_launcher(
        Path(execution_gate_plan),
        Path(output_dir),
        approval_artifact_id,
        reviewer_id,
        approval_attestation,
        project_id=project_id,
        operator_notes=operator_notes,
    )
    payload = result.payload
    complete = bool(result.complete)
    false_fields = {
        field_name: False
        for field_name in LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_REQUIRED_SOURCE_FALSE_FIELDS
    }
    false_fields.update(
        {
            "approval_token_issued": False,
            "execution_token_issued": False,
            "runner_created": False,
            "runnable_job_created": False,
            "adapter_execution_performed": False,
            "playwright_execution_performed": False,
            "browser_open_performed": False,
            "network_access_performed": False,
            "live_website_access_performed": False,
            "autonomous_execution_performed": False,
            "production_promotion_granted": False,
        }
    )
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "local_fixture_human_approval_artifact_complete": complete,
        "local_fixture_human_approval_artifact_path": payload.get(
            "local_fixture_human_approval_artifact_path"
        ),
        "local_fixture_human_approval_artifact_result_path": payload.get(
            "local_fixture_human_approval_artifact_result_path"
        ),
        "local_fixture_human_approval_artifact_manifest_path": payload.get(
            "local_fixture_human_approval_artifact_manifest_path"
        ),
        "local_fixture_human_approval_artifact_summary_path": payload.get(
            "local_fixture_human_approval_artifact_summary_path"
        ),
        "local_fixture_human_approval_artifact_checklist_path": payload.get(
            "local_fixture_human_approval_artifact_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "approval_artifact_id": payload.get("approval_artifact_id"),
        "approval_recorded": payload.get("approval_recorded"),
        "approval_artifact_status": payload.get("approval_artifact_status"),
        "approval_artifact_decision": payload.get("approval_artifact_decision"),
        "source_execution_gate_plan_path": payload.get(
            "source_execution_gate_plan_path"
        ),
        "source_execution_gate_plan_sha256": payload.get(
            "source_execution_gate_plan_sha256"
        ),
        "source_execution_gate_plan_id": payload.get(
            "source_execution_gate_plan_id"
        ),
        "source_gate_plan_type": payload.get("source_gate_plan_type"),
        "source_gate_plan_status": payload.get("source_gate_plan_status"),
        "source_gate_plan_decision": payload.get("source_gate_plan_decision"),
        "promoted_adapter_id": payload.get("adapter_id"),
        "candidate_id": payload.get("candidate_id"),
        "repo_full_name": payload.get("repo_full_name"),
        "local_fixture_sha256": payload.get("local_fixture_sha256"),
        "metadata_only": payload.get("metadata_only"),
        "future_runner_requires_separate_pr": payload.get(
            "future_runner_requires_separate_pr"
        ),
        "future_execution_requires_separate_runner_receipt": payload.get(
            "future_execution_requires_separate_runner_receipt"
        ),
        "future_execution_requires_explicit_local_fixture_runner_gate": payload.get(
            "future_execution_requires_explicit_local_fixture_runner_gate"
        ),
        "rejection_reasons": payload.get("rejection_reasons"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "failure_stage": None if complete else "human_approval_artifact_rejected",
        "error_message": None
        if complete
        else ",".join(str(reason) for reason in payload.get("rejection_reasons", [])),
        "safe_to_retry": not complete,
        "replay_hint": (
            "Fix the #431 execution-gate plan result or approval artifact metadata and rerun the approval artifact node."
        )
        if not complete
        else "A separate runner-contract PR remains required before future local-fixture execution.",
        "required_human_approval": True,
        "required_human_review": True,
        **false_fields,
    }


def _run_local_fixture_playwright_admission_gate_node_if_requested(node):
    if node["adapter_id"] != _LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_ADAPTER_ID:
        return None
    if node["capability"] != _LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_CAPABILITY:
        raise ValueError(
            "task graph local-fixture Playwright admission gate capability is not registered"
        )
    inputs = node["inputs"]
    receipt_dir = _required_string_input(
        inputs,
        "receipt_dir",
        "local-fixture Playwright adapter admission gate",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local-fixture Playwright adapter admission gate",
    )
    gate_id = _required_string_input(
        inputs,
        "gate_id",
        "local-fixture Playwright adapter admission gate",
    )
    review_attestation = _required_string_input(
        inputs,
        "review_attestation",
        "local-fixture Playwright adapter admission gate",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "local-fixture Playwright adapter admission gate",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "local-fixture Playwright adapter admission gate",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "local-fixture Playwright adapter admission gate",
    )
    aggregation_result = _optional_nonempty_string_input(
        inputs,
        "aggregation_result",
        "local-fixture Playwright adapter admission gate",
    )
    require_aggregation_evidence = _optional_bool_input(
        inputs,
        "require_aggregation_evidence",
        False,
    )
    require_regression_evidence = _optional_bool_input(
        inputs,
        "require_regression_evidence",
        False,
    )
    plan_only = _optional_bool_input(inputs, "plan_only", False)

    from kernel.capabilities.local_fixture_playwright_adapter_admission_gate import (
        LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS,
        LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_local_fixture_playwright_adapter_admission_gate_launcher,
    )

    result = run_local_fixture_playwright_adapter_admission_gate_launcher(
        Path(receipt_dir),
        Path(output_dir),
        gate_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        aggregation_result=None
        if aggregation_result is None
        else Path(aggregation_result),
        require_aggregation_evidence=require_aggregation_evidence,
        require_regression_evidence=require_regression_evidence,
        plan_only=plan_only,
    )
    payload = result.payload
    complete = bool(result.complete)
    false_fields = dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS)
    false_fields.update(
        dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS)
    )
    false_fields["local_fixture_admission_granted"] = payload.get(
        "local_fixture_admission_granted",
        False,
    )
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "local_fixture_playwright_adapter_admission_gate_complete": complete,
        "local_fixture_playwright_adapter_admission_gate_plan_path": payload.get(
            "local_fixture_playwright_adapter_admission_gate_plan_path"
        ),
        "local_fixture_playwright_adapter_admission_gate_manifest_path": payload.get(
            "local_fixture_playwright_adapter_admission_gate_manifest_path"
        ),
        "local_fixture_playwright_adapter_admission_gate_summary_path": payload.get(
            "local_fixture_playwright_adapter_admission_gate_summary_path"
        ),
        "local_fixture_playwright_adapter_admission_gate_checklist_path": payload.get(
            "local_fixture_playwright_adapter_admission_gate_checklist_path"
        ),
        "local_fixture_playwright_adapter_admission_gate_decision_path": payload.get(
            "local_fixture_playwright_adapter_admission_gate_decision_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "receipt_dir": payload.get("receipt_dir"),
        "receipt_plan_path": payload.get("receipt_plan_path"),
        "receipt_manifest_path": payload.get("receipt_manifest_path"),
        "receipt_result_path": payload.get("receipt_result_path"),
        "receipt_artifact_index_path": payload.get("receipt_artifact_index_path"),
        "adapter_draft_run_dir": payload.get("adapter_draft_run_dir"),
        "adapter_draft_plan_path": payload.get("adapter_draft_plan_path"),
        "adapter_draft_manifest_path": payload.get("adapter_draft_manifest_path"),
        "adapter_draft_result_path": payload.get("adapter_draft_result_path"),
        "embedded_smoke_dir": payload.get("embedded_smoke_dir"),
        "embedded_smoke_plan_path": payload.get("embedded_smoke_plan_path"),
        "embedded_smoke_manifest_path": payload.get("embedded_smoke_manifest_path"),
        "embedded_smoke_result_path": payload.get("embedded_smoke_result_path"),
        "gate_id": payload.get("gate_id"),
        "receipt_id": payload.get("receipt_id"),
        "adapter_draft_id": payload.get("adapter_draft_id"),
        "candidate_id": payload.get("candidate_id"),
        "repo_full_name": payload.get("repo_full_name"),
        "gate_status": payload.get("gate_status"),
        "gate_decision": payload.get("gate_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "admission_checks_total": payload.get("admission_checks_total"),
        "admission_checks_passed": payload.get("admission_checks_passed"),
        "admission_checks_failed": payload.get("admission_checks_failed"),
        "failed_check_ids": payload.get("failed_check_ids"),
        "receipt_success": payload.get("receipt_success"),
        "adapter_draft_success": payload.get("adapter_draft_success"),
        "embedded_smoke_success": payload.get("embedded_smoke_success"),
        "embedded_fixture_url": payload.get("embedded_fixture_url"),
        "embedded_fixture_url_scheme": payload.get("embedded_fixture_url_scheme"),
        "embedded_non_local_request_count": payload.get(
            "embedded_non_local_request_count"
        ),
        "artifact_hashes_verified": payload.get("artifact_hashes_verified"),
        "aggregation_evidence_supplied": payload.get("aggregation_evidence_supplied"),
        "aggregation_evidence_required": payload.get("aggregation_evidence_required"),
        "aggregation_result_path": payload.get("aggregation_result_path"),
        "aggregation_result_sha256": payload.get("aggregation_result_sha256"),
        "aggregation_result_type": payload.get("aggregation_result_type"),
        "aggregation_result_valid": payload.get("aggregation_result_valid"),
        "aggregation_result_rejection_reasons": payload.get(
            "aggregation_result_rejection_reasons"
        ),
        "aggregation_suite_run_count_evaluated": payload.get(
            "aggregation_suite_run_count_evaluated"
        ),
        "aggregation_suite_run_count_passed": payload.get(
            "aggregation_suite_run_count_passed"
        ),
        "aggregation_suite_run_count_failed": payload.get(
            "aggregation_suite_run_count_failed"
        ),
        "aggregation_suite_run_count_rejected": payload.get(
            "aggregation_suite_run_count_rejected"
        ),
        "aggregation_pass_rate_bps": payload.get("aggregation_pass_rate_bps"),
        "aggregation_flaky_rate_bps": payload.get("aggregation_flaky_rate_bps"),
        "aggregation_regression_detected": payload.get(
            "aggregation_regression_detected"
        ),
        "aggregation_stale_evidence_detected": payload.get(
            "aggregation_stale_evidence_detected"
        ),
        "aggregation_missing_coverage_detected": payload.get(
            "aggregation_missing_coverage_detected"
        ),
        "aggregation_hashes_verified_all": payload.get(
            "aggregation_hashes_verified_all"
        ),
        "aggregation_boundaries_false_all": payload.get(
            "aggregation_boundaries_false_all"
        ),
        "regression_evidence_required": payload.get("regression_evidence_required"),
        "regression_evidence_present": payload.get("regression_evidence_present"),
        "regression_scenario_coverage_complete": payload.get(
            "regression_scenario_coverage_complete"
        ),
        "local_fixture_aggregation_bound_to_admission_gate": payload.get(
            "local_fixture_aggregation_bound_to_admission_gate"
        ),
        "admission_gate_result": payload.get("admission_gate_result"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "error_message": None if complete else payload.get("error_message"),
        "safe_to_retry": not complete,
        "replay_hint": (
            "Fix the receipt evidence and rerun the local-fixture admission gate."
        )
        if not complete
        else "Use the admitted adapter only in the local-fixture lane under human review.",
        "required_human_approval": True,
        "required_human_review": True,
        **false_fields,
    }


def _run_operator_playwright_receipt_node_if_requested(node):
    if node["adapter_id"] != _OPERATOR_PLAYWRIGHT_RECEIPT_ADAPTER_ID:
        return None
    if node["capability"] != _OPERATOR_PLAYWRIGHT_RECEIPT_CAPABILITY:
        raise ValueError(
            "task graph operator-provided Playwright receipt capability is not registered"
        )
    inputs = node["inputs"]
    selection_matrix = _required_string_input(
        inputs,
        "selection_matrix",
        "operator-provided Playwright execution receipt",
    )
    candidate_manifest = _required_string_input(
        inputs,
        "playwright_candidate_manifest",
        "operator-provided Playwright execution receipt",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "operator-provided Playwright execution receipt",
    )
    receipt_id = _required_string_input(
        inputs,
        "receipt_id",
        "operator-provided Playwright execution receipt",
    )
    node_command = _required_string_input(
        inputs,
        "node_command",
        "operator-provided Playwright execution receipt",
    )
    runner_script = _required_string_input(
        inputs,
        "runner_script",
        "operator-provided Playwright execution receipt",
    )
    operator_attestation = _required_string_input(
        inputs,
        "operator_attestation",
        "operator-provided Playwright execution receipt",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "operator-provided Playwright execution receipt",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "operator-provided Playwright execution receipt",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "operator-provided Playwright execution receipt",
    )
    expected_node_version = _optional_nonempty_string_input(
        inputs,
        "expected_node_version",
        "operator-provided Playwright execution receipt",
    )
    expected_playwright_source = _optional_nonempty_string_input(
        inputs,
        "expected_playwright_source",
        "operator-provided Playwright execution receipt",
    )
    plan_only = _optional_bool_input(inputs, "plan_only", False)

    from kernel.capabilities.operator_provided_playwright_execution_receipt import (
        OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_operator_provided_playwright_execution_receipt_launcher,
    )

    result = run_operator_provided_playwright_execution_receipt_launcher(
        Path(selection_matrix),
        Path(candidate_manifest),
        Path(output_dir),
        receipt_id,
        node_command=Path(node_command),
        runner_script=Path(runner_script),
        operator_attestation=operator_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        expected_node_version=expected_node_version,
        expected_playwright_source=expected_playwright_source,
        plan_only=plan_only,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "operator_provided_playwright_execution_receipt_complete": complete,
        "operator_provided_playwright_execution_receipt_plan_path": payload.get(
            "operator_provided_playwright_execution_receipt_plan_path"
        ),
        "operator_provided_playwright_execution_receipt_manifest_path": payload.get(
            "operator_provided_playwright_execution_receipt_manifest_path"
        ),
        "operator_provided_playwright_execution_receipt_summary_path": payload.get(
            "operator_provided_playwright_execution_receipt_summary_path"
        ),
        "operator_provided_playwright_execution_receipt_checklist_path": payload.get(
            "operator_provided_playwright_execution_receipt_checklist_path"
        ),
        "operator_provided_playwright_execution_receipt_result_path": payload.get(
            "operator_provided_playwright_execution_receipt_result_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "adapter_draft_run_dir": payload.get("adapter_draft_run_dir"),
        "adapter_draft_plan_path": payload.get("adapter_draft_plan_path"),
        "adapter_draft_manifest_path": payload.get("adapter_draft_manifest_path"),
        "adapter_draft_summary_path": payload.get("adapter_draft_summary_path"),
        "adapter_draft_checklist_path": payload.get("adapter_draft_checklist_path"),
        "adapter_draft_result_path": payload.get("adapter_draft_result_path"),
        "embedded_smoke_plan_path": payload.get("embedded_smoke_plan_path"),
        "embedded_smoke_manifest_path": payload.get("embedded_smoke_manifest_path"),
        "embedded_smoke_summary_path": payload.get("embedded_smoke_summary_path"),
        "embedded_smoke_checklist_path": payload.get("embedded_smoke_checklist_path"),
        "embedded_smoke_result_path": payload.get("embedded_smoke_result_path"),
        "embedded_smoke_runner_output_path": payload.get(
            "embedded_smoke_runner_output_path"
        ),
        "embedded_smoke_screenshot_path": payload.get("embedded_smoke_screenshot_path"),
        "embedded_fixture_url": payload.get("embedded_fixture_url"),
        "embedded_fixture_index_path": payload.get("embedded_fixture_index_path"),
        "embedded_fixture_app_js_path": payload.get("embedded_fixture_app_js_path"),
        "embedded_fixture_style_css_path": payload.get(
            "embedded_fixture_style_css_path"
        ),
        "embedded_fixture_url_scheme": payload.get("embedded_fixture_url_scheme"),
        "receipt_id": payload.get("receipt_id"),
        "adapter_draft_id": payload.get("adapter_draft_id"),
        "candidate_id": payload.get("candidate_id"),
        "repo_full_name": payload.get("repo_full_name"),
        "executed": payload.get("executed"),
        "success": payload.get("success"),
        "receipt_status": payload.get("receipt_status"),
        "receipt_decision": payload.get("receipt_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "node_command_path": payload.get("node_command_path"),
        "node_command_sha256": payload.get("node_command_sha256"),
        "runner_script_path": payload.get("runner_script_path"),
        "runner_script_sha256": payload.get("runner_script_sha256"),
        "operator_provided_local_executable_supplied": payload.get(
            "operator_provided_local_executable_supplied"
        ),
        "operator_provided_local_runner_supplied": payload.get(
            "operator_provided_local_runner_supplied"
        ),
        "owned_local_smoke_runner_executed": payload.get(
            "owned_local_smoke_runner_executed"
        ),
        "embedded_playwright_local_fixture_smoke_executed": payload.get(
            "embedded_playwright_local_fixture_smoke_executed"
        ),
        "bounded_adapter_draft_wrapper_executed": payload.get(
            "bounded_adapter_draft_wrapper_executed"
        ),
        "operator_provided_receipt_generated": payload.get(
            "operator_provided_receipt_generated"
        ),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "error_message": None if complete else payload.get("error_message"),
        "safe_to_retry": not complete,
        "replay_hint": (
            "Fix operator-provided local fixture receipt inputs or embedded smoke result and rerun this node."
        )
        if not complete
        else "Review the operator-provided execution receipt before any local-only gate.",
        "required_human_approval": True,
        "required_human_review": True,
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS),
    }


def _run_bounded_playwright_adapter_draft_node_if_requested(node):
    if node["adapter_id"] != _BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_ID:
        return None
    if node["capability"] != _BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_CAPABILITY:
        raise ValueError(
            "task graph bounded Playwright adapter draft capability is not registered"
        )
    inputs = node["inputs"]
    selection_matrix = _required_string_input(
        inputs,
        "selection_matrix",
        "bounded Playwright worker adapter draft",
    )
    candidate_manifest = _required_string_input(
        inputs,
        "playwright_candidate_manifest",
        "bounded Playwright worker adapter draft",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "bounded Playwright worker adapter draft",
    )
    adapter_draft_id = _required_string_input(
        inputs,
        "adapter_draft_id",
        "bounded Playwright worker adapter draft",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "bounded Playwright worker adapter draft",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "bounded Playwright worker adapter draft",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "bounded Playwright worker adapter draft",
    )
    node_command = _optional_nonempty_string_input(
        inputs,
        "node_command",
        "bounded Playwright worker adapter draft",
    )
    runner_script = _optional_nonempty_string_input(
        inputs,
        "runner_script",
        "bounded Playwright worker adapter draft",
    )
    execute_local_fixture_smoke = _optional_bool_input(
        inputs,
        "execute_local_fixture_smoke",
        False,
    )

    from kernel.capabilities.bounded_playwright_worker_adapter_draft import (
        BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_bounded_playwright_worker_adapter_draft_launcher,
    )

    result = run_bounded_playwright_worker_adapter_draft_launcher(
        Path(selection_matrix),
        Path(candidate_manifest),
        Path(output_dir),
        adapter_draft_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        node_command=None if node_command is None else Path(node_command),
        runner_script=None if runner_script is None else Path(runner_script),
        execute_local_fixture_smoke=execute_local_fixture_smoke,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "bounded_playwright_worker_adapter_draft_complete": complete,
        "bounded_playwright_worker_adapter_draft_plan_path": payload.get(
            "bounded_playwright_worker_adapter_draft_plan_path"
        ),
        "bounded_playwright_worker_adapter_draft_manifest_path": payload.get(
            "bounded_playwright_worker_adapter_draft_manifest_path"
        ),
        "bounded_playwright_worker_adapter_draft_summary_path": payload.get(
            "bounded_playwright_worker_adapter_draft_summary_path"
        ),
        "bounded_playwright_worker_adapter_draft_checklist_path": payload.get(
            "bounded_playwright_worker_adapter_draft_checklist_path"
        ),
        "bounded_playwright_worker_adapter_draft_result_path": payload.get(
            "bounded_playwright_worker_adapter_draft_result_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "embedded_smoke_dir": payload.get("embedded_smoke_dir"),
        "embedded_smoke_plan_path": payload.get("embedded_smoke_plan_path"),
        "embedded_smoke_manifest_path": payload.get("embedded_smoke_manifest_path"),
        "embedded_smoke_summary_path": payload.get("embedded_smoke_summary_path"),
        "embedded_smoke_checklist_path": payload.get("embedded_smoke_checklist_path"),
        "embedded_smoke_result_path": payload.get("embedded_smoke_result_path"),
        "embedded_smoke_runner_output_path": payload.get(
            "embedded_smoke_runner_output_path"
        ),
        "embedded_smoke_screenshot_path": payload.get("embedded_smoke_screenshot_path"),
        "embedded_fixture_dir": payload.get("embedded_fixture_dir"),
        "embedded_fixture_index_path": payload.get("embedded_fixture_index_path"),
        "embedded_fixture_app_js_path": payload.get("embedded_fixture_app_js_path"),
        "embedded_fixture_style_css_path": payload.get(
            "embedded_fixture_style_css_path"
        ),
        "embedded_fixture_url": payload.get("embedded_fixture_url"),
        "embedded_fixture_url_scheme": payload.get("embedded_fixture_url_scheme"),
        "adapter_draft_id": payload.get("adapter_draft_id"),
        "candidate_id": payload.get("candidate_id"),
        "repo_full_name": payload.get("repo_full_name"),
        "executed": payload.get("executed"),
        "success": payload.get("success"),
        "worker_adapter_status": payload.get("worker_adapter_status"),
        "adapter_draft_decision": payload.get("adapter_draft_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "owned_local_smoke_runner_executed": payload.get(
            "owned_local_smoke_runner_executed"
        ),
        "embedded_playwright_local_fixture_smoke_executed": payload.get(
            "embedded_playwright_local_fixture_smoke_executed"
        ),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "error_message": None if complete else payload.get("error_message"),
        "safe_to_retry": not complete,
        "replay_hint": (
            "Fix bounded Playwright adapter draft inputs or embedded smoke "
            "result and rerun this node."
        )
        if not complete
        else "Review the adapter draft before any admission or runtime milestone.",
        "required_human_approval": True,
        "required_human_review": True,
        **dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS),
    }


def _run_playwright_smoke_node_if_requested(node):
    if node["adapter_id"] != _PLAYWRIGHT_SMOKE_ADAPTER_ID:
        return None
    if node["capability"] != _PLAYWRIGHT_SMOKE_CAPABILITY:
        raise ValueError("task graph playwright smoke capability is not registered")
    inputs = node["inputs"]
    selection_matrix = _required_string_input(
        inputs,
        "selection_matrix",
        "playwright local fixture smoke",
    )
    candidate_manifest = _required_string_input(
        inputs,
        "playwright_candidate_manifest",
        "playwright local fixture smoke",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "playwright local fixture smoke",
    )
    smoke_id = _required_string_input(
        inputs,
        "smoke_id",
        "playwright local fixture smoke",
    )
    project_id = _optional_nonempty_string_input(
        inputs,
        "project_id",
        "playwright local fixture smoke",
    )
    reviewer_id = _optional_nonempty_string_input(
        inputs,
        "reviewer_id",
        "playwright local fixture smoke",
    )
    operator_notes = _optional_nonempty_string_input(
        inputs,
        "operator_notes",
        "playwright local fixture smoke",
    )
    node_command = _optional_nonempty_string_input(
        inputs,
        "node_command",
        "playwright local fixture smoke",
    )
    runner_script = _optional_nonempty_string_input(
        inputs,
        "runner_script",
        "playwright local fixture smoke",
    )
    execute_local_fixture_smoke = _optional_bool_input(
        inputs,
        "execute_local_fixture_smoke",
        False,
    )

    from kernel.capabilities.playwright_local_fixture_sandbox_smoke import (
        PLAYWRIGHT_BOUNDARY_FALSE_FIELDS,
    )
    from kernel.personal_ai.local_launcher import (
        run_playwright_local_fixture_sandbox_smoke_launcher,
    )

    result = run_playwright_local_fixture_sandbox_smoke_launcher(
        Path(selection_matrix),
        Path(candidate_manifest),
        Path(output_dir),
        smoke_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        node_command=None if node_command is None else Path(node_command),
        runner_script=None if runner_script is None else Path(runner_script),
        execute_local_fixture_smoke=execute_local_fixture_smoke,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "playwright_local_fixture_sandbox_smoke_complete": complete,
        "playwright_local_fixture_sandbox_smoke_plan_path": payload.get(
            "playwright_local_fixture_sandbox_smoke_plan_path"
        ),
        "playwright_local_fixture_sandbox_smoke_manifest_path": payload.get(
            "playwright_local_fixture_sandbox_smoke_manifest_path"
        ),
        "playwright_local_fixture_sandbox_smoke_summary_path": payload.get(
            "playwright_local_fixture_sandbox_smoke_summary_path"
        ),
        "playwright_local_fixture_sandbox_smoke_checklist_path": payload.get(
            "playwright_local_fixture_sandbox_smoke_checklist_path"
        ),
        "playwright_local_fixture_sandbox_smoke_result_path": payload.get(
            "playwright_local_fixture_sandbox_smoke_result_path"
        ),
        "playwright_local_fixture_sandbox_smoke_runner_output_path": payload.get(
            "playwright_local_fixture_sandbox_smoke_runner_output_path"
        ),
        "playwright_local_fixture_sandbox_smoke_screenshot_path": payload.get(
            "playwright_local_fixture_sandbox_smoke_screenshot_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "fixture_dir": payload.get("fixture_dir"),
        "fixture_index_path": payload.get("fixture_index_path"),
        "fixture_app_js_path": payload.get("fixture_app_js_path"),
        "fixture_style_css_path": payload.get("fixture_style_css_path"),
        "fixture_url": payload.get("fixture_url"),
        "fixture_url_scheme": payload.get("fixture_url_scheme"),
        "smoke_id": payload.get("smoke_id"),
        "project_id": payload.get("project_id"),
        "reviewer_id": payload.get("reviewer_id"),
        "candidate_id": payload.get("candidate_id"),
        "repo_full_name": payload.get("repo_full_name"),
        "intended_use": payload.get("intended_use"),
        "executed": payload.get("executed"),
        "success": payload.get("success"),
        "bounded_local_fixture_execution_only": True,
        "owned_local_smoke_runner_executed": payload.get(
            "owned_local_smoke_runner_executed"
        ),
        "smoke_status": payload.get("smoke_status"),
        "smoke_decision": payload.get("smoke_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "error_message": None if complete else payload.get("error_message"),
        "safe_to_retry": not complete,
        "replay_hint": "Fix Playwright local fixture smoke preflight or runner output and rerun this node."
        if not complete
        else "Review the local fixture smoke result before any adapter draft.",
        "required_human_approval": True,
        "required_human_review": True,
        **dict(PLAYWRIGHT_BOUNDARY_FALSE_FIELDS),
    }


def _run_local_asset_node_if_requested(node):
    if node["adapter_id"] != _LOCAL_ASSET_ADAPTER_ID:
        return None
    if node["capability"] != _LOCAL_ASSET_CAPABILITY:
        if node["capability"] == _LOCAL_ASSET_SMOKE_READINESS_CAPABILITY:
            return _run_local_asset_smoke_readiness_node(node)
        if node["capability"] == _LOCAL_ASSET_HUMAN_SMOKE_CAPABILITY:
            return _run_local_asset_human_smoke_node(node)
        if node["capability"] == _LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_CAPABILITY:
            return _run_local_asset_bounded_smoke_iteration_node(node)
        if node["capability"] == _LOCAL_ASSET_SMOKE_REVIEW_PACKET_CAPABILITY:
            return _run_local_asset_smoke_review_packet_node(node)
        if (
            node["capability"]
            == _LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_CAPABILITY
        ):
            return _run_local_asset_smoke_iteration_review_packet_node(node)
        if node["capability"] == _LOCAL_ASSET_SMOKE_PROMOTION_GATE_CAPABILITY:
            return _run_local_asset_smoke_promotion_gate_node(node)
        if node["capability"] == _LOCAL_ASSET_ITERATION_PROMOTION_GATE_CAPABILITY:
            return _run_local_asset_iteration_promotion_gate_node(node)
        if node["capability"] == _LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_CAPABILITY:
            return _run_local_asset_bounded_smoke_cycle_contract_node(node)
        if (
            node["capability"]
            == _LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CAPABILITY
        ):
            return _run_local_asset_bounded_smoke_cycle_human_review_node(node)
        if (
            node["capability"]
            == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CAPABILITY
        ):
            return _run_local_asset_next_bounded_smoke_iteration_admission_node(node)
        if (
            node["capability"]
            == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CAPABILITY
        ):
            return _run_local_asset_next_bounded_smoke_iteration_execution_request_node(
                node
            )
        if (
            node["capability"]
            == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CAPABILITY
        ):
            return _run_local_asset_next_bounded_smoke_iteration_runner_admission_node(
                node
            )
        if (
            node["capability"]
            == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CAPABILITY
        ):
            return _run_local_asset_next_bounded_smoke_iteration_runner_node(node)
        if (
            node["capability"]
            == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CAPABILITY
        ):
            return (
                _run_local_asset_next_bounded_smoke_iteration_run_review_packet_node(
                    node
                )
            )
        if (
            node["capability"]
            == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CAPABILITY
        ):
            return (
                _run_local_asset_next_bounded_smoke_iteration_run_promotion_gate_node(
                    node
                )
            )
        if (
            node["capability"]
            == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_FROM_RUN_PROMOTION_GATE_CAPABILITY
        ):
            return (
                _run_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_node(
                    node
                )
            )
        if (
            node["capability"]
            == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_HUMAN_REVIEW_FROM_RUN_PROMOTION_GATE_CAPABILITY
        ):
            return (
                _run_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_node(
                    node
                )
            )
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


def _run_local_asset_human_smoke_node(node):
    inputs = node["inputs"]
    candidate_input_dir = _required_string_input(
        inputs,
        "candidate_input_dir",
        "local asset human smoke",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local asset human smoke",
    )
    readiness_report = _required_string_input(
        inputs,
        "readiness_report",
        "local asset human smoke",
    )
    human_approval_id = _required_string_input(
        inputs,
        "human_approval_id",
        "local asset human smoke",
    )
    human_approval_phrase = _required_string_input(
        inputs,
        "human_approval_phrase",
        "local asset human smoke",
    )
    recursive = _optional_bool_input(inputs, "recursive", False)
    include_hidden = _optional_bool_input(inputs, "include_hidden", False)
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError("task graph local asset human smoke project_id is malformed")
    max_smoke_files = _optional_int_input(
        inputs,
        "max_smoke_files",
        100,
        "local asset human smoke",
    )
    max_smoke_bytes = _optional_int_input(
        inputs,
        "max_smoke_bytes",
        2000000000,
        "local asset human smoke",
    )
    max_smoke_depth = _optional_int_input(
        inputs,
        "max_smoke_depth",
        8,
        "local asset human smoke",
    )
    previous_scan_output_dir = inputs.get("previous_scan_output_dir")
    if previous_scan_output_dir is not None and (
        not isinstance(previous_scan_output_dir, str) or not previous_scan_output_dir
    ):
        raise ValueError(
            "task graph local asset human smoke previous_scan_output_dir is malformed"
        )

    from kernel.personal_ai.local_launcher import run_local_asset_human_smoke_launcher

    result = run_local_asset_human_smoke_launcher(
        Path(candidate_input_dir),
        Path(output_dir),
        Path(readiness_report),
        human_approval_id=human_approval_id,
        human_approval_phrase=human_approval_phrase,
        recursive=recursive,
        include_hidden=include_hidden,
        project_id=project_id,
        max_smoke_files=max_smoke_files,
        max_smoke_bytes=max_smoke_bytes,
        max_smoke_depth=max_smoke_depth,
        previous_scan_output_dir=None
        if previous_scan_output_dir is None
        else Path(previous_scan_output_dir),
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "local_asset_human_smoke_complete": complete,
        "local_asset_human_smoke_approval_path": payload.get(
            "local_asset_human_smoke_approval_path"
        ),
        "local_asset_human_smoke_admission_receipt_path": payload.get(
            "local_asset_human_smoke_admission_receipt_path"
        ),
        "local_asset_human_smoke_run_summary_path": payload.get(
            "local_asset_human_smoke_run_summary_path"
        ),
        "scan_output_dir": payload.get("scan_output_dir"),
        "control_output_dir": payload.get("control_output_dir"),
        "readiness_report_path": payload.get("readiness_report_path"),
        "readiness_status": payload.get("readiness_status"),
        "readiness_decision": payload.get("readiness_decision"),
        "admitted": payload.get("admitted"),
        "scan_launcher_invoked": payload.get("scan_launcher_invoked"),
        "scan_complete": payload.get("scan_complete"),
        "bounded_smoke_run_performed": payload.get(
            "bounded_smoke_run_performed"
        ),
        "production_scan_performed": False,
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "scan_artifact_index_path": payload.get("scan_artifact_index_path"),
        "scan_artifact_index_manifest_path": payload.get(
            "scan_artifact_index_manifest_path"
        ),
        "asset_scan_run_receipt_path": payload.get("asset_scan_run_receipt_path"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "safe_to_retry": payload.get("safe_to_retry"),
        "replay_hint": payload.get("replay_hint"),
        "required_human_approval": True,
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


def _run_local_asset_bounded_smoke_iteration_node(node):
    inputs = node["inputs"]
    promotion_output_dir = _required_string_input(
        inputs,
        "promotion_output_dir",
        "local asset bounded smoke iteration",
    )
    candidate_input_dir = _required_string_input(
        inputs,
        "candidate_input_dir",
        "local asset bounded smoke iteration",
    )
    readiness_report = _required_string_input(
        inputs,
        "readiness_report",
        "local asset bounded smoke iteration",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local asset bounded smoke iteration",
    )
    human_signoff_id = _required_string_input(
        inputs,
        "human_signoff_id",
        "local asset bounded smoke iteration",
    )
    human_signoff_phrase = _required_string_input(
        inputs,
        "human_signoff_phrase",
        "local asset bounded smoke iteration",
    )
    recursive = _optional_bool_input(inputs, "recursive", False)
    include_hidden = _optional_bool_input(inputs, "include_hidden", False)
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError(
            "task graph local asset bounded smoke iteration project_id is malformed"
        )
    max_smoke_files = _optional_int_input(
        inputs,
        "max_smoke_files",
        100,
        "local asset bounded smoke iteration",
    )
    max_smoke_bytes = _optional_int_input(
        inputs,
        "max_smoke_bytes",
        1073741824,
        "local asset bounded smoke iteration",
    )
    max_smoke_depth = _optional_int_input(
        inputs,
        "max_smoke_depth",
        12,
        "local asset bounded smoke iteration",
    )
    previous_scan_output_dir = inputs.get("previous_scan_output_dir")
    if previous_scan_output_dir is not None and (
        not isinstance(previous_scan_output_dir, str) or not previous_scan_output_dir
    ):
        raise ValueError(
            "task graph local asset bounded smoke iteration "
            "previous_scan_output_dir is malformed"
        )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_bounded_smoke_iteration_launcher,
    )

    result = run_local_asset_bounded_smoke_iteration_launcher(
        Path(promotion_output_dir),
        Path(candidate_input_dir),
        Path(readiness_report),
        Path(output_dir),
        human_signoff_id=human_signoff_id,
        human_signoff_phrase=human_signoff_phrase,
        recursive=recursive,
        include_hidden=include_hidden,
        project_id=project_id,
        max_smoke_files=max_smoke_files,
        max_smoke_bytes=max_smoke_bytes,
        max_smoke_depth=max_smoke_depth,
        previous_scan_output_dir=None
        if previous_scan_output_dir is None
        else Path(previous_scan_output_dir),
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "promotion_output_dir": payload.get("promotion_output_dir"),
        "candidate_input_dir": payload.get("candidate_input_dir"),
        "readiness_report": payload.get("readiness_report"),
        "project_id": payload.get("project_id"),
        "local_asset_bounded_smoke_iteration_complete": complete,
        "local_asset_bounded_smoke_iteration_result_path": payload.get(
            "local_asset_bounded_smoke_iteration_result_path"
        ),
        "local_asset_bounded_smoke_iteration_manifest_path": payload.get(
            "local_asset_bounded_smoke_iteration_manifest_path"
        ),
        "local_asset_bounded_smoke_iteration_summary_path": payload.get(
            "local_asset_bounded_smoke_iteration_summary_path"
        ),
        "local_asset_bounded_smoke_iteration_human_review_checklist_path": (
            payload.get(
                "local_asset_bounded_smoke_iteration_human_review_checklist_path"
            )
        ),
        "local_asset_bounded_smoke_iteration_signoff_path": payload.get(
            "local_asset_bounded_smoke_iteration_signoff_path"
        ),
        "local_asset_bounded_smoke_iteration_admission_path": payload.get(
            "local_asset_bounded_smoke_iteration_admission_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "iteration_status": payload.get("iteration_status"),
        "iteration_decision": payload.get("iteration_decision"),
        "bounded_smoke_iteration_performed": payload.get(
            "bounded_smoke_iteration_performed"
        ),
        "bounded_smoke_iteration_allowed": payload.get(
            "bounded_smoke_iteration_allowed"
        ),
        "promotion_gate_status": payload.get("promotion_gate_status"),
        "promotion_decision": payload.get("promotion_decision"),
        "human_signoff_valid": payload.get("human_signoff_valid"),
        "smoke_launcher_invoked": payload.get("smoke_launcher_invoked"),
        "smoke_run_complete": payload.get("smoke_run_complete"),
        "scan_complete": payload.get("scan_complete"),
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
        "automatic_approval_performed": False,
        "watcher_daemon_started": False,
        "raw_candidate_content_read_outside_scan_runtime": False,
        "candidate_file_hashing_outside_scan_runtime": False,
        "input_mutation_performed": False,
        "promotion_output_mutation_performed": False,
        "review_output_mutation_performed": False,
        "smoke_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "required_human_approval": True,
        "failure_stage": None if complete else payload.get("failure_stage"),
    }


def _run_local_asset_smoke_review_packet_node(node):
    inputs = node["inputs"]
    smoke_output_dir = _required_string_input(
        inputs,
        "smoke_output_dir",
        "local asset smoke review packet",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local asset smoke review packet",
    )
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError(
            "task graph local asset smoke review packet project_id is malformed"
        )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_smoke_review_packet_launcher,
    )

    result = run_local_asset_smoke_review_packet_launcher(
        Path(smoke_output_dir),
        Path(output_dir),
        project_id=project_id,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "smoke_output_dir": payload.get("smoke_output_dir"),
        "project_id": payload.get("project_id"),
        "local_asset_smoke_review_packet_complete": complete,
        "local_asset_smoke_review_packet_path": payload.get(
            "local_asset_smoke_review_packet_path"
        ),
        "local_asset_smoke_review_packet_manifest_path": payload.get(
            "local_asset_smoke_review_packet_manifest_path"
        ),
        "local_asset_smoke_review_summary_path": payload.get(
            "local_asset_smoke_review_summary_path"
        ),
        "local_asset_smoke_human_decision_checklist_path": payload.get(
            "local_asset_smoke_human_decision_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "review_packet_status": payload.get("review_packet_status"),
        "recommended_human_decision": payload.get("recommended_human_decision"),
        "smoke_run_complete": payload.get("smoke_run_complete"),
        "smoke_run_admitted": payload.get("smoke_run_admitted"),
        "scan_complete": payload.get("scan_complete"),
        "readiness_status": payload.get("readiness_status"),
        "readiness_decision": payload.get("readiness_decision"),
        "duplicate_group_count": payload.get("duplicate_group_count"),
        "quarantined_path_count": payload.get("quarantined_path_count"),
        "incremental_plan_mode": payload.get("incremental_plan_mode"),
        "changed_asset_count": payload.get("changed_asset_count"),
        "new_asset_count": payload.get("new_asset_count"),
        "missing_asset_count": payload.get("missing_asset_count"),
        "suspicious_change_count": payload.get("suspicious_change_count"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "scan_performed": False,
        "readiness_run_performed": False,
        "raw_candidate_content_read": False,
        "candidate_file_hashing_performed": False,
        "input_mutation_performed": False,
        "smoke_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
    }


def _run_local_asset_smoke_iteration_review_packet_node(node):
    inputs = node["inputs"]
    iteration_output_dir = _required_string_input(
        inputs,
        "iteration_output_dir",
        "local asset smoke iteration review packet",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local asset smoke iteration review packet",
    )
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError(
            "task graph local asset smoke iteration review packet "
            "project_id is malformed"
        )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_smoke_iteration_review_packet_launcher,
    )

    result = run_local_asset_smoke_iteration_review_packet_launcher(
        Path(iteration_output_dir),
        Path(output_dir),
        project_id=project_id,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "iteration_output_dir": payload.get("iteration_output_dir"),
        "project_id": payload.get("project_id"),
        "local_asset_smoke_iteration_review_packet_complete": complete,
        "local_asset_smoke_iteration_review_packet_path": payload.get(
            "local_asset_smoke_iteration_review_packet_path"
        ),
        "local_asset_smoke_iteration_review_packet_manifest_path": payload.get(
            "local_asset_smoke_iteration_review_packet_manifest_path"
        ),
        "local_asset_smoke_iteration_review_summary_path": payload.get(
            "local_asset_smoke_iteration_review_summary_path"
        ),
        "local_asset_smoke_iteration_human_decision_checklist_path": payload.get(
            "local_asset_smoke_iteration_human_decision_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "iteration_review_status": payload.get("iteration_review_status"),
        "recommended_human_decision": payload.get("recommended_human_decision"),
        "iteration_status": payload.get("iteration_status"),
        "bounded_smoke_iteration_performed": payload.get(
            "bounded_smoke_iteration_performed"
        ),
        "smoke_run_complete": payload.get("smoke_run_complete"),
        "scan_complete": payload.get("scan_complete"),
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "production_scan_performed": False,
        "raw_candidate_content_read": False,
        "candidate_file_hashing_performed": False,
        "scan_performed": False,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "bounded_smoke_iteration_performed_by_review_packet": False,
        "promotion_gate_run_performed": False,
        "input_mutation_performed": False,
        "iteration_output_mutation_performed": False,
        "smoke_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "required_human_approval": True,
        "failure_stage": None if complete else payload.get("failure_stage"),
    }


def _run_local_asset_smoke_promotion_gate_node(node):
    inputs = node["inputs"]
    review_output_dir = _required_string_input(
        inputs,
        "review_output_dir",
        "local asset smoke promotion gate",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local asset smoke promotion gate",
    )
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError(
            "task graph local asset smoke promotion gate project_id is malformed"
        )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_smoke_promotion_gate_launcher,
    )

    result = run_local_asset_smoke_promotion_gate_launcher(
        Path(review_output_dir),
        Path(output_dir),
        project_id=project_id,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "review_output_dir": payload.get("review_output_dir"),
        "project_id": payload.get("project_id"),
        "local_asset_smoke_promotion_gate_complete": complete,
        "local_asset_smoke_promotion_decision_path": payload.get(
            "local_asset_smoke_promotion_decision_path"
        ),
        "local_asset_smoke_promotion_gate_manifest_path": payload.get(
            "local_asset_smoke_promotion_gate_manifest_path"
        ),
        "local_asset_smoke_promotion_summary_path": payload.get(
            "local_asset_smoke_promotion_summary_path"
        ),
        "local_asset_smoke_promotion_human_signoff_checklist_path": payload.get(
            "local_asset_smoke_promotion_human_signoff_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "promotion_gate_status": payload.get("promotion_gate_status"),
        "promotion_decision": payload.get("promotion_decision"),
        "next_bounded_smoke_iteration_allowed": payload.get(
            "next_bounded_smoke_iteration_allowed"
        ),
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "review_packet_status": payload.get("review_packet_status"),
        "review_recommended_human_decision": payload.get(
            "review_recommended_human_decision"
        ),
        "promotion_blocker_count": payload.get("promotion_blocker_count"),
        "promotion_blockers": payload.get("promotion_blockers"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "scan_performed": False,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "review_packet_mutation_performed": False,
        "smoke_output_mutation_performed": False,
        "raw_candidate_content_read": False,
        "candidate_file_hashing_performed": False,
        "input_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
    }


def _run_local_asset_iteration_promotion_gate_node(node):
    inputs = node["inputs"]
    iteration_review_output_dir = _required_string_input(
        inputs,
        "iteration_review_output_dir",
        "local asset iteration promotion gate",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local asset iteration promotion gate",
    )
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError(
            "task graph local asset iteration promotion gate "
            "project_id is malformed"
        )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_iteration_promotion_gate_launcher,
    )

    result = run_local_asset_iteration_promotion_gate_launcher(
        Path(iteration_review_output_dir),
        Path(output_dir),
        project_id=project_id,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "iteration_review_output_dir": payload.get("iteration_review_output_dir"),
        "project_id": payload.get("project_id"),
        "local_asset_iteration_promotion_gate_complete": complete,
        "local_asset_iteration_promotion_decision_path": payload.get(
            "local_asset_iteration_promotion_decision_path"
        ),
        "local_asset_iteration_promotion_gate_manifest_path": payload.get(
            "local_asset_iteration_promotion_gate_manifest_path"
        ),
        "local_asset_iteration_promotion_summary_path": payload.get(
            "local_asset_iteration_promotion_summary_path"
        ),
        "local_asset_iteration_promotion_human_signoff_checklist_path": payload.get(
            "local_asset_iteration_promotion_human_signoff_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "iteration_promotion_gate_status": payload.get(
            "iteration_promotion_gate_status"
        ),
        "iteration_promotion_decision": payload.get(
            "iteration_promotion_decision"
        ),
        "next_bounded_smoke_iteration_allowed": payload.get(
            "next_bounded_smoke_iteration_allowed"
        ),
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
        "iteration_review_status": payload.get("iteration_review_status"),
        "iteration_review_recommended_human_decision": payload.get(
            "iteration_review_recommended_human_decision"
        ),
        "iteration_promotion_blocker_count": payload.get(
            "iteration_promotion_blocker_count"
        ),
        "iteration_promotion_blockers": payload.get(
            "iteration_promotion_blockers"
        ),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "scan_performed": False,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "bounded_smoke_iteration_performed_by_gate": False,
        "iteration_review_packet_run_performed": False,
        "iteration_review_output_mutation_performed": False,
        "iteration_output_mutation_performed": False,
        "delegated_smoke_output_mutation_performed": False,
        "raw_candidate_content_read": False,
        "candidate_file_hashing_performed": False,
        "input_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
    }


def _run_local_asset_bounded_smoke_cycle_contract_node(node):
    inputs = node["inputs"]
    readiness_output_dir = _required_string_input(
        inputs,
        "readiness_output_dir",
        "local asset bounded smoke cycle contract",
    )
    smoke_output_dir = _required_string_input(
        inputs,
        "smoke_output_dir",
        "local asset bounded smoke cycle contract",
    )
    smoke_review_output_dir = _required_string_input(
        inputs,
        "smoke_review_output_dir",
        "local asset bounded smoke cycle contract",
    )
    smoke_promotion_output_dir = _required_string_input(
        inputs,
        "smoke_promotion_output_dir",
        "local asset bounded smoke cycle contract",
    )
    iteration_output_dir = _required_string_input(
        inputs,
        "iteration_output_dir",
        "local asset bounded smoke cycle contract",
    )
    iteration_review_output_dir = _required_string_input(
        inputs,
        "iteration_review_output_dir",
        "local asset bounded smoke cycle contract",
    )
    iteration_promotion_output_dir = _required_string_input(
        inputs,
        "iteration_promotion_output_dir",
        "local asset bounded smoke cycle contract",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local asset bounded smoke cycle contract",
    )
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError(
            "task graph local asset bounded smoke cycle contract "
            "project_id is malformed"
        )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_bounded_smoke_cycle_contract_launcher,
    )

    result = run_local_asset_bounded_smoke_cycle_contract_launcher(
        Path(readiness_output_dir),
        Path(smoke_output_dir),
        Path(smoke_review_output_dir),
        Path(smoke_promotion_output_dir),
        Path(iteration_output_dir),
        Path(iteration_review_output_dir),
        Path(iteration_promotion_output_dir),
        Path(output_dir),
        project_id=project_id,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "readiness_output_dir": payload.get("readiness_output_dir"),
        "smoke_output_dir": payload.get("smoke_output_dir"),
        "smoke_review_output_dir": payload.get("smoke_review_output_dir"),
        "smoke_promotion_output_dir": payload.get("smoke_promotion_output_dir"),
        "iteration_output_dir": payload.get("iteration_output_dir"),
        "iteration_review_output_dir": payload.get("iteration_review_output_dir"),
        "iteration_promotion_output_dir": payload.get(
            "iteration_promotion_output_dir"
        ),
        "project_id": payload.get("project_id"),
        "local_asset_bounded_smoke_cycle_contract_complete": complete,
        "local_asset_bounded_smoke_cycle_contract_path": payload.get(
            "local_asset_bounded_smoke_cycle_contract_path"
        ),
        "local_asset_bounded_smoke_cycle_contract_manifest_path": payload.get(
            "local_asset_bounded_smoke_cycle_contract_manifest_path"
        ),
        "local_asset_bounded_smoke_cycle_summary_path": payload.get(
            "local_asset_bounded_smoke_cycle_summary_path"
        ),
        "local_asset_bounded_smoke_cycle_human_review_checklist_path": payload.get(
            "local_asset_bounded_smoke_cycle_human_review_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "cycle_contract_status": payload.get("cycle_contract_status"),
        "cycle_contract_decision": payload.get("cycle_contract_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "allowed_after_human_review": payload.get("allowed_after_human_review"),
        "disallowed_actions": payload.get("disallowed_actions"),
        "cycle_blocker_count": payload.get("cycle_blocker_count"),
        "cycle_blockers": payload.get("cycle_blockers"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "required_human_review": True,
        "scan_performed": False,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "smoke_review_packet_run_performed": False,
        "smoke_promotion_gate_run_performed": False,
        "bounded_smoke_iteration_performed_by_contract": False,
        "iteration_review_packet_run_performed": False,
        "iteration_promotion_gate_run_performed": False,
        "raw_candidate_content_read": False,
        "candidate_file_hashing_performed": False,
        "input_mutation_performed": False,
        "upstream_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
    }


def _run_local_asset_bounded_smoke_cycle_human_review_node(node):
    inputs = node["inputs"]
    cycle_contract_output_dir = _required_string_input(
        inputs,
        "cycle_contract_output_dir",
        "local asset bounded smoke cycle human review",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local asset bounded smoke cycle human review",
    )
    human_review_id = _required_string_input(
        inputs,
        "human_review_id",
        "local asset bounded smoke cycle human review",
    )
    human_reviewer_id = _required_string_input(
        inputs,
        "human_reviewer_id",
        "local asset bounded smoke cycle human review",
    )
    human_decision = _required_string_input(
        inputs,
        "human_decision",
        "local asset bounded smoke cycle human review",
    )
    human_signoff_phrase = _required_string_input(
        inputs,
        "human_signoff_phrase",
        "local asset bounded smoke cycle human review",
    )
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError(
            "task graph local asset bounded smoke cycle human review "
            "project_id is malformed"
        )
    human_review_notes = inputs.get("human_review_notes")
    if human_review_notes is not None and not isinstance(human_review_notes, str):
        raise ValueError(
            "task graph local asset bounded smoke cycle human review "
            "human_review_notes is malformed"
        )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_bounded_smoke_cycle_human_review_launcher,
    )

    result = run_local_asset_bounded_smoke_cycle_human_review_launcher(
        Path(cycle_contract_output_dir),
        Path(output_dir),
        human_review_id=human_review_id,
        human_reviewer_id=human_reviewer_id,
        human_decision=human_decision,
        human_signoff_phrase=human_signoff_phrase,
        project_id=project_id,
        human_review_notes=human_review_notes,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "cycle_contract_output_dir": payload.get("cycle_contract_output_dir"),
        "project_id": payload.get("project_id"),
        "human_review_id": payload.get("human_review_id"),
        "human_reviewer_id": payload.get("human_reviewer_id"),
        "human_decision": payload.get("human_decision"),
        "local_asset_bounded_smoke_cycle_human_review_complete": complete,
        "local_asset_bounded_smoke_cycle_human_review_decision_path": payload.get(
            "local_asset_bounded_smoke_cycle_human_review_decision_path"
        ),
        "local_asset_bounded_smoke_cycle_human_review_manifest_path": payload.get(
            "local_asset_bounded_smoke_cycle_human_review_manifest_path"
        ),
        "local_asset_bounded_smoke_cycle_human_review_summary_path": payload.get(
            "local_asset_bounded_smoke_cycle_human_review_summary_path"
        ),
        "local_asset_bounded_smoke_cycle_human_review_checklist_path": payload.get(
            "local_asset_bounded_smoke_cycle_human_review_checklist_path"
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "human_review_status": payload.get("human_review_status"),
        "human_review_decision": payload.get("human_review_decision"),
        "next_bounded_smoke_iteration_prepare_allowed": payload.get(
            "next_bounded_smoke_iteration_prepare_allowed"
        ),
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_allowed_action": payload.get("next_allowed_action"),
        "disallowed_actions": payload.get("disallowed_actions"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "required_human_review": True,
        "scan_performed": False,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "smoke_review_packet_run_performed": False,
        "smoke_promotion_gate_run_performed": False,
        "bounded_smoke_iteration_performed_by_review": False,
        "iteration_review_packet_run_performed": False,
        "iteration_promotion_gate_run_performed": False,
        "cycle_contract_run_performed": False,
        "raw_candidate_content_read": False,
        "candidate_file_hashing_performed": False,
        "input_mutation_performed": False,
        "upstream_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
    }


def _run_local_asset_next_bounded_smoke_iteration_admission_node(node):
    inputs = node["inputs"]
    cycle_human_review_output_dir = _required_string_input(
        inputs,
        "cycle_human_review_output_dir",
        "local asset next bounded smoke iteration admission",
    )
    output_dir = _required_string_input(
        inputs,
        "output_dir",
        "local asset next bounded smoke iteration admission",
    )
    project_id = inputs.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not project_id
    ):
        raise ValueError(
            "task graph local asset next bounded smoke iteration admission "
            "project_id is malformed"
        )
    requested_next_iteration_id = inputs.get("requested_next_iteration_id")
    if requested_next_iteration_id is not None and (
        not isinstance(requested_next_iteration_id, str)
        or not requested_next_iteration_id
    ):
        raise ValueError(
            "task graph local asset next bounded smoke iteration admission "
            "requested_next_iteration_id is malformed"
        )
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        raise ValueError(
            "task graph local asset next bounded smoke iteration admission "
            "operator_notes is malformed"
        )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_next_bounded_smoke_iteration_admission_launcher,
    )

    result = run_local_asset_next_bounded_smoke_iteration_admission_launcher(
        Path(cycle_human_review_output_dir),
        Path(output_dir),
        project_id=project_id,
        requested_next_iteration_id=requested_next_iteration_id,
        operator_notes=operator_notes,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "cycle_human_review_output_dir": payload.get(
            "cycle_human_review_output_dir"
        ),
        "project_id": payload.get("project_id"),
        "requested_next_iteration_id": payload.get(
            "requested_next_iteration_id"
        ),
        "local_asset_next_bounded_smoke_iteration_admission_complete": complete,
        "local_asset_next_bounded_smoke_iteration_admission_path": payload.get(
            "local_asset_next_bounded_smoke_iteration_admission_path"
        ),
        "local_asset_next_bounded_smoke_iteration_admission_manifest_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_admission_manifest_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_admission_summary_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_admission_summary_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_admission_checklist_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_admission_checklist_path"
            )
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "admission_status": payload.get("admission_status"),
        "admission_decision": payload.get("admission_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "next_bounded_smoke_iteration_prepare_admitted": payload.get(
            "next_bounded_smoke_iteration_prepare_admitted"
        ),
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_bounded_smoke_iteration_executed": False,
        "next_iteration_output_dir_created": False,
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "required_human_review": True,
        "scan_performed": False,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "smoke_review_packet_run_performed": False,
        "smoke_promotion_gate_run_performed": False,
        "bounded_smoke_iteration_performed_by_admission": False,
        "iteration_review_packet_run_performed": False,
        "iteration_promotion_gate_run_performed": False,
        "cycle_contract_run_performed": False,
        "cycle_human_review_run_performed": False,
        "raw_candidate_content_read": False,
        "candidate_file_hashing_performed": False,
        "input_mutation_performed": False,
        "upstream_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
    }


def _run_local_asset_next_bounded_smoke_iteration_execution_request_node(node):
    inputs = node["inputs"]
    node_label = "local asset next bounded smoke iteration execution request"
    next_admission_output_dir = _required_string_input(
        inputs,
        "next_admission_output_dir",
        node_label,
    )
    output_dir = _required_string_input(inputs, "output_dir", node_label)
    requested_next_iteration_id = _required_string_input(
        inputs,
        "requested_next_iteration_id",
        node_label,
    )
    requested_candidate_input_dir = _required_string_input(
        inputs,
        "requested_candidate_input_dir",
        node_label,
    )
    requested_next_iteration_output_dir = _required_string_input(
        inputs,
        "requested_next_iteration_output_dir",
        node_label,
    )
    requested_max_files = _required_int_input(
        inputs,
        "requested_max_files",
        node_label,
    )
    requested_max_total_bytes = _required_int_input(
        inputs,
        "requested_max_total_bytes",
        node_label,
    )
    requested_max_depth = _required_int_input(
        inputs,
        "requested_max_depth",
        node_label,
    )
    project_id = _optional_nonempty_string_input(inputs, "project_id", node_label)
    request_id = _optional_nonempty_string_input(inputs, "request_id", node_label)
    operator_id = _optional_nonempty_string_input(inputs, "operator_id", node_label)
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        raise ValueError("task graph " + node_label + " operator_notes is malformed")
    requested_compare_previous_scan_manifest_path = _optional_nonempty_string_input(
        inputs,
        "requested_compare_previous_scan_manifest_path",
        node_label,
    )
    requested_previous_iteration_artifact_index_path = _optional_nonempty_string_input(
        inputs,
        "requested_previous_iteration_artifact_index_path",
        node_label,
    )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_next_bounded_smoke_iteration_execution_request_launcher,
    )

    result = run_local_asset_next_bounded_smoke_iteration_execution_request_launcher(
        Path(next_admission_output_dir),
        Path(output_dir),
        requested_next_iteration_id=requested_next_iteration_id,
        requested_candidate_input_dir=requested_candidate_input_dir,
        requested_next_iteration_output_dir=requested_next_iteration_output_dir,
        requested_max_files=requested_max_files,
        requested_max_total_bytes=requested_max_total_bytes,
        requested_max_depth=requested_max_depth,
        project_id=project_id,
        request_id=request_id,
        operator_id=operator_id,
        operator_notes=operator_notes,
        requested_compare_previous_scan_manifest_path=(
            requested_compare_previous_scan_manifest_path
        ),
        requested_previous_iteration_artifact_index_path=(
            requested_previous_iteration_artifact_index_path
        ),
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "next_admission_output_dir": payload.get("next_admission_output_dir"),
        "project_id": payload.get("project_id"),
        "request_id": payload.get("request_id"),
        "operator_id": payload.get("operator_id"),
        "requested_next_iteration_id": payload.get("requested_next_iteration_id"),
        "requested_candidate_input_dir": payload.get(
            "requested_candidate_input_dir"
        ),
        "requested_next_iteration_output_dir": payload.get(
            "requested_next_iteration_output_dir"
        ),
        "requested_limits": payload.get("requested_limits"),
        "local_asset_next_bounded_smoke_iteration_execution_request_complete": (
            complete
        ),
        "local_asset_next_bounded_smoke_iteration_execution_request_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_execution_request_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_execution_request_manifest_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_execution_request_manifest_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_execution_request_summary_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_execution_request_summary_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_execution_request_checklist_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_execution_request_checklist_path"
            )
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "request_status": payload.get("request_status"),
        "request_decision": payload.get("request_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "future_execution_request_created": payload.get(
            "future_execution_request_created"
        ),
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_bounded_smoke_iteration_executed": False,
        "next_iteration_output_dir_created": False,
        "requested_next_iteration_output_dir_created": False,
        "candidate_input_path_checked": False,
        "candidate_input_path_listed": False,
        "candidate_input_file_read": False,
        "candidate_input_file_hashing_performed": False,
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "required_human_review": True,
        "scan_performed": False,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "smoke_review_packet_run_performed": False,
        "smoke_promotion_gate_run_performed": False,
        "bounded_smoke_iteration_performed_by_request": False,
        "iteration_review_packet_run_performed": False,
        "iteration_promotion_gate_run_performed": False,
        "cycle_contract_run_performed": False,
        "cycle_human_review_run_performed": False,
        "next_admission_run_performed": False,
        "raw_candidate_content_read": False,
        "candidate_file_hashing_performed": False,
        "candidate_path_validation_performed": False,
        "candidate_path_listing_performed": False,
        "input_mutation_performed": False,
        "upstream_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
    }


def _run_local_asset_next_bounded_smoke_iteration_runner_admission_node(node):
    inputs = node["inputs"]
    node_label = "local asset next bounded smoke iteration runner admission"
    execution_request_output_dir = _required_string_input(
        inputs,
        "execution_request_output_dir",
        node_label,
    )
    output_dir = _required_string_input(inputs, "output_dir", node_label)
    runner_admission_id = _required_string_input(
        inputs,
        "runner_admission_id",
        node_label,
    )
    runner_operator_id = _required_string_input(
        inputs,
        "runner_operator_id",
        node_label,
    )
    runner_operator_acknowledgement_phrase = _required_string_input(
        inputs,
        "runner_operator_acknowledgement_phrase",
        node_label,
    )
    admitted_runner_id = _required_string_input(
        inputs,
        "admitted_runner_id",
        node_label,
    )
    admitted_runner_version = _required_string_input(
        inputs,
        "admitted_runner_version",
        node_label,
    )
    admitted_max_files = _required_int_input(
        inputs,
        "admitted_max_files",
        node_label,
    )
    admitted_max_total_bytes = _required_int_input(
        inputs,
        "admitted_max_total_bytes",
        node_label,
    )
    admitted_max_depth = _required_int_input(
        inputs,
        "admitted_max_depth",
        node_label,
    )
    project_id = _optional_nonempty_string_input(inputs, "project_id", node_label)
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        raise ValueError("task graph " + node_label + " operator_notes is malformed")
    runner_environment_label = _optional_nonempty_string_input(
        inputs,
        "runner_environment_label",
        node_label,
    )

    from kernel.personal_ai.local_launcher import (
        run_local_asset_next_bounded_smoke_iteration_runner_admission_launcher,
    )

    result = run_local_asset_next_bounded_smoke_iteration_runner_admission_launcher(
        Path(execution_request_output_dir),
        Path(output_dir),
        runner_admission_id=runner_admission_id,
        runner_operator_id=runner_operator_id,
        runner_operator_acknowledgement_phrase=(
            runner_operator_acknowledgement_phrase
        ),
        admitted_runner_id=admitted_runner_id,
        admitted_runner_version=admitted_runner_version,
        admitted_max_files=admitted_max_files,
        admitted_max_total_bytes=admitted_max_total_bytes,
        admitted_max_depth=admitted_max_depth,
        project_id=project_id,
        operator_notes=operator_notes,
        runner_environment_label=runner_environment_label,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "execution_request_output_dir": payload.get(
            "execution_request_output_dir"
        ),
        "project_id": payload.get("project_id"),
        "runner_admission_id": payload.get("runner_admission_id"),
        "runner_operator_id": payload.get("runner_operator_id"),
        "admitted_runner_id": payload.get("admitted_runner_id"),
        "admitted_runner_version": payload.get("admitted_runner_version"),
        "runner_environment_label": payload.get("runner_environment_label"),
        "requested_next_iteration_id": payload.get(
            "requested_next_iteration_id"
        ),
        "requested_candidate_input_dir": payload.get(
            "requested_candidate_input_dir"
        ),
        "requested_next_iteration_output_dir": payload.get(
            "requested_next_iteration_output_dir"
        ),
        "requested_limits": payload.get("requested_limits"),
        "admitted_limits": payload.get("admitted_limits"),
        "local_asset_next_bounded_smoke_iteration_runner_admission_complete": (
            complete
        ),
        "local_asset_next_bounded_smoke_iteration_runner_admission_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_runner_admission_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_runner_admission_manifest_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_runner_admission_manifest_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_runner_admission_summary_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_runner_admission_summary_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_runner_admission_checklist_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_runner_admission_checklist_path"
            )
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "admission_status": payload.get("admission_status"),
        "admission_decision": payload.get("admission_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "runner_consume_request_admitted": payload.get(
            "runner_consume_request_admitted"
        ),
        "runner_execution_allowed": False,
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_bounded_smoke_iteration_executed": False,
        "next_iteration_output_dir_created": False,
        "requested_next_iteration_output_dir_created": False,
        "candidate_input_path_checked": False,
        "candidate_input_path_listed": False,
        "candidate_input_file_read": False,
        "candidate_input_file_hashing_performed": False,
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "required_human_review": True,
        "scan_performed": False,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "smoke_review_packet_run_performed": False,
        "smoke_promotion_gate_run_performed": False,
        "bounded_smoke_iteration_performed_by_runner_admission": False,
        "iteration_review_packet_run_performed": False,
        "iteration_promotion_gate_run_performed": False,
        "cycle_contract_run_performed": False,
        "cycle_human_review_run_performed": False,
        "next_admission_run_performed": False,
        "execution_request_run_performed": False,
        "raw_candidate_content_read": False,
        "candidate_file_hashing_performed": False,
        "candidate_path_validation_performed": False,
        "candidate_path_listing_performed": False,
        "input_mutation_performed": False,
        "upstream_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
    }


def _run_local_asset_next_bounded_smoke_iteration_runner_node(node):
    inputs = node["inputs"]
    node_label = "local asset next bounded smoke iteration runner"
    runner_admission_output_dir = _required_string_input(
        inputs,
        "runner_admission_output_dir",
        node_label,
    )
    runner_output_dir = _required_string_input(
        inputs,
        "runner_output_dir",
        node_label,
    )
    actual_next_iteration_output_dir = _required_string_input(
        inputs,
        "actual_next_iteration_output_dir",
        node_label,
    )
    runner_execution_id = _required_string_input(
        inputs,
        "runner_execution_id",
        node_label,
    )
    runner_operator_id = _required_string_input(
        inputs,
        "runner_operator_id",
        node_label,
    )
    runner_execution_acknowledgement_phrase = _required_string_input(
        inputs,
        "runner_execution_acknowledgement_phrase",
        node_label,
    )
    project_id = _optional_nonempty_string_input(inputs, "project_id", node_label)
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        raise ValueError("task graph " + node_label + " operator_notes is malformed")

    from kernel.personal_ai.local_launcher import (
        run_local_asset_next_bounded_smoke_iteration_runner_launcher,
    )

    result = run_local_asset_next_bounded_smoke_iteration_runner_launcher(
        Path(runner_admission_output_dir),
        Path(runner_output_dir),
        Path(actual_next_iteration_output_dir),
        runner_execution_id=runner_execution_id,
        runner_operator_id=runner_operator_id,
        runner_execution_acknowledgement_phrase=(
            runner_execution_acknowledgement_phrase
        ),
        project_id=project_id,
        operator_notes=operator_notes,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "runner_admission_output_dir": payload.get(
            "runner_admission_output_dir"
        ),
        "runner_output_dir": payload.get("runner_output_dir"),
        "actual_next_iteration_output_dir": payload.get(
            "actual_next_iteration_output_dir"
        ),
        "project_id": payload.get("project_id"),
        "runner_execution_id": payload.get("runner_execution_id"),
        "runner_operator_id": payload.get("runner_operator_id"),
        "runner_admission_id": payload.get("runner_admission_id"),
        "admitted_runner_id": payload.get("admitted_runner_id"),
        "admitted_runner_version": payload.get("admitted_runner_version"),
        "requested_next_iteration_id": payload.get(
            "requested_next_iteration_id"
        ),
        "requested_candidate_input_dir": payload.get(
            "requested_candidate_input_dir"
        ),
        "requested_next_iteration_output_dir": payload.get(
            "requested_next_iteration_output_dir"
        ),
        "requested_limits": payload.get("requested_limits"),
        "admitted_limits": payload.get("admitted_limits"),
        "local_asset_next_bounded_smoke_iteration_runner_complete": complete,
        "local_asset_next_bounded_smoke_iteration_runner_path": payload.get(
            "local_asset_next_bounded_smoke_iteration_runner_path"
        ),
        "local_asset_next_bounded_smoke_iteration_runner_manifest_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_runner_manifest_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_runner_summary_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_runner_summary_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_runner_checklist_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_runner_checklist_path"
            )
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "actual_iteration_artifacts": payload.get("actual_iteration_artifacts"),
        "runner_status": payload.get("runner_status"),
        "runner_decision": payload.get("runner_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "runner_execution_performed": payload.get("runner_execution_performed"),
        "next_bounded_smoke_iteration_executed": payload.get(
            "next_bounded_smoke_iteration_executed"
        ),
        "next_iteration_output_dir_created": False,
        "actual_next_iteration_output_dir_created": False,
        "candidate_input_path_checked": payload.get(
            "candidate_input_path_checked"
        ),
        "candidate_input_path_listed": payload.get(
            "candidate_input_path_listed"
        ),
        "candidate_input_file_read": payload.get("candidate_input_file_read"),
        "candidate_input_file_hashing_performed": payload.get(
            "candidate_input_file_hashing_performed"
        ),
        "candidate_file_count": payload.get("candidate_file_count"),
        "candidate_total_bytes": payload.get("candidate_total_bytes"),
        "candidate_limit_enforced": payload.get("candidate_limit_enforced"),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "required_human_review": True,
        "scan_performed": False,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "smoke_review_packet_run_performed": False,
        "smoke_promotion_gate_run_performed": False,
        "bounded_smoke_iteration_performed_by_runner": payload.get(
            "bounded_smoke_iteration_performed_by_runner"
        ),
        "iteration_review_packet_run_performed": False,
        "iteration_promotion_gate_run_performed": False,
        "cycle_contract_run_performed": False,
        "cycle_human_review_run_performed": False,
        "next_admission_run_performed": False,
        "execution_request_run_performed": False,
        "runner_admission_run_performed": False,
        "raw_candidate_content_copied": False,
        "input_mutation_performed": False,
        "upstream_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
    }


def _run_local_asset_next_bounded_smoke_iteration_run_review_packet_node(node):
    inputs = node["inputs"]
    node_label = "local asset next bounded smoke iteration run review packet"
    runner_output_dir = _required_string_input(
        inputs,
        "runner_output_dir",
        node_label,
    )
    actual_next_iteration_output_dir = _required_string_input(
        inputs,
        "actual_next_iteration_output_dir",
        node_label,
    )
    output_dir = _required_string_input(inputs, "output_dir", node_label)
    review_packet_id = _required_string_input(
        inputs,
        "review_packet_id",
        node_label,
    )
    project_id = _optional_nonempty_string_input(inputs, "project_id", node_label)
    reviewer_id = _optional_nonempty_string_input(inputs, "reviewer_id", node_label)
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        raise ValueError("task graph " + node_label + " operator_notes is malformed")

    from kernel.personal_ai.local_launcher import (
        run_local_asset_next_bounded_smoke_iteration_run_review_packet_launcher,
    )

    result = run_local_asset_next_bounded_smoke_iteration_run_review_packet_launcher(
        Path(runner_output_dir),
        Path(actual_next_iteration_output_dir),
        Path(output_dir),
        review_packet_id=review_packet_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "runner_output_dir": payload.get("runner_output_dir"),
        "actual_next_iteration_output_dir": payload.get(
            "actual_next_iteration_output_dir"
        ),
        "project_id": payload.get("project_id"),
        "review_packet_id": payload.get("review_packet_id"),
        "reviewer_id": payload.get("reviewer_id"),
        "runner_execution_id": payload.get("runner_execution_id"),
        "runner_operator_id": payload.get("runner_operator_id"),
        "runner_admission_id": payload.get("runner_admission_id"),
        "requested_next_iteration_id": payload.get(
            "requested_next_iteration_id"
        ),
        "requested_candidate_input_dir": payload.get(
            "requested_candidate_input_dir"
        ),
        "requested_next_iteration_output_dir": payload.get(
            "requested_next_iteration_output_dir"
        ),
        "requested_limits": payload.get("requested_limits"),
        "admitted_limits": payload.get("admitted_limits"),
        "local_asset_next_bounded_smoke_iteration_run_review_packet_complete": (
            complete
        ),
        "local_asset_next_bounded_smoke_iteration_run_review_packet_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_run_review_packet_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_run_review_packet_summary_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_run_review_packet_summary_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist_path"
            )
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "review_status": payload.get("review_status"),
        "review_decision": payload.get("review_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "review_packet_created": payload.get("review_packet_created"),
        "promotion_approved": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "runner_reexecution_performed": False,
        "candidate_input_path_checked_by_review": False,
        "candidate_input_path_listed_by_review": False,
        "candidate_input_file_read_by_review": False,
        "candidate_input_file_hashing_performed_by_review": False,
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "required_human_review": True,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "smoke_review_packet_run_performed": False,
        "smoke_promotion_gate_run_performed": False,
        "bounded_smoke_iteration_performed_by_review_packet": False,
        "iteration_review_packet_run_performed": False,
        "iteration_promotion_gate_run_performed": False,
        "cycle_contract_run_performed": False,
        "cycle_human_review_run_performed": False,
        "next_admission_run_performed": False,
        "execution_request_run_performed": False,
        "runner_admission_run_performed": False,
        "runner_execution_run_performed_by_review_packet": False,
        "raw_candidate_content_read_by_review": False,
        "candidate_file_hashing_performed_by_review": False,
        "candidate_path_validation_performed_by_review": False,
        "candidate_path_listing_performed_by_review": False,
        "input_mutation_performed": False,
        "upstream_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
    }


def _run_local_asset_next_bounded_smoke_iteration_run_promotion_gate_node(node):
    inputs = node["inputs"]
    node_label = "local asset next bounded smoke iteration run promotion gate"
    run_review_packet_output_dir = _required_string_input(
        inputs,
        "run_review_packet_output_dir",
        node_label,
    )
    output_dir = _required_string_input(inputs, "output_dir", node_label)
    promotion_gate_id = _required_string_input(
        inputs,
        "promotion_gate_id",
        node_label,
    )
    project_id = _optional_nonempty_string_input(inputs, "project_id", node_label)
    reviewer_id = _optional_nonempty_string_input(inputs, "reviewer_id", node_label)
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        raise ValueError("task graph " + node_label + " operator_notes is malformed")

    from kernel.personal_ai.local_launcher import (
        run_local_asset_next_bounded_smoke_iteration_run_promotion_gate_launcher,
    )

    result = run_local_asset_next_bounded_smoke_iteration_run_promotion_gate_launcher(
        Path(run_review_packet_output_dir),
        Path(output_dir),
        promotion_gate_id=promotion_gate_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "run_review_packet_output_dir": payload.get(
            "run_review_packet_output_dir"
        ),
        "project_id": payload.get("project_id"),
        "promotion_gate_id": payload.get("promotion_gate_id"),
        "reviewer_id": payload.get("reviewer_id"),
        "review_packet_id": payload.get("review_packet_id"),
        "runner_execution_id": payload.get("runner_execution_id"),
        "runner_operator_id": payload.get("runner_operator_id"),
        "runner_admission_id": payload.get("runner_admission_id"),
        "requested_next_iteration_id": payload.get(
            "requested_next_iteration_id"
        ),
        "requested_candidate_input_dir": payload.get(
            "requested_candidate_input_dir"
        ),
        "requested_next_iteration_output_dir": payload.get(
            "requested_next_iteration_output_dir"
        ),
        "actual_next_iteration_output_dir": payload.get(
            "actual_next_iteration_output_dir"
        ),
        "requested_limits": payload.get("requested_limits"),
        "admitted_limits": payload.get("admitted_limits"),
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_complete": (
            complete
        ),
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_run_promotion_gate_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary_path"
            )
        ),
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist_path": (
            payload.get(
                "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist_path"
            )
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "gate_status": payload.get("gate_status"),
        "gate_decision": payload.get("gate_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "bounded_run_promotion_approved": payload.get(
            "bounded_run_promotion_approved"
        ),
        "cycle_contract_generation_allowed": payload.get(
            "cycle_contract_generation_allowed"
        ),
        "cycle_contract_generated": False,
        "promotion_approved": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "runner_reexecution_performed": False,
        "candidate_input_path_checked_by_gate": False,
        "candidate_input_path_listed_by_gate": False,
        "candidate_input_file_read_by_gate": False,
        "candidate_input_file_hashing_performed_by_gate": False,
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "required_human_review": True,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "smoke_review_packet_run_performed": False,
        "smoke_promotion_gate_run_performed": False,
        "bounded_smoke_iteration_performed_by_gate": False,
        "iteration_review_packet_run_performed": False,
        "iteration_promotion_gate_run_performed": False,
        "cycle_contract_run_performed": False,
        "cycle_human_review_run_performed": False,
        "next_admission_run_performed": False,
        "execution_request_run_performed": False,
        "runner_admission_run_performed": False,
        "runner_execution_run_performed_by_gate": False,
        "run_review_packet_run_performed_by_gate": False,
        "raw_candidate_content_read_by_gate": False,
        "candidate_file_hashing_performed_by_gate": False,
        "candidate_path_validation_performed_by_gate": False,
        "candidate_path_listing_performed_by_gate": False,
        "input_mutation_performed": False,
        "upstream_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
    }


def _run_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_node(
    node,
):
    inputs = node["inputs"]
    node_label = (
        "local asset next bounded smoke cycle contract from run promotion gate"
    )
    run_promotion_gate_output_dir = _required_string_input(
        inputs,
        "run_promotion_gate_output_dir",
        node_label,
    )
    output_dir = _required_string_input(inputs, "output_dir", node_label)
    cycle_contract_id = _required_string_input(
        inputs,
        "cycle_contract_id",
        node_label,
    )
    project_id = _optional_nonempty_string_input(inputs, "project_id", node_label)
    reviewer_id = _optional_nonempty_string_input(inputs, "reviewer_id", node_label)
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        raise ValueError("task graph " + node_label + " operator_notes is malformed")

    from kernel.personal_ai.local_launcher import (
        run_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_launcher,
    )

    result = (
        run_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_launcher(
            Path(run_promotion_gate_output_dir),
            Path(output_dir),
            cycle_contract_id=cycle_contract_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
        )
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "run_promotion_gate_output_dir": payload.get(
            "run_promotion_gate_output_dir"
        ),
        "project_id": payload.get("project_id"),
        "cycle_contract_id": payload.get("cycle_contract_id"),
        "reviewer_id": payload.get("reviewer_id"),
        "review_packet_id": payload.get("review_packet_id"),
        "runner_execution_id": payload.get("runner_execution_id"),
        "runner_operator_id": payload.get("runner_operator_id"),
        "runner_admission_id": payload.get("runner_admission_id"),
        "requested_next_iteration_id": payload.get(
            "requested_next_iteration_id"
        ),
        "requested_candidate_input_dir": payload.get(
            "requested_candidate_input_dir"
        ),
        "requested_next_iteration_output_dir": payload.get(
            "requested_next_iteration_output_dir"
        ),
        "actual_next_iteration_output_dir": payload.get(
            "actual_next_iteration_output_dir"
        ),
        "requested_limits": payload.get("requested_limits"),
        "admitted_limits": payload.get("admitted_limits"),
        "candidate_file_count": payload.get("candidate_file_count"),
        "candidate_total_bytes": payload.get("candidate_total_bytes"),
        "candidate_max_depth_observed": payload.get(
            "candidate_max_depth_observed"
        ),
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_complete": (
            complete
        ),
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_path": (
            payload.get(
                "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_path"
            )
        ),
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest_path": (
            payload.get(
                "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest_path"
            )
        ),
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_summary_path": (
            payload.get(
                "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_summary_path"
            )
        ),
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist_path": (
            payload.get(
                "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist_path"
            )
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "source_gate_status": payload.get("source_gate_status"),
        "source_gate_decision": payload.get("source_gate_decision"),
        "source_next_allowed_action": payload.get("source_next_allowed_action"),
        "contract_status": payload.get("contract_status"),
        "contract_decision": payload.get("contract_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "cycle_contract_created": payload.get("cycle_contract_created", False),
        "cycle_contract_from_run_promotion_gate": payload.get(
            "cycle_contract_from_run_promotion_gate",
            False,
        ),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "required_human_review": True,
        "runner_execution_performed_by_contract": False,
        "review_packet_generation_performed_by_contract": False,
        "run_promotion_gate_reexecution_performed": False,
        "candidate_input_path_checked_by_contract": False,
        "candidate_input_path_listed_by_contract": False,
        "candidate_input_file_read_by_contract": False,
        "candidate_input_file_hashing_performed_by_contract": False,
        "raw_candidate_content_read_by_contract": False,
        "readiness_run_performed": False,
        "human_smoke_run_performed": False,
        "smoke_review_packet_run_performed": False,
        "smoke_promotion_gate_run_performed": False,
        "bounded_smoke_iteration_performed_by_contract": False,
        "iteration_review_packet_run_performed": False,
        "iteration_promotion_gate_run_performed": False,
        "cycle_human_review_run_performed": False,
        "next_admission_run_performed": False,
        "execution_request_run_performed": False,
        "runner_admission_run_performed": False,
        "runner_execution_run_performed": False,
        "run_review_packet_run_performed": False,
        "input_mutation_performed": False,
        "upstream_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
    }


def _run_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_node(
    node,
):
    inputs = node["inputs"]
    node_label = (
        "local asset next bounded smoke cycle contract human review from run promotion gate"
    )
    cycle_contract_output_dir = _required_string_input(
        inputs,
        "cycle_contract_output_dir",
        node_label,
    )
    output_dir = _required_string_input(inputs, "output_dir", node_label)
    human_review_id = _required_string_input(
        inputs,
        "human_review_id",
        node_label,
    )
    human_decision = _required_string_input(
        inputs,
        "human_decision",
        node_label,
    )
    human_signoff_phrase = _required_string_input(
        inputs,
        "human_signoff_phrase",
        node_label,
    )
    project_id = _optional_nonempty_string_input(inputs, "project_id", node_label)
    reviewer_id = _optional_nonempty_string_input(inputs, "reviewer_id", node_label)
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        raise ValueError("task graph " + node_label + " operator_notes is malformed")

    from kernel.personal_ai.local_launcher import (
        run_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_launcher,
    )

    result = (
        run_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_launcher(
            Path(cycle_contract_output_dir),
            Path(output_dir),
            human_review_id=human_review_id,
            human_decision=human_decision,
            human_signoff_phrase=human_signoff_phrase,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
        )
    )
    payload = result.payload
    complete = bool(result.complete)
    return {
        "status": "completed" if complete else "failed",
        "output_dir": result.output_dir.as_posix(),
        "cycle_contract_output_dir": payload.get("cycle_contract_output_dir"),
        "project_id": payload.get("project_id"),
        "human_review_id": payload.get("human_review_id"),
        "human_decision": payload.get("human_decision"),
        "human_signoff_phrase_sha256": payload.get("human_signoff_phrase_sha256"),
        "human_signoff_phrase_persisted": payload.get(
            "human_signoff_phrase_persisted",
            False,
        ),
        "reviewer_id": payload.get("reviewer_id"),
        "cycle_contract_id": payload.get("cycle_contract_id"),
        "review_packet_id": payload.get("review_packet_id"),
        "runner_execution_id": payload.get("runner_execution_id"),
        "runner_operator_id": payload.get("runner_operator_id"),
        "runner_admission_id": payload.get("runner_admission_id"),
        "requested_next_iteration_id": payload.get(
            "requested_next_iteration_id"
        ),
        "requested_candidate_input_dir": payload.get(
            "requested_candidate_input_dir"
        ),
        "requested_next_iteration_output_dir": payload.get(
            "requested_next_iteration_output_dir"
        ),
        "actual_next_iteration_output_dir": payload.get(
            "actual_next_iteration_output_dir"
        ),
        "requested_limits": payload.get("requested_limits"),
        "admitted_limits": payload.get("admitted_limits"),
        "candidate_file_count": payload.get("candidate_file_count"),
        "candidate_total_bytes": payload.get("candidate_total_bytes"),
        "candidate_max_depth_observed": payload.get(
            "candidate_max_depth_observed"
        ),
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_complete": (
            complete
        ),
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_path": (
            payload.get(
                "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_path"
            )
        ),
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_manifest_path": (
            payload.get(
                "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_manifest_path"
            )
        ),
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_summary_path": (
            payload.get(
                "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_summary_path"
            )
        ),
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_checklist_path": (
            payload.get(
                "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_checklist_path"
            )
        ),
        "artifact_index_path": payload.get("artifact_index_path"),
        "artifact_index_manifest_path": payload.get("artifact_index_manifest_path"),
        "source_contract_status": payload.get("source_contract_status"),
        "source_contract_decision": payload.get("source_contract_decision"),
        "source_next_allowed_action": payload.get("source_next_allowed_action"),
        "source_cycle_contract_created": payload.get(
            "source_cycle_contract_created",
            False,
        ),
        "source_cycle_contract_from_run_promotion_gate": payload.get(
            "source_cycle_contract_from_run_promotion_gate",
            False,
        ),
        "human_review_status": payload.get("human_review_status"),
        "human_review_decision": payload.get("human_review_decision"),
        "next_allowed_action": payload.get("next_allowed_action"),
        "bounded_cycle_contract_human_review_created": payload.get(
            "bounded_cycle_contract_human_review_created",
            False,
        ),
        "bounded_cycle_admission_allowed": payload.get(
            "bounded_cycle_admission_allowed",
            False,
        ),
        "failure_stage": None if complete else payload.get("failure_stage"),
        "required_human_approval": True,
        "required_human_review": True,
        "deterministic_ordering": True,
        "runner_execution_performed_by_human_review": False,
        "cycle_contract_reexecution_performed": False,
        "candidate_input_path_checked_by_human_review": False,
        "candidate_input_path_listed_by_human_review": False,
        "candidate_input_file_read_by_human_review": False,
        "candidate_input_file_hashing_performed_by_human_review": False,
        "raw_candidate_content_read_by_human_review": False,
        "bounded_smoke_iteration_performed_by_human_review": False,
        "input_mutation_performed": False,
        "upstream_output_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "duplicate_deletion_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "production_scan_performed": False,
        "production_scan_recommended": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
    }


def _required_string_input(inputs, field_name, node_label):
    value = inputs.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError("task graph " + node_label + " " + field_name + " is missing")
    return value


def _required_int_input(inputs, field_name, node_label):
    value = inputs.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("task graph " + node_label + " " + field_name + " is missing")
    return value


def _optional_nonempty_string_input(inputs, field_name, node_label):
    value = inputs.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(
            "task graph " + node_label + " " + field_name + " is malformed"
        )
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
            node["adapter_id"] == _GITHUB_CAPABILITY_ADAPTER_ID
            and node["capability"] == _GITHUB_CAPABILITY_INTAKE_PACKET_CAPABILITY
        ):
            node_refs["github_capability_intake_packet"] = {
                "packet": _path_ref(
                    node.get("github_capability_intake_packet_path")
                ),
                "packet_manifest": _path_ref(
                    node.get("github_capability_intake_packet_manifest_path")
                ),
                "summary": _path_ref(
                    node.get("github_capability_intake_packet_summary_path")
                ),
                "checklist": _path_ref(
                    node.get("github_capability_intake_packet_checklist_path")
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "intake_status": node.get("intake_status"),
                "intake_decision": node.get("intake_decision"),
                "next_allowed_action": node.get("next_allowed_action"),
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
        if (
            node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
            and node["capability"] == _LOCAL_ASSET_HUMAN_SMOKE_CAPABILITY
        ):
            node_refs["local_asset_human_smoke"] = {
                "output_dir": node.get("output_dir"),
                "control_output_dir": node.get("control_output_dir"),
                "scan_output_dir": node.get("scan_output_dir"),
                "approval": _path_ref(
                    node.get("local_asset_human_smoke_approval_path")
                ),
                "admission_receipt": _path_ref(
                    node.get("local_asset_human_smoke_admission_receipt_path")
                ),
                "summary": _path_ref(
                    node.get("local_asset_human_smoke_run_summary_path")
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "scan_artifact_index": _path_ref(
                    node.get("scan_artifact_index_path")
                ),
                "scan_artifact_index_manifest": _path_ref(
                    node.get("scan_artifact_index_manifest_path")
                ),
                "readiness_report": _path_ref(node.get("readiness_report_path")),
                "readiness_status": node.get("readiness_status"),
                "readiness_decision": node.get("readiness_decision"),
                "admitted": node.get("admitted"),
                "scan_launcher_invoked": node.get("scan_launcher_invoked"),
                "scan_complete": node.get("scan_complete"),
                "bounded_smoke_run_performed": node.get(
                    "bounded_smoke_run_performed"
                ),
                "production_scan_performed": node.get("production_scan_performed"),
                "required_human_approval": node.get("required_human_approval"),
                "failure_stage": node.get("failure_stage"),
            }
        if (
            node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
            and node["capability"] == _LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_CAPABILITY
        ):
            node_refs["local_asset_bounded_smoke_iteration"] = {
                "output_dir": node.get("output_dir"),
                "promotion_output_dir": node.get("promotion_output_dir"),
                "candidate_input_dir": node.get("candidate_input_dir"),
                "readiness_report": _path_ref(node.get("readiness_report")),
                "result": _path_ref(
                    node.get("local_asset_bounded_smoke_iteration_result_path")
                ),
                "manifest": _path_ref(
                    node.get("local_asset_bounded_smoke_iteration_manifest_path")
                ),
                "summary": _path_ref(
                    node.get("local_asset_bounded_smoke_iteration_summary_path")
                ),
                "human_review_checklist": _path_ref(
                    node.get(
                        "local_asset_bounded_smoke_iteration_human_review_checklist_path"
                    )
                ),
                "signoff": _path_ref(
                    node.get("local_asset_bounded_smoke_iteration_signoff_path")
                ),
                "admission": _path_ref(
                    node.get("local_asset_bounded_smoke_iteration_admission_path")
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "iteration_status": node.get("iteration_status"),
                "iteration_decision": node.get("iteration_decision"),
                "bounded_smoke_iteration_performed": node.get(
                    "bounded_smoke_iteration_performed"
                ),
                "production_promotion_granted": node.get(
                    "production_promotion_granted"
                ),
                "production_scan_approved": node.get("production_scan_approved"),
                "production_scan_performed": node.get("production_scan_performed"),
                "required_human_approval": node.get("required_human_approval"),
                "input_mutation_performed": node.get("input_mutation_performed"),
                "file_move_performed": node.get("file_move_performed"),
                "file_rename_performed": node.get("file_rename_performed"),
                "file_delete_performed": node.get("file_delete_performed"),
                "duplicate_deletion_performed": node.get(
                    "duplicate_deletion_performed"
                ),
                "media_organizer_behavior_performed": node.get(
                    "media_organizer_behavior_performed"
                ),
                "network_access_performed": node.get("network_access_performed"),
                "model_api_called": node.get("model_api_called"),
                "external_runtime_invoked": node.get("external_runtime_invoked"),
                "failure_stage": node.get("failure_stage"),
            }
        if (
            node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
            and node["capability"] == _LOCAL_ASSET_SMOKE_REVIEW_PACKET_CAPABILITY
        ):
            node_refs["local_asset_smoke_review_packet"] = {
                "output_dir": node.get("output_dir"),
                "smoke_output_dir": node.get("smoke_output_dir"),
                "packet": _path_ref(
                    node.get("local_asset_smoke_review_packet_path")
                ),
                "packet_manifest": _path_ref(
                    node.get("local_asset_smoke_review_packet_manifest_path")
                ),
                "summary": _path_ref(
                    node.get("local_asset_smoke_review_summary_path")
                ),
                "decision_checklist": _path_ref(
                    node.get("local_asset_smoke_human_decision_checklist_path")
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "review_packet_status": node.get("review_packet_status"),
                "recommended_human_decision": node.get(
                    "recommended_human_decision"
                ),
                "scan_performed": node.get("scan_performed"),
                "readiness_run_performed": node.get("readiness_run_performed"),
                "raw_candidate_content_read": node.get(
                    "raw_candidate_content_read"
                ),
                "candidate_file_hashing_performed": node.get(
                    "candidate_file_hashing_performed"
                ),
                "required_human_approval": node.get("required_human_approval"),
                "failure_stage": node.get("failure_stage"),
            }
        if (
            node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
            and node["capability"]
            == _LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_CAPABILITY
        ):
            node_refs["local_asset_smoke_iteration_review_packet"] = {
                "output_dir": node.get("output_dir"),
                "iteration_output_dir": node.get("iteration_output_dir"),
                "packet": _path_ref(
                    node.get("local_asset_smoke_iteration_review_packet_path")
                ),
                "packet_manifest": _path_ref(
                    node.get(
                        "local_asset_smoke_iteration_review_packet_manifest_path"
                    )
                ),
                "summary": _path_ref(
                    node.get("local_asset_smoke_iteration_review_summary_path")
                ),
                "decision_checklist": _path_ref(
                    node.get(
                        "local_asset_smoke_iteration_human_decision_checklist_path"
                    )
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "iteration_review_status": node.get("iteration_review_status"),
                "recommended_human_decision": node.get(
                    "recommended_human_decision"
                ),
                "iteration_status": node.get("iteration_status"),
                "bounded_smoke_iteration_performed": node.get(
                    "bounded_smoke_iteration_performed"
                ),
                "scan_performed": node.get("scan_performed"),
                "readiness_run_performed": node.get("readiness_run_performed"),
                "human_smoke_run_performed": node.get("human_smoke_run_performed"),
                "bounded_smoke_iteration_performed_by_review_packet": node.get(
                    "bounded_smoke_iteration_performed_by_review_packet"
                ),
                "promotion_gate_run_performed": node.get(
                    "promotion_gate_run_performed"
                ),
                "raw_candidate_content_read": node.get(
                    "raw_candidate_content_read"
                ),
                "candidate_file_hashing_performed": node.get(
                    "candidate_file_hashing_performed"
                ),
                "required_human_approval": node.get("required_human_approval"),
                "failure_stage": node.get("failure_stage"),
            }
        if (
            node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
            and node["capability"] == _LOCAL_ASSET_SMOKE_PROMOTION_GATE_CAPABILITY
        ):
            node_refs["local_asset_smoke_promotion_gate"] = {
                "output_dir": node.get("output_dir"),
                "review_output_dir": node.get("review_output_dir"),
                "decision": _path_ref(
                    node.get("local_asset_smoke_promotion_decision_path")
                ),
                "gate_manifest": _path_ref(
                    node.get("local_asset_smoke_promotion_gate_manifest_path")
                ),
                "summary": _path_ref(
                    node.get("local_asset_smoke_promotion_summary_path")
                ),
                "human_signoff_checklist": _path_ref(
                    node.get(
                        "local_asset_smoke_promotion_human_signoff_checklist_path"
                    )
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "promotion_gate_status": node.get("promotion_gate_status"),
                "promotion_decision": node.get("promotion_decision"),
                "next_bounded_smoke_iteration_allowed": node.get(
                    "next_bounded_smoke_iteration_allowed"
                ),
                "production_promotion_granted": node.get(
                    "production_promotion_granted"
                ),
                "production_scan_approved": node.get("production_scan_approved"),
                "scan_performed": node.get("scan_performed"),
                "readiness_run_performed": node.get("readiness_run_performed"),
                "human_smoke_run_performed": node.get("human_smoke_run_performed"),
                "review_packet_mutation_performed": node.get(
                    "review_packet_mutation_performed"
                ),
                "smoke_output_mutation_performed": node.get(
                    "smoke_output_mutation_performed"
                ),
                "raw_candidate_content_read": node.get(
                    "raw_candidate_content_read"
                ),
                "candidate_file_hashing_performed": node.get(
                    "candidate_file_hashing_performed"
                ),
                "required_human_approval": node.get("required_human_approval"),
                "failure_stage": node.get("failure_stage"),
            }
        if (
            node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
            and node["capability"]
            == _LOCAL_ASSET_ITERATION_PROMOTION_GATE_CAPABILITY
        ):
            node_refs["local_asset_iteration_promotion_gate"] = {
                "output_dir": node.get("output_dir"),
                "iteration_review_output_dir": node.get(
                    "iteration_review_output_dir"
                ),
                "decision": _path_ref(
                    node.get("local_asset_iteration_promotion_decision_path")
                ),
                "gate_manifest": _path_ref(
                    node.get(
                        "local_asset_iteration_promotion_gate_manifest_path"
                    )
                ),
                "summary": _path_ref(
                    node.get("local_asset_iteration_promotion_summary_path")
                ),
                "human_signoff_checklist": _path_ref(
                    node.get(
                        "local_asset_iteration_promotion_human_signoff_checklist_path"
                    )
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "iteration_promotion_gate_status": node.get(
                    "iteration_promotion_gate_status"
                ),
                "iteration_promotion_decision": node.get(
                    "iteration_promotion_decision"
                ),
                "next_bounded_smoke_iteration_allowed": node.get(
                    "next_bounded_smoke_iteration_allowed"
                ),
                "production_promotion_granted": node.get(
                    "production_promotion_granted"
                ),
                "production_scan_approved": node.get("production_scan_approved"),
                "production_scan_performed": node.get("production_scan_performed"),
                "production_scan_recommended": node.get(
                    "production_scan_recommended"
                ),
                "scan_performed": node.get("scan_performed"),
                "readiness_run_performed": node.get("readiness_run_performed"),
                "human_smoke_run_performed": node.get("human_smoke_run_performed"),
                "bounded_smoke_iteration_performed_by_gate": node.get(
                    "bounded_smoke_iteration_performed_by_gate"
                ),
                "iteration_review_packet_run_performed": node.get(
                    "iteration_review_packet_run_performed"
                ),
                "iteration_review_output_mutation_performed": node.get(
                    "iteration_review_output_mutation_performed"
                ),
                "raw_candidate_content_read": node.get(
                    "raw_candidate_content_read"
                ),
                "candidate_file_hashing_performed": node.get(
                    "candidate_file_hashing_performed"
                ),
                "required_human_approval": node.get("required_human_approval"),
                "failure_stage": node.get("failure_stage"),
            }
        if (
            node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
            and node["capability"]
            == _LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_CAPABILITY
        ):
            node_refs["local_asset_bounded_smoke_cycle_contract"] = {
                "output_dir": node.get("output_dir"),
                "readiness_output_dir": node.get("readiness_output_dir"),
                "smoke_output_dir": node.get("smoke_output_dir"),
                "smoke_review_output_dir": node.get("smoke_review_output_dir"),
                "smoke_promotion_output_dir": node.get(
                    "smoke_promotion_output_dir"
                ),
                "iteration_output_dir": node.get("iteration_output_dir"),
                "iteration_review_output_dir": node.get(
                    "iteration_review_output_dir"
                ),
                "iteration_promotion_output_dir": node.get(
                    "iteration_promotion_output_dir"
                ),
                "contract": _path_ref(
                    node.get("local_asset_bounded_smoke_cycle_contract_path")
                ),
                "contract_manifest": _path_ref(
                    node.get(
                        "local_asset_bounded_smoke_cycle_contract_manifest_path"
                    )
                ),
                "summary": _path_ref(
                    node.get("local_asset_bounded_smoke_cycle_summary_path")
                ),
                "human_review_checklist": _path_ref(
                    node.get(
                        "local_asset_bounded_smoke_cycle_human_review_checklist_path"
                    )
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "cycle_contract_status": node.get("cycle_contract_status"),
                "cycle_contract_decision": node.get("cycle_contract_decision"),
                "next_allowed_action": node.get("next_allowed_action"),
                "cycle_blocker_count": node.get("cycle_blocker_count"),
                "scan_performed": node.get("scan_performed"),
                "readiness_run_performed": node.get("readiness_run_performed"),
                "human_smoke_run_performed": node.get("human_smoke_run_performed"),
                "smoke_review_packet_run_performed": node.get(
                    "smoke_review_packet_run_performed"
                ),
                "smoke_promotion_gate_run_performed": node.get(
                    "smoke_promotion_gate_run_performed"
                ),
                "bounded_smoke_iteration_performed_by_contract": node.get(
                    "bounded_smoke_iteration_performed_by_contract"
                ),
                "iteration_review_packet_run_performed": node.get(
                    "iteration_review_packet_run_performed"
                ),
                "iteration_promotion_gate_run_performed": node.get(
                    "iteration_promotion_gate_run_performed"
                ),
                "raw_candidate_content_read": node.get(
                    "raw_candidate_content_read"
                ),
                "candidate_file_hashing_performed": node.get(
                    "candidate_file_hashing_performed"
                ),
                "required_human_approval": node.get("required_human_approval"),
                "required_human_review": node.get("required_human_review"),
                "failure_stage": node.get("failure_stage"),
            }
        if (
            node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
            and node["capability"]
            == _LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CAPABILITY
        ):
            node_refs["local_asset_bounded_smoke_cycle_human_review"] = {
                "output_dir": node.get("output_dir"),
                "cycle_contract_output_dir": node.get(
                    "cycle_contract_output_dir"
                ),
                "decision": _path_ref(
                    node.get(
                        "local_asset_bounded_smoke_cycle_human_review_decision_path"
                    )
                ),
                "manifest": _path_ref(
                    node.get(
                        "local_asset_bounded_smoke_cycle_human_review_manifest_path"
                    )
                ),
                "summary": _path_ref(
                    node.get(
                        "local_asset_bounded_smoke_cycle_human_review_summary_path"
                    )
                ),
                "human_review_checklist": _path_ref(
                    node.get(
                        "local_asset_bounded_smoke_cycle_human_review_checklist_path"
                    )
                ),
                "artifact_index": _path_ref(node.get("artifact_index_path")),
                "artifact_index_manifest": _path_ref(
                    node.get("artifact_index_manifest_path")
                ),
                "human_review_status": node.get("human_review_status"),
                "human_review_decision": node.get("human_review_decision"),
                "next_allowed_action": node.get("next_allowed_action"),
                "next_bounded_smoke_iteration_prepare_allowed": node.get(
                    "next_bounded_smoke_iteration_prepare_allowed"
                ),
                "next_bounded_smoke_iteration_execute_allowed": node.get(
                    "next_bounded_smoke_iteration_execute_allowed"
                ),
                "scan_performed": node.get("scan_performed"),
                "cycle_contract_run_performed": node.get(
                    "cycle_contract_run_performed"
                ),
                "bounded_smoke_iteration_performed_by_review": node.get(
                    "bounded_smoke_iteration_performed_by_review"
                ),
                "raw_candidate_content_read": node.get(
                    "raw_candidate_content_read"
                ),
                "candidate_file_hashing_performed": node.get(
                    "candidate_file_hashing_performed"
                ),
                "required_human_approval": node.get("required_human_approval"),
                "required_human_review": node.get("required_human_review"),
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
