"""Optional Houdini/hython adapter contract."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import shutil

from execution_plane.adapters.base import AdapterContract, HOUDINI_HYTHON_ADAPTER, ProvisionResult
from execution_plane.permits.builder import stable_id
from execution_plane.permits.validator import validate_execution_permit
from execution_plane.runner.process_runner import run_controlled_process
from execution_plane.runner.result_envelope import build_execution_result, utc_now
from execution_plane.runtime.state_ledger import state_event


def detect_hython() -> str | None:
    return shutil.which("hython")


def run_houdini_hython_smoke(permit: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_execution_permit(
        permit,
        expected_adapter="houdini_hython",
    )
    started_at = utc_now()
    hython = detect_hython()
    run_id = stable_id("RUN", checked["permit_id"], started_at, "hython_missing")
    if not hython:
        return build_execution_result(
            permit=checked,
            run_id=run_id,
            started_at=started_at,
            ended_at=utc_now(),
            exit_code=-1,
            status="BLOCKED",
            output_root=Path(str(checked["allowed_output_root"])),
            outputs=[],
            stdout="",
            stderr="",
            failure_summary="ENV_NOT_FOUND: hython not found",
            policy_blocks=["ENV_NOT_FOUND"],
            evidence_manifest_path=None,
            state_transitions=[
                state_event(run_id=run_id, adapter=HOUDINI_HYTHON_ADAPTER, state="PREFLIGHTING"),
                state_event(
                    run_id=run_id,
                    adapter=HOUDINI_HYTHON_ADAPTER,
                    state="FAILED",
                    detail={"failure_code": "ADAPTER_UNAVAILABLE"},
                ),
            ],
        )

    script = (
        "import json, pathlib\n"
        "root = pathlib.Path.cwd()\n"
        "payload = {'schema_version':'seos_houdini_hython_smoke_v1',"
        "'adapter':'houdini_hython','output':'hython_scene_summary.json'}\n"
        "(root / 'hython_scene_summary.json').write_text(json.dumps(payload, sort_keys=True) + '\\n', encoding='utf-8')\n"
    )
    result = run_controlled_process(
        permit=checked,
        command=[hython, "-c", script],
        declared_output_paths=["hython_scene_summary.json"],
    )
    if result["status"] != "SUCCEEDED":
        result = dict(result)
        result["status"] = "BLOCKED"
        result["failure_summary"] = "LICENSE_BLOCKED_OR_HYTHON_UNAVAILABLE"
        blocks = list(result.get("policy_blocks", []))
        if "LICENSE_BLOCKED" not in blocks:
            blocks.append("LICENSE_BLOCKED")
        result["policy_blocks"] = blocks
    return result


class HoudiniHythonAdapter(AdapterContract):
    name = HOUDINI_HYTHON_ADAPTER
    actions = frozenset(
        {
            "version_probe",
            "smoke_cache_test",
            "geometry_cache_test",
            "hip_open_validate",
            "houdini_generate_geometry_cache",
        }
    )

    def detect(self) -> dict[str, Any]:
        hython = detect_hython()
        return {
            "adapter": self.name,
            "available": hython is not None,
            "status": "READY" if hython else "BLOCKED",
            "executable": "<resolved:hython>" if hython else None,
        }

    def preflight(self, action: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if action not in self.actions:
            return {"adapter": self.name, "action": action, "status": "BLOCKED", "failure_code": "METHOD_NOT_ALLOWED"}
        detected = self.detect()
        return {
            "adapter": self.name,
            "action": action,
            "status": "READY" if detected["available"] else "BLOCKED",
            "failure_code": None if detected["available"] else "ADAPTER_UNAVAILABLE",
        }

    def auto_provision(self, intent: Mapping[str, Any], policy: Mapping[str, Any]) -> ProvisionResult:
        detected = self.detect()
        return ProvisionResult(
            adapter=self.name,
            status="PROVISIONED" if detected["available"] else "FAILED",
            method="resolve_executable_path",
            heartbeat_status="READY" if detected["available"] else "UNAVAILABLE",
            details={"headless_subprocess_mode": True},
        )

    def execute(self, permit: Mapping[str, Any], payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return run_houdini_hython_smoke(permit)
