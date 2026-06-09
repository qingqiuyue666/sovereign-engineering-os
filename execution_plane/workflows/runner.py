"""Cross-software workflow runner."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from creative.common import write_json
from execution_plane.adapters.registry import dispatch_adapter
from execution_plane.permits.builder import create_execution_permit, stable_id
from execution_plane.runner.result_envelope import utc_now
from execution_plane.runtime.error_convergence import execute_with_retry
from execution_plane.runtime.state_ledger import append_state_events, state_event
from execution_plane.runtime.worker_pool import run_bounded_jobs
from execution_plane.workflows.artifact_router import routed_payload_for_node
from execution_plane.workflows.definition import WorkflowDefinition, load_workflow_definition
from execution_plane.workflows.node import WorkflowNode
from execution_plane.workflows.rerun import build_rerun_definition
from execution_plane.workflows.scheduler import topological_layers

WorkflowDispatch = Callable[[Mapping[str, Any], Mapping[str, Any] | None], dict[str, Any]]


def run_workflow(
    params: Mapping[str, Any],
    *,
    dispatch: WorkflowDispatch | None = None,
) -> dict[str, Any]:
    started_at = utc_now()
    try:
        definition = load_workflow_definition(params)
    except Exception as exc:
        return _schema_failure(params, started_at, exc)
    dispatcher = dispatch or dispatch_adapter
    output_root = definition.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = stable_id("WFRUN", definition.workflow_id, started_at)
    workflow_events = [
        state_event(run_id=run_id, adapter="workflow_engine", state="CREATED"),
        state_event(run_id=run_id, adapter="workflow_engine", state="VALIDATING"),
        state_event(run_id=run_id, adapter="workflow_engine", state="RUNNING"),
    ]
    append_state_events(output_root / "workflow_state_ledger.jsonl", workflow_events)
    write_json(output_root / "workflow_definition.json", definition.as_dict())

    node_results: dict[str, dict[str, Any]] = {}
    node_order: list[str] = []
    try:
        layers = topological_layers(definition)
    except Exception as exc:
        receipt = _finish_receipt(
            definition=definition,
            run_id=run_id,
            started_at=started_at,
            node_results=[],
            terminal_status="TERMINAL_FAILED",
            failure_code="SCHEDULER_FAILED",
            failure_summary=f"{exc.__class__.__name__}: {exc}",
        )
        _write_workflow_failure(output_root, receipt)
        return receipt

    for layer in layers:
        runnable_jobs: list[dict[str, Any]] = []
        for node in layer:
            blocked = _dependency_block(definition, node, node_results)
            if blocked is not None:
                node_result = _blocked_node_result(definition, node, blocked, run_id)
                _write_node_receipt(output_root, node, node_result, payload=dict(node.payload))
                node_results[node.node_id] = node_result
                node_order.append(node.node_id)
                continue
            payload = routed_payload_for_node(
                definition=definition,
                node=node,
                node_results=node_results,
                workflow_output_root=output_root,
            )
            permit = _permit_for_node(definition=definition, node=node, output_root=output_root / node.node_id)
            runnable_jobs.append({"node": node, "adapter": node.adapter, "permit": permit, "payload": payload})
        if runnable_jobs:
            results = run_bounded_jobs(
                runnable_jobs,
                _workflow_token(definition),
                lambda job: _dispatch_node(job, dispatcher, output_root),
            )
            for item in sorted(results, key=lambda result: str(result.get("node_id"))):
                node_results[str(item["node_id"])] = dict(item["result"])
                node_order.append(str(item["node_id"]))

    ordered_results = [
        {"node_id": node_id, "result": node_results[node_id]}
        for node_id in node_order
    ]
    terminal_status = (
        "TERMINAL_SUCCEEDED"
        if ordered_results and all(item["result"].get("status") == "SUCCEEDED" for item in ordered_results)
        else "TERMINAL_FAILED"
    )
    failure_node = _first_failed_node(ordered_results)
    receipt = _finish_receipt(
        definition=definition,
        run_id=run_id,
        started_at=started_at,
        node_results=ordered_results,
        terminal_status=terminal_status,
        failure_code=_failure_code_for_node(failure_node),
        failure_summary=_failure_summary_for_node(failure_node),
    )
    if failure_node is not None:
        rerun_definition = build_rerun_definition(definition, str(failure_node["node_id"]))
        write_json(output_root / "rerun_from_failed_node.json", rerun_definition)
        _write_workflow_failure(output_root, receipt)
    write_json(output_root / "artifact_manifest.json", _artifact_manifest(receipt))
    write_json(output_root / "workflow_receipt.json", receipt)
    append_state_events(
        output_root / "workflow_state_ledger.jsonl",
        [state_event(run_id=run_id, adapter="workflow_engine", state=terminal_status, detail={"failure_node": failure_node})],
    )
    return receipt


def _dispatch_node(
    job: Mapping[str, Any],
    dispatcher: WorkflowDispatch,
    output_root: Path,
) -> dict[str, Any]:
    node = job["node"]
    assert isinstance(node, WorkflowNode)
    payload = dict(job.get("payload") or {})
    permit = dict(job.get("permit") or {})
    node_dir = output_root / node.node_id
    node_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = execute_with_retry(permit=permit, payload=payload, dispatch=dispatcher)
    except Exception as exc:
        result = _exception_node_result(node, permit, exc)
    write_json(node_dir / "node_input_payload.json", payload)
    _write_node_receipt(output_root, node, result, payload=payload)
    return {"node_id": node.node_id, "result": result}


def _permit_for_node(*, definition: WorkflowDefinition, node: WorkflowNode, output_root: Path) -> dict[str, Any]:
    token = definition.runtime_token
    return create_execution_permit(
        task_id=str(token.get("task_id", f"TASK_WORKFLOW_{definition.workflow_id}_{node.node_id}")),
        operator_approval_id=str(token.get("operator_approval_id", "RCPT_WORKFLOW_APPROVED")),
        allowed_adapter=node.adapter,
        allowed_action=node.action,
        allowed_output_root=output_root,
        expires_at=str(token.get("expires_at", "2099-01-01T00:00:00Z")),
        max_runtime_seconds=int(token.get("max_runtime_seconds", 60)),
        max_output_bytes=int(token.get("max_output_bytes", 104_857_600)),
        max_files=int(token.get("max_files", 100)),
        auto_provision=token.get("auto_provision") if isinstance(token.get("auto_provision"), Mapping) else None,
        concurrency=token.get("concurrency") if isinstance(token.get("concurrency"), Mapping) else None,
        retry=token.get("retry") if isinstance(token.get("retry"), Mapping) else None,
        patch_repair=token.get("patch_repair") if isinstance(token.get("patch_repair"), Mapping) else None,
    )


def _workflow_token(definition: WorkflowDefinition) -> dict[str, Any]:
    token = dict(definition.runtime_token)
    token.setdefault("concurrency", {})
    return token


def _dependency_block(
    definition: WorkflowDefinition,
    node: WorkflowNode,
    node_results: Mapping[str, Mapping[str, Any]],
) -> str | None:
    for dep in sorted(definition.dependencies_for(node.node_id)):
        dep_result = node_results.get(dep)
        if dep_result is None:
            return f"dependency_missing:{dep}"
        if dep_result.get("status") != "SUCCEEDED":
            return f"dependency_failed:{dep}"
    return None


def _blocked_node_result(
    definition: WorkflowDefinition,
    node: WorkflowNode,
    reason: str,
    workflow_run_id: str,
) -> dict[str, Any]:
    run_id = stable_id("NODE", workflow_run_id, node.node_id)
    return {
        "schema_version": "seos_execution_result_v1",
        "permit_id": "",
        "run_id": run_id,
        "adapter": node.adapter,
        "started_at": utc_now(),
        "ended_at": utc_now(),
        "exit_code": -1,
        "status": "BLOCKED",
        "output_root": (definition.output_root / node.node_id).as_posix(),
        "outputs": [],
        "artifact_refs": [],
        "stdout_digest": "",
        "stderr_digest": "",
        "failure_summary": reason,
        "policy_blocks": ["DEPENDENCY_FAILED"],
        "evidence_manifest_path": None,
        "state_transitions": [
            state_event(run_id=run_id, adapter=node.adapter, state="PREFLIGHTING"),
            state_event(run_id=run_id, adapter=node.adapter, state="FAILED", detail={"failure_code": "DEPENDENCY_FAILED"}),
        ],
        "provision_result": {},
    }


def _exception_node_result(node: WorkflowNode, permit: Mapping[str, Any], exc: Exception) -> dict[str, Any]:
    run_id = stable_id("NODE", permit.get("permit_id", ""), node.node_id, utc_now())
    return {
        "schema_version": "seos_execution_result_v1",
        "permit_id": str(permit.get("permit_id", "")),
        "run_id": run_id,
        "adapter": node.adapter,
        "started_at": utc_now(),
        "ended_at": utc_now(),
        "exit_code": -1,
        "status": "FAILED",
        "output_root": str(permit.get("allowed_output_root", "")),
        "outputs": [],
        "artifact_refs": [],
        "stdout_digest": "",
        "stderr_digest": "",
        "failure_summary": f"{exc.__class__.__name__}: {exc}",
        "policy_blocks": ["EXECUTION_FAILED"],
        "evidence_manifest_path": None,
        "state_transitions": [
            state_event(run_id=run_id, adapter=node.adapter, state="RUNNING"),
            state_event(run_id=run_id, adapter=node.adapter, state="FAILED", detail={"failure_code": "EXECUTION_FAILED"}),
        ],
        "provision_result": {},
    }


def _write_node_receipt(output_root: Path, node: WorkflowNode, result: Mapping[str, Any], *, payload: Mapping[str, Any]) -> None:
    node_dir = output_root / node.node_id
    node_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": "seos.workflow_node_receipt.v1",
        "node_id": node.node_id,
        "adapter": node.adapter,
        "action": node.action,
        "status": result.get("status"),
        "run_id": result.get("run_id"),
        "attempt_count": result.get("attempt_count", 1),
        "convergence_decision": result.get("convergence_decision", {}),
        "artifact_refs": [dict(ref) for ref in result.get("artifact_refs", []) if isinstance(ref, Mapping)],
        "failure_summary": result.get("failure_summary"),
        "payload_artifact_refs": [
            dict(ref)
            for ref in payload.get("artifact_refs", [])
            if isinstance(ref, Mapping)
        ],
    }
    write_json(node_dir / "node_receipt.json", receipt)
    if result.get("status") != "SUCCEEDED":
        write_json(
            node_dir / "failure_bundle.json",
            {
                "schema_version": "seos.workflow_node_failure_bundle.v1",
                "node_id": node.node_id,
                "adapter": node.adapter,
                "action": node.action,
                "status": result.get("status"),
                "failure_summary": result.get("failure_summary"),
                "policy_blocks": list(result.get("policy_blocks", [])),
            },
        )


def _finish_receipt(
    *,
    definition: WorkflowDefinition,
    run_id: str,
    started_at: str,
    node_results: list[dict[str, Any]],
    terminal_status: str,
    failure_code: str | None,
    failure_summary: str | None,
) -> dict[str, Any]:
    ended_at = utc_now()
    return {
        "schema_version": "seos.workflow_receipt.v1",
        "workflow_id": definition.workflow_id,
        "workflow_run_id": run_id,
        "source_path": definition.source_path,
        "started_at": started_at,
        "ended_at": ended_at,
        "terminal_status": terminal_status,
        "failure_code": failure_code,
        "failure_summary": failure_summary,
        "node_results": node_results,
        "artifact_refs": [
            dict(ref)
            for item in node_results
            for ref in item.get("result", {}).get("artifact_refs", [])
            if isinstance(ref, Mapping)
        ],
    }


def _schema_failure(params: Mapping[str, Any], started_at: str, exc: Exception) -> dict[str, Any]:
    output_root = Path(str(params.get("output_root", "work/rpc/workflow"))) if isinstance(params, Mapping) else Path("work/rpc/workflow")
    output_root.mkdir(parents=True, exist_ok=True)
    definition = WorkflowDefinition(
        workflow_id=str(params.get("workflow_id", "invalid_workflow")) if isinstance(params, Mapping) else "invalid_workflow",
        nodes=(),
        output_root=output_root,
    )
    receipt = _finish_receipt(
        definition=definition,
        run_id=stable_id("WFRUN", "schema", started_at),
        started_at=started_at,
        node_results=[],
        terminal_status="TERMINAL_FAILED",
        failure_code="SCHEMA_INVALID",
        failure_summary=f"{exc.__class__.__name__}: {exc}",
    )
    _write_workflow_failure(output_root, receipt)
    write_json(output_root / "workflow_receipt.json", receipt)
    return receipt


def _artifact_manifest(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "seos.workflow_artifact_manifest.v1",
        "workflow_id": receipt.get("workflow_id"),
        "workflow_run_id": receipt.get("workflow_run_id"),
        "terminal_status": receipt.get("terminal_status"),
        "artifact_refs": [dict(ref) for ref in receipt.get("artifact_refs", []) if isinstance(ref, Mapping)],
    }


def _write_workflow_failure(output_root: Path, receipt: Mapping[str, Any]) -> None:
    write_json(
        output_root / "failure_bundle.json",
        {
            "schema_version": "seos.workflow_failure_bundle.v1",
            "workflow_id": receipt.get("workflow_id"),
            "workflow_run_id": receipt.get("workflow_run_id"),
            "terminal_status": receipt.get("terminal_status"),
            "failure_code": receipt.get("failure_code"),
            "failure_summary": receipt.get("failure_summary"),
        },
    )


def _first_failed_node(node_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in node_results:
        result = item.get("result", {})
        if isinstance(result, Mapping) and result.get("status") != "SUCCEEDED":
            return item
    return None


def _failure_code_for_node(node_item: Mapping[str, Any] | None) -> str | None:
    if node_item is None:
        return None
    result = node_item.get("result", {})
    if not isinstance(result, Mapping):
        return "EXECUTION_FAILED"
    policy_blocks = result.get("policy_blocks", [])
    if isinstance(policy_blocks, list) and policy_blocks:
        return str(policy_blocks[0])
    return "EXECUTION_FAILED"


def _failure_summary_for_node(node_item: Mapping[str, Any] | None) -> str | None:
    if node_item is None:
        return None
    result = node_item.get("result", {})
    if isinstance(result, Mapping):
        return str(result.get("failure_summary") or "")
    return "node_failed"
