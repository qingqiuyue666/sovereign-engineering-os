"""JSON-RPC style gateway for controlled execution-plane workflows."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from creative.common import load_json, write_json
from execution_plane.adapters.registry import dispatch_adapter
from execution_plane.permits.builder import create_execution_permit, stable_id
from execution_plane.runner.result_envelope import utc_now
from execution_plane.runtime.worker_pool import run_bounded_jobs


def invoke_rpc_file(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    return invoke_rpc(payload)


def invoke_rpc(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _rpc_error(None, "SCHEMA_INVALID", "payload_must_be_mapping")
    method = str(payload.get("method", ""))
    request_id = payload.get("id")
    if method not in {"workflow.invoke", "adapter.execute"}:
        return _rpc_error(request_id, "METHOD_NOT_ALLOWED", method)
    params = payload.get("params")
    if not isinstance(params, Mapping):
        return _rpc_error(request_id, "SCHEMA_INVALID", "params_must_be_mapping")
    if method == "adapter.execute":
        result = _invoke_single(params)
    else:
        result = _invoke_workflow(params)
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _invoke_single(params: Mapping[str, Any]) -> dict[str, Any]:
    output_root = Path(str(params.get("output_root", "work/rpc/adapter_execute")))
    adapter = str(params.get("adapter", "fake_dcc"))
    action = str(params.get("action", "smoke_generate_file"))
    token = params.get("runtime_token") if isinstance(params.get("runtime_token"), Mapping) else {}
    permit = _permit_for_node(
        adapter=adapter,
        action=action,
        output_root=output_root,
        token=token,
        node_id="single",
    )
    result = dispatch_adapter(permit, params.get("payload") if isinstance(params.get("payload"), Mapping) else None)
    return {
        "terminal_status": "TERMINAL_SUCCEEDED" if result.get("status") == "SUCCEEDED" else "TERMINAL_FAILED",
        "node_results": [{"node_id": "single", "result": result}],
    }


def _invoke_workflow(params: Mapping[str, Any]) -> dict[str, Any]:
    output_root = Path(str(params.get("output_root", "work/rpc/workflow")))
    workflow_id = str(params.get("workflow_id", stable_id("WORKFLOW", utc_now())))
    token = params.get("runtime_token") if isinstance(params.get("runtime_token"), Mapping) else {}
    nodes = params.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return {
            "workflow_id": workflow_id,
            "terminal_status": "TERMINAL_FAILED",
            "failure_code": "SCHEMA_INVALID",
            "node_results": [],
        }
    jobs = []
    for index, raw_node in enumerate(nodes):
        node = raw_node if isinstance(raw_node, Mapping) else {}
        node_id = str(node.get("node_id", f"n{index + 1}"))
        adapter = str(node.get("adapter", ""))
        action = str(node.get("action", ""))
        permit = _permit_for_node(
            adapter=adapter,
            action=action,
            output_root=output_root / node_id,
            token=token,
            node_id=node_id,
        )
        jobs.append(
            {
                "node_id": node_id,
                "adapter": adapter,
                "action": action,
                "permit": permit,
                "payload": node.get("payload") if isinstance(node.get("payload"), Mapping) else {},
            }
        )

    def dispatch(job: Mapping[str, Any]) -> dict[str, Any]:
        try:
            result = dispatch_adapter(job["permit"], job.get("payload"))
            return {"node_id": job["node_id"], "result": result}
        except Exception as exc:
            return {
                "node_id": job.get("node_id"),
                "result": {
                    "schema_version": "seos_execution_result_v1",
                    "status": "BLOCKED",
                    "adapter": job.get("adapter"),
                    "failure_summary": f"{exc.__class__.__name__}: {exc}",
                    "policy_blocks": ["EXECUTION_FAILED"],
                    "outputs": [],
                    "artifact_refs": [],
                },
            }

    node_results = run_bounded_jobs(jobs, {**dict(token), **jobs[0]["permit"]}, dispatch)
    terminal_status = (
        "TERMINAL_SUCCEEDED"
        if all(item.get("result", {}).get("status") == "SUCCEEDED" for item in node_results)
        else "TERMINAL_FAILED"
    )
    receipt = {
        "schema_version": "seos.workflow_receipt.v1",
        "workflow_id": workflow_id,
        "terminal_status": terminal_status,
        "node_results": sorted(node_results, key=lambda item: str(item.get("node_id"))),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    write_json(output_root / "workflow_receipt.json", receipt)
    return receipt


def _permit_for_node(
    *,
    adapter: str,
    action: str,
    output_root: Path,
    token: Mapping[str, Any],
    node_id: str,
) -> dict[str, Any]:
    return create_execution_permit(
        task_id=str(token.get("task_id", f"TASK_RPC_{node_id}")),
        operator_approval_id=str(token.get("operator_approval_id", "RCPT_RPC_APPROVED")),
        allowed_adapter=adapter,
        allowed_action=action,
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


def _rpc_error(request_id: object, code: str, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
