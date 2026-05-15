"""ComfyUI endpoint admission and disabled runner.

This module admits only a future loopback ComfyUI endpoint package and can call
an injected transport after explicit gates. It does not contact ComfyUI by
itself and normal tests use fake transports only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
import json

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = ["ComfyUIEndpointDisabledRunnerResult", "run_comfyui_endpoint_disabled_runner"]

_RESULT_FILE = "comfyui_endpoint_disabled_runner_result.json"
_FAILURE_FILE = "comfyui_endpoint_disabled_runner_failure_quarantine.json"
_RESULT_TYPE = "personal_ai_comfyui_endpoint_disabled_runner_result_v1"
_FAILURE_TYPE = "personal_ai_comfyui_endpoint_disabled_runner_failure_v1"
_ENABLE_FLAG = "SEOS_ENABLE_COMFYUI_ENDPOINT_DISABLED_RUNNER"
_EXPECTED_ENABLE_VALUE = "true"

ComfyUITransport = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class ComfyUIEndpointDisabledRunnerResult:
    output_dir: Path
    result_path: Path | None
    failure_path: Path | None
    status: str
    real_endpoint_called: bool
    external_network_used: bool
    arbitrary_node_execution_used: bool
    required_human_approval: bool


def run_comfyui_endpoint_disabled_runner(
    workflow_path: Path,
    output_dir: Path,
    *,
    endpoint_url: str = "http://127.0.0.1:8188",
    environ: Mapping[str, str] | None = None,
    allow_endpoint_runner: bool = False,
    comfyui_transport: ComfyUITransport | None = None,
) -> ComfyUIEndpointDisabledRunnerResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    result_path = output_path / _RESULT_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(result_path)
    _require_no_overwrite(failure_path)
    try:
        workflow_file = Path(workflow_path)
        workflow = _read_json(workflow_file)
        _validate_endpoint(endpoint_url)
        _validate_workflow(workflow)
        source = {} if environ is None else environ
        if allow_endpoint_runner is not True:
            return _write_denied_result(result_path, workflow_file, endpoint_url, "disabled_by_callsite")
        if source.get(_ENABLE_FLAG) != _EXPECTED_ENABLE_VALUE:
            return _write_denied_result(result_path, workflow_file, endpoint_url, "disabled_by_environment_flag")
        if comfyui_transport is None:
            return _write_denied_result(result_path, workflow_file, endpoint_url, "missing_explicit_comfyui_transport")
        request = _build_request(workflow_file, workflow, endpoint_url)
        response = comfyui_transport(request)
        response_validation = _validate_response(response)
        result = {
            "result_type": _RESULT_TYPE,
            "status": "completed_via_explicit_comfyui_transport",
            "workflow_path": workflow_file.as_posix(),
            "workflow_sha256": sha256_file(workflow_file),
            "endpoint_url": endpoint_url,
            "environment_enable_flag": _ENABLE_FLAG,
            "environment_enable_flag_value_matched": True,
            "transport_called": True,
            "real_endpoint_called": True,
            "loopback_only": True,
            "external_network_used": False,
            "external_downloads_allowed": False,
            "external_downloads_performed": False,
            "arbitrary_node_execution_allowed": False,
            "arbitrary_node_execution_used": False,
            "model_download_allowed": False,
            "workflow_response_validation": response_validation,
            "raw_image_payload_persisted": False,
            "required_human_approval": True,
            "next_allowed_action": "human_review_comfyui_endpoint_runner_result",
        }
        write_json_atomically(result_path, result)
        return ComfyUIEndpointDisabledRunnerResult(
            output_dir=output_path,
            result_path=result_path,
            failure_path=None,
            status="completed_via_explicit_comfyui_transport",
            real_endpoint_called=True,
            external_network_used=False,
            arbitrary_node_execution_used=False,
            required_human_approval=True,
        )
    except ValueError as error:
        failure = {
            "failure_type": _FAILURE_TYPE,
            "status": "failed_closed",
            "reason": str(error),
            "workflow_path": Path(workflow_path).as_posix(),
            "real_endpoint_called": False,
            "external_network_used": False,
            "arbitrary_node_execution_used": False,
            "required_human_approval": True,
        }
        write_json_atomically(failure_path, failure)
        return ComfyUIEndpointDisabledRunnerResult(
            output_dir=output_path,
            result_path=None,
            failure_path=failure_path,
            status="failed_closed",
            real_endpoint_called=False,
            external_network_used=False,
            arbitrary_node_execution_used=False,
            required_human_approval=True,
        )


def _write_denied_result(result_path: Path, workflow_path: Path, endpoint_url: str, status: str) -> ComfyUIEndpointDisabledRunnerResult:
    result = {
        "result_type": _RESULT_TYPE,
        "status": status,
        "workflow_path": workflow_path.as_posix(),
        "workflow_sha256": sha256_file(workflow_path),
        "endpoint_url": endpoint_url,
        "environment_enable_flag": _ENABLE_FLAG,
        "transport_called": False,
        "real_endpoint_called": False,
        "loopback_only": True,
        "external_network_used": False,
        "external_downloads_performed": False,
        "arbitrary_node_execution_used": False,
        "model_download_allowed": False,
        "raw_image_payload_persisted": False,
        "required_human_approval": True,
    }
    write_json_atomically(result_path, result)
    return ComfyUIEndpointDisabledRunnerResult(
        output_dir=result_path.parent,
        result_path=result_path,
        failure_path=None,
        status=status,
        real_endpoint_called=False,
        external_network_used=False,
        arbitrary_node_execution_used=False,
        required_human_approval=True,
    )


def _build_request(workflow_path: Path, workflow: dict[str, object], endpoint_url: str) -> dict[str, object]:
    return {
        "request_type": "personal_ai_comfyui_endpoint_disabled_runner_request_v1",
        "workflow_path": workflow_path.as_posix(),
        "workflow_sha256": sha256_file(workflow_path),
        "endpoint_url": endpoint_url,
        "node_count": len(workflow.get("nodes", [])),
        "loopback_only": True,
        "external_network_allowed": False,
        "external_downloads_allowed": False,
        "arbitrary_node_execution_allowed": False,
        "model_download_allowed": False,
    }


def _validate_response(response: dict[str, object]) -> dict[str, object]:
    failures: list[str] = []
    if not isinstance(response, dict):
        response = {}
        failures.append("response_malformed")
    if response.get("status") != "ok":
        failures.append("status_not_ok")
    for field_name in ("external_network_used", "external_downloads_performed", "arbitrary_node_execution_used", "model_download_performed", "raw_image_payload_persisted"):
        if response.get(field_name) not in (None, False):
            failures.append(field_name)
    return {"complete": not failures, "failures": sorted(set(failures))}


def _validate_endpoint(endpoint_url: str) -> None:
    if not endpoint_url.startswith(("http://127.0.0.1", "http://localhost")):
        raise ValueError("comfyui endpoint must be loopback")


def _validate_workflow(workflow: dict[str, object]) -> None:
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("workflow nodes are malformed")
    forbidden = ("download", "exec", "http", "network", "python", "script", "subprocess", "url")
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("workflow node is malformed")
        node_type = str(node.get("type", "")).lower()
        if any(token in node_type for token in forbidden):
            raise ValueError("workflow node type is forbidden")


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        raise ValueError("workflow_path is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("workflow_path is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError("workflow_path is malformed")
    return payload


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("comfyui endpoint runner output already exists")
