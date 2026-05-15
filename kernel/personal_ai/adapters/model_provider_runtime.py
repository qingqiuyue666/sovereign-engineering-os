"""Product-grade model provider runtime facade."""

from dataclasses import dataclass
from pathlib import Path
import json
import os

from kernel.personal_ai.adapters.model_adapter_contract import find_model_provider
from kernel.personal_ai.adapters.model_provider_boundary import boundary_for_provider
from kernel.personal_ai.adapters.model_typed_schema_runtime import (
    load_provider_api_key_from_environment,
    run_model_fixture,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_admission_gate import (
    RuntimeAdmissionDecision,
    RuntimeAdmissionRequest,
    evaluate_runtime_admission,
)

__all__ = [
    "ModelProviderRuntimeResult",
    "build_optional_live_smoke_status",
    "run_model_provider_runtime",
]

_REQUEST_TYPE = "personal_ai_execution_os_v2_model_request"
_RESULT_MANIFEST_FILE = "model_provider_result_manifest.json"
_DRY_RUN_PLAN_FILE = "model_provider_dry_run_plan.json"
_FAILURE_FILE = "model_provider_failure_quarantine.json"
_MOCK_PROVIDER = "deterministic_mock"
_LIVE_SMOKE_ENV = "SEOS_ENABLE_LIVE_MODEL_SMOKE"


@dataclass(frozen=True)
class ModelProviderRuntimeResult:
    request_path: Path
    output_dir: Path
    result_manifest_path: Path | None
    dry_run_plan_path: Path | None
    inference_artifact_path: Path | None
    failure_quarantine_path: Path | None
    success: bool
    provider_id: str
    live_provider_called: bool
    required_human_approval: bool


def run_model_provider_runtime(
    request_path: Path,
    output_dir: Path,
    *,
    admission_config_path: Path | None = None,
    admission_approval_path: Path | None = None,
    admission_manifest_path: Path | None = None,
    dry_run: bool = True,
    environ=None,
) -> ModelProviderRuntimeResult:
    request_file = Path(request_path)
    output_path = Path(output_dir)
    _validate_paths(request_file, output_path)
    result_manifest_path = output_path / _RESULT_MANIFEST_FILE
    dry_run_plan_path = output_path / _DRY_RUN_PLAN_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(result_manifest_path)
    _require_no_overwrite(dry_run_plan_path)
    _require_no_overwrite(failure_path)

    try:
        request = _read_request(request_file)
        provider_id = str(request.get("provider", ""))
        if provider_id == _MOCK_PROVIDER:
            return _run_mock_provider(
                request_file,
                output_path,
                result_manifest_path,
            )
        return _run_live_provider_dry_run(
            request_file,
            output_path,
            request,
            result_manifest_path,
            dry_run_plan_path,
            admission_config_path=admission_config_path,
            admission_approval_path=admission_approval_path,
            admission_manifest_path=admission_manifest_path,
            dry_run=dry_run,
            environ=environ,
        )
    except ValueError as error:
        provider_id = _provider_from_request_file(request_file)
        _write_failure_quarantine(request_file, failure_path, provider_id, error)
        return ModelProviderRuntimeResult(
            request_path=request_file,
            output_dir=output_path,
            result_manifest_path=None,
            dry_run_plan_path=None,
            inference_artifact_path=None,
            failure_quarantine_path=failure_path,
            success=False,
            provider_id=provider_id,
            live_provider_called=False,
            required_human_approval=True,
        )


def build_optional_live_smoke_status(
    provider_id: str,
    admission_decision: RuntimeAdmissionDecision,
    *,
    environ=None,
) -> dict[str, object]:
    provider = find_model_provider(provider_id)
    source = os.environ if environ is None else environ
    explicit_env_enabled = source.get(_LIVE_SMOKE_ENV) == "true"
    api_key_present = (
        False
        if provider.api_key_env_var is None
        else bool(load_provider_api_key_from_environment(provider_id, source))
    )
    enabled = (
        explicit_env_enabled
        and api_key_present
        and admission_decision.activation_allowed
    )
    return {
        "smoke_type": "personal_ai_optional_live_model_smoke_status_v1",
        "provider_id": provider_id,
        "enabled": enabled,
        "disabled_by_default": True,
        "explicit_env_required": _LIVE_SMOKE_ENV,
        "explicit_env_enabled": explicit_env_enabled,
        "api_key_source": "environment_only"
        if provider.api_key_env_var
        else "none",
        "api_key_env_var": provider.api_key_env_var,
        "api_key_present": api_key_present,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "admission_activation_allowed": admission_decision.activation_allowed,
        "live_call_performed": False,
    }


def _run_mock_provider(
    request_file: Path,
    output_path: Path,
    result_manifest_path: Path,
) -> ModelProviderRuntimeResult:
    fixture_result = run_model_fixture(request_file, output_path)
    if not fixture_result.success:
        return ModelProviderRuntimeResult(
            request_path=request_file,
            output_dir=output_path,
            result_manifest_path=None,
            dry_run_plan_path=None,
            inference_artifact_path=None,
            failure_quarantine_path=fixture_result.failure_bundle_path,
            success=False,
            provider_id=_MOCK_PROVIDER,
            live_provider_called=False,
            required_human_approval=True,
        )
    inference = _read_json(fixture_result.inference_artifact_path)
    manifest = {
        "manifest_type": "personal_ai_model_provider_result_manifest_v1",
        "authority": "non_authority",
        "execution_capability": "deterministic_mock_model_only",
        "provider": _MOCK_PROVIDER,
        "provider_kind": "mock",
        "default_provider": True,
        "request_path": request_file.as_posix(),
        "request_sha256": sha256_file(request_file),
        "inference_artifact_path": (
            fixture_result.inference_artifact_path.as_posix()
        ),
        "inference_artifact_sha256": sha256_file(
            fixture_result.inference_artifact_path
        ),
        "typed_response_schema": inference.get("typed_response_schema"),
        "schema_retry_policy": inference.get("schema_retry_policy"),
        "schema_retry_attempts": inference.get("schema_retry_attempts"),
        "invalid_outputs_quarantined": inference.get(
            "invalid_outputs_quarantined"
        ),
        "live_provider_runtime": False,
        "live_provider_called": False,
        "network_used": False,
        "api_key_used": False,
        "api_key_persisted": False,
        "api_key_logged": False,
        "model_output_can_grant_authority": False,
        "model_output_can_edit_files": False,
        "model_output_can_call_tools": False,
        "required_human_approval": True,
    }
    write_json_atomically(result_manifest_path, manifest)
    return ModelProviderRuntimeResult(
        request_path=request_file,
        output_dir=output_path,
        result_manifest_path=result_manifest_path,
        dry_run_plan_path=None,
        inference_artifact_path=fixture_result.inference_artifact_path,
        failure_quarantine_path=None,
        success=True,
        provider_id=_MOCK_PROVIDER,
        live_provider_called=False,
        required_human_approval=True,
    )


def _run_live_provider_dry_run(
    request_file: Path,
    output_path: Path,
    request: dict[str, object],
    result_manifest_path: Path,
    dry_run_plan_path: Path,
    *,
    admission_config_path: Path | None,
    admission_approval_path: Path | None,
    admission_manifest_path: Path | None,
    dry_run: bool,
    environ,
) -> ModelProviderRuntimeResult:
    provider_id = str(request.get("provider", ""))
    boundary = boundary_for_provider(provider_id)
    provider = find_model_provider(provider_id)
    if provider.live_provider_runtime is not True:
        raise ValueError("model provider kind is not supported")
    _validate_live_request_boundary(request, provider_id, dry_run)
    admission = evaluate_runtime_admission(
        RuntimeAdmissionRequest(
            adapter_id=boundary.adapter_id,
            capability=boundary.capability,
            runtime_class=boundary.runtime_class,
            config_artifact_path=admission_config_path,
            human_approval_artifact_path=admission_approval_path,
            manifest_artifact_path=admission_manifest_path,
            dry_run=dry_run,
            activation_sources=("human_approval_artifact",),
        )
    )
    if not admission.admitted:
        raise ValueError(
            "model provider runtime admission denied: "
            + ",".join(admission.reason_codes)
        )
    api_key_present = (
        provider.api_key_env_var is not None
        and load_provider_api_key_from_environment(
            provider_id,
            os.environ if environ is None else environ,
        )
        is not None
    )
    dry_run_plan = {
        "plan_type": "personal_ai_model_provider_dry_run_plan_v1",
        "authority": "non_authority",
        "execution_capability": "dry_run_model_provider_boundary_only",
        "provider": provider_id,
        "provider_kind": provider.provider_kind,
        "request_path": request_file.as_posix(),
        "request_sha256": sha256_file(request_file),
        "schema_name": request["schema_name"],
        "timeout_seconds": request["timeout_seconds"],
        "max_budget_usd": request["max_budget_usd"],
        "schema_retry_policy": request["schema_retry_policy"],
        "api_key_source": "environment_only",
        "api_key_env_var": provider.api_key_env_var,
        "api_key_present": api_key_present,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "network_call_planned": False,
        "network_call_performed": False,
        "live_provider_call_performed": False,
        "runtime_admission_decision": admission.to_dict(),
        "required_human_approval": True,
    }
    result_manifest = {
        "manifest_type": "personal_ai_model_provider_result_manifest_v1",
        "authority": "non_authority",
        "execution_capability": "dry_run_model_provider_boundary_only",
        "provider": provider_id,
        "provider_kind": provider.provider_kind,
        "default_provider": False,
        "request_path": request_file.as_posix(),
        "request_sha256": sha256_file(request_file),
        "dry_run_plan_path": dry_run_plan_path.as_posix(),
        "live_provider_runtime": True,
        "live_provider_enabled_by_default": False,
        "live_provider_called": False,
        "network_used": False,
        "api_key_source": "environment_only",
        "api_key_env_var": provider.api_key_env_var,
        "api_key_present": api_key_present,
        "api_key_persisted": False,
        "api_key_logged": False,
        "timeout_seconds": request["timeout_seconds"],
        "max_budget_usd": request["max_budget_usd"],
        "estimated_cost_usd": request["estimated_cost_usd"],
        "schema_retry_policy": request["schema_retry_policy"],
        "provider_result_schema_validated": False,
        "invalid_output_quarantine_required": True,
        "model_output_can_grant_authority": False,
        "model_output_can_edit_files": False,
        "model_output_can_call_tools": False,
        "runtime_admission_decision": admission.to_dict(),
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(dry_run_plan_path, dry_run_plan)
    write_json_atomically(result_manifest_path, result_manifest)
    return ModelProviderRuntimeResult(
        request_path=request_file,
        output_dir=output_path,
        result_manifest_path=result_manifest_path,
        dry_run_plan_path=dry_run_plan_path,
        inference_artifact_path=None,
        failure_quarantine_path=None,
        success=True,
        provider_id=provider_id,
        live_provider_called=False,
        required_human_approval=True,
    )


def _validate_paths(request_file: Path, output_path: Path) -> None:
    if not request_file.exists() or not request_file.is_file():
        raise ValueError("request_path is missing")
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("model provider runtime output already exists")


def _read_request(request_file: Path) -> dict[str, object]:
    request = _read_json(request_file)
    if not isinstance(request, dict):
        raise ValueError("model provider request must be an object")
    if request.get("request_type") != _REQUEST_TYPE:
        raise ValueError("model provider request_type mismatch")
    return request


def _read_json(path: Path | None) -> dict[str, object]:
    if path is None:
        raise ValueError("json artifact path is missing")
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("json artifact is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError("json artifact must be an object")
    return payload


def _validate_live_request_boundary(
    request: dict[str, object],
    provider_id: str,
    dry_run: bool,
) -> None:
    provider = find_model_provider(provider_id)
    if dry_run is not True:
        raise ValueError("live model provider execution is disabled by default")
    if request.get("provider_enabled") is not False:
        raise ValueError("live model provider must be disabled by default")
    if request.get("live_provider_runtime") is not True:
        raise ValueError("live model provider request is malformed")
    if request.get("network_allowed") is not False:
        raise ValueError("live model network runtime is not admitted")
    if request.get("api_key_source") != "environment_only":
        raise ValueError("live model api key source must be environment_only")
    if request.get("api_key_persisted") is not False:
        raise ValueError("api key persistence is not admitted")
    if request.get("api_key_logged") is not False:
        raise ValueError("api key logging is not admitted")
    if request.get("tool_calls_allowed") is not False:
        raise ValueError("tool calls are not admitted")
    if request.get("file_edits_allowed") is not False:
        raise ValueError("file edits are not admitted")
    if request.get("timeout_seconds", 0) > provider.timeout_seconds_max:
        raise ValueError("model timeout_seconds exceeds provider policy")
    if request.get("max_budget_usd", -1) > provider.max_budget_usd_hard_limit:
        raise ValueError("model max_budget_usd exceeds provider policy")
    retry_policy = request.get("schema_retry_policy")
    if not isinstance(retry_policy, dict):
        raise ValueError("schema retry policy is missing")
    if retry_policy.get("max_attempts", 0) > provider.max_schema_retries + 1:
        raise ValueError("schema retry policy exceeds provider policy")


def _provider_from_request_file(request_file: Path) -> str:
    try:
        request = json.loads(request_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "unknown"
    if not isinstance(request, dict):
        return "unknown"
    return str(request.get("provider", "unknown"))


def _write_failure_quarantine(
    request_file: Path,
    failure_path: Path,
    provider_id: str,
    error: ValueError,
) -> None:
    payload = {
        "failure_type": "personal_ai_model_provider_failure_quarantine_v1",
        "authority": "non_authority",
        "execution_capability": "model_provider_boundary_only",
        "provider": provider_id,
        "request_path": request_file.as_posix(),
        "request_sha256": sha256_file(request_file),
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "live_provider_called": False,
        "network_used": False,
        "api_key_used": False,
        "api_key_persisted": False,
        "api_key_logged": False,
        "invalid_output_quarantine_required": True,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(failure_path, payload)
