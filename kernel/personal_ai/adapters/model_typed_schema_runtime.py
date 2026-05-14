"""Deterministic local typed-schema mock model runtime."""

from dataclasses import dataclass
from pathlib import Path
import json
import os

from kernel.personal_ai.adapters.adapter_registry import admit_adapter_capability
from kernel.personal_ai.adapters.model_adapter_contract import (
    ModelFixtureSchema,
    ModelRuntimePaths,
    build_model_fixture_capability_request,
    build_model_provider_registry,
    find_model_provider,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ModelFixtureResult",
    "load_provider_api_key_from_environment",
    "run_model_fixture",
    "write_model_provider_request",
    "write_model_fixture_request",
]

_REQUEST_TYPE = "personal_ai_execution_os_v2_model_request"
_INFERENCE_TYPE = "personal_ai_execution_os_v2_model_inference_artifact"
_FAILURE_TYPE = "personal_ai_execution_os_v2_model_failure_bundle"
_PROVIDER = "deterministic_mock"


@dataclass(frozen=True)
class ModelFixtureResult:
    request_path: Path
    output_dir: Path
    inference_artifact_path: Path | None
    failure_bundle_path: Path | None
    success: bool
    schema_name: str
    required_human_approval: bool


def write_model_fixture_request(
    input_artifact_path: Path,
    output_request_path: Path,
    *,
    schema_name: str,
) -> Path:
    return write_model_provider_request(
        input_artifact_path,
        output_request_path,
        schema_name=schema_name,
        provider=_PROVIDER,
    )


def write_model_provider_request(
    input_artifact_path: Path,
    output_request_path: Path,
    *,
    schema_name: str,
    provider: str = _PROVIDER,
    timeout_seconds: int | None = None,
    max_budget_usd: float | None = None,
    max_schema_retries: int = 0,
) -> Path:
    input_path = Path(input_artifact_path)
    request_path = Path(output_request_path)
    if not input_path.exists() or not input_path.is_file():
        raise ValueError("input_artifact_path is missing")
    if request_path.exists():
        raise ValueError("model request output already exists")
    if not request_path.parent.exists() or not request_path.parent.is_dir():
        raise ValueError("model request output parent is missing")
    if schema_name not in ModelFixtureSchema.allowed():
        raise ValueError("schema_name is not supported")
    provider_entry = find_model_provider(provider)
    effective_timeout = (
        provider_entry.timeout_seconds_default
        if timeout_seconds is None
        else timeout_seconds
    )
    effective_budget = (
        provider_entry.max_budget_usd_default
        if max_budget_usd is None
        else max_budget_usd
    )
    payload = {
        "request_type": _REQUEST_TYPE,
        "request_version": 1,
        "provider": provider_entry.provider_id,
        "provider_kind": provider_entry.provider_kind,
        "provider_admitted": provider_entry.admitted,
        "provider_enabled": provider_entry.enabled_by_default,
        "live_provider_runtime": provider_entry.live_provider_runtime,
        "schema_name": schema_name,
        "typed_request_schema": "personal_ai_model_request_v1",
        "typed_response_schema": schema_name,
        "input_artifact_path": input_path.as_posix(),
        "input_artifact_sha256": sha256_file(input_path),
        "network_allowed": False,
        "api_key_required": provider_entry.api_key_env_var is not None,
        "api_key_source": (
            "environment_only" if provider_entry.api_key_env_var else "none"
        ),
        "api_key_env_var": provider_entry.api_key_env_var,
        "api_key_persisted": False,
        "api_key_logged": False,
        "timeout_seconds": effective_timeout,
        "max_budget_usd": effective_budget,
        "estimated_cost_usd": 0.0,
        "schema_retry_policy": {
            "max_attempts": max_schema_retries + 1,
            "retry_on_schema_validation_failure_only": True,
            "invalid_output_quarantine_required": True,
        },
        "tool_calls_allowed": False,
        "file_edits_allowed": False,
        "required_human_approval": True,
    }
    _reject_inline_secret_fields(payload)
    _validate_timeout_and_budget(payload, provider_entry)
    _validate_schema_retry_policy(payload, provider_entry)
    write_json_atomically(request_path, payload)
    return request_path


def load_provider_api_key_from_environment(provider_id: str, environ=None) -> str | None:
    provider = find_model_provider(provider_id)
    if provider.api_key_env_var is None:
        return None
    source = os.environ if environ is None else environ
    return source.get(provider.api_key_env_var)


def run_model_fixture(
    request_path: Path,
    output_dir: Path,
) -> ModelFixtureResult:
    request_file = Path(request_path)
    output_path = Path(output_dir)
    if not request_file.exists() or not request_file.is_file():
        raise ValueError("request_path is missing")
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")

    paths = ModelRuntimePaths()
    inference_path = output_path / paths.inference_artifact_file
    failure_path = output_path / paths.failure_bundle_file
    _require_no_overwrite(inference_path)
    _require_no_overwrite(failure_path)

    decision = admit_adapter_capability(build_model_fixture_capability_request())
    if not decision.is_runtime_safe_for_current_branch():
        raise ValueError("mock model adapter is not admitted")

    try:
        request = _read_json(request_file)
        _validate_request(request)
        input_artifact = _read_json(Path(request["input_artifact_path"]))
        output, retry_summary = _build_validated_fixture_output(
            request,
            input_artifact,
        )
    except ValueError as error:
        _write_failure_bundle(request_file, failure_path, error)
        return ModelFixtureResult(
            request_path=request_file,
            output_dir=output_path,
            inference_artifact_path=None,
            failure_bundle_path=failure_path,
            success=False,
            schema_name=_schema_name_from_request_file(request_file),
            required_human_approval=True,
        )

    artifact = {
        "artifact_type": _INFERENCE_TYPE,
        "authority": "non_authority",
        "execution_capability": "deterministic_mock_model_only",
        "provider": _PROVIDER,
        "provider_registry": [
            entry.to_dict() for entry in build_model_provider_registry()
        ],
        "live_provider_runtime": False,
        "network_used": False,
        "api_key_used": False,
        "api_key_persisted": False,
        "api_key_logged": False,
        "timeout_seconds": request["timeout_seconds"],
        "max_budget_usd": request["max_budget_usd"],
        "estimated_cost_usd": 0.0,
        "schema_retry_policy": request["schema_retry_policy"],
        "schema_retry_attempts": retry_summary["attempts"],
        "invalid_outputs_quarantined": retry_summary["invalid_outputs_quarantined"],
        "model_output_can_grant_authority": False,
        "model_output_can_edit_files": False,
        "model_output_can_call_tools": False,
        "request_path": request_file.as_posix(),
        "request_sha256": sha256_file(request_file),
        "schema_name": request["schema_name"],
        "typed_request_schema": request["typed_request_schema"],
        "typed_response_schema": request["typed_response_schema"],
        "input_artifact_path": request["input_artifact_path"],
        "input_artifact_sha256": request["input_artifact_sha256"],
        "typed_output": output,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(inference_path, artifact)
    return ModelFixtureResult(
        request_path=request_file,
        output_dir=output_path,
        inference_artifact_path=inference_path,
        failure_bundle_path=None,
        success=True,
        schema_name=request["schema_name"],
        required_human_approval=True,
    )


def _require_no_overwrite(path):
    if Path(path).exists():
        raise ValueError("model runtime output already exists")


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("json artifact is malformed") from error


def _validate_request(request):
    if not isinstance(request, dict):
        raise ValueError("model request must be an object")
    if request.get("request_type") != _REQUEST_TYPE:
        raise ValueError("model request_type mismatch")
    provider = find_model_provider(str(request.get("provider", "")))
    if provider.provider_id != _PROVIDER:
        _validate_live_provider_request_boundary(request, provider)
        raise ValueError("live model provider is disabled by default")
    if request.get("provider_admitted") is not True:
        raise ValueError("model provider is not admitted")
    if request.get("provider_enabled") is not True:
        raise ValueError("model provider is not enabled")
    if request.get("live_provider_runtime") is not False:
        raise ValueError("live provider runtime is not admitted")
    if request.get("schema_name") not in ModelFixtureSchema.allowed():
        raise ValueError("schema_name is not supported")
    if request.get("typed_request_schema") != "personal_ai_model_request_v1":
        raise ValueError("typed request schema mismatch")
    if request.get("typed_response_schema") != request.get("schema_name"):
        raise ValueError("typed response schema mismatch")
    _reject_inline_secret_fields(request)
    if request.get("api_key_required") is not False:
        raise ValueError("api key use is not admitted")
    if request.get("api_key_source") != "none":
        raise ValueError("api key source is not admitted")
    if request.get("api_key_persisted") is not False:
        raise ValueError("api key persistence is not admitted")
    if request.get("api_key_logged") is not False:
        raise ValueError("api key logging is not admitted")
    if request.get("network_allowed") is not False:
        raise ValueError("network runtime is not admitted")
    if request.get("tool_calls_allowed") is not False:
        raise ValueError("tool calls are not admitted")
    if request.get("file_edits_allowed") is not False:
        raise ValueError("file edits are not admitted")
    input_path = Path(str(request.get("input_artifact_path", "")))
    if not input_path.exists() or not input_path.is_file():
        raise ValueError("input_artifact_path is missing")
    if request.get("input_artifact_sha256") != sha256_file(input_path):
        raise ValueError("input artifact hash mismatch")
    _validate_timeout_and_budget(request, provider)
    _validate_schema_retry_policy(request, provider)


def _validate_live_provider_request_boundary(request, provider):
    _reject_inline_secret_fields(request)
    if provider.enabled_by_default is not False or provider.admitted is not False:
        raise ValueError("live model provider registry boundary is malformed")
    if request.get("network_allowed") is not False:
        raise ValueError("live model network runtime is not admitted")
    if request.get("provider_enabled") is not False:
        raise ValueError("live model provider must be disabled by default")
    if request.get("api_key_source") != "environment_only":
        raise ValueError("live model api key source must be environment_only")
    if request.get("api_key_persisted") is not False:
        raise ValueError("api key persistence is not admitted")
    if request.get("api_key_logged") is not False:
        raise ValueError("api key logging is not admitted")
    _validate_timeout_and_budget(request, provider)
    _validate_schema_retry_policy(request, provider)


def _reject_inline_secret_fields(request):
    forbidden_fields = {
        "api_key",
        "access_token",
        "authorization",
        "bearer_token",
        "password",
        "secret",
    }
    if any(field in request for field in forbidden_fields):
        raise ValueError("inline model provider secrets are not admitted")


def _validate_timeout_and_budget(request, provider):
    timeout_seconds = request.get("timeout_seconds")
    if type(timeout_seconds) is not int or timeout_seconds <= 0:
        raise ValueError("model timeout_seconds is invalid")
    if timeout_seconds > provider.timeout_seconds_max:
        raise ValueError("model timeout_seconds exceeds provider policy")
    max_budget = request.get("max_budget_usd")
    estimated_cost = request.get("estimated_cost_usd")
    if type(max_budget) not in (int, float) or max_budget < 0:
        raise ValueError("model max_budget_usd is invalid")
    if type(estimated_cost) not in (int, float) or estimated_cost < 0:
        raise ValueError("model estimated_cost_usd is invalid")
    if max_budget > provider.max_budget_usd_hard_limit:
        raise ValueError("model max_budget_usd exceeds provider policy")
    if estimated_cost > max_budget:
        raise ValueError("model estimated_cost_usd exceeds budget")


def _validate_schema_retry_policy(request, provider):
    retry_policy = request.get("schema_retry_policy")
    if not isinstance(retry_policy, dict):
        raise ValueError("schema retry policy is missing")
    max_attempts = retry_policy.get("max_attempts")
    if type(max_attempts) is not int or max_attempts <= 0:
        raise ValueError("schema retry policy max_attempts is invalid")
    if max_attempts > provider.max_schema_retries + 1:
        raise ValueError("schema retry policy exceeds provider policy")
    if retry_policy.get("retry_on_schema_validation_failure_only") is not True:
        raise ValueError("schema retry policy must be schema-only")
    if retry_policy.get("invalid_output_quarantine_required") is not True:
        raise ValueError("schema retry policy must require quarantine")


def _build_validated_fixture_output(request, input_artifact):
    candidates = _fixture_output_candidates(request, input_artifact)
    max_attempts = request["schema_retry_policy"]["max_attempts"]
    last_error = None
    invalid_outputs_quarantined = 0
    for attempt_index, candidate in enumerate(candidates[:max_attempts], start=1):
        try:
            _validate_model_output(request["schema_name"], candidate)
        except ValueError as error:
            invalid_outputs_quarantined += 1
            last_error = error
            continue
        return candidate, {
            "attempts": attempt_index,
            "invalid_outputs_quarantined": invalid_outputs_quarantined,
        }
    if last_error is None:
        raise ValueError("model output candidates are missing")
    raise ValueError("model output schema retry exhausted: " + str(last_error))


def _fixture_output_candidates(request, input_artifact):
    if "fixture_response_sequence" in request:
        sequence = request["fixture_response_sequence"]
        if not isinstance(sequence, list) or not sequence:
            raise ValueError("fixture response sequence is malformed")
        return [_parse_fixture_output_value(value) for value in sequence]
    return [_build_or_parse_fixture_output(request, input_artifact)]


def _build_or_parse_fixture_output(request, input_artifact):
    if "fixture_response_json" in request:
        try:
            output = json.loads(request["fixture_response_json"])
        except json.JSONDecodeError as error:
            raise ValueError("fixture response json is malformed") from error
        return output
    if "fixture_response" in request:
        return request["fixture_response"]

    schema_name = request["schema_name"]
    if schema_name == ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION:
        return _classify_job_route(input_artifact)
    if schema_name == ModelFixtureSchema.ARTIFACT_PROFILE_SUMMARY:
        return _summarize_artifact_profile(input_artifact)
    if schema_name == ModelFixtureSchema.NEXT_STEP_RECOMMENDATION:
        return _recommend_next_step(input_artifact)
    raise ValueError("schema_name is not supported")


def _parse_fixture_output_value(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("fixture response sequence json is malformed") from error
    return value


def _classify_job_route(input_artifact):
    return _base_output(
        ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        {
            "route_type": str(input_artifact.get("route_type", "unknown")),
            "recommended_processor_lane": str(
                input_artifact.get("recommended_processor_lane", "human_review_only")
            ),
            "confidence": "deterministic_fixture",
        },
    )


def _summarize_artifact_profile(input_artifact):
    artifacts = input_artifact.get("artifacts", [])
    if not isinstance(artifacts, list):
        artifacts = []
    categories = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        category = str(artifact.get("category", "unknown"))
        categories[category] = categories.get(category, 0) + 1
    return _base_output(
        ModelFixtureSchema.ARTIFACT_PROFILE_SUMMARY,
        {
            "artifact_count": len(artifacts),
            "category_counts": {
                key: categories[key]
                for key in sorted(categories)
            },
        },
    )


def _recommend_next_step(input_artifact):
    return _base_output(
        ModelFixtureSchema.NEXT_STEP_RECOMMENDATION,
        {
            "recommendation": str(
                input_artifact.get("next_allowed_action", "human_review_only")
            ),
            "requires_human_approval": True,
        },
    )


def _base_output(schema_name, payload):
    output = {
        "schema_name": schema_name,
        "authority": "non_authority",
        "can_grant_authority": False,
        "can_edit_files": False,
        "can_call_tools": False,
    }
    output.update(payload)
    return output


def _validate_model_output(schema_name, output):
    if not isinstance(output, dict):
        raise ValueError("model output must be an object")
    required = {
        "schema_name",
        "authority",
        "can_grant_authority",
        "can_edit_files",
        "can_call_tools",
    }
    missing = sorted(required.difference(output))
    if missing:
        raise ValueError("model output is missing required fields")
    if output["schema_name"] != schema_name:
        raise ValueError("model output schema_name mismatch")
    if output["authority"] != "non_authority":
        raise ValueError("model output authority mismatch")
    if output["can_grant_authority"] is not False:
        raise ValueError("model output cannot grant authority")
    if output["can_edit_files"] is not False:
        raise ValueError("model output cannot edit files")
    if output["can_call_tools"] is not False:
        raise ValueError("model output cannot call tools")
    if schema_name == ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION:
        _require_string(output, "route_type")
        _require_string(output, "recommended_processor_lane")
        _require_string(output, "confidence")
    elif schema_name == ModelFixtureSchema.ARTIFACT_PROFILE_SUMMARY:
        if type(output.get("artifact_count")) is not int:
            raise ValueError("artifact_count is invalid")
        if not isinstance(output.get("category_counts"), dict):
            raise ValueError("category_counts is invalid")
    elif schema_name == ModelFixtureSchema.NEXT_STEP_RECOMMENDATION:
        _require_string(output, "recommendation")
        if output.get("requires_human_approval") is not True:
            raise ValueError("requires_human_approval is invalid")


def _require_string(output, field_name):
    if not isinstance(output.get(field_name), str) or not output[field_name]:
        raise ValueError(field_name + " is invalid")


def _write_failure_bundle(request_file, failure_path, error):
    request = _read_json_for_failure(request_file)
    retry_policy = (
        request.get("schema_retry_policy", {})
        if isinstance(request, dict)
        else {}
    )
    payload = {
        "failure_type": _FAILURE_TYPE,
        "authority": "non_authority",
        "execution_capability": "deterministic_mock_model_only",
        "request_path": request_file.as_posix(),
        "request_sha256": sha256_file(request_file),
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "live_provider_runtime": False,
        "network_used": False,
        "api_key_used": False,
        "api_key_persisted": False,
        "api_key_logged": False,
        "schema_retry_policy": retry_policy,
        "schema_retry_attempts": retry_policy.get("max_attempts", 1),
        "invalid_output_quarantined": True,
        "model_output_granted_authority": False,
        "model_output_edited_files": False,
        "model_output_called_tools": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(failure_path, payload)


def _read_json_for_failure(path):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _schema_name_from_request_file(request_file):
    try:
        request = json.loads(Path(request_file).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "unknown"
    return str(request.get("schema_name", "unknown"))
