"""Contract helpers for the local mock typed-schema model adapter."""

from dataclasses import dataclass

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterCapabilityRequest,
    AdapterExecutionBoundary,
    AdapterMode,
    AdapterRiskClass,
)

__all__ = [
    "ModelFixtureSchema",
    "ModelRuntimePaths",
    "build_model_fixture_capability_request",
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


def build_model_fixture_capability_request() -> AdapterCapabilityRequest:
    return AdapterCapabilityRequest(
        adapter_id="mock_model_typed_schema_runtime",
        capability="classify_local_job_package",
        mode=AdapterMode.MOCK_RUNTIME,
        risk_class=AdapterRiskClass.MOCK_MODEL,
        requested_operations=("read_local_json_artifact", "write_model_artifact"),
        boundary=AdapterExecutionBoundary(),
    )
