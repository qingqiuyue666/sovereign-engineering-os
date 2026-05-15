"""Product-grade ComfyUI runtime facade."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.adapters.comfyui_controlled_runtime import (
    run_comfyui_controlled_fixture,
)
from kernel.personal_ai.adapters.comfyui_runtime_boundary import (
    boundary_for_comfyui_runtime,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_admission_gate import (
    RuntimeAdmissionRequest,
    evaluate_runtime_admission,
)

__all__ = [
    "ComfyUIRuntimeResult",
    "run_comfyui_runtime",
]

_RESULT_MANIFEST_FILE = "comfyui_runtime_result_manifest.json"
_DRY_RUN_PLAN_FILE = "comfyui_endpoint_dry_run_plan.json"
_FAILURE_FILE = "comfyui_runtime_failure_quarantine.json"
_ENDPOINT_RUNTIME_ID = "comfyui_local_endpoint_boundary"


@dataclass(frozen=True)
class ComfyUIRuntimeResult:
    workflow_path: Path
    output_dir: Path
    result_manifest_path: Path | None
    dry_run_plan_path: Path | None
    output_manifest_path: Path | None
    preview_evidence_path: Path | None
    failure_quarantine_path: Path | None
    success: bool
    real_endpoint_called: bool
    required_human_approval: bool


def run_comfyui_runtime(
    workflow_path: Path,
    output_dir: Path,
    *,
    input_asset_paths: tuple[Path, ...] = (),
    endpoint_config_path: Path | None = None,
    admission_config_path: Path | None = None,
    admission_approval_path: Path | None = None,
    admission_manifest_path: Path | None = None,
    dry_run: bool = True,
) -> ComfyUIRuntimeResult:
    workflow_file = Path(workflow_path)
    output_path = Path(output_dir)
    _validate_output_dir(output_path)
    result_manifest_path = output_path / _RESULT_MANIFEST_FILE
    dry_run_plan_path = output_path / _DRY_RUN_PLAN_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(result_manifest_path)
    _require_no_overwrite(dry_run_plan_path)
    _require_no_overwrite(failure_path)

    try:
        if endpoint_config_path is not None or admission_config_path is not None:
            return _run_endpoint_dry_run(
                workflow_file,
                output_path,
                input_asset_paths=input_asset_paths,
                endpoint_config_path=endpoint_config_path,
                result_manifest_path=result_manifest_path,
                dry_run_plan_path=dry_run_plan_path,
                admission_config_path=admission_config_path,
                admission_approval_path=admission_approval_path,
                admission_manifest_path=admission_manifest_path,
                dry_run=dry_run,
            )
        return _run_fixture(
            workflow_file,
            output_path,
            input_asset_paths=input_asset_paths,
            result_manifest_path=result_manifest_path,
        )
    except ValueError as error:
        _write_failure_quarantine(workflow_file, failure_path, error)
        return ComfyUIRuntimeResult(
            workflow_path=workflow_file,
            output_dir=output_path,
            result_manifest_path=None,
            dry_run_plan_path=None,
            output_manifest_path=None,
            preview_evidence_path=None,
            failure_quarantine_path=failure_path,
            success=False,
            real_endpoint_called=False,
            required_human_approval=True,
        )


def _run_fixture(
    workflow_file: Path,
    output_path: Path,
    *,
    input_asset_paths: tuple[Path, ...],
    result_manifest_path: Path,
) -> ComfyUIRuntimeResult:
    fixture_result = run_comfyui_controlled_fixture(
        workflow_file,
        output_path,
        input_asset_paths=input_asset_paths,
    )
    if not fixture_result.success:
        return ComfyUIRuntimeResult(
            workflow_path=workflow_file,
            output_dir=output_path,
            result_manifest_path=None,
            dry_run_plan_path=None,
            output_manifest_path=None,
            preview_evidence_path=None,
            failure_quarantine_path=fixture_result.failure_bundle_path,
            success=False,
            real_endpoint_called=False,
            required_human_approval=True,
        )
    _write_result_manifest(
        result_manifest_path,
        workflow_file,
        fixture_result.output_manifest_path,
        fixture_result.preview_evidence_path,
        execution_capability="local_fixture_contract_only",
        runtime_id="comfyui_workflow_fixture",
        dry_run_plan_path=None,
        admission_decision=None,
    )
    return ComfyUIRuntimeResult(
        workflow_path=workflow_file,
        output_dir=output_path,
        result_manifest_path=result_manifest_path,
        dry_run_plan_path=None,
        output_manifest_path=fixture_result.output_manifest_path,
        preview_evidence_path=fixture_result.preview_evidence_path,
        failure_quarantine_path=None,
        success=True,
        real_endpoint_called=False,
        required_human_approval=True,
    )


def _run_endpoint_dry_run(
    workflow_file: Path,
    output_path: Path,
    *,
    input_asset_paths: tuple[Path, ...],
    endpoint_config_path: Path | None,
    result_manifest_path: Path,
    dry_run_plan_path: Path,
    admission_config_path: Path | None,
    admission_approval_path: Path | None,
    admission_manifest_path: Path | None,
    dry_run: bool,
) -> ComfyUIRuntimeResult:
    if endpoint_config_path is None:
        raise ValueError("endpoint_config_path is required")
    if dry_run is not True:
        raise ValueError("real ComfyUI endpoint execution is disabled by default")
    endpoint_config = _read_endpoint_config(endpoint_config_path)
    boundary = boundary_for_comfyui_runtime(_ENDPOINT_RUNTIME_ID)
    admission = evaluate_runtime_admission(
        RuntimeAdmissionRequest(
            adapter_id=boundary.adapter_id,
            capability=boundary.capability,
            runtime_class=boundary.runtime_class,
            config_artifact_path=admission_config_path,
            human_approval_artifact_path=admission_approval_path,
            manifest_artifact_path=admission_manifest_path,
            dry_run=True,
            activation_sources=("human_approval_artifact",),
        )
    )
    if not admission.admitted:
        raise ValueError(
            "comfyui runtime admission denied: "
            + ",".join(admission.reason_codes)
        )

    fixture_result = run_comfyui_controlled_fixture(
        workflow_file,
        output_path,
        input_asset_paths=input_asset_paths,
        endpoint_config_path=endpoint_config_path,
    )
    if not fixture_result.success:
        return ComfyUIRuntimeResult(
            workflow_path=workflow_file,
            output_dir=output_path,
            result_manifest_path=None,
            dry_run_plan_path=None,
            output_manifest_path=None,
            preview_evidence_path=None,
            failure_quarantine_path=fixture_result.failure_bundle_path,
            success=False,
            real_endpoint_called=False,
            required_human_approval=True,
        )

    dry_run_plan = {
        "plan_type": "personal_ai_comfyui_endpoint_dry_run_plan_v1",
        "authority": "non_authority",
        "execution_capability": "dry_run_comfyui_endpoint_boundary_only",
        "runtime_id": boundary.runtime_id,
        "endpoint": endpoint_config["endpoint"],
        "loopback_only": True,
        "workflow_path": workflow_file.as_posix(),
        "workflow_sha256": sha256_file(workflow_file),
        "input_asset_paths": [Path(path).as_posix() for path in input_asset_paths],
        "input_asset_hash_binding_required": True,
        "output_manifest_path": fixture_result.output_manifest_path.as_posix(),
        "preview_evidence_path": fixture_result.preview_evidence_path.as_posix(),
        "real_comfyui_endpoint_called": False,
        "network_call_performed": False,
        "external_downloads_performed": False,
        "arbitrary_node_execution_performed": False,
        "runtime_admission_decision": admission.to_dict(),
        "required_human_approval": True,
    }
    write_json_atomically(dry_run_plan_path, dry_run_plan)
    _write_result_manifest(
        result_manifest_path,
        workflow_file,
        fixture_result.output_manifest_path,
        fixture_result.preview_evidence_path,
        execution_capability="dry_run_comfyui_endpoint_boundary_only",
        runtime_id=boundary.runtime_id,
        dry_run_plan_path=dry_run_plan_path,
        admission_decision=admission.to_dict(),
    )
    return ComfyUIRuntimeResult(
        workflow_path=workflow_file,
        output_dir=output_path,
        result_manifest_path=result_manifest_path,
        dry_run_plan_path=dry_run_plan_path,
        output_manifest_path=fixture_result.output_manifest_path,
        preview_evidence_path=fixture_result.preview_evidence_path,
        failure_quarantine_path=None,
        success=True,
        real_endpoint_called=False,
        required_human_approval=True,
    )


def _write_result_manifest(
    result_manifest_path: Path,
    workflow_file: Path,
    output_manifest_path: Path,
    preview_evidence_path: Path,
    *,
    execution_capability: str,
    runtime_id: str,
    dry_run_plan_path: Path | None,
    admission_decision: dict[str, object] | None,
) -> None:
    manifest = {
        "manifest_type": "personal_ai_comfyui_runtime_result_manifest_v1",
        "authority": "non_authority",
        "execution_capability": execution_capability,
        "runtime_id": runtime_id,
        "workflow_path": workflow_file.as_posix(),
        "workflow_sha256": sha256_file(workflow_file),
        "output_manifest_path": output_manifest_path.as_posix(),
        "output_manifest_sha256": sha256_file(output_manifest_path),
        "preview_evidence_path": preview_evidence_path.as_posix(),
        "preview_evidence_sha256": sha256_file(preview_evidence_path),
        "dry_run_plan_path": None
        if dry_run_plan_path is None
        else dry_run_plan_path.as_posix(),
        "real_comfyui_endpoint_called": False,
        "network_used": False,
        "external_downloads_performed": False,
        "arbitrary_node_execution_performed": False,
        "output_manifest_required": True,
        "preview_evidence_required": True,
        "failure_quarantine_required": True,
        "runtime_admission_decision": admission_decision,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(result_manifest_path, manifest)


def _read_endpoint_config(endpoint_config_path: Path) -> dict[str, object]:
    if not endpoint_config_path.exists() or not endpoint_config_path.is_file():
        raise ValueError("endpoint_config_path is missing")
    try:
        config = json.loads(endpoint_config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("endpoint_config_path is malformed") from error
    if not isinstance(config, dict):
        raise ValueError("endpoint_config_path must be an object")
    endpoint = str(config.get("endpoint", ""))
    if not endpoint.startswith(("http://127.0.0.1", "http://localhost")):
        raise ValueError("comfyui endpoint must be loopback")
    if config.get("enable_real_endpoint") is True:
        raise ValueError("real ComfyUI endpoint calls are not admitted")
    return config


def _validate_output_dir(output_path: Path) -> None:
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("comfyui runtime output already exists")


def _write_failure_quarantine(
    workflow_file: Path,
    failure_path: Path,
    error: ValueError,
) -> None:
    payload = {
        "failure_type": "personal_ai_comfyui_runtime_failure_quarantine_v1",
        "authority": "non_authority",
        "execution_capability": "comfyui_runtime_boundary_only",
        "workflow_path": workflow_file.as_posix(),
        "workflow_sha256": sha256_file(workflow_file)
        if workflow_file.exists() and workflow_file.is_file()
        else None,
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "real_comfyui_endpoint_called": False,
        "network_used": False,
        "external_downloads_performed": False,
        "arbitrary_node_execution_performed": False,
        "source_asset_overwrite_performed": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(failure_path, payload)
