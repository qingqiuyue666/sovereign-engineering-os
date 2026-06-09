"""ComfyUI local-service adapter."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from time import monotonic, sleep
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json
import subprocess

from creative.common import load_json, write_json
from execution_plane.adapters.base import AdapterContract, COMFYUI_LOCAL_ADAPTER, ProvisionResult
from execution_plane.artifacts import build_artifact_refs
from execution_plane.permits.builder import stable_id
from execution_plane.permits.validator import validate_execution_permit
from execution_plane.runner.path_guard import (
    PathGuardError,
    assert_within_root,
    resolve_output_root,
    validate_relative_output_path,
)
from execution_plane.runner.result_envelope import (
    build_execution_result,
    collect_output_records,
    sha256_file,
    utc_now,
)
from execution_plane.runtime.state_ledger import state_event
from execution_plane.runtime.token_policy import auto_provision_allowed, normalize_runtime_policy

DEFAULT_CONFIG_PATH = Path("config/local_adapters/comfyui_local.json")
DEFAULT_WORKFLOW_PATH = Path("examples/comfyui/workflows/minimal_save_image.json")


class ComfyUIClientError(RuntimeError):
    """Raised when the local ComfyUI HTTP API cannot complete a request."""

    def __init__(self, failure_code: str, message: str) -> None:
        self.failure_code = failure_code
        super().__init__(message)


class ComfyUIAdapterFailure(RuntimeError):
    """Normalized adapter failure used to write truthful failure bundles."""

    def __init__(self, failure_code: str, message: str, *, status: str = "FAILED") -> None:
        self.failure_code = failure_code
        self.status = status
        super().__init__(message)


class ComfyUIClient:
    """Small HTTP client for the local ComfyUI API."""

    def __init__(
        self,
        config: Mapping[str, Any] | None = None,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        client_id: str | None = None,
        output_directory_mapping: Mapping[str, Any] | None = None,
    ) -> None:
        cfg = dict(config or load_comfyui_config())
        self.base_url = str(base_url or cfg.get("base_url", "http://127.0.0.1:8188")).rstrip("/")
        self.timeout_seconds = float(timeout_seconds or cfg.get("timeout_seconds", 5.0))
        self.client_id = str(client_id or cfg.get("client_id") or stable_id("COMFYUI_CLIENT", "seos"))
        configured_mapping = cfg.get("output_directory_mapping")
        mapping = output_directory_mapping if isinstance(output_directory_mapping, Mapping) else configured_mapping
        self.output_directory_mapping = {
            "output": "comfyui_outputs",
            "temp": "comfyui_temp",
            "input": "comfyui_inputs",
        }
        if isinstance(mapping, Mapping):
            self.output_directory_mapping.update({str(key): str(value) for key, value in mapping.items()})

    def system_stats(self) -> dict[str, Any]:
        return self._request_json("GET", "/system_stats")

    def submit_prompt(self, workflow: Mapping[str, Any], *, prompt_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"prompt": dict(workflow), "client_id": self.client_id}
        if prompt_id:
            payload["prompt_id"] = prompt_id
        return self._request_json("POST", "/prompt", payload)

    def history(self, prompt_id: str) -> dict[str, Any]:
        safe_prompt_id = str(prompt_id).strip()
        if not safe_prompt_id:
            raise ComfyUIClientError("SCHEMA_INVALID", "prompt_id_required")
        return self._request_json("GET", f"/history/{safe_prompt_id}")

    def view(self, *, filename: str, subfolder: str = "", output_type: str = "output") -> bytes:
        query = urlencode({"filename": filename, "subfolder": subfolder, "type": output_type})
        return self._request_bytes("GET", f"/view?{query}")

    def _request_json(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, sort_keys=True).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read()
        except HTTPError as exc:
            detail = _read_http_error(exc)
            raise ComfyUIClientError(f"HTTP_{exc.code}", detail) from exc
        except (OSError, URLError, TimeoutError) as exc:
            raise ComfyUIClientError("SERVICE_UNAVAILABLE", str(exc)) from exc
        try:
            decoded = body.decode("utf-8")
            return json.loads(decoded) if decoded.strip() else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ComfyUIClientError("RESPONSE_INVALID", "json_response_invalid") from exc

    def _request_bytes(self, method: str, path: str) -> bytes:
        request = Request(self.base_url + path, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            detail = _read_http_error(exc)
            raise ComfyUIClientError(f"HTTP_{exc.code}", detail) from exc
        except (OSError, URLError, TimeoutError) as exc:
            raise ComfyUIClientError("SERVICE_UNAVAILABLE", str(exc)) from exc


def load_comfyui_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return {
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "base_url": "http://127.0.0.1:8188",
            "client_id": "seos-comfyui-local",
            "launch_command": [],
            "working_dir": "",
            "heartbeat_path": "/system_stats",
            "startup_timeout_seconds": 90,
            "timeout_seconds": 5,
            "output_directory_mapping": {
                "output": "comfyui_outputs",
                "temp": "comfyui_temp",
                "input": "comfyui_inputs",
            },
        }
    return dict(load_json(path))


def probe_comfyui(config: Mapping[str, Any] | None = None, *, timeout_seconds: float = 1.0) -> dict[str, Any]:
    cfg = dict(config or load_comfyui_config())
    base_url = str(cfg.get("base_url", "http://127.0.0.1:8188")).rstrip("/")
    try:
        client = ComfyUIClient(cfg, base_url=base_url, timeout_seconds=timeout_seconds)
        stats = client.system_stats()
        return {
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "available": True,
            "status": "READY",
            "heartbeat_status": "READY",
            "base_url": base_url,
            "system_stats": _summarize_mapping(stats),
        }
    except ComfyUIClientError:
        return {
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "available": False,
            "status": "BLOCKED",
            "heartbeat_status": "UNAVAILABLE",
            "base_url": base_url,
        }


def validate_comfyui_workflow(workflow: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the minimal executable ComfyUI prompt shape before submission."""

    if not isinstance(workflow, Mapping) or not workflow:
        raise ComfyUIAdapterFailure("SCHEMA_INVALID", "workflow_must_be_nonempty_mapping", status="BLOCKED")
    try:
        json.dumps(workflow, sort_keys=True)
    except TypeError as exc:
        raise ComfyUIAdapterFailure("SCHEMA_INVALID", "workflow_must_be_json_serializable", status="BLOCKED") from exc
    normalized: dict[str, Any] = {}
    for node_id, raw_node in workflow.items():
        if not isinstance(node_id, str) or not node_id.strip():
            raise ComfyUIAdapterFailure("SCHEMA_INVALID", "workflow_node_id_required", status="BLOCKED")
        if not isinstance(raw_node, Mapping):
            raise ComfyUIAdapterFailure("SCHEMA_INVALID", f"workflow_node_must_be_mapping:{node_id}", status="BLOCKED")
        class_type = raw_node.get("class_type")
        inputs = raw_node.get("inputs")
        if not isinstance(class_type, str) or not class_type.strip():
            raise ComfyUIAdapterFailure("SCHEMA_INVALID", f"workflow_node_class_type_required:{node_id}", status="BLOCKED")
        if not isinstance(inputs, Mapping):
            raise ComfyUIAdapterFailure("SCHEMA_INVALID", f"workflow_node_inputs_required:{node_id}", status="BLOCKED")
        normalized[node_id] = {**dict(raw_node), "class_type": class_type, "inputs": dict(inputs)}
    return normalized


def collect_comfyui_outputs(
    *,
    client: ComfyUIClient,
    history_payload: Mapping[str, Any],
    prompt_id: str,
    output_root: Path,
) -> list[dict[str, Any]]:
    """Download ComfyUI history outputs through /view and write local files."""

    outputs_by_node = _history_outputs(history_payload, prompt_id)
    collected: list[dict[str, Any]] = []
    for node_id, node_outputs in outputs_by_node.items():
        if not isinstance(node_outputs, Mapping):
            continue
        for bucket_name, raw_items in node_outputs.items():
            if not isinstance(raw_items, list):
                continue
            for index, item in enumerate(raw_items):
                if not isinstance(item, Mapping):
                    continue
                filename = str(item.get("filename", "")).strip()
                if not filename:
                    continue
                subfolder = str(item.get("subfolder", "")).strip()
                output_type = str(item.get("type", "output")).strip() or "output"
                payload = client.view(filename=filename, subfolder=subfolder, output_type=output_type)
                local_relpath = _comfyui_local_output_path(
                    client=client,
                    output_type=output_type,
                    subfolder=subfolder,
                    filename=filename,
                    bucket_name=str(bucket_name),
                    index=index,
                )
                local_path = assert_within_root(local_relpath, output_root)
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(payload)
                collected.append(
                    {
                        "node_id": str(node_id),
                        "bucket": str(bucket_name),
                        "source": {"filename": filename, "subfolder": subfolder, "type": output_type},
                        "relative_path": local_path.relative_to(output_root.resolve()).as_posix(),
                        "size_bytes": local_path.stat().st_size,
                        "sha256": sha256_file(local_path),
                    }
                )
    return collected


def _read_http_error(exc: HTTPError) -> str:
    try:
        detail = exc.read(4096).decode("utf-8", errors="replace")
    finally:
        exc.close()
    return detail or str(exc)


def _summarize_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): payload[key] for key in sorted(payload)[:8]}


def _history_outputs(history_payload: Mapping[str, Any], prompt_id: str) -> Mapping[str, Any]:
    if prompt_id in history_payload and isinstance(history_payload[prompt_id], Mapping):
        prompt_record = history_payload[prompt_id]
    else:
        prompt_record = history_payload
    outputs = prompt_record.get("outputs") if isinstance(prompt_record, Mapping) else None
    if isinstance(outputs, Mapping):
        return outputs
    return {}


def _comfyui_local_output_path(
    *,
    client: ComfyUIClient,
    output_type: str,
    subfolder: str,
    filename: str,
    bucket_name: str,
    index: int,
) -> str:
    base_dir = client.output_directory_mapping.get(output_type, client.output_directory_mapping.get("output", "comfyui_outputs"))
    parts = [base_dir]
    if subfolder:
        parts.append(subfolder)
    safe_name = filename or f"{bucket_name}_{index}.bin"
    parts.append(safe_name)
    return validate_relative_output_path("/".join(part.strip("/") for part in parts if part))


class ComfyUILocalAdapter(AdapterContract):
    name = COMFYUI_LOCAL_ADAPTER
    actions = frozenset({"service_probe", "submit_workflow", "poll_history", "collect_outputs"})

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path

    def detect(self) -> dict[str, Any]:
        return probe_comfyui(load_comfyui_config(self.config_path))

    def preflight(self, action: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if action not in self.actions:
            return {"adapter": self.name, "action": action, "status": "BLOCKED", "failure_code": "METHOD_NOT_ALLOWED"}
        detected = self.detect()
        return {
            "adapter": self.name,
            "action": action,
            "status": "READY" if detected["available"] else "BLOCKED",
            "failure_code": None if detected["available"] else "SERVICE_UNAVAILABLE",
        }

    def auto_provision(self, intent: Mapping[str, Any], policy: Mapping[str, Any]) -> ProvisionResult:
        cfg = load_comfyui_config(self.config_path)
        token = {**dict(intent), **dict(policy)}
        if not auto_provision_allowed(token, self.name):
            return ProvisionResult(adapter=self.name, status="SKIPPED", method="policy_denied")
        launch_command = cfg.get("launch_command")
        working_dir = str(cfg.get("working_dir", ""))
        if not isinstance(launch_command, list) or not launch_command:
            return ProvisionResult(
                adapter=self.name,
                status="FAILED",
                method="launch_command",
                heartbeat_status="UNAVAILABLE",
                details={"failure_code": "AUTO_PROVISION_FAILED", "reason": "launch_command_not_configured"},
            )
        cwd = Path(working_dir)
        if not cwd.exists():
            return ProvisionResult(
                adapter=self.name,
                status="FAILED",
                method="launch_command",
                heartbeat_status="UNAVAILABLE",
                details={"failure_code": "AUTO_PROVISION_FAILED", "reason": "working_dir_missing"},
            )
        started = monotonic()
        process = subprocess.Popen(
            [str(part) for part in launch_command],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        runtime_policy = normalize_runtime_policy(token)
        wait_seconds = int(runtime_policy["auto_provision"]["max_wait_seconds"]) or int(
            cfg.get("startup_timeout_seconds", 90)
        )
        heartbeat_interval = int(runtime_policy["auto_provision"]["heartbeat_interval_seconds"])
        while monotonic() - started <= wait_seconds:
            probe = probe_comfyui(cfg, timeout_seconds=1.0)
            if probe["available"]:
                return ProvisionResult(
                    adapter=self.name,
                    status="PROVISIONED",
                    method="launch_command",
                    pid=process.pid,
                    heartbeat_status="READY",
                    elapsed_ms=int((monotonic() - started) * 1000),
                )
            sleep(heartbeat_interval)
        return ProvisionResult(
            adapter=self.name,
            status="FAILED",
            method="launch_command",
            pid=process.pid,
            heartbeat_status="UNAVAILABLE",
            elapsed_ms=int((monotonic() - started) * 1000),
            details={"failure_code": "AUTO_PROVISION_FAILED"},
        )

    def execute(self, permit: Mapping[str, Any], payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        checked = validate_execution_permit(permit, expected_adapter=self.name)
        started_at = utc_now()
        run_id = stable_id("RUN", checked["permit_id"], started_at, self.name)
        output_root = resolve_output_root(str(checked["allowed_output_root"]))
        output_root.mkdir(parents=True, exist_ok=True)
        transitions = [
            state_event(run_id=run_id, adapter=self.name, state="PREFLIGHTING"),
        ]
        payload_data = dict(payload or {})
        cfg = load_comfyui_config(self.config_path)
        client = ComfyUIClient(
            cfg,
            timeout_seconds=payload_data.get("timeout_seconds")
            if isinstance(payload_data.get("timeout_seconds"), (int, float))
            else None,
            client_id=str(payload_data.get("client_id")) if payload_data.get("client_id") else None,
            output_directory_mapping=payload_data.get("output_directory_mapping")
            if isinstance(payload_data.get("output_directory_mapping"), Mapping)
            else None,
        )
        detected = self.detect()
        provision: dict[str, Any] = {}
        if not detected["available"]:
            transitions.append(state_event(run_id=run_id, adapter=self.name, state="PROVISIONING"))
            provision = self.auto_provision(checked, checked).as_dict()
            detected = self.detect()
        if not detected["available"]:
            transitions.append(
                state_event(
                    run_id=run_id,
                    adapter=self.name,
                    state="FAILED",
                    detail={"failure_code": provision.get("details", {}).get("failure_code", "SERVICE_UNAVAILABLE")},
                )
            )
            return _finalize_comfyui_result(
                permit=checked,
                run_id=run_id,
                started_at=started_at,
                exit_code=-1,
                status="BLOCKED",
                output_root=output_root,
                stdout="",
                stderr="",
                failure_summary="SERVICE_UNAVAILABLE: ComfyUI heartbeat unavailable",
                policy_blocks=["SERVICE_UNAVAILABLE"],
                state_transitions=transitions,
                provision_result=provision,
            )
        transitions.append(state_event(run_id=run_id, adapter=self.name, state="RUNNING"))
        try:
            action_result = _run_comfyui_action(
                action=str(checked["allowed_action"]),
                payload=payload_data,
                client=client,
                output_root=output_root,
                run_id=run_id,
                permit=checked,
                detected=detected,
            )
        except ComfyUIAdapterFailure as exc:
            transitions.append(
                state_event(
                    run_id=run_id,
                    adapter=self.name,
                    state="FAILED",
                    detail={"failure_code": exc.failure_code},
                )
            )
            return _finalize_comfyui_result(
                permit=checked,
                run_id=run_id,
                started_at=started_at,
                exit_code=-1,
                status=exc.status,
                output_root=output_root,
                stdout="",
                stderr=str(exc),
                failure_summary=f"{exc.failure_code}: {exc}",
                policy_blocks=[exc.failure_code],
                state_transitions=transitions,
                provision_result=provision,
            )
        except ComfyUIClientError as exc:
            transitions.append(
                state_event(
                    run_id=run_id,
                    adapter=self.name,
                    state="FAILED",
                    detail={"failure_code": exc.failure_code},
                )
            )
            return _finalize_comfyui_result(
                permit=checked,
                run_id=run_id,
                started_at=started_at,
                exit_code=-1,
                status="BLOCKED" if exc.failure_code == "SERVICE_UNAVAILABLE" else "FAILED",
                output_root=output_root,
                stdout="",
                stderr=str(exc),
                failure_summary=f"{exc.failure_code}: {exc}",
                policy_blocks=[exc.failure_code],
                state_transitions=transitions,
                provision_result=provision,
            )
        except PathGuardError as exc:
            transitions.append(
                state_event(
                    run_id=run_id,
                    adapter=self.name,
                    state="FAILED",
                    detail={"failure_code": "OUTPUT_INVALID"},
                )
            )
            return _finalize_comfyui_result(
                permit=checked,
                run_id=run_id,
                started_at=started_at,
                exit_code=-1,
                status="BLOCKED",
                output_root=output_root,
                stdout="",
                stderr=str(exc),
                failure_summary=f"OUTPUT_INVALID: {exc}",
                policy_blocks=["OUTPUT_INVALID"],
                state_transitions=transitions,
                provision_result=provision,
            )
        transitions.append(state_event(run_id=run_id, adapter=self.name, state="COLLECTING"))
        write_json(
            output_root / "comfyui_action_result.json",
            {
                "schema_version": "seos.comfyui.action_result.v1",
                "adapter": self.name,
                "action": checked["allowed_action"],
                "run_id": run_id,
                "result": action_result,
            },
        )
        transitions.append(state_event(run_id=run_id, adapter=self.name, state="SUCCEEDED"))
        return _finalize_comfyui_result(
            permit=checked,
            run_id=run_id,
            started_at=started_at,
            exit_code=0,
            status="SUCCEEDED",
            output_root=output_root,
            stdout="comfyui_local completed",
            stderr="",
            failure_summary=None,
            policy_blocks=[],
            state_transitions=transitions,
            provision_result=provision,
        )


def _run_comfyui_action(
    *,
    action: str,
    payload: Mapping[str, Any],
    client: ComfyUIClient,
    output_root: Path,
    run_id: str,
    permit: Mapping[str, Any],
    detected: Mapping[str, Any],
) -> dict[str, Any]:
    if action == "service_probe":
        stats = client.system_stats()
        artifact = {
            "schema_version": "seos.comfyui.service_probe.v1",
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "action": action,
            "run_id": run_id,
            "permit_id": permit["permit_id"],
            "heartbeat_status": detected.get("heartbeat_status", "READY"),
            "base_url": client.base_url,
            "system_stats": _summarize_mapping(stats),
        }
        write_json(output_root / "comfyui_service_probe.json", artifact)
        return {"status": "SUCCEEDED", "artifact_path": "comfyui_service_probe.json"}

    if action == "submit_workflow":
        workflow, workflow_source = _load_workflow(payload)
        write_json(output_root / "workflow_submitted.json", workflow)
        response = client.submit_prompt(workflow, prompt_id=str(payload.get("prompt_id", "")) or None)
        prompt_id = _extract_prompt_id(response)
        write_json(
            output_root / "prompt_response.json",
            {
                "schema_version": "seos.comfyui.prompt_response.v1",
                "run_id": run_id,
                "workflow_source": workflow_source,
                "response": response,
                "prompt_id": prompt_id,
            },
        )
        history = _poll_history(
            client=client,
            prompt_id=prompt_id,
            timeout_seconds=float(payload.get("history_timeout_seconds", 60)),
            poll_interval_seconds=float(payload.get("poll_interval_seconds", 1)),
        )
        write_json(output_root / "history.json", history)
        collected = collect_comfyui_outputs(
            client=client,
            history_payload=history,
            prompt_id=prompt_id,
            output_root=output_root,
        )
        write_json(
            output_root / "collected_outputs.json",
            {
                "schema_version": "seos.comfyui.collected_outputs.v1",
                "run_id": run_id,
                "prompt_id": prompt_id,
                "outputs": collected,
            },
        )
        if not collected:
            raise ComfyUIAdapterFailure("OUTPUT_MISSING", "ComfyUI completed without downloadable outputs")
        return {"status": "SUCCEEDED", "prompt_id": prompt_id, "outputs": collected}

    if action == "poll_history":
        prompt_id = str(payload.get("prompt_id", "")).strip()
        if not prompt_id:
            raise ComfyUIAdapterFailure("SCHEMA_INVALID", "prompt_id_required", status="BLOCKED")
        history = client.history(prompt_id)
        write_json(output_root / "history.json", history)
        return {"status": "SUCCEEDED", "prompt_id": prompt_id, "history_path": "history.json"}

    if action == "collect_outputs":
        prompt_id = str(payload.get("prompt_id", "")).strip()
        history = payload.get("history") if isinstance(payload.get("history"), Mapping) else None
        if not history:
            if not prompt_id:
                raise ComfyUIAdapterFailure("SCHEMA_INVALID", "prompt_id_or_history_required", status="BLOCKED")
            history = client.history(prompt_id)
        if not prompt_id:
            prompt_id = _first_history_prompt_id(history)
        write_json(output_root / "history.json", history)
        collected = collect_comfyui_outputs(
            client=client,
            history_payload=history,
            prompt_id=prompt_id,
            output_root=output_root,
        )
        write_json(
            output_root / "collected_outputs.json",
            {
                "schema_version": "seos.comfyui.collected_outputs.v1",
                "run_id": run_id,
                "prompt_id": prompt_id,
                "outputs": collected,
            },
        )
        if not collected:
            raise ComfyUIAdapterFailure("OUTPUT_MISSING", "no ComfyUI outputs found in history")
        return {"status": "SUCCEEDED", "prompt_id": prompt_id, "outputs": collected}

    raise ComfyUIAdapterFailure("METHOD_NOT_ALLOWED", f"unsupported_action:{action}", status="BLOCKED")


def _load_workflow(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    raw_workflow = payload.get("workflow")
    if isinstance(raw_workflow, Mapping):
        return validate_comfyui_workflow(raw_workflow), "payload.workflow"
    workflow_path = Path(str(payload.get("workflow_path") or DEFAULT_WORKFLOW_PATH))
    if not workflow_path.exists():
        raise ComfyUIAdapterFailure("SCHEMA_INVALID", f"workflow_file_missing:{workflow_path}", status="BLOCKED")
    loaded = load_json(workflow_path)
    return validate_comfyui_workflow(loaded), workflow_path.as_posix()


def _extract_prompt_id(response: Mapping[str, Any]) -> str:
    for key in ("prompt_id", "id"):
        value = response.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ComfyUIAdapterFailure("RESPONSE_INVALID", "prompt_response_missing_prompt_id")


def _poll_history(
    *,
    client: ComfyUIClient,
    prompt_id: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    started = monotonic()
    last_history: dict[str, Any] = {}
    bounded_timeout = max(0.0, timeout_seconds)
    interval = max(0.0, min(poll_interval_seconds, 5.0))
    while True:
        history = client.history(prompt_id)
        last_history = history
        if _history_outputs(history, prompt_id):
            return history
        if monotonic() - started >= bounded_timeout:
            return last_history
        if interval:
            sleep(interval)


def _first_history_prompt_id(history: Mapping[str, Any]) -> str:
    for key, value in history.items():
        if isinstance(key, str) and isinstance(value, Mapping) and "outputs" in value:
            return key
    return "prompt"


def _finalize_comfyui_result(
    *,
    permit: Mapping[str, Any],
    run_id: str,
    started_at: str,
    exit_code: int,
    status: str,
    output_root: Path,
    stdout: str,
    stderr: str,
    failure_summary: str | None,
    policy_blocks: list[str],
    state_transitions: list[dict[str, Any]],
    provision_result: Mapping[str, Any],
) -> dict[str, Any]:
    action = str(permit.get("allowed_action", "comfyui_action"))
    if failure_summary:
        _write_failure_bundle(
            output_root=output_root,
            permit=permit,
            run_id=run_id,
            action=action,
            status=status,
            failure_summary=failure_summary,
            policy_blocks=policy_blocks,
            state_transitions=state_transitions,
            provision_result=provision_result,
        )
    _write_artifact_manifest(output_root=output_root, run_id=run_id, action=action)
    _write_execution_receipt(
        output_root=output_root,
        permit=permit,
        run_id=run_id,
        action=action,
        started_at=started_at,
        ended_at=utc_now(),
        exit_code=exit_code,
        status=status,
        failure_summary=failure_summary,
        policy_blocks=policy_blocks,
        state_transitions=state_transitions,
        provision_result=provision_result,
    )
    outputs = collect_output_records(output_root)
    return build_execution_result(
        permit=permit,
        run_id=run_id,
        started_at=started_at,
        ended_at=utc_now(),
        exit_code=exit_code,
        status=status,
        output_root=output_root,
        outputs=outputs,
        stdout=stdout,
        stderr=stderr,
        failure_summary=failure_summary,
        policy_blocks=policy_blocks,
        evidence_manifest_path="artifact_manifest.json",
        state_transitions=state_transitions,
        provision_result=provision_result,
    )


def _write_artifact_manifest(*, output_root: Path, run_id: str, action: str) -> None:
    outputs = collect_output_records(output_root)
    refs = build_artifact_refs(run_id=run_id, node_id=action, output_records=outputs)
    write_json(
        output_root / "artifact_manifest.json",
        {
            "schema_version": "seos.artifact_manifest.v1",
            "run_id": run_id,
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "action": action,
            "outputs": outputs,
            "artifact_refs": refs,
        },
    )


def _write_execution_receipt(
    *,
    output_root: Path,
    permit: Mapping[str, Any],
    run_id: str,
    action: str,
    started_at: str,
    ended_at: str,
    exit_code: int,
    status: str,
    failure_summary: str | None,
    policy_blocks: list[str],
    state_transitions: list[dict[str, Any]],
    provision_result: Mapping[str, Any],
) -> None:
    outputs = collect_output_records(output_root)
    refs = build_artifact_refs(run_id=run_id, node_id=action, output_records=outputs)
    write_json(
        output_root / "execution_receipt.json",
        {
            "schema_version": "seos.execution_receipt.v1",
            "run_id": run_id,
            "permit_id": permit["permit_id"],
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "action": action,
            "started_at": started_at,
            "ended_at": ended_at,
            "exit_code": exit_code,
            "status": status,
            "failure_summary": failure_summary,
            "policy_blocks": policy_blocks,
            "artifact_manifest_path": "artifact_manifest.json",
            "failure_bundle_path": "failure_bundle.json" if failure_summary else None,
            "artifact_refs": refs,
            "state_transitions": state_transitions,
            "provision_result": dict(provision_result),
        },
    )


def _write_failure_bundle(
    *,
    output_root: Path,
    permit: Mapping[str, Any],
    run_id: str,
    action: str,
    status: str,
    failure_summary: str,
    policy_blocks: list[str],
    state_transitions: list[dict[str, Any]],
    provision_result: Mapping[str, Any],
) -> None:
    write_json(
        output_root / "failure_bundle.json",
        {
            "schema_version": "seos.failure_bundle.v1",
            "run_id": run_id,
            "permit_id": permit["permit_id"],
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "action": action,
            "status": status,
            "failure_summary": failure_summary,
            "failure_code": policy_blocks[0] if policy_blocks else "EXECUTION_FAILED",
            "policy_blocks": policy_blocks,
            "state_transitions": state_transitions,
            "provision_result": dict(provision_result),
            "repair_hint": {
                "retryable": bool(policy_blocks and policy_blocks[0] in {"SERVICE_UNAVAILABLE", "TIMEOUT"}),
                "local_runbook": "docs/runbooks/comfyui_real_local_execution.md",
            },
        },
    )
