"""Controlled activation package for live model provider boundaries.

This module does not call live providers. It prepares and validates the
artifacts required before a future live-provider smoke runner can be admitted.
"""

from dataclasses import dataclass
from pathlib import Path
import json
import os

from kernel.personal_ai.adapters.model_adapter_contract import (
    ModelFixtureSchema,
    find_model_provider,
)
from kernel.personal_ai.adapters.model_provider_boundary import (
    boundary_for_provider,
    validate_model_provider_boundary,
    write_model_provider_admission_artifacts,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_admission_gate import (
    RuntimeAdmissionRequest,
    evaluate_runtime_admission,
)

__all__ = [
    "ModelProviderActivationPackageResult",
    "build_model_provider_activation_package",
    "validate_model_provider_activation_package",
]

_ACTIVATION_PLAN_FILE = "model_provider_activation_plan.json"
_ADMISSION_DIR = "runtime_admission"
_VALIDATION_FILE = "model_provider_activation_validation.json"
_PACKAGE_TYPE = "personal_ai_model_provider_controlled_activation_package_v1"
_VALIDATION_TYPE = "personal_ai_model_provider_controlled_activation_validation_v1"


@dataclass(frozen=True)
class ModelProviderActivationPackageResult:
    package_dir: Path
    activation_plan_path: Path
    admission_config_path: Path
    admission_approval_path: Path
    admission_manifest_path: Path
    validation_path: Path
    provider_id: str
    schema_name: str
    complete: bool
    live_provider_called: bool
    network_used: bool
    required_human_approval: bool


def build_model_provider_activation_package(
    output_dir: Path,
    *,
    provider_id: str,
    schema_name: str,
    reviewer_id: str,
    environ=None,
) -> ModelProviderActivationPackageResult:
    """Build a controlled activation package without executing a live call."""

    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    if schema_name not in ModelFixtureSchema.allowed():
        raise ValueError("schema_name is not supported")
    if not reviewer_id.strip():
        raise ValueError("reviewer_id is required")

    provider = find_model_provider(provider_id)
    boundary = boundary_for_provider(provider_id)
    failures = validate_model_provider_boundary(boundary)
    if failures:
        raise ValueError("model provider boundary is invalid: " + ",".join(failures))
    if provider.live_provider_runtime is not True:
        raise ValueError("controlled activation package is only for live provider boundaries")

    plan_path = output_path / _ACTIVATION_PLAN_FILE
    validation_path = output_path / _VALIDATION_FILE
    admission_dir = output_path / _ADMISSION_DIR
    _require_no_overwrite(plan_path)
    _require_no_overwrite(validation_path)
    _require_no_overwrite(admission_dir)
    admission_dir.mkdir()

    artifacts = write_model_provider_admission_artifacts(
        admission_dir,
        provider_id=provider_id,
        schema_name=schema_name,
        dry_run=True,
        reviewer_id=reviewer_id,
    )
    admission_decision = evaluate_runtime_admission(
        RuntimeAdmissionRequest(
            adapter_id=boundary.adapter_id,
            capability=boundary.capability,
            runtime_class=boundary.runtime_class,
            config_artifact_path=artifacts.config_path,
            human_approval_artifact_path=artifacts.human_approval_path,
            manifest_artifact_path=artifacts.manifest_path,
            dry_run=True,
            activation_sources=("human_approval_artifact",),
        )
    )
    source = os.environ if environ is None else environ
    api_key_present = (
        provider.api_key_env_var is not None
        and bool(source.get(provider.api_key_env_var, ""))
    )
    plan = {
        "package_type": _PACKAGE_TYPE,
        "authority": "non_authority",
        "execution_capability": "controlled_activation_plan_only",
        "provider_id": provider_id,
        "schema_name": schema_name,
        "adapter_id": boundary.adapter_id,
        "capability": boundary.capability,
        "runtime_class": boundary.runtime_class,
        "live_provider_runtime": True,
        "live_provider_enabled_by_default": False,
        "activation_enabled": False,
        "dry_run_only": True,
        "api_key_source": "environment_only",
        "api_key_env_var": provider.api_key_env_var,
        "api_key_present": api_key_present,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "network_call_allowed": False,
        "network_call_performed": False,
        "live_provider_call_performed": False,
        "tool_calls_allowed": False,
        "file_edits_allowed": False,
        "timeout_seconds_default": provider.timeout_seconds_default,
        "timeout_seconds_max": provider.timeout_seconds_max,
        "max_budget_usd_default": provider.max_budget_usd_default,
        "max_budget_usd_hard_limit": provider.max_budget_usd_hard_limit,
        "max_schema_retries": provider.max_schema_retries,
        "schema_validation_required": True,
        "invalid_output_quarantine_required": True,
        "admission_config_path": artifacts.config_path.as_posix(),
        "admission_config_sha256": artifacts.config_sha256,
        "admission_approval_path": artifacts.human_approval_path.as_posix(),
        "admission_approval_sha256": artifacts.human_approval_sha256,
        "admission_manifest_path": artifacts.manifest_path.as_posix(),
        "admission_manifest_sha256": artifacts.manifest_sha256,
        "runtime_admission_decision": admission_decision.to_dict(),
        "required_human_approval": True,
        "human_review_required_before_live_smoke": True,
        "next_allowed_action": "human_review_activation_package",
    }
    write_json_atomically(plan_path, plan)
    validation = _build_validation_payload(output_path, plan_path)
    write_json_atomically(validation_path, validation)
    return ModelProviderActivationPackageResult(
        package_dir=output_path,
        activation_plan_path=plan_path,
        admission_config_path=artifacts.config_path,
        admission_approval_path=artifacts.human_approval_path,
        admission_manifest_path=artifacts.manifest_path,
        validation_path=validation_path,
        provider_id=provider_id,
        schema_name=schema_name,
        complete=bool(validation["complete"]),
        live_provider_called=False,
        network_used=False,
        required_human_approval=True,
    )


def validate_model_provider_activation_package(
    package_dir: Path,
    output_path: Path | None = None,
) -> dict[str, object]:
    package_path = Path(package_dir)
    if not package_path.exists() or not package_path.is_dir():
        raise ValueError("package_dir is missing")
    plan_path = package_path / _ACTIVATION_PLAN_FILE
    validation = _build_validation_payload(package_path, plan_path)
    if output_path is not None:
        output_file = Path(output_path)
        if output_file.exists():
            raise ValueError("activation validation output already exists")
        if not output_file.parent.exists() or not output_file.parent.is_dir():
            raise ValueError("activation validation output parent is missing")
        write_json_atomically(output_file, validation)
    return validation


def _build_validation_payload(package_path: Path, plan_path: Path) -> dict[str, object]:
    failures: list[str] = []
    plan = _read_json_file(plan_path, failures, "activation_plan")
    _validate_plan(plan, failures)
    artifact_hashes = _validate_artifact_hashes(plan, failures)
    complete = not failures
    return {
        "validation_type": _VALIDATION_TYPE,
        "package_dir": package_path.as_posix(),
        "activation_plan_path": plan_path.as_posix(),
        "activation_plan_sha256": sha256_file(plan_path)
        if plan_path.exists() and plan_path.is_file()
        else None,
        "complete": complete,
        "failures": sorted(set(failures)),
        "artifact_hashes": artifact_hashes,
        "live_provider_called": False,
        "network_used": False,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "activation_enabled": False,
        "dry_run_only": True,
        "required_human_approval": True,
    }


def _read_json_file(path: Path, failures: list[str], label: str) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        failures.append(label + "_missing")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        failures.append(label + "_malformed")
        return {}
    if not isinstance(payload, dict):
        failures.append(label + "_malformed")
        return {}
    return payload


def _validate_plan(plan: dict[str, object], failures: list[str]) -> None:
    if not plan:
        return
    expected_false = (
        "activation_enabled",
        "network_call_allowed",
        "network_call_performed",
        "live_provider_call_performed",
        "tool_calls_allowed",
        "file_edits_allowed",
        "api_key_value_persisted",
        "api_key_value_logged",
    )
    for field_name in expected_false:
        if plan.get(field_name) is not False:
            failures.append(field_name + "_must_be_false")
    if plan.get("package_type") != _PACKAGE_TYPE:
        failures.append("package_type_mismatch")
    if plan.get("authority") != "non_authority":
        failures.append("authority_mismatch")
    if plan.get("execution_capability") != "controlled_activation_plan_only":
        failures.append("execution_capability_mismatch")
    if plan.get("dry_run_only") is not True:
        failures.append("dry_run_only_required")
    if plan.get("api_key_source") != "environment_only":
        failures.append("api_key_source_mismatch")
    if plan.get("schema_validation_required") is not True:
        failures.append("schema_validation_required")
    if plan.get("invalid_output_quarantine_required") is not True:
        failures.append("invalid_output_quarantine_required")
    if plan.get("required_human_approval") is not True:
        failures.append("required_human_approval")
    decision = plan.get("runtime_admission_decision")
    if not isinstance(decision, dict):
        failures.append("runtime_admission_decision_missing")
        return
    if decision.get("admitted") is not True:
        failures.append("runtime_admission_not_admitted")
    if decision.get("activation_allowed") is not False:
        failures.append("runtime_activation_must_remain_false")
    if decision.get("dry_run") is not True:
        failures.append("runtime_admission_dry_run_required")
    if decision.get("required_human_approval") is not True:
        failures.append("runtime_admission_human_approval_required")
    if decision.get("manifest_hash_bound") is not True:
        failures.append("runtime_admission_manifest_hash_bound_required")


def _validate_artifact_hashes(
    plan: dict[str, object],
    failures: list[str],
) -> dict[str, str]:
    artifact_hashes: dict[str, str] = {}
    if not plan:
        return artifact_hashes
    for label, path_key, hash_key in (
        ("config", "admission_config_path", "admission_config_sha256"),
        ("approval", "admission_approval_path", "admission_approval_sha256"),
        ("manifest", "admission_manifest_path", "admission_manifest_sha256"),
    ):
        path_value = plan.get(path_key)
        hash_value = plan.get(hash_key)
        if not isinstance(path_value, str) or not path_value:
            failures.append(label + "_path_missing")
            continue
        path = Path(path_value)
        if not path.exists() or not path.is_file():
            failures.append(label + "_artifact_missing")
            continue
        actual_hash = sha256_file(path)
        artifact_hashes[label + "_sha256"] = actual_hash
        if hash_value != actual_hash:
            failures.append(label + "_hash_mismatch")
    return artifact_hashes


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("model provider activation package output already exists")
