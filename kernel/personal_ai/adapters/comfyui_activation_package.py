"""Controlled activation package for local ComfyUI endpoint boundaries."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.adapters.comfyui_runtime import run_comfyui_runtime
from kernel.personal_ai.adapters.comfyui_runtime_boundary import (
    write_comfyui_runtime_admission_artifacts,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ComfyUIActivationPackageResult",
    "build_comfyui_activation_package",
    "validate_comfyui_activation_package",
]

_PACKAGE_PLAN_FILE = "comfyui_activation_plan.json"
_ENDPOINT_CONFIG_FILE = "comfyui_endpoint_config.json"
_VALIDATION_FILE = "comfyui_activation_validation.json"
_ADMISSION_DIR = "runtime_admission"
_PACKAGE_TYPE = "personal_ai_comfyui_controlled_activation_package_v1"
_VALIDATION_TYPE = "personal_ai_comfyui_controlled_activation_validation_v1"


@dataclass(frozen=True)
class ComfyUIActivationPackageResult:
    output_dir: Path
    activation_plan_path: Path
    validation_path: Path
    runtime_result_manifest_path: Path | None
    complete: bool
    real_endpoint_called: bool
    network_used: bool
    required_human_approval: bool


def build_comfyui_activation_package(
    workflow_path: Path,
    output_dir: Path,
    *,
    input_asset_paths: tuple[Path, ...] = (),
    endpoint: str = "http://127.0.0.1:8188",
) -> ComfyUIActivationPackageResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    plan_path = output_path / _PACKAGE_PLAN_FILE
    endpoint_config_path = output_path / _ENDPOINT_CONFIG_FILE
    validation_path = output_path / _VALIDATION_FILE
    admission_dir = output_path / _ADMISSION_DIR
    _require_no_overwrite(plan_path)
    _require_no_overwrite(endpoint_config_path)
    _require_no_overwrite(validation_path)
    _require_no_overwrite(admission_dir)
    admission_dir.mkdir()
    write_json_atomically(
        endpoint_config_path,
        {"endpoint": endpoint, "enable_real_endpoint": False},
    )
    artifacts = write_comfyui_runtime_admission_artifacts(admission_dir)
    runtime_result = run_comfyui_runtime(
        Path(workflow_path),
        output_path,
        input_asset_paths=tuple(Path(path) for path in input_asset_paths),
        endpoint_config_path=endpoint_config_path,
        admission_config_path=artifacts.config_path,
        admission_approval_path=artifacts.human_approval_path,
        admission_manifest_path=artifacts.manifest_path,
        dry_run=True,
    )
    if not runtime_result.success:
        raise ValueError("comfyui dry-run runtime package failed")
    plan = {
        "package_type": _PACKAGE_TYPE,
        "authority": "non_authority",
        "execution_capability": "controlled_comfyui_activation_plan_only",
        "workflow_path": Path(workflow_path).as_posix(),
        "workflow_sha256": sha256_file(Path(workflow_path)),
        "endpoint_config_path": endpoint_config_path.as_posix(),
        "endpoint_config_sha256": sha256_file(endpoint_config_path),
        "loopback_only": True,
        "activation_enabled": False,
        "dry_run_only": True,
        "real_comfyui_endpoint_called": False,
        "network_call_allowed": False,
        "network_call_performed": False,
        "external_downloads_allowed": False,
        "external_downloads_performed": False,
        "arbitrary_node_execution_allowed": False,
        "arbitrary_node_execution_performed": False,
        "input_asset_hash_binding_required": True,
        "runtime_result_manifest_path": None
        if runtime_result.result_manifest_path is None
        else runtime_result.result_manifest_path.as_posix(),
        "runtime_result_manifest_sha256": None
        if runtime_result.result_manifest_path is None
        else sha256_file(runtime_result.result_manifest_path),
        "required_human_approval": True,
        "next_allowed_action": "human_review_comfyui_activation_package",
    }
    write_json_atomically(plan_path, plan)
    validation = _validate_package(output_path)
    write_json_atomically(validation_path, validation)
    return ComfyUIActivationPackageResult(
        output_dir=output_path,
        activation_plan_path=plan_path,
        validation_path=validation_path,
        runtime_result_manifest_path=runtime_result.result_manifest_path,
        complete=bool(validation["complete"]),
        real_endpoint_called=False,
        network_used=False,
        required_human_approval=True,
    )


def validate_comfyui_activation_package(package_dir: Path) -> dict[str, object]:
    return _validate_package(Path(package_dir))


def _validate_package(package_path: Path) -> dict[str, object]:
    failures: list[str] = []
    plan_path = package_path / _PACKAGE_PLAN_FILE
    plan = _read_json_file(plan_path, failures)
    if plan:
        if plan.get("package_type") != _PACKAGE_TYPE:
            failures.append("package_type_mismatch")
        if plan.get("loopback_only") is not True:
            failures.append("loopback_only_required")
        for field_name in (
            "activation_enabled",
            "real_comfyui_endpoint_called",
            "network_call_allowed",
            "network_call_performed",
            "external_downloads_allowed",
            "external_downloads_performed",
            "arbitrary_node_execution_allowed",
            "arbitrary_node_execution_performed",
        ):
            if plan.get(field_name) is not False:
                failures.append(field_name + "_must_be_false")
        if plan.get("dry_run_only") is not True:
            failures.append("dry_run_only_required")
        if plan.get("required_human_approval") is not True:
            failures.append("required_human_approval")
    return {
        "validation_type": _VALIDATION_TYPE,
        "package_dir": package_path.as_posix(),
        "activation_plan_path": plan_path.as_posix(),
        "activation_plan_sha256": sha256_file(plan_path)
        if plan_path.exists() and plan_path.is_file()
        else None,
        "complete": not failures,
        "failures": sorted(set(failures)),
        "real_comfyui_endpoint_called": False,
        "network_used": False,
        "external_downloads_performed": False,
        "arbitrary_node_execution_performed": False,
        "required_human_approval": True,
    }


def _read_json_file(path: Path, failures: list[str]) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        failures.append("activation_plan_missing")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        failures.append("activation_plan_malformed")
        return {}
    if not isinstance(payload, dict):
        failures.append("activation_plan_malformed")
        return {}
    return payload


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("comfyui activation package output already exists")
