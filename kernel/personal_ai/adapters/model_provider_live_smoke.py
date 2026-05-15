"""Disabled-by-default live model provider smoke plan.

This module deliberately does not call a live model provider. It creates and
validates a future live-smoke plan that remains disabled until a later explicit
runner is reviewed and admitted.
"""

from dataclasses import dataclass
from pathlib import Path
import json
import os

from kernel.personal_ai.adapters.model_provider_activation_package import (
    validate_model_provider_activation_package,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ModelProviderLiveSmokePlanResult",
    "build_disabled_model_provider_live_smoke_plan",
    "validate_disabled_model_provider_live_smoke_plan",
]

_PLAN_FILE = "model_provider_live_smoke_plan.json"
_VALIDATION_FILE = "model_provider_live_smoke_validation.json"
_PLAN_TYPE = "personal_ai_model_provider_disabled_live_smoke_plan_v1"
_VALIDATION_TYPE = "personal_ai_model_provider_disabled_live_smoke_validation_v1"


@dataclass(frozen=True)
class ModelProviderLiveSmokePlanResult:
    output_dir: Path
    plan_path: Path
    validation_path: Path
    complete: bool
    live_provider_called: bool
    network_used: bool
    required_human_approval: bool


def build_disabled_model_provider_live_smoke_plan(
    activation_package_dir: Path,
    output_dir: Path,
    *,
    provider_id: str,
    api_key_env_var: str,
    environ=None,
) -> ModelProviderLiveSmokePlanResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    if not provider_id:
        raise ValueError("provider_id is required")
    if not api_key_env_var:
        raise ValueError("api_key_env_var is required")
    plan_path = output_path / _PLAN_FILE
    validation_path = output_path / _VALIDATION_FILE
    _require_no_overwrite(plan_path)
    _require_no_overwrite(validation_path)
    activation_validation = validate_model_provider_activation_package(
        Path(activation_package_dir)
    )
    if not activation_validation["complete"]:
        raise ValueError("activation package validation failed")
    source = os.environ if environ is None else environ
    api_key_present = bool(source.get(api_key_env_var, ""))
    plan = {
        "plan_type": _PLAN_TYPE,
        "authority": "non_authority",
        "execution_capability": "disabled_live_smoke_plan_only",
        "provider_id": provider_id,
        "activation_package_dir": Path(activation_package_dir).as_posix(),
        "activation_validation_complete": True,
        "activation_validation_sha256": sha256_file(
            Path(activation_package_dir) / "model_provider_activation_validation.json"
        ),
        "api_key_source": "environment_only",
        "api_key_env_var": api_key_env_var,
        "api_key_present": api_key_present,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "live_smoke_enabled": False,
        "explicit_enable_flag_required": "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE=true",
        "network_call_allowed": False,
        "network_call_performed": False,
        "live_provider_call_performed": False,
        "tool_calls_allowed": False,
        "file_edits_allowed": False,
        "normal_tests_must_not_require_api_key": True,
        "required_human_approval": True,
        "next_allowed_action": "human_review_disabled_live_smoke_plan",
    }
    write_json_atomically(plan_path, plan)
    validation = _validate_plan_payload(plan_path)
    write_json_atomically(validation_path, validation)
    return ModelProviderLiveSmokePlanResult(
        output_dir=output_path,
        plan_path=plan_path,
        validation_path=validation_path,
        complete=bool(validation["complete"]),
        live_provider_called=False,
        network_used=False,
        required_human_approval=True,
    )


def validate_disabled_model_provider_live_smoke_plan(plan_path: Path) -> dict[str, object]:
    return _validate_plan_payload(Path(plan_path))


def _validate_plan_payload(plan_path: Path) -> dict[str, object]:
    failures: list[str] = []
    plan = _read_json_file(plan_path, failures)
    if plan:
        if plan.get("plan_type") != _PLAN_TYPE:
            failures.append("plan_type_mismatch")
        if plan.get("authority") != "non_authority":
            failures.append("authority_mismatch")
        if plan.get("execution_capability") != "disabled_live_smoke_plan_only":
            failures.append("execution_capability_mismatch")
        for field_name in (
            "live_smoke_enabled",
            "network_call_allowed",
            "network_call_performed",
            "live_provider_call_performed",
            "api_key_value_persisted",
            "api_key_value_logged",
            "tool_calls_allowed",
            "file_edits_allowed",
        ):
            if plan.get(field_name) is not False:
                failures.append(field_name + "_must_be_false")
        if plan.get("api_key_source") != "environment_only":
            failures.append("api_key_source_mismatch")
        if plan.get("required_human_approval") is not True:
            failures.append("required_human_approval")
    return {
        "validation_type": _VALIDATION_TYPE,
        "plan_path": plan_path.as_posix(),
        "plan_sha256": sha256_file(plan_path)
        if plan_path.exists() and plan_path.is_file()
        else None,
        "complete": not failures,
        "failures": sorted(set(failures)),
        "live_provider_called": False,
        "network_used": False,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "required_human_approval": True,
    }


def _read_json_file(path: Path, failures: list[str]) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        failures.append("plan_missing")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        failures.append("plan_malformed")
        return {}
    if not isinstance(payload, dict):
        failures.append("plan_malformed")
        return {}
    return payload


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("model provider live smoke output already exists")
