"""Optional Houdini/hython adapter contract."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import shutil
import subprocess

from creative.common import load_json
from execution_plane.adapters.base import AdapterContract, HOUDINI_HYTHON_ADAPTER, ProvisionResult
from execution_plane.artifacts import build_artifact_refs
from execution_plane.permits.builder import stable_id
from execution_plane.permits.validator import validate_execution_permit
from execution_plane.runner.path_guard import resolve_output_root
from execution_plane.runner.result_envelope import build_execution_result, collect_output_records, utc_now
from execution_plane.runtime.state_ledger import state_event

HOUDINI_SCRIPT_PATH = Path("execution_plane/adapters/houdini_scripts/smoke_cache_test.py")
DEFAULT_CONFIG_PATH = Path("config/local_adapters/houdini_hython.json")


def load_houdini_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return {"adapter": HOUDINI_HYTHON_ADAPTER, "hython_path": ""}
    return dict(load_json(path))


def detect_hython(config: Mapping[str, Any] | None = None) -> str | None:
    cfg = dict(config or load_houdini_config())
    configured = str(cfg.get("hython_path", "")).strip()
    if configured:
        path = Path(configured)
        if path.is_file():
            return path.as_posix()
    return shutil.which("hython")


def run_houdini_hython_smoke(
    permit: Mapping[str, Any],
    payload: Mapping[str, Any] | None = None,
    *,
    config_path: Path | None = None,
) -> dict[str, Any]:
    checked = validate_execution_permit(
        permit,
        expected_adapter="houdini_hython",
    )
    started_at = utc_now()
    action = str(checked["allowed_action"])
    output_root = resolve_output_root(str(checked["allowed_output_root"]))
    output_root.mkdir(parents=True, exist_ok=True)
    transitions = [state_event(run_id="PENDING", adapter=HOUDINI_HYTHON_ADAPTER, state="PREFLIGHTING")]
    hython = detect_hython(load_houdini_config(config_path))
    run_id = stable_id("RUN", checked["permit_id"], started_at, action)
    transitions = [state_event(run_id=run_id, adapter=HOUDINI_HYTHON_ADAPTER, state="PREFLIGHTING")]
    if not hython:
        transitions.append(
            state_event(
                run_id=run_id,
                adapter=HOUDINI_HYTHON_ADAPTER,
                state="FAILED",
                detail={"failure_code": "ADAPTER_UNAVAILABLE"},
            )
        )
        return _finalize_houdini_result(
            permit=checked,
            run_id=run_id,
            started_at=started_at,
            exit_code=-1,
            status="BLOCKED",
            output_root=output_root,
            stdout="",
            stderr="",
            failure_summary="ENV_NOT_FOUND: hython not found",
            policy_blocks=["ENV_NOT_FOUND"],
            state_transitions=transitions,
        )

    transitions.append(state_event(run_id=run_id, adapter=HOUDINI_HYTHON_ADAPTER, state="RUNNING"))
    script_path = Path(__file__).resolve().parents[2] / HOUDINI_SCRIPT_PATH
    command = [
        hython,
        script_path.as_posix(),
        "--output-root",
        output_root.as_posix(),
        "--action",
        action,
        "--run-id",
        run_id,
    ]
    if payload and isinstance(payload.get("extra_args"), list):
        command.extend(str(item) for item in payload["extra_args"])
    try:
        completed = subprocess.run(
            command,
            cwd=Path(__file__).resolve().parents[2],
            check=False,
            capture_output=True,
            text=True,
            timeout=int(checked["max_runtime_seconds"]),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        transitions.append(
            state_event(
                run_id=run_id,
                adapter=HOUDINI_HYTHON_ADAPTER,
                state="FAILED",
                detail={"failure_code": "TIMEOUT"},
            )
        )
        return _finalize_houdini_result(
            permit=checked,
            run_id=run_id,
            started_at=started_at,
            exit_code=-1,
            status="TIMED_OUT",
            output_root=output_root,
            stdout=stdout,
            stderr=stderr,
            failure_summary="TIMEOUT: hython execution exceeded max_runtime_seconds",
            policy_blocks=["TIMEOUT"],
            state_transitions=transitions,
        )

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if completed.returncode != 0:
        transitions.append(
            state_event(
                run_id=run_id,
                adapter=HOUDINI_HYTHON_ADAPTER,
                state="FAILED",
                detail={"failure_code": "NONZERO_EXIT", "exit_code": completed.returncode},
            )
        )
        return _finalize_houdini_result(
            permit=checked,
            run_id=run_id,
            started_at=started_at,
            exit_code=completed.returncode,
            status="FAILED",
            output_root=output_root,
            stdout=stdout,
            stderr=stderr,
            failure_summary=f"NONZERO_EXIT: hython exited {completed.returncode}",
            policy_blocks=["NONZERO_EXIT"],
            state_transitions=transitions,
        )

    missing = _missing_required_houdini_outputs(output_root, action)
    if missing:
        transitions.append(
            state_event(
                run_id=run_id,
                adapter=HOUDINI_HYTHON_ADAPTER,
                state="FAILED",
                detail={"failure_code": "OUTPUT_MISSING", "missing": missing},
            )
        )
        return _finalize_houdini_result(
            permit=checked,
            run_id=run_id,
            started_at=started_at,
            exit_code=0,
            status="FAILED",
            output_root=output_root,
            stdout=stdout,
            stderr=stderr,
            failure_summary="OUTPUT_MISSING: " + ",".join(missing),
            policy_blocks=["OUTPUT_MISSING"],
            state_transitions=transitions,
        )

    transitions.append(state_event(run_id=run_id, adapter=HOUDINI_HYTHON_ADAPTER, state="COLLECTING"))
    transitions.append(state_event(run_id=run_id, adapter=HOUDINI_HYTHON_ADAPTER, state="SUCCEEDED"))
    return _finalize_houdini_result(
        permit=checked,
        run_id=run_id,
        started_at=started_at,
        exit_code=0,
        status="SUCCEEDED",
        output_root=output_root,
        stdout=stdout,
        stderr=stderr,
        failure_summary=None,
        policy_blocks=[],
        state_transitions=transitions,
    )


def _missing_required_houdini_outputs(output_root: Path, action: str) -> list[str]:
    if action == "version_probe":
        required = ["houdini_version_probe.json", "smoke_cache_execution.log"]
    else:
        required = ["smoke_cache_metadata.json", "smoke_cache_execution.log"]
    return [relative for relative in required if not (output_root / relative).is_file()]


def _finalize_houdini_result(
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
) -> dict[str, Any]:
    action = str(permit.get("allowed_action", "houdini_action"))
    if failure_summary:
        _write_houdini_failure_bundle(
            output_root=output_root,
            permit=permit,
            run_id=run_id,
            action=action,
            status=status,
            failure_summary=failure_summary,
            policy_blocks=policy_blocks,
            state_transitions=state_transitions,
        )
    _write_houdini_artifact_manifest(output_root=output_root, run_id=run_id, action=action)
    _write_houdini_execution_receipt(
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
    )


def _write_houdini_artifact_manifest(*, output_root: Path, run_id: str, action: str) -> None:
    outputs = collect_output_records(output_root)
    refs = build_artifact_refs(run_id=run_id, node_id=action, output_records=outputs)
    from creative.common import write_json

    write_json(
        output_root / "artifact_manifest.json",
        {
            "schema_version": "seos.artifact_manifest.v1",
            "run_id": run_id,
            "adapter": HOUDINI_HYTHON_ADAPTER,
            "action": action,
            "outputs": outputs,
            "artifact_refs": refs,
        },
    )


def _write_houdini_execution_receipt(
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
) -> None:
    outputs = collect_output_records(output_root)
    refs = build_artifact_refs(run_id=run_id, node_id=action, output_records=outputs)
    from creative.common import write_json

    write_json(
        output_root / "execution_receipt.json",
        {
            "schema_version": "seos.execution_receipt.v1",
            "run_id": run_id,
            "permit_id": permit["permit_id"],
            "adapter": HOUDINI_HYTHON_ADAPTER,
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
        },
    )


def _write_houdini_failure_bundle(
    *,
    output_root: Path,
    permit: Mapping[str, Any],
    run_id: str,
    action: str,
    status: str,
    failure_summary: str,
    policy_blocks: list[str],
    state_transitions: list[dict[str, Any]],
) -> None:
    from creative.common import write_json

    write_json(
        output_root / "failure_bundle.json",
        {
            "schema_version": "seos.failure_bundle.v1",
            "run_id": run_id,
            "permit_id": permit["permit_id"],
            "adapter": HOUDINI_HYTHON_ADAPTER,
            "action": action,
            "status": status,
            "failure_summary": failure_summary,
            "failure_code": policy_blocks[0] if policy_blocks else "EXECUTION_FAILED",
            "policy_blocks": policy_blocks,
            "state_transitions": state_transitions,
            "repair_hint": {
                "retryable": bool(policy_blocks and policy_blocks[0] in {"TIMEOUT", "LICENSE_BLOCKED"}),
                "local_runbook": "docs/runbooks/houdini_physical_output_adapter.md",
            },
        },
    )


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

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path

    def detect(self) -> dict[str, Any]:
        hython = detect_hython(load_houdini_config(self.config_path))
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
        return run_houdini_hython_smoke(permit, payload=payload, config_path=self.config_path)
