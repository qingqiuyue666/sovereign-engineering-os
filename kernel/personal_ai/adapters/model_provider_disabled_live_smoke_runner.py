"""Disabled-by-default live model provider smoke runner.

This runner does not import network clients and does not perform a live call by
itself. A future live caller must supply an explicit transport callable after a
human-reviewed smoke plan is produced. Normal tests exercise only denied and
injected-transport paths.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
import json
import os

from kernel.personal_ai.adapters.model_provider_live_smoke import (
    validate_disabled_model_provider_live_smoke_plan,
)
from kernel.personal_ai.adapters.model_provider_transport_adapter import (
    build_live_smoke_transport_request,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ModelProviderLiveSmokeRunnerResult",
    "run_model_provider_disabled_live_smoke",
]

_RESULT_FILE = "model_provider_live_smoke_result.json"
_FAILURE_FILE = "model_provider_live_smoke_failure_quarantine.json"
_RESULT_TYPE = "personal_ai_model_provider_disabled_live_smoke_result_v1"
_FAILURE_TYPE = "personal_ai_model_provider_disabled_live_smoke_failure_v1"
_ENABLE_FLAG = "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE"
_EXPECTED_ENABLE_VALUE = "true"

LiveSmokeTransport = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class ModelProviderLiveSmokeRunnerResult:
    output_dir: Path
    result_path: Path | None
    failure_path: Path | None
    status: str
    live_provider_called: bool
    network_used_by_runner: bool
    api_key_value_persisted: bool
    api_key_value_logged: bool
    required_human_approval: bool


def run_model_provider_disabled_live_smoke(
    plan_path: Path,
    output_dir: Path,
    *,
    environ: Mapping[str, str] | None = None,
    allow_live_smoke: bool = False,
    live_transport: LiveSmokeTransport | None = None,
) -> ModelProviderLiveSmokeRunnerResult:
    """Run the gated live-smoke path only when every explicit control is set."""

    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    result_path = output_path / _RESULT_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(result_path)
    _require_no_overwrite(failure_path)
    try:
        plan_file = Path(plan_path)
        validation = validate_disabled_model_provider_live_smoke_plan(plan_file)
        if not validation["complete"]:
            raise ValueError("live smoke plan validation failed")
        plan = _read_plan(plan_file)
        source = os.environ if environ is None else environ
        api_key_env_var = _require_string(plan, "api_key_env_var")
        api_key_present = bool(source.get(api_key_env_var, ""))
        if allow_live_smoke is not True:
            return _write_denied_result(
                result_path,
                plan_file,
                plan,
                status="disabled_by_callsite",
                api_key_present=api_key_present,
            )
        if source.get(_ENABLE_FLAG) != _EXPECTED_ENABLE_VALUE:
            return _write_denied_result(
                result_path,
                plan_file,
                plan,
                status="disabled_by_environment_flag",
                api_key_present=api_key_present,
            )
        if not api_key_present:
            return _write_denied_result(
                result_path,
                plan_file,
                plan,
                status="missing_environment_api_key",
                api_key_present=False,
            )
        if live_transport is None:
            return _write_denied_result(
                result_path,
                plan_file,
                plan,
                status="missing_explicit_live_transport",
                api_key_present=True,
            )
        request = _build_transport_request(plan, plan_file)
        provider_response = live_transport(request)
        response_validation = _validate_transport_response(provider_response)
        result = {
            "result_type": _RESULT_TYPE,
            "authority": "non_authority",
            "execution_capability": "explicit_transport_live_smoke_only",
            "status": "completed_via_explicit_transport",
            "provider_id": plan.get("provider_id"),
            "plan_path": plan_file.as_posix(),
            "plan_sha256": sha256_file(plan_file),
            "allow_live_smoke": True,
            "environment_enable_flag": _ENABLE_FLAG,
            "environment_enable_flag_value_matched": True,
            "api_key_source": "environment_only",
            "api_key_env_var": api_key_env_var,
            "api_key_present": True,
            "api_key_value_persisted": False,
            "api_key_value_logged": False,
            "live_transport_required": True,
            "live_transport_called": True,
            "live_provider_called": True,
            "network_used_by_runner": False,
            "tool_calls_allowed": False,
            "tool_calls_performed": False,
            "file_edits_allowed": False,
            "file_edits_performed": False,
            "schema_validation_performed": True,
            "schema_validation": response_validation,
            "raw_provider_response_persisted": False,
            "required_human_approval": True,
            "next_allowed_action": "human_review_live_smoke_result",
        }
        write_json_atomically(result_path, result)
        return ModelProviderLiveSmokeRunnerResult(
            output_dir=output_path,
            result_path=result_path,
            failure_path=None,
            status="completed_via_explicit_transport",
            live_provider_called=True,
            network_used_by_runner=False,
            api_key_value_persisted=False,
            api_key_value_logged=False,
            required_human_approval=True,
        )
    except ValueError as error:
        failure = {
            "failure_type": _FAILURE_TYPE,
            "status": "failed_closed",
            "reason": str(error),
            "plan_path": Path(plan_path).as_posix(),
            "live_provider_called": False,
            "network_used_by_runner": False,
            "api_key_value_persisted": False,
            "api_key_value_logged": False,
            "required_human_approval": True,
        }
        write_json_atomically(failure_path, failure)
        return ModelProviderLiveSmokeRunnerResult(
            output_dir=output_path,
            result_path=None,
            failure_path=failure_path,
            status="failed_closed",
            live_provider_called=False,
            network_used_by_runner=False,
            api_key_value_persisted=False,
            api_key_value_logged=False,
            required_human_approval=True,
        )


def _write_denied_result(
    result_path: Path,
    plan_file: Path,
    plan: dict[str, object],
    *,
    status: str,
    api_key_present: bool,
) -> ModelProviderLiveSmokeRunnerResult:
    result = {
        "result_type": _RESULT_TYPE,
        "authority": "non_authority",
        "execution_capability": "disabled_live_smoke_denial_only",
        "status": status,
        "provider_id": plan.get("provider_id"),
        "plan_path": plan_file.as_posix(),
        "plan_sha256": sha256_file(plan_file),
        "allow_live_smoke": False,
        "environment_enable_flag": _ENABLE_FLAG,
        "api_key_source": "environment_only",
        "api_key_env_var": plan.get("api_key_env_var"),
        "api_key_present": api_key_present,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "live_transport_called": False,
        "live_provider_called": False,
        "network_used_by_runner": False,
        "tool_calls_allowed": False,
        "tool_calls_performed": False,
        "file_edits_allowed": False,
        "file_edits_performed": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_live_smoke_denial",
    }
    write_json_atomically(result_path, result)
    return ModelProviderLiveSmokeRunnerResult(
        output_dir=result_path.parent,
        result_path=result_path,
        failure_path=None,
        status=status,
        live_provider_called=False,
        network_used_by_runner=False,
        api_key_value_persisted=False,
        api_key_value_logged=False,
        required_human_approval=True,
    )


def _build_transport_request(
    plan: dict[str, object],
    plan_file: Path,
) -> dict[str, object]:
    provider_id = _require_string(plan, "provider_id")
    return build_live_smoke_transport_request(
        provider_id=provider_id,
        plan_sha256=sha256_file(plan_file),
        timeout_seconds=20,
        max_budget_usd=0.01,
        schema_name="live_smoke_status_v1",
    )


def _validate_transport_response(response: dict[str, object]) -> dict[str, object]:
    failures: list[str] = []
    if not isinstance(response, dict):
        failures.append("response_malformed")
        response = {}
    if response.get("status") != "ok":
        failures.append("status_not_ok")
    if not isinstance(response.get("provider_id"), str) or not response.get("provider_id"):
        failures.append("provider_id_missing")
    if response.get("tool_call_requested") not in (None, False):
        failures.append("tool_call_requested")
    if response.get("file_edit_requested") not in (None, False):
        failures.append("file_edit_requested")
    return {
        "complete": not failures,
        "failures": sorted(set(failures)),
        "allowed_output_fields": ["status", "provider_id"],
        "raw_response_persisted": False,
    }


def _read_plan(path: Path) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        raise ValueError("live smoke plan is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("live smoke plan is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError("live smoke plan is malformed")
    return payload


def _require_string(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(field_name + " is required")
    return value


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("model provider live smoke runner output already exists")
