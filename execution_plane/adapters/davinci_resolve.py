"""DaVinci Resolve local scripting adapter."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from time import monotonic, sleep
from typing import Any
import importlib
import subprocess

from creative.common import load_json, write_json
from execution_plane.adapters.base import AdapterContract, DAVINCI_RESOLVE_ADAPTER, ProvisionResult
from execution_plane.artifacts import build_artifact_refs
from execution_plane.permits.builder import stable_id
from execution_plane.permits.validator import validate_execution_permit
from execution_plane.runner.path_guard import resolve_output_root
from execution_plane.runner.result_envelope import build_execution_result, collect_output_records, utc_now
from execution_plane.runtime.state_ledger import state_event
from execution_plane.runtime.token_policy import auto_provision_allowed, normalize_runtime_policy

DEFAULT_CONFIG_PATH = Path("config/local_adapters/davinci_resolve.json")


class DaVinciAdapterFailure(RuntimeError):
    """Normalized DaVinci adapter failure."""

    def __init__(self, failure_code: str, message: str, *, status: str = "BLOCKED") -> None:
        self.failure_code = failure_code
        self.status = status
        super().__init__(message)


def load_davinci_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return {
            "adapter": DAVINCI_RESOLVE_ADAPTER,
            "app_name": "DaVinci Resolve",
            "startup_command": ["open", "-a", "DaVinci Resolve"],
            "startup_timeout_seconds": 120,
            "api_probe_script": "execution_plane/adapters/scripts/probe_davinci_api.py",
        }
    return dict(load_json(path))


def probe_davinci(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    attached = attach_davinci_api(config)
    available = attached["status"] == "SUCCEEDED"
    return {
        "adapter": DAVINCI_RESOLVE_ADAPTER,
        "available": available,
        "status": "READY" if available else "BLOCKED",
        "failure_code": None if available else attached["status"],
        "app_running": bool(attached.get("app_running")),
        "api_probe_script_available": bool(attached.get("api_probe_script_available")),
    }


def attach_davinci_api(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Attempt to load and attach the local DaVinci Resolve scripting API."""

    cfg = dict(config or load_davinci_config())
    probe_script = Path(str(cfg.get("api_probe_script", "")))
    module = _load_resolve_script_module()
    if module is None:
        return {
            "status": "DEPENDENCY_BLOCKED",
            "app_running": _process_running(("DaVinci Resolve", "Resolve")),
            "api_probe_script_available": probe_script.exists(),
            "resolve": None,
        }
    app_running = _process_running(("DaVinci Resolve", "Resolve"))
    if not app_running:
        return {
            "status": "APP_NOT_RUNNING",
            "app_running": False,
            "api_probe_script_available": probe_script.exists(),
            "resolve": None,
        }
    try:
        resolve = module.scriptapp("Resolve")
    except Exception as exc:
        return {
            "status": "API_ATTACH_FAILED",
            "app_running": True,
            "api_probe_script_available": probe_script.exists(),
            "error": exc.__class__.__name__,
            "resolve": None,
        }
    if resolve is None:
        return {
            "status": "API_ATTACH_FAILED",
            "app_running": True,
            "api_probe_script_available": probe_script.exists(),
            "resolve": None,
        }
    return {
        "status": "SUCCEEDED",
        "app_running": True,
        "api_probe_script_available": probe_script.exists(),
        "resolve": resolve,
    }


def _load_resolve_script_module() -> Any | None:
    try:
        return importlib.import_module("DaVinciResolveScript")
    except Exception:
        return None


class DaVinciResolveAdapter(AdapterContract):
    name = DAVINCI_RESOLVE_ADAPTER
    actions = frozenset({"version_probe", "project_probe", "timeline_export_probe", "render_preset_test"})

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path

    def detect(self) -> dict[str, Any]:
        return probe_davinci(load_davinci_config(self.config_path))

    def preflight(self, action: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if action not in self.actions:
            return {"adapter": self.name, "action": action, "status": "BLOCKED", "failure_code": "METHOD_NOT_ALLOWED"}
        detected = self.detect()
        return {
            "adapter": self.name,
            "action": action,
            "status": "READY" if detected["available"] else "BLOCKED",
            "failure_code": None if detected["available"] else detected.get("failure_code", "DEPENDENCY_BLOCKED"),
        }

    def auto_provision(self, intent: Mapping[str, Any], policy: Mapping[str, Any]) -> ProvisionResult:
        cfg = load_davinci_config(self.config_path)
        token = {**dict(intent), **dict(policy)}
        if not auto_provision_allowed(token, self.name):
            return ProvisionResult(adapter=self.name, status="SKIPPED", method="policy_denied")
        startup_command = cfg.get("startup_command")
        if not isinstance(startup_command, list) or not startup_command:
            return ProvisionResult(
                adapter=self.name,
                status="FAILED",
                method="app_launch",
                heartbeat_status="UNAVAILABLE",
                details={"failure_code": "AUTO_PROVISION_FAILED", "reason": "startup_command_not_configured"},
            )
        started = monotonic()
        completed = subprocess.run([str(part) for part in startup_command], check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            return ProvisionResult(
                adapter=self.name,
                status="FAILED",
                method="app_launch",
                heartbeat_status="UNAVAILABLE",
                elapsed_ms=int((monotonic() - started) * 1000),
                details={"failure_code": "AUTO_PROVISION_FAILED", "returncode": completed.returncode},
            )
        runtime_policy = normalize_runtime_policy(token)
        wait_seconds = int(runtime_policy["auto_provision"]["max_wait_seconds"]) or int(
            cfg.get("startup_timeout_seconds", 120)
        )
        heartbeat_interval = int(runtime_policy["auto_provision"]["heartbeat_interval_seconds"])
        while monotonic() - started <= wait_seconds:
            probe = self.detect()
            if probe["available"]:
                return ProvisionResult(
                    adapter=self.name,
                    status="PROVISIONED",
                    method="app_launch",
                    heartbeat_status="READY",
                    elapsed_ms=int((monotonic() - started) * 1000),
                )
            sleep(heartbeat_interval)
        return ProvisionResult(
            adapter=self.name,
            status="FAILED",
            method="app_launch",
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
        transitions = [state_event(run_id=run_id, adapter=self.name, state="PREFLIGHTING")]
        cfg = load_davinci_config(self.config_path)
        attached = attach_davinci_api(cfg)
        provision: dict[str, Any] = {}
        if attached["status"] == "APP_NOT_RUNNING" or (
            attached["status"] == "DEPENDENCY_BLOCKED" and not attached.get("app_running")
        ):
            transitions.append(state_event(run_id=run_id, adapter=self.name, state="PROVISIONING"))
            provision = self.auto_provision(checked, checked).as_dict()
            attached = attach_davinci_api(cfg)
        if attached["status"] != "SUCCEEDED":
            failure_code = str(attached["status"])
            transitions.append(
                state_event(
                    run_id=run_id,
                    adapter=self.name,
                    state="FAILED",
                    detail={"failure_code": provision.get("details", {}).get("failure_code", failure_code)},
                )
            )
            return _finalize_davinci_result(
                permit=checked,
                run_id=run_id,
                started_at=started_at,
                exit_code=-1,
                status="BLOCKED",
                output_root=output_root,
                stdout="",
                stderr="",
                failure_summary=f"{failure_code}: DaVinci Resolve scripting API unavailable",
                policy_blocks=[failure_code],
                state_transitions=transitions,
                provision_result=provision,
            )
        transitions.append(state_event(run_id=run_id, adapter=self.name, state="RUNNING"))
        try:
            action_result = _run_davinci_action(
                action=str(checked["allowed_action"]),
                payload=dict(payload or {}),
                resolve=attached["resolve"],
                output_root=output_root,
                run_id=run_id,
            )
        except DaVinciAdapterFailure as exc:
            transitions.append(
                state_event(
                    run_id=run_id,
                    adapter=self.name,
                    state="FAILED",
                    detail={"failure_code": exc.failure_code},
                )
            )
            return _finalize_davinci_result(
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
        transitions.append(state_event(run_id=run_id, adapter=self.name, state="COLLECTING"))
        write_json(
            output_root / "davinci_action_result.json",
            {
                "schema_version": "seos.davinci.action_result.v1",
                "adapter": self.name,
                "action": checked["allowed_action"],
                "run_id": run_id,
                "result": action_result,
            },
        )
        transitions.append(state_event(run_id=run_id, adapter=self.name, state="SUCCEEDED"))
        return _finalize_davinci_result(
            permit=checked,
            run_id=run_id,
            started_at=started_at,
            exit_code=0,
            status="SUCCEEDED",
            output_root=output_root,
            stdout="davinci_resolve completed",
            stderr="",
            failure_summary=None,
            policy_blocks=[],
            state_transitions=transitions,
            provision_result=provision,
        )


def _run_davinci_action(
    *,
    action: str,
    payload: Mapping[str, Any],
    resolve: Any,
    output_root: Path,
    run_id: str,
) -> dict[str, Any]:
    if action == "version_probe":
        version = _call_optional(resolve, "GetVersionString")
        if version is None:
            version = _call_optional(resolve, "GetVersion")
        artifact = {
            "schema_version": "seos.davinci.version_probe.v1",
            "adapter": DAVINCI_RESOLVE_ADAPTER,
            "action": action,
            "run_id": run_id,
            "status": "SUCCEEDED",
            "version": version,
        }
        write_json(output_root / "davinci_version_probe.json", artifact)
        return {"status": "SUCCEEDED", "artifact_path": "davinci_version_probe.json", "version": version}

    if action == "project_probe":
        project_name = str(payload.get("project_name", "")).strip()
        project = _resolve_project(resolve, project_name=project_name or None)
        if project is None:
            raise DaVinciAdapterFailure("PROJECT_NOT_FOUND", project_name or "current_project_missing")
        name = _call_optional(project, "GetName") or project_name or "UNKNOWN"
        timeline = _call_optional(project, "GetCurrentTimeline")
        artifact = {
            "schema_version": "seos.davinci.project_probe.v1",
            "adapter": DAVINCI_RESOLVE_ADAPTER,
            "action": action,
            "run_id": run_id,
            "status": "SUCCEEDED",
            "project_name": name,
            "current_timeline_name": _call_optional(timeline, "GetName") if timeline is not None else None,
        }
        write_json(output_root / "davinci_project_probe.json", artifact)
        return {"status": "SUCCEEDED", "artifact_path": "davinci_project_probe.json", "project_name": name}

    if action in {"timeline_export_probe", "render_preset_test"}:
        project = _resolve_project(resolve, project_name=None)
        if project is None:
            raise DaVinciAdapterFailure("PROJECT_NOT_FOUND", "current_project_missing")
        artifact_path = output_root / f"davinci_{action}.json"
        artifact = {
            "schema_version": f"seos.davinci.{action}.v1",
            "adapter": DAVINCI_RESOLVE_ADAPTER,
            "action": action,
            "run_id": run_id,
            "status": "SUCCEEDED",
            "project_name": _call_optional(project, "GetName"),
            "capability_note": "probe only; no render or timeline mutation performed",
        }
        write_json(artifact_path, artifact)
        return {"status": "SUCCEEDED", "artifact_path": artifact_path.name}

    raise DaVinciAdapterFailure("METHOD_NOT_ALLOWED", f"unsupported_action:{action}")


def _resolve_project(resolve: Any, *, project_name: str | None) -> Any | None:
    manager = _call_optional(resolve, "GetProjectManager")
    if manager is None:
        raise DaVinciAdapterFailure("API_ATTACH_FAILED", "project_manager_unavailable")
    if project_name:
        project = _call_optional(manager, "LoadProject", project_name)
        if project is not None:
            return project
    return _call_optional(manager, "GetCurrentProject")


def _call_optional(target: Any, method_name: str, *args: object) -> Any:
    if target is None:
        return None
    method = getattr(target, method_name, None)
    if not callable(method):
        return None
    try:
        return method(*args)
    except Exception:
        return None


def _finalize_davinci_result(
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
    action = str(permit.get("allowed_action", "davinci_action"))
    if failure_summary:
        _write_davinci_failure_bundle(
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
    _write_davinci_artifact_manifest(output_root=output_root, run_id=run_id, action=action)
    _write_davinci_execution_receipt(
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


def _write_davinci_artifact_manifest(*, output_root: Path, run_id: str, action: str) -> None:
    outputs = collect_output_records(output_root)
    refs = build_artifact_refs(run_id=run_id, node_id=action, output_records=outputs)
    write_json(
        output_root / "artifact_manifest.json",
        {
            "schema_version": "seos.artifact_manifest.v1",
            "run_id": run_id,
            "adapter": DAVINCI_RESOLVE_ADAPTER,
            "action": action,
            "outputs": outputs,
            "artifact_refs": refs,
        },
    )


def _write_davinci_execution_receipt(
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
            "adapter": DAVINCI_RESOLVE_ADAPTER,
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


def _write_davinci_failure_bundle(
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
            "adapter": DAVINCI_RESOLVE_ADAPTER,
            "action": action,
            "status": status,
            "failure_summary": failure_summary,
            "failure_code": policy_blocks[0] if policy_blocks else "EXECUTION_FAILED",
            "policy_blocks": policy_blocks,
            "state_transitions": state_transitions,
            "provision_result": dict(provision_result),
            "repair_hint": {
                "retryable": bool(policy_blocks and policy_blocks[0] in {"APP_NOT_RUNNING", "API_ATTACH_FAILED"}),
                "local_runbook": "docs/runbooks/davinci_real_local_api_adapter.md",
            },
        },
    )


def _process_running(names: tuple[str, ...]) -> bool:
    for name in names:
        completed = subprocess.run(["pgrep", "-x", name], check=False, capture_output=True, text=True)
        if completed.returncode == 0:
            return True
    return False
