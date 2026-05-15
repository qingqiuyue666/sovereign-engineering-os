"""Blender runtime admission and disabled runner.

This module prepares a future Blender runtime gate without launching Blender,
starting subprocesses, or executing Python inside Blender. Normal tests use fake
transports only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
import json

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = ["BlenderRuntimeAdmissionDisabledRunnerResult", "run_blender_runtime_admission_disabled_runner"]

_RESULT_FILE = "blender_runtime_admission_disabled_runner_result.json"
_FAILURE_FILE = "blender_runtime_admission_disabled_runner_failure_quarantine.json"
_RESULT_TYPE = "personal_ai_blender_runtime_admission_disabled_runner_result_v1"
_FAILURE_TYPE = "personal_ai_blender_runtime_admission_disabled_runner_failure_v1"
_ENABLE_FLAG = "SEOS_ENABLE_BLENDER_RUNTIME_ADMISSION_DISABLED_RUNNER"
_EXPECTED_ENABLE_VALUE = "true"

BlenderTransport = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class BlenderRuntimeAdmissionDisabledRunnerResult:
    output_dir: Path
    result_path: Path | None
    failure_path: Path | None
    status: str
    blender_runtime_called: bool
    subprocess_used: bool
    arbitrary_python_used: bool
    required_human_approval: bool


def run_blender_runtime_admission_disabled_runner(
    scene_path: Path,
    operation_plan_path: Path,
    output_dir: Path,
    *,
    environ: Mapping[str, str] | None = None,
    allow_blender_runner: bool = False,
    blender_transport: BlenderTransport | None = None,
) -> BlenderRuntimeAdmissionDisabledRunnerResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    result_path = output_path / _RESULT_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(result_path)
    _require_no_overwrite(failure_path)
    try:
        scene_file = Path(scene_path)
        plan_file = Path(operation_plan_path)
        _validate_scene(scene_file)
        plan = _read_json(plan_file)
        _validate_plan(plan)
        source = {} if environ is None else environ
        if allow_blender_runner is not True:
            return _write_denied_result(result_path, scene_file, plan_file, "disabled_by_callsite")
        if source.get(_ENABLE_FLAG) != _EXPECTED_ENABLE_VALUE:
            return _write_denied_result(result_path, scene_file, plan_file, "disabled_by_environment_flag")
        if blender_transport is None:
            return _write_denied_result(result_path, scene_file, plan_file, "missing_explicit_blender_transport")
        request = _build_request(scene_file, plan_file, plan)
        response = blender_transport(request)
        response_validation = _validate_response(response)
        result = {
            "result_type": _RESULT_TYPE,
            "status": "completed_via_explicit_blender_transport",
            "scene_path": scene_file.as_posix(),
            "scene_sha256": sha256_file(scene_file),
            "operation_plan_path": plan_file.as_posix(),
            "operation_plan_sha256": sha256_file(plan_file),
            "environment_enable_flag": _ENABLE_FLAG,
            "environment_enable_flag_value_matched": True,
            "transport_called": True,
            "real_blender_runtime_called": True,
            "subprocess_used": False,
            "arbitrary_python_execution_used": False,
            "external_network_used": False,
            "source_asset_overwrite_performed": False,
            "operation_response_validation": response_validation,
            "required_human_approval": True,
            "next_allowed_action": "human_review_blender_runtime_runner_result",
        }
        write_json_atomically(result_path, result)
        return BlenderRuntimeAdmissionDisabledRunnerResult(
            output_dir=output_path,
            result_path=result_path,
            failure_path=None,
            status="completed_via_explicit_blender_transport",
            blender_runtime_called=True,
            subprocess_used=False,
            arbitrary_python_used=False,
            required_human_approval=True,
        )
    except ValueError as error:
        failure = {
            "failure_type": _FAILURE_TYPE,
            "status": "failed_closed",
            "reason": str(error),
            "scene_path": Path(scene_path).as_posix(),
            "operation_plan_path": Path(operation_plan_path).as_posix(),
            "real_blender_runtime_called": False,
            "subprocess_used": False,
            "arbitrary_python_execution_used": False,
            "required_human_approval": True,
        }
        write_json_atomically(failure_path, failure)
        return BlenderRuntimeAdmissionDisabledRunnerResult(
            output_dir=output_path,
            result_path=None,
            failure_path=failure_path,
            status="failed_closed",
            blender_runtime_called=False,
            subprocess_used=False,
            arbitrary_python_used=False,
            required_human_approval=True,
        )


def _write_denied_result(result_path: Path, scene_file: Path, plan_file: Path, status: str) -> BlenderRuntimeAdmissionDisabledRunnerResult:
    result = {
        "result_type": _RESULT_TYPE,
        "status": status,
        "scene_path": scene_file.as_posix(),
        "scene_sha256": sha256_file(scene_file),
        "operation_plan_path": plan_file.as_posix(),
        "operation_plan_sha256": sha256_file(plan_file),
        "environment_enable_flag": _ENABLE_FLAG,
        "transport_called": False,
        "real_blender_runtime_called": False,
        "subprocess_used": False,
        "arbitrary_python_execution_used": False,
        "external_network_used": False,
        "source_asset_overwrite_performed": False,
        "required_human_approval": True,
    }
    write_json_atomically(result_path, result)
    return BlenderRuntimeAdmissionDisabledRunnerResult(
        output_dir=result_path.parent,
        result_path=result_path,
        failure_path=None,
        status=status,
        blender_runtime_called=False,
        subprocess_used=False,
        arbitrary_python_used=False,
        required_human_approval=True,
    )


def _build_request(scene_file: Path, plan_file: Path, plan: dict[str, object]) -> dict[str, object]:
    return {
        "request_type": "personal_ai_blender_runtime_admission_disabled_runner_request_v1",
        "scene_path": scene_file.as_posix(),
        "scene_sha256": sha256_file(scene_file),
        "operation_plan_path": plan_file.as_posix(),
        "operation_plan_sha256": sha256_file(plan_file),
        "operation_count": len(plan.get("operations", [])),
        "subprocess_allowed": False,
        "arbitrary_python_allowed": False,
        "external_network_allowed": False,
        "source_asset_overwrite_allowed": False,
    }


def _validate_response(response: dict[str, object]) -> dict[str, object]:
    failures: list[str] = []
    if not isinstance(response, dict):
        response = {}
        failures.append("response_malformed")
    if response.get("status") != "ok":
        failures.append("status_not_ok")
    for field_name in ("subprocess_used", "arbitrary_python_execution_used", "external_network_used", "source_asset_overwrite_performed"):
        if response.get(field_name) not in (None, False):
            failures.append(field_name)
    return {"complete": not failures, "failures": sorted(set(failures))}


def _validate_scene(scene_file: Path) -> None:
    if not scene_file.exists() or not scene_file.is_file():
        raise ValueError("scene_path is missing")
    if scene_file.is_symlink():
        raise ValueError("scene_path must not be symlink")
    if scene_file.suffix.lower() not in (".blend", ".glb", ".gltf"):
        raise ValueError("scene_path extension is not allowed")


def _validate_plan(plan: dict[str, object]) -> None:
    operations = plan.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("operation plan operations are malformed")
    forbidden = ("__import__", "eval", "exec", "http", "network", "open(", "os.", "python", "script", "subprocess", "sys.", "url")
    allowed = {"add_camera", "add_light", "add_mesh_primitive", "assign_material", "create_collection", "export_glb_preview", "render_preview", "set_camera", "set_object_transform"}
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("operation is malformed")
        operation_type = str(operation.get("operation", ""))
        if operation_type not in allowed:
            raise ValueError("operation is not allowed")
        serialized = json.dumps(operation, sort_keys=True).lower()
        if any(token in serialized for token in forbidden):
            raise ValueError("operation contains forbidden token")


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        raise ValueError("operation_plan_path is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("operation_plan_path is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError("operation_plan_path is malformed")
    return payload


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("blender runtime runner output already exists")
