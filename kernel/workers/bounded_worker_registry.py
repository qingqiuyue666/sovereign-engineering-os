"""Bounded worker type declarations without live provider execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

__all__ = [
    "REQUIRED_WORKER_IDS",
    "BoundedWorkerDeclaration",
    "WorkerRoutingPlan",
    "build_default_bounded_worker_registry",
    "validate_bounded_worker_registry",
    "build_worker_routing_plan",
    "registry_as_payload",
]


REQUIRED_WORKER_IDS = (
    "codex",
    "claude",
    "gemini",
    "gpt",
    "deepseek",
    "local_deterministic_python",
)

_COMMON_TASK_CLASSES = (
    "code_review",
    "implementation_plan",
    "test_design",
    "documentation_draft",
)

_COMMON_INPUT_CONTRACT = (
    "task_descriptor_digest",
    "repository_revision",
    "allowed_context_refs",
    "expected_output_contract",
)

_COMMON_OUTPUT_CONTRACT = (
    "worker_result_digest",
    "evidence_refs",
    "uncertainty_notes",
    "forbidden_surface_attestation",
)

_COMMON_EVIDENCE_REQUIREMENTS = (
    "input_digest_bound",
    "repo_revision_bound",
    "output_digest_recorded",
    "human_review_required_before_action",
)

_COMMON_HALLUCINATION_BOUNDARY = (
    "must not claim unobserved files",
    "must label uncertainty",
    "must cite evidence refs for claims",
    "must not invent validation results",
)


@dataclass(frozen=True)
class BoundedWorkerDeclaration:
    worker_id: str
    display_name: str
    provider_family: str
    task_classes: tuple[str, ...]
    input_contract: tuple[str, ...]
    output_contract: tuple[str, ...]
    timeout_seconds: int
    budget_units: int
    evidence_requirements: tuple[str, ...]
    hallucination_boundary: tuple[str, ...]
    live_provider_calls_enabled: bool = False
    credential_storage_enabled: bool = False
    tool_execution_enabled: bool = False
    production_autonomy_enabled: bool = False
    default_route_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "display_name": self.display_name,
            "provider_family": self.provider_family,
            "task_classes": list(self.task_classes),
            "input_contract": list(self.input_contract),
            "output_contract": list(self.output_contract),
            "timeout_seconds": self.timeout_seconds,
            "budget_units": self.budget_units,
            "evidence_requirements": list(self.evidence_requirements),
            "hallucination_boundary": list(self.hallucination_boundary),
            "live_provider_calls_enabled": self.live_provider_calls_enabled,
            "credential_storage_enabled": self.credential_storage_enabled,
            "tool_execution_enabled": self.tool_execution_enabled,
            "production_autonomy_enabled": self.production_autonomy_enabled,
            "default_route_enabled": self.default_route_enabled,
        }


@dataclass(frozen=True)
class WorkerRoutingPlan:
    task_class: str
    candidate_worker_ids: tuple[str, ...]
    rejected_worker_ids: tuple[str, ...]
    provider_execution_disabled: bool
    tool_execution_disabled: bool
    production_autonomy_disabled: bool
    evidence_required_before_dispatch: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_type": "bounded_worker_routing_plan_v1",
            "task_class": self.task_class,
            "candidate_worker_ids": list(self.candidate_worker_ids),
            "rejected_worker_ids": list(self.rejected_worker_ids),
            "provider_execution_disabled": self.provider_execution_disabled,
            "tool_execution_disabled": self.tool_execution_disabled,
            "production_autonomy_disabled": self.production_autonomy_disabled,
            "evidence_required_before_dispatch": list(self.evidence_required_before_dispatch),
            "dispatch_performed": False,
            "provider_call_performed": False,
            "credential_access_performed": False,
            "tool_execution_performed": False,
        }


def build_default_bounded_worker_registry() -> tuple[BoundedWorkerDeclaration, ...]:
    """Return deterministic worker declarations only."""

    return (
        _provider_worker("codex", "Codex", "openai_codex"),
        _provider_worker("claude", "Claude", "anthropic_claude"),
        _provider_worker("gemini", "Gemini", "google_gemini"),
        _provider_worker("gpt", "GPT", "openai_gpt"),
        _provider_worker("deepseek", "DeepSeek", "deepseek"),
        BoundedWorkerDeclaration(
            worker_id="local_deterministic_python",
            display_name="Local Deterministic Python",
            provider_family="local_deterministic",
            task_classes=(
                "fixture_validation",
                "static_contract_check",
                "artifact_summary",
            ),
            input_contract=_COMMON_INPUT_CONTRACT,
            output_contract=_COMMON_OUTPUT_CONTRACT,
            timeout_seconds=30,
            budget_units=1,
            evidence_requirements=_COMMON_EVIDENCE_REQUIREMENTS,
            hallucination_boundary=_COMMON_HALLUCINATION_BOUNDARY,
        ),
    )


def validate_bounded_worker_registry(
    declarations: Sequence[BoundedWorkerDeclaration],
) -> tuple[str, ...]:
    failures: list[str] = []
    by_id: dict[str, BoundedWorkerDeclaration] = {}
    for declaration in declarations:
        if declaration.worker_id in by_id:
            failures.append(f"duplicate_worker_id:{declaration.worker_id}")
        by_id[declaration.worker_id] = declaration
        if declaration.live_provider_calls_enabled:
            failures.append(f"live_provider_enabled:{declaration.worker_id}")
        if declaration.credential_storage_enabled:
            failures.append(f"credential_storage_enabled:{declaration.worker_id}")
        if declaration.tool_execution_enabled:
            failures.append(f"tool_execution_enabled:{declaration.worker_id}")
        if declaration.production_autonomy_enabled:
            failures.append(f"production_autonomy_enabled:{declaration.worker_id}")
        if not declaration.task_classes:
            failures.append(f"task_classes_missing:{declaration.worker_id}")
        if not declaration.input_contract:
            failures.append(f"input_contract_missing:{declaration.worker_id}")
        if not declaration.output_contract:
            failures.append(f"output_contract_missing:{declaration.worker_id}")
        if declaration.timeout_seconds <= 0:
            failures.append(f"timeout_invalid:{declaration.worker_id}")
        if declaration.budget_units <= 0:
            failures.append(f"budget_invalid:{declaration.worker_id}")
        if not declaration.evidence_requirements:
            failures.append(f"evidence_requirements_missing:{declaration.worker_id}")
        if not declaration.hallucination_boundary:
            failures.append(f"hallucination_boundary_missing:{declaration.worker_id}")
    for worker_id in REQUIRED_WORKER_IDS:
        if worker_id not in by_id:
            failures.append(f"required_worker_missing:{worker_id}")
    return tuple(failures)


def build_worker_routing_plan(
    task_class: str,
    declarations: Sequence[BoundedWorkerDeclaration] | None = None,
) -> WorkerRoutingPlan:
    registry = tuple(declarations or build_default_bounded_worker_registry())
    failures = validate_bounded_worker_registry(registry)
    if failures:
        raise ValueError("bounded_worker_registry_invalid:" + ",".join(failures))
    candidates = tuple(
        declaration.worker_id
        for declaration in registry
        if task_class in declaration.task_classes
    )
    rejected = tuple(
        declaration.worker_id
        for declaration in registry
        if task_class not in declaration.task_classes
    )
    return WorkerRoutingPlan(
        task_class=task_class,
        candidate_worker_ids=candidates,
        rejected_worker_ids=rejected,
        provider_execution_disabled=True,
        tool_execution_disabled=True,
        production_autonomy_disabled=True,
        evidence_required_before_dispatch=_COMMON_EVIDENCE_REQUIREMENTS,
    )


def _provider_worker(
    worker_id: str,
    display_name: str,
    provider_family: str,
) -> BoundedWorkerDeclaration:
    return BoundedWorkerDeclaration(
        worker_id=worker_id,
        display_name=display_name,
        provider_family=provider_family,
        task_classes=_COMMON_TASK_CLASSES,
        input_contract=_COMMON_INPUT_CONTRACT,
        output_contract=_COMMON_OUTPUT_CONTRACT,
        timeout_seconds=120,
        budget_units=1,
        evidence_requirements=_COMMON_EVIDENCE_REQUIREMENTS,
        hallucination_boundary=_COMMON_HALLUCINATION_BOUNDARY,
    )


def registry_as_payload(
    declarations: Sequence[BoundedWorkerDeclaration] | None = None,
) -> dict[str, object]:
    registry = tuple(declarations or build_default_bounded_worker_registry())
    failures = validate_bounded_worker_registry(registry)
    return {
        "registry_type": "bounded_worker_registry_v1",
        "version": "v1",
        "valid": not failures,
        "validation_failures": list(failures),
        "workers": [declaration.as_dict() for declaration in registry],
        "live_provider_calls_enabled": False,
        "credential_storage_enabled": False,
        "tool_execution_enabled": False,
        "production_autonomy_enabled": False,
        "routing_plan_only": True,
    }
