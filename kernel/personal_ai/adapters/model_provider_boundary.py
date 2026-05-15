"""Product-grade model provider boundary helpers."""

from dataclasses import dataclass
from pathlib import Path

from kernel.personal_ai.adapters.model_adapter_contract import (
    ModelFixtureSchema,
    ModelProviderRegistryEntry,
    build_model_provider_registry,
    find_model_provider,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_admission_gate import runtime_policy_for_class

__all__ = [
    "ModelProviderAdmissionArtifacts",
    "ModelProviderBoundary",
    "boundary_for_provider",
    "build_model_provider_boundaries",
    "validate_model_provider_boundary",
    "write_model_provider_admission_artifacts",
]

_CONFIG_TYPE = "personal_ai_runtime_config_v1"
_APPROVAL_TYPE = "personal_ai_runtime_human_approval_v1"
_MANIFEST_TYPE = "personal_ai_runtime_manifest_v1"
_APPROVED_ACTION = "admit_runtime_execution"


@dataclass(frozen=True)
class ModelProviderBoundary:
    provider_id: str
    adapter_id: str
    capability: str
    runtime_class: str
    default_provider: bool
    enabled_by_default: bool
    admitted_by_default: bool
    live_provider_runtime: bool
    api_key_env_var: str | None
    timeout_seconds_default: int
    timeout_seconds_max: int
    max_budget_usd_default: float
    max_budget_usd_hard_limit: float
    max_schema_retries: int
    supported_schemas: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "adapter_id": self.adapter_id,
            "capability": self.capability,
            "runtime_class": self.runtime_class,
            "default_provider": self.default_provider,
            "enabled_by_default": self.enabled_by_default,
            "admitted_by_default": self.admitted_by_default,
            "live_provider_runtime": self.live_provider_runtime,
            "api_key_source": "environment_only"
            if self.api_key_env_var
            else "none",
            "api_key_env_var": self.api_key_env_var,
            "api_key_persisted": False,
            "api_key_logged": False,
            "timeout_seconds_default": self.timeout_seconds_default,
            "timeout_seconds_max": self.timeout_seconds_max,
            "max_budget_usd_default": self.max_budget_usd_default,
            "max_budget_usd_hard_limit": self.max_budget_usd_hard_limit,
            "max_schema_retries": self.max_schema_retries,
            "supported_schemas": list(self.supported_schemas),
            "real_provider_calls_allowed_by_default": False,
            "tool_calls_allowed": False,
            "file_edits_allowed": False,
            "schema_validation_required": True,
            "invalid_output_quarantine_required": True,
            "runtime_admission_required_for_live_provider": (
                self.live_provider_runtime
            ),
        }


@dataclass(frozen=True)
class ModelProviderAdmissionArtifacts:
    config_path: Path
    human_approval_path: Path
    manifest_path: Path
    config_sha256: str
    human_approval_sha256: str
    manifest_sha256: str


def build_model_provider_boundaries() -> tuple[ModelProviderBoundary, ...]:
    return tuple(
        _boundary_from_registry_entry(entry)
        for entry in build_model_provider_registry()
    )


def boundary_for_provider(provider_id: str) -> ModelProviderBoundary:
    return _boundary_from_registry_entry(find_model_provider(provider_id))


def validate_model_provider_boundary(
    boundary: ModelProviderBoundary,
) -> tuple[str, ...]:
    failures = []
    if not boundary.provider_id:
        failures.append("provider_id_missing")
    if not boundary.adapter_id:
        failures.append("adapter_id_missing")
    if not boundary.capability:
        failures.append("capability_missing")
    if boundary.runtime_class not in ("mock_model", "live_model_provider"):
        failures.append("runtime_class_invalid")
    if not boundary.supported_schemas:
        failures.append("supported_schemas_missing")
    if boundary.timeout_seconds_default <= 0:
        failures.append("timeout_default_invalid")
    if boundary.timeout_seconds_max < boundary.timeout_seconds_default:
        failures.append("timeout_max_invalid")
    if boundary.max_budget_usd_default < 0:
        failures.append("budget_default_invalid")
    if boundary.max_budget_usd_hard_limit < boundary.max_budget_usd_default:
        failures.append("budget_hard_limit_invalid")
    if boundary.max_schema_retries < 0:
        failures.append("schema_retries_invalid")
    if boundary.live_provider_runtime:
        if boundary.enabled_by_default:
            failures.append("live_provider_enabled_by_default")
        if boundary.admitted_by_default:
            failures.append("live_provider_admitted_by_default")
        if not boundary.api_key_env_var:
            failures.append("live_provider_api_key_env_var_missing")
    else:
        if boundary.api_key_env_var is not None:
            failures.append("mock_provider_must_not_require_api_key")
        if not boundary.enabled_by_default:
            failures.append("mock_provider_disabled")
        if not boundary.admitted_by_default:
            failures.append("mock_provider_not_admitted")
    return tuple(sorted(failures))


def write_model_provider_admission_artifacts(
    output_dir: Path,
    *,
    provider_id: str,
    schema_name: str,
    dry_run: bool = True,
    reviewer_id: str = "human-reviewer",
) -> ModelProviderAdmissionArtifacts:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    if schema_name not in ModelFixtureSchema.allowed():
        raise ValueError("schema_name is not supported")
    boundary = boundary_for_provider(provider_id)
    failures = validate_model_provider_boundary(boundary)
    if failures:
        raise ValueError("model provider boundary is invalid: " + ",".join(failures))
    if not reviewer_id.strip():
        raise ValueError("reviewer_id is required")
    config_path = output_path / "model_provider_runtime_config.json"
    manifest_path = output_path / "model_provider_runtime_manifest.json"
    approval_path = output_path / "model_provider_runtime_approval.json"
    _require_no_overwrite(config_path)
    _require_no_overwrite(manifest_path)
    _require_no_overwrite(approval_path)

    policy = runtime_policy_for_class(boundary.runtime_class).to_dict()
    config = {
        "config_type": _CONFIG_TYPE,
        "adapter_id": boundary.adapter_id,
        "capability": boundary.capability,
        "runtime_class": boundary.runtime_class,
        "provider_id": boundary.provider_id,
        "schema_name": schema_name,
        "dry_run": dry_run,
        "real_runtime_enabled": False,
        "runtime_class_policy": policy,
        "environment_only_api_key_lookup": boundary.api_key_env_var is not None,
        "api_key_env_var": boundary.api_key_env_var,
        "api_key_persisted": False,
        "api_key_logged": False,
        "network_allowed": False,
        "tool_calls_allowed": False,
        "file_edits_allowed": False,
        "timeout_seconds_max": boundary.timeout_seconds_max,
        "max_budget_usd_hard_limit": boundary.max_budget_usd_hard_limit,
        "schema_validation_required": True,
        "schema_retry_max": boundary.max_schema_retries,
        "required_human_approval": True,
    }
    write_json_atomically(config_path, config)
    config_sha256 = sha256_file(config_path)

    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "adapter_id": boundary.adapter_id,
        "capability": boundary.capability,
        "runtime_class": boundary.runtime_class,
        "provider_id": boundary.provider_id,
        "schema_name": schema_name,
        "dry_run": dry_run,
        "config_sha256": config_sha256,
        "manifest_hash_binding_required": True,
        "provider_result_manifest_required": True,
        "invalid_output_quarantine_required": True,
        "live_provider_runtime_called": False,
        "network_used": False,
        "api_key_persisted": False,
        "api_key_logged": False,
        "required_human_approval": True,
    }
    write_json_atomically(manifest_path, manifest)
    manifest_sha256 = sha256_file(manifest_path)

    approval = {
        "approval_type": _APPROVAL_TYPE,
        "adapter_id": boundary.adapter_id,
        "capability": boundary.capability,
        "runtime_class": boundary.runtime_class,
        "provider_id": boundary.provider_id,
        "schema_name": schema_name,
        "approved_action": _APPROVED_ACTION,
        "approved": True,
        "human_reviewed": True,
        "reviewer_id": reviewer_id.strip(),
        "config_sha256": config_sha256,
        "manifest_sha256": manifest_sha256,
        "required_human_approval": True,
    }
    write_json_atomically(approval_path, approval)
    return ModelProviderAdmissionArtifacts(
        config_path=config_path,
        human_approval_path=approval_path,
        manifest_path=manifest_path,
        config_sha256=config_sha256,
        human_approval_sha256=sha256_file(approval_path),
        manifest_sha256=manifest_sha256,
    )


def _boundary_from_registry_entry(
    entry: ModelProviderRegistryEntry,
) -> ModelProviderBoundary:
    if entry.provider_id == "deterministic_mock":
        return ModelProviderBoundary(
            provider_id=entry.provider_id,
            adapter_id="mock_model_typed_schema_runtime",
            capability="classify_local_job_package",
            runtime_class="mock_model",
            default_provider=True,
            enabled_by_default=entry.enabled_by_default,
            admitted_by_default=entry.admitted,
            live_provider_runtime=entry.live_provider_runtime,
            api_key_env_var=entry.api_key_env_var,
            timeout_seconds_default=entry.timeout_seconds_default,
            timeout_seconds_max=entry.timeout_seconds_max,
            max_budget_usd_default=entry.max_budget_usd_default,
            max_budget_usd_hard_limit=entry.max_budget_usd_hard_limit,
            max_schema_retries=entry.max_schema_retries,
            supported_schemas=entry.supported_schemas,
        )
    return ModelProviderBoundary(
        provider_id=entry.provider_id,
        adapter_id="live_model_provider_boundary",
        capability="call_typed_schema_provider",
        runtime_class="live_model_provider",
        default_provider=False,
        enabled_by_default=entry.enabled_by_default,
        admitted_by_default=entry.admitted,
        live_provider_runtime=entry.live_provider_runtime,
        api_key_env_var=entry.api_key_env_var,
        timeout_seconds_default=entry.timeout_seconds_default,
        timeout_seconds_max=entry.timeout_seconds_max,
        max_budget_usd_default=entry.max_budget_usd_default,
        max_budget_usd_hard_limit=entry.max_budget_usd_hard_limit,
        max_schema_retries=entry.max_schema_retries,
        supported_schemas=entry.supported_schemas,
    )


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("model provider admission artifact already exists")
