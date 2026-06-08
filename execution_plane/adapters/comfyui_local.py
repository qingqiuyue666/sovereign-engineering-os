"""ComfyUI local-service adapter."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from time import monotonic, sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import subprocess

from creative.common import load_json, write_json
from execution_plane.adapters.base import AdapterContract, COMFYUI_LOCAL_ADAPTER, ProvisionResult
from execution_plane.permits.builder import stable_id
from execution_plane.permits.validator import validate_execution_permit
from execution_plane.runner.path_guard import resolve_output_root
from execution_plane.runner.result_envelope import build_execution_result, collect_output_records, utc_now
from execution_plane.runtime.state_ledger import state_event
from execution_plane.runtime.token_policy import auto_provision_allowed, normalize_runtime_policy

DEFAULT_CONFIG_PATH = Path("config/local_adapters/comfyui_local.json")


def load_comfyui_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return {
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "base_url": "http://127.0.0.1:8188",
            "launch_command": [],
            "working_dir": "",
            "heartbeat_path": "/system_stats",
            "startup_timeout_seconds": 90,
        }
    return dict(load_json(path))


def probe_comfyui(config: Mapping[str, Any] | None = None, *, timeout_seconds: float = 1.0) -> dict[str, Any]:
    cfg = dict(config or load_comfyui_config())
    base_url = str(cfg.get("base_url", "http://127.0.0.1:8188")).rstrip("/")
    heartbeat_path = str(cfg.get("heartbeat_path", "/system_stats"))
    url = base_url + heartbeat_path
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", 200))
        available = 200 <= status_code < 500
        return {
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "available": available,
            "status": "READY" if available else "BLOCKED",
            "heartbeat_status": "READY" if available else "UNAVAILABLE",
            "base_url": base_url,
        }
    except HTTPError as exc:
        if exc.fp is not None:
            exc.close()
        return {
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "available": False,
            "status": "BLOCKED",
            "heartbeat_status": "UNAVAILABLE",
            "base_url": base_url,
        }
    except (OSError, URLError, TimeoutError):
        return {
            "adapter": COMFYUI_LOCAL_ADAPTER,
            "available": False,
            "status": "BLOCKED",
            "heartbeat_status": "UNAVAILABLE",
            "base_url": base_url,
        }


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
        process = subprocess.Popen([str(part) for part in launch_command], cwd=cwd)
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
            return build_execution_result(
                permit=checked,
                run_id=run_id,
                started_at=started_at,
                ended_at=utc_now(),
                exit_code=-1,
                status="BLOCKED",
                output_root=output_root,
                outputs=[],
                stdout="",
                stderr="",
                failure_summary="SERVICE_UNAVAILABLE: ComfyUI heartbeat unavailable",
                policy_blocks=["SERVICE_UNAVAILABLE"],
                state_transitions=transitions,
                provision_result=provision,
            )
        transitions.append(state_event(run_id=run_id, adapter=self.name, state="RUNNING"))
        manifest_path = output_root / "comfyui_probe_manifest.json"
        write_json(
            manifest_path,
            {
                "schema_version": "seos_comfyui_local_probe_v1",
                "adapter": self.name,
                "action": checked["allowed_action"],
                "run_id": run_id,
                "heartbeat_status": detected["heartbeat_status"],
            },
        )
        outputs = collect_output_records(output_root)
        transitions.append(state_event(run_id=run_id, adapter=self.name, state="SUCCEEDED"))
        return build_execution_result(
            permit=checked,
            run_id=run_id,
            started_at=started_at,
            ended_at=utc_now(),
            exit_code=0,
            status="SUCCEEDED",
            output_root=output_root,
            outputs=outputs,
            stdout="comfyui_local completed",
            stderr="",
            failure_summary=None,
            policy_blocks=[],
            evidence_manifest_path="comfyui_probe_manifest.json",
            state_transitions=transitions,
            provision_result=provision,
        )
