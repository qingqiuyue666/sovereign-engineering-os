"""Contract helpers for the local mock typed-schema model adapter."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterCapabilityRequest,
    AdapterExecutionBoundary,
    AdapterMode,
    AdapterRiskClass,
)

__all__ = [
    "ModelFixtureSchema",
    "ModelProviderRegistryEntry",
    "ModelRuntimePaths",
    "build_model_fixture_capability_request",
    "build_model_provider_registry",
    "find_model_provider",
]


class ModelFixtureSchema:
    JOB_ROUTE_CLASSIFICATION = "job_route_classification_v1"
    ARTIFACT_PROFILE_SUMMARY = "artifact_profile_summary_v1"
    NEXT_STEP_RECOMMENDATION = "next_step_recommendation_v1"

    @classmethod
    def allowed(cls) -> tuple[str, ...]:
        return (
            cls.JOB_ROUTE_CLASSIFICATION,
            cls.ARTIFACT_PROFILE_SUMMARY,
            cls.NEXT_STEP_RECOMMENDATION,
        )


@dataclass(frozen=True)
class ModelRuntimePaths:
    inference_artifact_file: str = "model_inference_artifact.json"
    failure_bundle_file: str = "model_failure_bundle.json"


@dataclass(frozen=True)
class ModelProviderRegistryEntry:
    provider_id: str
    provider_name: str
    provider_kind: str
    admitted: bool
    enabled_by_default: bool
    live_provider_runtime: bool
    api_key_env_var: str | None
    timeout_seconds_default: int
    timeout_seconds_max: int
    max_budget_usd_default: float
    max_budget_usd_hard_limit: float
    max_schema_retries: int
    supported_schemas: tuple[str, ...]
    policy: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_kind": self.provider_kind,
            "admitted": self.admitted,
            "enabled_by_default": self.enabled_by_default,
            "live_provider_runtime": self.live_provider_runtime,
            "api_key_env_var": self.api_key_env_var,
            "timeout_seconds_default": self.timeout_seconds_default,
            "timeout_seconds_max": self.timeout_seconds_max,
            "max_budget_usd_default": self.max_budget_usd_default,
            "max_budget_usd_hard_limit": self.max_budget_usd_hard_limit,
            "max_schema_retries": self.max_schema_retries,
            "supported_schemas": list(self.supported_schemas),
            "policy": {
                key: self.policy[key]
                for key in sorted(self.policy)
            },
        }


def build_model_provider_registry() -> tuple[ModelProviderRegistryEntry, ...]:
    supported_schemas = ModelFixtureSchema.allowed()
    disabled_live_policy = MappingProxyType(
        {
            "api_key_source": "environment_only",
            "api_key_persistence_allowed": False,
            "api_key_logging_allowed": False,
            "network_allowed_by_default": False,
            "tool_calls_allowed": False,
            "file_edits_allowed": False,
            "real_provider_calls_allowed": False,
            "requires_future_policy_gate": True,
            "requires_budget_gate": True,
            "requires_timeout": True,
            "requires_schema_validation": True,
            "invalid_output_quarantine_required": True,
        }
    )
    return (
        ModelProviderRegistryEntry(
            provider_id="deterministic_mock",
            provider_name="Deterministic Mock Provider",
            provider_kind="mock",
            admitted=True,
            enabled_by_default=True,
            live_provider_runtime=False,
            api_key_env_var=None,
            timeout_seconds_default=1,
            timeout_seconds_max=5,
            max_budget_usd_default=0.0,
            max_budget_usd_hard_limit=0.0,
            max_schema_retries=2,
            supported_schemas=supported_schemas,
            policy=MappingProxyType(
                {
                    "api_key_source": "none",
                    "api_key_persistence_allowed": False,
                    "api_key_logging_allowed": False,
                    "network_allowed_by_default": False,
                    "tool_calls_allowed": False,
                    "file_edits_allowed": False,
                    "real_provider_calls_allowed": False,
                    "requires_budget_gate": True,
                    "requires_timeout": True,
                    "requires_schema_validation": True,
                    "invalid_output_quarantine_required": True,
                }
            ),
        ),
        ModelProviderRegistryEntry(
            provider_id="openai",
            provider_name="OpenAI Live Provider Boundary",
            provider_kind="live",
            admitted=False,
            enabled_by_default=False,
            live_provider_runtime=True,
            api_key_env_var="OPENAI_API_KEY",
            timeout_seconds_default=30,
            timeout_seconds_max=60,
            max_budget_usd_default=0.0,
            max_budget_usd_hard_limit=0.0,
            max_schema_retries=1,
            supported_schemas=supported_schemas,
            policy=disabled_live_policy,
        ),
    )


def find_model_provider(provider_id: str) -> ModelProviderRegistryEntry:
    for entry in build_model_provider_registry():
        if entry.provider_id == provider_id:
            return entry
    raise ValueError("model provider is not registered")


def build_model_fixture_capability_request() -> AdapterCapabilityRequest:
    return AdapterCapabilityRequest(
        adapter_id="mock_model_typed_schema_runtime",
        capability="classify_local_job_package",
        mode=AdapterMode.MOCK_RUNTIME,
        risk_class=AdapterRiskClass.MOCK_MODEL,
        requested_operations=("read_local_json_artifact", "write_model_artifact"),
        boundary=AdapterExecutionBoundary(),
    )
