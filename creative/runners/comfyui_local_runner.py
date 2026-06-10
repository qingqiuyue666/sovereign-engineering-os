"""Truthful local ComfyUI workflow smoke runner."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final
import hashlib
import json
import re
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

from creative.common import sanitize_path, write_json

RUNNER_SCHEMA_VERSION: Final[str] = "seos_comfyui_local_runner_v1"
PROMPT_SUMMARY_NAME: Final[str] = "comfyui_prompt_response_summary_v1.json"
HISTORY_SUMMARY_NAME: Final[str] = "comfyui_history_summary_v1.json"
DEFAULT_ENDPOINT_URL: Final[str] = "http://127.0.0.1:8188"
DEFAULT_TIMEOUT_SECONDS: Final[float] = 60.0
MAX_TIMEOUT_SECONDS: Final[float] = 3600.0
DEFAULT_POLL_INTERVAL_SECONDS: Final[float] = 1.0
MAX_WORKFLOW_BYTES: Final[int] = 5 * 1024 * 1024
MAX_JSON_RESPONSE_BYTES: Final[int] = 5 * 1024 * 1024
MAX_ARTIFACT_BYTES: Final[int] = 25 * 1024 * 1024
MAX_OUTPUT_ARTIFACTS: Final[int] = 12
READ_CHUNK_BYTES: Final[int] = 1024 * 1024
SAFE_APPROVAL_RE: Final[re.Pattern[str]] = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
SAFE_FILENAME_RE: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9._-]+")
LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({"127.0.0.1", "localhost", "::1"})


class ComfyUILocalRunnerError(RuntimeError):
    """Raised when the ComfyUI smoke request is structurally unsafe."""


class ComfyUITransportError(RuntimeError):
    """Raised when a ComfyUI HTTP request cannot be completed."""


@dataclass(frozen=True, slots=True)
class ComfyUIHttpResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str] | None = None


ComfyUITransport = Callable[
    [str, str, bytes | None, Mapping[str, str], float, int],
    ComfyUIHttpResponse,
]


@dataclass(frozen=True, slots=True)
class ComfyUIWorkflowRequest:
    workflow_json: Path | str
    output_root: Path | str
    endpoint_url: str = DEFAULT_ENDPOINT_URL
    mode: str = "public"
    approved: bool = False
    approval_id: str = ""
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS
    download_outputs: bool = True
    max_output_artifacts: int = MAX_OUTPUT_ARTIFACTS
    max_artifact_bytes: int = MAX_ARTIFACT_BYTES
    observed_at: str | None = None

    def validated(self) -> ComfyUIWorkflowRequest:
        if self.mode not in {"public", "local"}:
            raise ComfyUILocalRunnerError("mode must be public or local")
        endpoint_url = _validated_endpoint_url(self.endpoint_url)
        output_root = Path(self.output_root).expanduser().resolve()
        if output_root.exists() and not output_root.is_dir():
            raise ComfyUILocalRunnerError("output_root must be a directory")
        if output_root.exists() and output_root.is_symlink():
            raise ComfyUILocalRunnerError("output_root may not be a symlink")
        workflow_json = Path(self.workflow_json).expanduser()
        if self.timeout_seconds <= 0 or self.timeout_seconds > MAX_TIMEOUT_SECONDS:
            raise ComfyUILocalRunnerError(
                f"timeout_seconds must be within (0, {MAX_TIMEOUT_SECONDS}]"
            )
        if self.poll_interval_seconds < 0 or self.poll_interval_seconds > self.timeout_seconds:
            raise ComfyUILocalRunnerError("poll_interval_seconds must be within [0, timeout_seconds]")
        if self.max_output_artifacts < 0 or self.max_output_artifacts > MAX_OUTPUT_ARTIFACTS:
            raise ComfyUILocalRunnerError(
                f"max_output_artifacts must be within [0, {MAX_OUTPUT_ARTIFACTS}]"
            )
        if self.max_artifact_bytes <= 0 or self.max_artifact_bytes > MAX_ARTIFACT_BYTES:
            raise ComfyUILocalRunnerError(
                f"max_artifact_bytes must be within (0, {MAX_ARTIFACT_BYTES}]"
            )
        approval_id = str(self.approval_id or "")
        if self.approved and not SAFE_APPROVAL_RE.fullmatch(approval_id):
            raise ComfyUILocalRunnerError("approved ComfyUI smoke requires a safe approval_id")
        return ComfyUIWorkflowRequest(
            workflow_json=workflow_json,
            output_root=output_root,
            endpoint_url=endpoint_url,
            mode=self.mode,
            approved=bool(self.approved),
            approval_id=approval_id,
            timeout_seconds=float(self.timeout_seconds),
            poll_interval_seconds=float(self.poll_interval_seconds),
            download_outputs=bool(self.download_outputs),
            max_output_artifacts=int(self.max_output_artifacts),
            max_artifact_bytes=int(self.max_artifact_bytes),
            observed_at=self.observed_at,
        )


def run_comfyui_workflow_smoke(
    request: ComfyUIWorkflowRequest,
    *,
    transport: ComfyUITransport | None = None,
) -> dict[str, object]:
    """Submit an approved API-format workflow to a running loopback ComfyUI server."""

    admitted = request.validated()
    observed_at = admitted.observed_at or _now()
    loaded = _load_workflow(admitted.workflow_json, mode=admitted.mode)
    base = _base_result(admitted, observed_at=observed_at, workflow=loaded["workflow"])

    if loaded["status"] != "READY":
        status = "ENV_NOT_FOUND" if loaded["error_code"] == "ENV_NOT_FOUND" else "VALIDATION_FAILED"
        return {
            **base,
            "status": status,
            "complete": False,
            "execution_attempted": False,
            "error_code": loaded["error_code"],
            "service": _service_not_contacted(admitted),
            "prompt": _empty_prompt(),
            "history": _empty_history(),
            "outputs": _empty_outputs(),
            "materialization": _materialization(
                status="blocked_resource_missing" if status == "ENV_NOT_FOUND" else "blocked_validation_failed",
                output_root=admitted.output_root,
                mode=admitted.mode,
                targets=(),
                reasons=(str(loaded["reason"]),),
            ),
            "next_actions": _next_actions(status),
        }

    active_transport = transport or _urllib_transport
    service = _probe_service(admitted, transport=active_transport)
    base = _base_result(admitted, observed_at=observed_at, workflow=loaded["workflow"])
    if service["status"] != "AVAILABLE":
        return {
            **base,
            "status": "SERVICE_UNAVAILABLE",
            "complete": False,
            "execution_attempted": False,
            "error_code": "SERVICE_UNAVAILABLE",
            "service": service,
            "prompt": _empty_prompt(),
            "history": _empty_history(),
            "outputs": _empty_outputs(),
            "materialization": _materialization(
                status="blocked_service_unavailable",
                output_root=admitted.output_root,
                mode=admitted.mode,
                targets=(),
                reasons=("ComfyUI loopback service did not answer /system_stats",),
            ),
            "next_actions": _next_actions("SERVICE_UNAVAILABLE"),
        }

    if not admitted.approved:
        return {
            **base,
            "status": "USER_APPROVAL_REQUIRED",
            "complete": False,
            "execution_attempted": False,
            "error_code": "USER_APPROVAL_REQUIRED",
            "service": service,
            "prompt": _empty_prompt(),
            "history": _empty_history(),
            "outputs": _empty_outputs(),
            "materialization": _materialization(
                status="blocked_human_review_required",
                output_root=admitted.output_root,
                mode=admitted.mode,
                targets=(),
                reasons=("explicit human approval is required before POST /prompt",),
            ),
            "next_actions": _next_actions("USER_APPROVAL_REQUIRED"),
        }

    workflow = loaded["workflow_payload"]
    admitted.output_root.mkdir(parents=True, exist_ok=True)
    prompt_response = _submit_prompt(
        admitted,
        workflow=workflow,
        transport=active_transport,
    )
    prompt_summary_path = admitted.output_root / PROMPT_SUMMARY_NAME
    _write_json_once(prompt_summary_path, prompt_response["summary"])
    prompt_target = _target_for_file(
        prompt_summary_path,
        admitted.output_root,
        artifact_type="comfyui_prompt_response_summary",
        mode=admitted.mode,
    )

    if prompt_response["status"] != "ACCEPTED":
        return {
            **base,
            "status": "EXECUTION_FAILED",
            "complete": False,
            "execution_attempted": True,
            "error_code": "VALIDATION_FAILED",
            "service": service,
            "prompt": prompt_response["summary"],
            "history": _empty_history(),
            "outputs": _empty_outputs(),
            "materialization": _materialization(
                status="blocked_validation_failed",
                output_root=admitted.output_root,
                mode=admitted.mode,
                targets=(prompt_target,),
                reasons=("ComfyUI rejected the workflow submission",),
            ),
            "next_actions": _next_actions("EXECUTION_FAILED"),
        }

    history = _poll_history(
        admitted,
        prompt_id=str(prompt_response["prompt_id"]),
        transport=active_transport,
    )
    if history["status"] == "LONG_TASK_BLOCKED":
        return {
            **base,
            "status": "LONG_TASK_BLOCKED",
            "complete": False,
            "execution_attempted": True,
            "error_code": "LONG_TASK_BLOCKED",
            "service": service,
            "prompt": prompt_response["summary"],
            "history": history["summary"],
            "outputs": _empty_outputs(),
            "materialization": _materialization(
                status="blocked_timeout",
                output_root=admitted.output_root,
                mode=admitted.mode,
                targets=(prompt_target,),
                reasons=("ComfyUI prompt did not reach history before the timeout",),
            ),
            "next_actions": _next_actions("LONG_TASK_BLOCKED"),
        }

    history_summary_path = admitted.output_root / HISTORY_SUMMARY_NAME
    _write_json_once(history_summary_path, history["summary"])
    history_target = _target_for_file(
        history_summary_path,
        admitted.output_root,
        artifact_type="comfyui_history_summary",
        mode=admitted.mode,
    )
    outputs = _collect_outputs(
        admitted,
        image_descriptors=history["image_descriptors"],
        transport=active_transport,
    )
    targets = (prompt_target, history_target, *outputs["artifact_targets"])
    execution_status = _history_execution_status(history["summary"])
    if execution_status != "EXECUTED":
        return {
            **base,
            "status": "EXECUTION_FAILED",
            "complete": False,
            "execution_attempted": True,
            "error_code": "VALIDATION_FAILED",
            "service": service,
            "prompt": prompt_response["summary"],
            "history": history["summary"],
            "outputs": outputs["summary"],
            "materialization": _materialization(
                status="blocked_validation_failed",
                output_root=admitted.output_root,
                mode=admitted.mode,
                targets=targets,
                reasons=("ComfyUI history reported a failed or incomplete execution",),
            ),
            "next_actions": _next_actions("EXECUTION_FAILED"),
        }

    return {
        **base,
        "status": "EXECUTED",
        "complete": True,
        "execution_attempted": True,
        "error_code": None,
        "service": service,
        "prompt": prompt_response["summary"],
        "history": history["summary"],
        "outputs": outputs["summary"],
        "materialization": _materialization(
            status="materialized_valid",
            output_root=admitted.output_root,
            mode=admitted.mode,
            targets=targets,
            reasons=("ComfyUI prompt reached history and evidence summaries were written",),
        ),
        "next_actions": _next_actions("EXECUTED"),
    }


def write_comfyui_smoke_reports(
    result: dict[str, object],
    *,
    result_json: Path | None = None,
    materialization_json: Path | None = None,
) -> dict[str, str]:
    outputs: dict[str, str] = {}
    if result_json is not None:
        write_json(result_json, result)
        outputs["result_json"] = result_json.as_posix()
    if materialization_json is not None:
        write_json(materialization_json, result.get("materialization", {}))
        outputs["materialization_json"] = materialization_json.as_posix()
    return outputs


def _load_workflow(path: Path | str, *, mode: str) -> dict[str, object]:
    workflow_path = Path(path).expanduser()
    report_path = _report_path(workflow_path, mode=mode)
    if not workflow_path.exists() or not workflow_path.is_file():
        return {
            "status": "MISSING",
            "error_code": "ENV_NOT_FOUND",
            "reason": "workflow_json is missing",
            "workflow": {
                "api_format": False,
                "class_types": [],
                "exists": False,
                "node_count": 0,
                "path": report_path,
                "sha256": "",
                "size_bytes": 0,
            },
        }
    if workflow_path.stat().st_size > MAX_WORKFLOW_BYTES:
        return {
            "status": "INVALID",
            "error_code": "VALIDATION_FAILED",
            "reason": "workflow_json exceeds maximum supported size",
            "workflow": _workflow_file_summary(workflow_path, mode=mode, api_format=False),
        }
    try:
        payload = json.loads(workflow_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": "INVALID",
            "error_code": "VALIDATION_FAILED",
            "reason": "workflow_json is malformed",
            "workflow": _workflow_file_summary(workflow_path, mode=mode, api_format=False),
        }
    validation = _validate_api_workflow(payload)
    summary = _workflow_file_summary(
        workflow_path,
        mode=mode,
        api_format=validation["api_format"],
        class_types=validation["class_types"],
        node_count=validation["node_count"],
    )
    if not validation["api_format"]:
        return {
            "status": "INVALID",
            "error_code": "VALIDATION_FAILED",
            "reason": validation["reason"],
            "workflow": summary,
        }
    return {
        "status": "READY",
        "error_code": None,
        "reason": "",
        "workflow": summary,
        "workflow_payload": payload,
    }


def _validate_api_workflow(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict) or not payload:
        return _invalid_workflow("workflow_json must be a non-empty API-format object")
    if isinstance(payload.get("nodes"), list):
        return _invalid_workflow("workflow_json appears to be save-format JSON; export Workflow API format")
    class_types: list[str] = []
    for node_id, node in payload.items():
        if not isinstance(node_id, str):
            return _invalid_workflow("workflow node ids must be strings")
        if not isinstance(node, dict):
            return _invalid_workflow("workflow nodes must be objects")
        class_type = node.get("class_type")
        inputs = node.get("inputs")
        if not isinstance(class_type, str) or not class_type.strip():
            return _invalid_workflow("workflow nodes must declare class_type")
        if not isinstance(inputs, dict):
            return _invalid_workflow("workflow nodes must declare inputs")
        class_types.append(class_type.strip())
    return {
        "api_format": True,
        "class_types": sorted(set(class_types)),
        "node_count": len(payload),
        "reason": "",
    }


def _invalid_workflow(reason: str) -> dict[str, object]:
    return {
        "api_format": False,
        "class_types": [],
        "node_count": 0,
        "reason": reason,
    }


def _probe_service(
    request: ComfyUIWorkflowRequest,
    *,
    transport: ComfyUITransport,
) -> dict[str, object]:
    started = time.monotonic()
    try:
        response = transport(
            "GET",
            _url(request.endpoint_url, "/system_stats"),
            None,
            {},
            _request_timeout(request),
            MAX_JSON_RESPONSE_BYTES,
        )
    except Exception as exc:
        return {
            "duration_seconds": round(time.monotonic() - started, 6),
            "endpoint_url": request.endpoint_url,
            "error": _clip(str(exc)),
            "http_status": None,
            "raw_sha256": _sha256_bytes(b""),
            "status": "SERVICE_UNAVAILABLE",
            "system": {},
        }
    raw_sha256 = _sha256_bytes(response.body)
    payload = _json_payload(response.body)
    if response.status_code != 200 or not isinstance(payload, dict):
        return {
            "duration_seconds": round(time.monotonic() - started, 6),
            "endpoint_url": request.endpoint_url,
            "error": "system_stats request failed or returned malformed JSON",
            "http_status": response.status_code,
            "raw_sha256": raw_sha256,
            "status": "SERVICE_UNAVAILABLE",
            "system": {},
        }
    system = payload.get("system") if isinstance(payload.get("system"), dict) else {}
    devices = payload.get("devices") if isinstance(payload.get("devices"), list) else []
    return {
        "device_count": len(devices),
        "duration_seconds": round(time.monotonic() - started, 6),
        "endpoint_url": request.endpoint_url,
        "http_status": response.status_code,
        "raw_sha256": raw_sha256,
        "status": "AVAILABLE",
        "system": {
            "comfyui_frontend_version": str(system.get("comfyui_frontend_version", "")),
            "comfyui_version": str(system.get("comfyui_version", "")),
            "embedded_python": bool(system.get("embedded_python", False)),
            "python_version": str(system.get("python_version", "")),
            "pytorch_version": str(system.get("pytorch_version", "")),
        },
    }


def _submit_prompt(
    request: ComfyUIWorkflowRequest,
    *,
    workflow: dict[str, object],
    transport: ComfyUITransport,
) -> dict[str, object]:
    client_id = f"seos-{uuid.uuid4()}"
    requested_prompt_id = str(uuid.uuid4())
    payload = {
        "client_id": client_id,
        "prompt": workflow,
        "prompt_id": requested_prompt_id,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    started = time.monotonic()
    try:
        response = transport(
            "POST",
            _url(request.endpoint_url, "/prompt"),
            body,
            {"Content-Type": "application/json"},
            _request_timeout(request),
            MAX_JSON_RESPONSE_BYTES,
        )
    except Exception as exc:
        summary = _prompt_summary(
            status="REJECTED",
            duration_seconds=time.monotonic() - started,
            http_status=None,
            raw_sha256=_sha256_bytes(b""),
            prompt_id=requested_prompt_id,
            response_payload={},
            error=_clip(str(exc)),
        )
        return {"status": "REJECTED", "prompt_id": requested_prompt_id, "summary": summary}
    response_payload = _json_payload(response.body)
    if not isinstance(response_payload, dict):
        response_payload = {}
    prompt_id = str(response_payload.get("prompt_id") or requested_prompt_id)
    response_has_error = bool(response_payload.get("error") or response_payload.get("node_errors"))
    accepted = response.status_code == 200 and bool(prompt_id) and not response_has_error
    summary = _prompt_summary(
        status="ACCEPTED" if accepted else "REJECTED",
        duration_seconds=time.monotonic() - started,
        http_status=response.status_code,
        raw_sha256=_sha256_bytes(response.body),
        prompt_id=prompt_id,
        response_payload=response_payload,
        error="" if accepted else "ComfyUI returned prompt validation errors",
    )
    return {"status": "ACCEPTED" if accepted else "REJECTED", "prompt_id": prompt_id, "summary": summary}


def _poll_history(
    request: ComfyUIWorkflowRequest,
    *,
    prompt_id: str,
    transport: ComfyUITransport,
) -> dict[str, object]:
    deadline = time.monotonic() + request.timeout_seconds
    attempts = 0
    last_http_status: int | None = None
    last_raw_sha256 = _sha256_bytes(b"")
    while time.monotonic() <= deadline:
        attempts += 1
        try:
            response = transport(
                "GET",
                _url(request.endpoint_url, f"/history/{urllib.parse.quote(prompt_id)}"),
                None,
                {},
                _request_timeout(request),
                MAX_JSON_RESPONSE_BYTES,
            )
            last_http_status = response.status_code
            last_raw_sha256 = _sha256_bytes(response.body)
            payload = _json_payload(response.body)
            entry = _history_entry(payload, prompt_id)
            if entry is not None:
                summary, descriptors = _history_summary(
                    prompt_id=prompt_id,
                    history_payload=payload,
                    entry=entry,
                    http_status=response.status_code,
                    raw_sha256=last_raw_sha256,
                    attempts=attempts,
                )
                return {
                    "status": "FOUND",
                    "summary": summary,
                    "image_descriptors": descriptors,
                }
        except Exception:
            last_http_status = None
            last_raw_sha256 = _sha256_bytes(b"")
        if request.poll_interval_seconds:
            time.sleep(request.poll_interval_seconds)
    return {
        "status": "LONG_TASK_BLOCKED",
        "summary": {
            "attempts": attempts,
            "complete": False,
            "history_response_sha256": last_raw_sha256,
            "http_status": last_http_status,
            "image_count": 0,
            "images": [],
            "kind": "comfyui_history_summary_v1",
            "prompt_id": prompt_id,
            "status": "TIMEOUT",
            "status_str": "timeout",
        },
        "image_descriptors": [],
    }


def _collect_outputs(
    request: ComfyUIWorkflowRequest,
    *,
    image_descriptors: object,
    transport: ComfyUITransport,
) -> dict[str, object]:
    descriptors = image_descriptors if isinstance(image_descriptors, list) else []
    artifacts: list[dict[str, object]] = []
    targets: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    if not request.download_outputs:
        return {
            "summary": {
                "artifact_count": 0,
                "artifacts": artifacts,
                "download_outputs": False,
                "skipped": descriptors,
            },
            "artifact_targets": targets,
        }
    for index, descriptor in enumerate(descriptors[: request.max_output_artifacts]):
        if not isinstance(descriptor, dict):
            continue
        try:
            query = urllib.parse.urlencode(
                {
                    "filename": str(descriptor.get("filename", "")),
                    "subfolder": str(descriptor.get("subfolder", "")),
                    "type": str(descriptor.get("type", "output") or "output"),
                }
            )
            response = transport(
                "GET",
                _url(request.endpoint_url, f"/view?{query}"),
                None,
                {},
                _request_timeout(request),
                request.max_artifact_bytes + 1,
            )
            if response.status_code != 200:
                skipped.append({**descriptor, "reason": f"view request returned {response.status_code}"})
                continue
            if len(response.body) > request.max_artifact_bytes:
                skipped.append({**descriptor, "reason": "artifact exceeded max_artifact_bytes"})
                continue
            artifact_path = request.output_root / _artifact_filename(descriptor, index=index)
            _ensure_contained(artifact_path, request.output_root)
            _write_bytes_once(artifact_path, response.body)
            artifact = _target_for_file(
                artifact_path,
                request.output_root,
                artifact_type="comfyui_output_artifact",
                mode=request.mode,
            )
            artifact["source"] = {
                "node_id": str(descriptor.get("node_id", "")),
                "type": str(descriptor.get("type", "")),
            }
            artifact["content_type"] = _header_value(response.headers, "content-type")
            artifacts.append(artifact)
            targets.append(artifact)
        except Exception as exc:
            skipped.append({**descriptor, "reason": _clip(str(exc))})
    if len(descriptors) > request.max_output_artifacts:
        skipped.append(
            {
                "reason": "max_output_artifacts limit reached",
                "skipped_count": len(descriptors) - request.max_output_artifacts,
            }
        )
    return {
        "summary": {
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
            "download_outputs": True,
            "skipped": skipped,
        },
        "artifact_targets": targets,
    }


def _prompt_summary(
    *,
    status: str,
    duration_seconds: float,
    http_status: int | None,
    raw_sha256: str,
    prompt_id: str,
    response_payload: dict[str, object],
    error: str,
) -> dict[str, object]:
    node_errors = response_payload.get("node_errors")
    return {
        "duration_seconds": round(duration_seconds, 6),
        "error": error,
        "http_status": http_status,
        "kind": "comfyui_prompt_response_summary_v1",
        "node_error_count": len(node_errors) if isinstance(node_errors, dict) else 0,
        "number": response_payload.get("number"),
        "prompt_id": prompt_id,
        "prompt_response_sha256": raw_sha256,
        "raw_prompt_persisted": False,
        "status": status,
    }


def _history_summary(
    *,
    prompt_id: str,
    history_payload: object,
    entry: dict[str, object],
    http_status: int,
    raw_sha256: str,
    attempts: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    status_payload = entry.get("status") if isinstance(entry.get("status"), dict) else {}
    outputs = entry.get("outputs") if isinstance(entry.get("outputs"), dict) else {}
    descriptors: list[dict[str, object]] = []
    for node_id, output in outputs.items():
        if not isinstance(output, dict):
            continue
        images = output.get("images")
        if not isinstance(images, list):
            continue
        for image_index, image in enumerate(images):
            if not isinstance(image, dict):
                continue
            descriptors.append(
                {
                    "filename": Path(str(image.get("filename", ""))).name,
                    "image_index": image_index,
                    "node_id": str(node_id),
                    "subfolder": str(image.get("subfolder", "")),
                    "type": str(image.get("type", "output") or "output"),
                }
            )
    messages = status_payload.get("messages")
    summary = {
        "attempts": attempts,
        "complete": bool(status_payload.get("completed", False)),
        "history_response_sha256": raw_sha256,
        "http_status": http_status,
        "image_count": len(descriptors),
        "images": descriptors,
        "kind": "comfyui_history_summary_v1",
        "message_count": len(messages) if isinstance(messages, list) else 0,
        "prompt_id": prompt_id,
        "raw_history_persisted": False,
        "status": "FOUND" if isinstance(history_payload, dict) else "MALFORMED",
        "status_str": str(status_payload.get("status_str", "")),
    }
    return summary, descriptors


def _history_entry(payload: object, prompt_id: str) -> dict[str, object] | None:
    if isinstance(payload, dict):
        entry = payload.get(prompt_id)
        return entry if isinstance(entry, dict) else None
    return None


def _history_execution_status(summary: object) -> str:
    if not isinstance(summary, dict):
        return "EXECUTION_FAILED"
    status_str = str(summary.get("status_str", "")).lower()
    if summary.get("complete") is True and status_str in {"success", "succeeded", "complete", "completed"}:
        return "EXECUTED"
    return "EXECUTION_FAILED"


def _workflow_file_summary(
    path: Path,
    *,
    mode: str,
    api_format: bool,
    class_types: object = (),
    node_count: int = 0,
) -> dict[str, object]:
    classes = class_types if isinstance(class_types, list) else list(class_types)
    return {
        "api_format": api_format,
        "class_types": classes[:50],
        "exists": path.is_file(),
        "node_count": int(node_count),
        "path": _report_path(path, mode=mode),
        "sha256": _sha256_file(path) if path.is_file() else "",
        "size_bytes": path.stat().st_size if path.is_file() else 0,
    }


def _base_result(
    request: ComfyUIWorkflowRequest,
    *,
    observed_at: str,
    workflow: object,
) -> dict[str, object]:
    return {
        "approval": {
            "approval_id": request.approval_id,
            "approved": request.approved,
            "required": True,
        },
        "destructive_actions_performed": False,
        "kind": "comfyui_workflow_smoke_result_v1",
        "mode": request.mode,
        "observed_at": observed_at,
        "ok": True,
        "output_root": _report_path(request.output_root, mode=request.mode),
        "schema_version": RUNNER_SCHEMA_VERSION,
        "safety": {
            "arbitrary_command_allowed": False,
            "download_outputs_bounded": True,
            "external_network_required_by_seos": False,
            "loopback_only": True,
            "post_prompt_requires_approval": True,
            "raw_history_persisted": False,
            "raw_prompt_persisted": False,
            "service_must_already_be_running": True,
            "workflow_custom_node_side_effects_not_controlled_by_seos": True,
        },
        "workflow": workflow,
    }


def _materialization(
    *,
    status: str,
    output_root: Path,
    mode: str,
    targets: tuple[dict[str, object], ...],
    reasons: tuple[str, ...],
) -> dict[str, object]:
    return {
        "kind": "comfyui_workflow_smoke_materialization_v1",
        "reasons": list(reasons),
        "status": status,
        "target_root": _report_path(output_root, mode=mode),
        "targets": list(targets),
    }


def _target_for_file(path: Path, root: Path, *, artifact_type: str, mode: str) -> dict[str, object]:
    return {
        "artifact_type": artifact_type,
        "path": _report_path(path, mode=mode),
        "relative_path": _relative_to(path, root),
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _service_not_contacted(request: ComfyUIWorkflowRequest) -> dict[str, object]:
    return {
        "endpoint_url": request.endpoint_url,
        "http_status": None,
        "raw_sha256": _sha256_bytes(b""),
        "status": "NOT_CONTACTED",
        "system": {},
    }


def _empty_prompt() -> dict[str, object]:
    return {
        "http_status": None,
        "kind": "comfyui_prompt_response_summary_v1",
        "prompt_id": "",
        "prompt_response_sha256": _sha256_bytes(b""),
        "raw_prompt_persisted": False,
        "status": "NOT_SUBMITTED",
    }


def _empty_history() -> dict[str, object]:
    return {
        "complete": False,
        "history_response_sha256": _sha256_bytes(b""),
        "image_count": 0,
        "images": [],
        "kind": "comfyui_history_summary_v1",
        "prompt_id": "",
        "raw_history_persisted": False,
        "status": "NOT_POLLED",
    }


def _empty_outputs() -> dict[str, object]:
    return {
        "artifact_count": 0,
        "artifacts": [],
        "download_outputs": False,
        "skipped": [],
    }


def _next_actions(status: str) -> list[str]:
    if status == "EXECUTED":
        return ["Review downloaded artifacts and the history summary before promoting the workflow."]
    if status == "ENV_NOT_FOUND":
        return ["Provide a ComfyUI workflow exported in API format with --workflow-json."]
    if status == "SERVICE_UNAVAILABLE":
        return ["Start local ComfyUI on 127.0.0.1:8188 or pass --endpoint with a loopback URL."]
    if status == "USER_APPROVAL_REQUIRED":
        return ["Rerun with --approve-local-execution and a safe --approval-id after operator review."]
    if status == "LONG_TASK_BLOCKED":
        return ["Increase timeout only after confirming the local ComfyUI job is healthy."]
    return ["Inspect prompt/history summaries and fix workflow validation or local model errors."]


def _urllib_transport(
    method: str,
    url: str,
    body: bytes | None,
    headers: Mapping[str, str],
    timeout_seconds: float,
    max_response_bytes: int,
) -> ComfyUIHttpResponse:
    request = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read(max_response_bytes + 1)
            return ComfyUIHttpResponse(
                status_code=int(response.status),
                body=payload,
                headers={key.lower(): value for key, value in response.headers.items()},
            )
    except urllib.error.HTTPError as exc:
        payload = exc.read(max_response_bytes + 1)
        return ComfyUIHttpResponse(
            status_code=int(exc.code),
            body=payload,
            headers={key.lower(): value for key, value in exc.headers.items()},
        )
    except (TimeoutError, OSError, urllib.error.URLError) as exc:
        raise ComfyUITransportError(str(exc)) from exc


def _validated_endpoint_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "http":
        raise ComfyUILocalRunnerError("ComfyUI endpoint must use http")
    if parsed.username or parsed.password:
        raise ComfyUILocalRunnerError("ComfyUI endpoint may not include credentials")
    hostname = parsed.hostname or ""
    if hostname not in LOOPBACK_HOSTS:
        raise ComfyUILocalRunnerError("ComfyUI endpoint must be loopback only")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise ComfyUILocalRunnerError("ComfyUI endpoint must be a base URL without path/query/fragment")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")


def _url(endpoint_url: str, path_and_query: str) -> str:
    return endpoint_url.rstrip("/") + path_and_query


def _request_timeout(request: ComfyUIWorkflowRequest) -> float:
    return min(max(1.0, request.timeout_seconds), 30.0)


def _json_payload(body: bytes) -> object:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _write_json_once(path: Path, payload: object) -> None:
    if path.exists():
        raise ComfyUILocalRunnerError(f"refusing to overwrite {path.name}")
    write_json(path, payload)


def _write_bytes_once(path: Path, payload: bytes) -> None:
    if path.exists():
        raise ComfyUILocalRunnerError(f"refusing to overwrite {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _artifact_filename(descriptor: Mapping[str, object], *, index: int) -> str:
    node_id = SAFE_FILENAME_RE.sub("_", str(descriptor.get("node_id", "node"))).strip("._")
    source_name = Path(str(descriptor.get("filename", "artifact.bin"))).name
    safe_source = SAFE_FILENAME_RE.sub("_", source_name).strip("._") or "artifact.bin"
    if "." not in safe_source:
        safe_source += ".bin"
    return f"comfyui_output_{index:03d}_{node_id}_{safe_source}"


def _header_value(headers: Mapping[str, str] | None, name: str) -> str:
    if not headers:
        return ""
    lowered = {key.lower(): str(value) for key, value in headers.items()}
    return lowered.get(name.lower(), "")


def _ensure_contained(path: Path, root: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ComfyUILocalRunnerError("output artifact must stay inside output_root") from exc


def _relative_to(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _report_path(path: object, *, mode: str) -> str:
    if not path:
        return ""
    text = Path(path).as_posix() if isinstance(path, Path) else str(path)
    return text if mode == "local" else sanitize_path(text)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(READ_CHUNK_BYTES), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _clip(value: str, *, max_chars: int = 2000) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}\n...[output truncated at {max_chars} chars]"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
