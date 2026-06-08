"""DaVinci Resolve local scripting adapter."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from time import monotonic, sleep
from typing import Any
import subprocess

from creative.common import load_json, write_json
from execution_plane.adapters.base import AdapterContract, DAVINCI_RESOLVE_ADAPTER, ProvisionResult
from execution_plane.permits.builder import stable_id
from execution_plane.permits.validator import validate_execution_permit
from execution_plane.runner.path_guard import resolve_output_root
from execution_plane.runner.result_envelope import build_execution_result, collect_output_records, utc_now
from execution_plane.runtime.state_ledger import state_event
from execution_plane.runtime.token_policy import auto_provision_allowed, normalize_runtime_policy

DEFAULT_CONFIG_PATH = Path("config/local_adapters/davinci_resolve.json")


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
    cfg = dict(config or load_davinci_config())
    probe_script = Path(str(cfg.get("api_probe_script", "")))
    script_available = probe_script.exists()
    app_running = _process_running(("DaVinci Resolve", "Resolve"))
    available = app_running and script_available
    return {
        "adapter": DAVINCI_RESOLVE_ADAPTER,
        "available": available,
        "status": "READY" if available else "BLOCKED",
        "app_running": app_running,
        "api_probe_script_available": script_available,
    }


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
            "failure_code": None if detected["available"] else "DEPENDENCY_BLOCKED",
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
        detected = self.detect()
        provision: dict[str, Any] = {}
        if not detected["available"] and not detected.get("app_running"):
            transitions.append(state_event(run_id=run_id, adapter=self.name, state="PROVISIONING"))
            provision = self.auto_provision(checked, checked).as_dict()
            detected = self.detect()
        if not detected["available"]:
            transitions.append(
                state_event(
                    run_id=run_id,
                    adapter=self.name,
                    state="FAILED",
                    detail={"failure_code": provision.get("details", {}).get("failure_code", "DEPENDENCY_BLOCKED")},
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
                failure_summary="DEPENDENCY_BLOCKED: DaVinci scripting API unavailable",
                policy_blocks=["DEPENDENCY_BLOCKED"],
                state_transitions=transitions,
                provision_result=provision,
            )
        transitions.append(state_event(run_id=run_id, adapter=self.name, state="RUNNING"))
        manifest_path = output_root / "davinci_probe_manifest.json"
        write_json(
            manifest_path,
            {
                "schema_version": "seos_davinci_resolve_probe_v1",
                "adapter": self.name,
                "action": checked["allowed_action"],
                "run_id": run_id,
                "api_probe_script_available": detected["api_probe_script_available"],
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
            stdout="davinci_resolve completed",
            stderr="",
            failure_summary=None,
            policy_blocks=[],
            evidence_manifest_path="davinci_probe_manifest.json",
            state_transitions=transitions,
            provision_result=provision,
        )


def _process_running(names: tuple[str, ...]) -> bool:
    for name in names:
        completed = subprocess.run(["pgrep", "-x", name], check=False, capture_output=True, text=True)
        if completed.returncode == 0:
            return True
    return False
