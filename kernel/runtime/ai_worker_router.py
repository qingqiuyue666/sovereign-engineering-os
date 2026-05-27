"""Deterministic non-executing AI worker router."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_nonempty_string

__all__ = [
    "AIWorkerDeclaration",
    "AIWorkerRoutePlan",
    "DEFAULT_AI_WORKER_DECLARATIONS",
    "render_ai_worker_route_plan_json",
    "route_ai_worker_task",
]

_POLICY_VERSION = "ai-worker-router-v1"
_CODE_VERSION = "0.1.0"
_FORBIDDEN_FIELD_MARKERS = (
    "raw_prompt",
    "raw_response",
    "raw_provider_response",
    "raw_exception",
    "raw_traceback",
    "env",
    "secret",
    "credential",
    "token",
    "api_key",
    "password",
    "private_key",
    "authorization",
)
_VALID_RISK_LEVELS = frozenset({"low", "medium", "high"})


@dataclass(frozen=True)
class AIWorkerDeclaration:
    worker_id: str
    display_name: str
    provider_family: str
    task_classes: tuple[str, ...]
    capabilities: tuple[str, ...]
    timeout_seconds: int
    budget_policy_ref: str
    evidence_requirements: tuple[str, ...]
    hallucination_boundary: str
    human_review_required: bool
    live_provider_call_allowed: bool = False
    credential_access_allowed: bool = False
    tool_execution_allowed: bool = False
    production_autonomy_allowed: bool = False

    def as_dict(self) -> dict[str, object]:
        return dict(sorted(asdict(self).items()))


@dataclass(frozen=True)
class AIWorkerRoutePlan:
    route_id: str
    task_id: str
    task_class: str
    risk_level: str
    selected_worker_id: str
    candidate_worker_ids: tuple[str, ...]
    rejected_worker_reasons: dict[str, tuple[str, ...]]
    required_capabilities: tuple[str, ...]
    route_status: str
    human_review_required: bool
    handoff_packet_required: bool
    provider_execution_permitted: bool
    worker_dispatch_performed: bool
    credential_accessed: bool
    tool_execution_performed: bool
    network_accessed: bool
    production_autonomy_enabled: bool
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "candidate_worker_ids": list(self.candidate_worker_ids),
            "code_version": self.code_version,
            "credential_accessed": self.credential_accessed,
            "handoff_packet_required": self.handoff_packet_required,
            "human_review_required": self.human_review_required,
            "network_accessed": self.network_accessed,
            "policy_version": self.policy_version,
            "production_autonomy_enabled": self.production_autonomy_enabled,
            "provider_execution_permitted": self.provider_execution_permitted,
            "rejected_worker_reasons": {
                worker_id: list(reasons)
                for worker_id, reasons in sorted(self.rejected_worker_reasons.items())
            },
            "required_capabilities": list(self.required_capabilities),
            "risk_level": self.risk_level,
            "route_id": self.route_id,
            "route_status": self.route_status,
            "selected_worker_id": self.selected_worker_id,
            "task_class": self.task_class,
            "task_id": self.task_id,
            "tool_execution_performed": self.tool_execution_performed,
            "worker_dispatch_performed": self.worker_dispatch_performed,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        return payload


DEFAULT_AI_WORKER_DECLARATIONS: tuple[AIWorkerDeclaration, ...] = (
    AIWorkerDeclaration(
        worker_id="local_python",
        display_name="Local Deterministic Python",
        provider_family="local",
        task_classes=("deterministic_validation", "repo_static_analysis", "fixture_review"),
        capabilities=("local_validation", "static_analysis", "fixture_review"),
        timeout_seconds=120,
        budget_policy_ref="budget-policy:local-zero-provider-spend",
        evidence_requirements=("test_command", "diff_check", "route_plan_hash"),
        hallucination_boundary="deterministic_local_evidence_only",
        human_review_required=False,
    ),
    AIWorkerDeclaration(
        worker_id="codex",
        display_name="Codex",
        provider_family="openai",
        task_classes=("code_change", "test_authoring", "repo_static_analysis", "implementation_review"),
        capabilities=("code_editing", "test_authoring", "static_analysis"),
        timeout_seconds=1800,
        budget_policy_ref="budget-policy:manual-ai-worker-review",
        evidence_requirements=("branch_diff", "focused_tests", "final_report"),
        hallucination_boundary="claims_must_be_backed_by_local_diff_and_tests",
        human_review_required=True,
    ),
    AIWorkerDeclaration(
        worker_id="claude",
        display_name="Claude",
        provider_family="anthropic",
        task_classes=("code_review", "longform_analysis", "implementation_review"),
        capabilities=("code_review", "analysis", "risk_review"),
        timeout_seconds=1200,
        budget_policy_ref="budget-policy:manual-ai-worker-review",
        evidence_requirements=("review_findings", "file_line_refs", "final_report"),
        hallucination_boundary="review_claims_require_file_line_evidence",
        human_review_required=True,
    ),
    AIWorkerDeclaration(
        worker_id="gemini",
        display_name="Gemini",
        provider_family="google",
        task_classes=("research_summary", "multimodal_review", "planning"),
        capabilities=("research_summary", "planning", "multimodal_review"),
        timeout_seconds=1200,
        budget_policy_ref="budget-policy:manual-ai-worker-review",
        evidence_requirements=("source_refs", "summary_packet", "final_report"),
        hallucination_boundary="research_claims_require_source_refs",
        human_review_required=True,
    ),
    AIWorkerDeclaration(
        worker_id="gpt",
        display_name="GPT",
        provider_family="openai",
        task_classes=("planning", "summarization", "code_review"),
        capabilities=("planning", "summarization", "code_review"),
        timeout_seconds=1200,
        budget_policy_ref="budget-policy:manual-ai-worker-review",
        evidence_requirements=("plan_packet", "source_refs", "final_report"),
        hallucination_boundary="planning_claims_are_non_authoritative_until_reviewed",
        human_review_required=True,
    ),
    AIWorkerDeclaration(
        worker_id="deepseek",
        display_name="DeepSeek",
        provider_family="deepseek",
        task_classes=("code_reasoning", "patch_review", "implementation_review"),
        capabilities=("code_reasoning", "patch_review", "analysis"),
        timeout_seconds=1200,
        budget_policy_ref="budget-policy:manual-ai-worker-review",
        evidence_requirements=("reasoning_summary", "file_line_refs", "final_report"),
        hallucination_boundary="reasoning_output_requires_local_verification",
        human_review_required=True,
    ),
)


def route_ai_worker_task(
    material: Mapping[str, object],
    *,
    declarations: tuple[AIWorkerDeclaration, ...] = DEFAULT_AI_WORKER_DECLARATIONS,
) -> AIWorkerRoutePlan:
    """Build a deterministic route plan without dispatching any worker."""

    if not isinstance(material, Mapping):
        raise ValueError("route_material_must_be_mapping")
    if not isinstance(declarations, tuple) or not declarations:
        raise ValueError("declarations_must_be_nonempty_tuple")
    _reject_forbidden_fields(material)
    route_id = _required_string(material, "route_id")
    task_id = _required_string(material, "task_id")
    task_class = _required_string(material, "task_class")
    risk_level = str(material.get("risk_level", "medium")).strip().lower()
    if risk_level not in _VALID_RISK_LEVELS:
        raise ValueError("risk_level_must_be_low_medium_or_high")
    required_capabilities = _string_tuple(material.get("required_capabilities", ()))
    requested_worker_id = _optional_string(material.get("requested_worker_id"))
    blocked_worker_ids = frozenset(_string_tuple(material.get("blocked_worker_ids", ())))

    seen_worker_ids: set[str] = set()
    candidates: list[AIWorkerDeclaration] = []
    rejected: dict[str, tuple[str, ...]] = {}
    for declaration in declarations:
        _validate_declaration(declaration)
        if declaration.worker_id in seen_worker_ids:
            raise ValueError("duplicate_worker_declaration")
        seen_worker_ids.add(declaration.worker_id)
        reasons = _rejection_reasons(
            declaration,
            task_class=task_class,
            required_capabilities=required_capabilities,
            requested_worker_id=requested_worker_id,
            blocked_worker_ids=blocked_worker_ids,
        )
        if reasons:
            rejected[declaration.worker_id] = reasons
        else:
            candidates.append(declaration)

    candidates = sorted(candidates, key=_candidate_sort_key)
    selected = candidates[0].worker_id if candidates else ""
    human_review_required = risk_level == "high" or any(
        candidate.human_review_required for candidate in candidates[:1]
    )
    plan = AIWorkerRoutePlan(
        route_id=route_id,
        task_id=task_id,
        task_class=task_class,
        risk_level=risk_level,
        selected_worker_id=selected,
        candidate_worker_ids=tuple(candidate.worker_id for candidate in candidates),
        rejected_worker_reasons=rejected,
        required_capabilities=required_capabilities,
        route_status="ready_for_handoff" if selected else "blocked_no_candidate",
        human_review_required=human_review_required,
        handoff_packet_required=True,
        provider_execution_permitted=False,
        worker_dispatch_performed=False,
        credential_accessed=False,
        tool_execution_performed=False,
        network_accessed=False,
        production_autonomy_enabled=False,
        content_hash="",
    )
    return _with_hash(plan)


def render_ai_worker_route_plan_json(plan: AIWorkerRoutePlan) -> str:
    if not isinstance(plan, AIWorkerRoutePlan):
        raise ValueError("plan_must_be_ai_worker_route_plan")
    return json.dumps(plan.as_dict(), indent=2, sort_keys=True) + "\n"


def _with_hash(plan: AIWorkerRoutePlan) -> AIWorkerRoutePlan:
    return AIWorkerRoutePlan(
        route_id=plan.route_id,
        task_id=plan.task_id,
        task_class=plan.task_class,
        risk_level=plan.risk_level,
        selected_worker_id=plan.selected_worker_id,
        candidate_worker_ids=plan.candidate_worker_ids,
        rejected_worker_reasons=plan.rejected_worker_reasons,
        required_capabilities=plan.required_capabilities,
        route_status=plan.route_status,
        human_review_required=plan.human_review_required,
        handoff_packet_required=plan.handoff_packet_required,
        provider_execution_permitted=plan.provider_execution_permitted,
        worker_dispatch_performed=plan.worker_dispatch_performed,
        credential_accessed=plan.credential_accessed,
        tool_execution_performed=plan.tool_execution_performed,
        network_accessed=plan.network_accessed,
        production_autonomy_enabled=plan.production_autonomy_enabled,
        policy_version=plan.policy_version,
        code_version=plan.code_version,
        content_hash=digest_payload(plan.deterministic_material()),
    )


def _rejection_reasons(
    declaration: AIWorkerDeclaration,
    *,
    task_class: str,
    required_capabilities: tuple[str, ...],
    requested_worker_id: str | None,
    blocked_worker_ids: frozenset[str],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if requested_worker_id and declaration.worker_id != requested_worker_id:
        reasons.append("not_requested_worker")
    if declaration.worker_id in blocked_worker_ids:
        reasons.append("worker_explicitly_blocked")
    if task_class not in declaration.task_classes:
        reasons.append("task_class_not_supported")
    missing_capabilities = sorted(set(required_capabilities).difference(declaration.capabilities))
    if missing_capabilities:
        reasons.append("required_capability_missing:" + ",".join(missing_capabilities))
    if declaration.live_provider_call_allowed:
        reasons.append("live_provider_call_not_allowed")
    if declaration.credential_access_allowed:
        reasons.append("credential_access_not_allowed")
    if declaration.tool_execution_allowed:
        reasons.append("tool_execution_not_allowed")
    if declaration.production_autonomy_allowed:
        reasons.append("production_autonomy_not_allowed")
    return tuple(reasons)


def _candidate_sort_key(declaration: AIWorkerDeclaration) -> tuple[int, str]:
    local_priority = 0 if declaration.provider_family == "local" else 1
    return (local_priority, declaration.worker_id)


def _validate_declaration(declaration: AIWorkerDeclaration) -> None:
    for field_name in ("worker_id", "display_name", "provider_family", "budget_policy_ref", "hallucination_boundary"):
        if not strict_nonempty_string(getattr(declaration, field_name)):
            raise ValueError(f"{field_name}_must_be_nonempty_string")
    for field_name in ("task_classes", "capabilities", "evidence_requirements"):
        value = getattr(declaration, field_name)
        if not isinstance(value, tuple) or not value:
            raise ValueError(f"{field_name}_must_be_nonempty_tuple")
        if not all(strict_nonempty_string(item) for item in value):
            raise ValueError(f"{field_name}_items_must_be_nonempty_strings")
    if declaration.timeout_seconds <= 0:
        raise ValueError("timeout_seconds_must_be_positive")


def _required_string(material: Mapping[str, object], field: str) -> str:
    value = material.get(field)
    if not strict_nonempty_string(value):
        raise ValueError(f"{field}_must_be_nonempty_string")
    return str(value)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not strict_nonempty_string(value):
        raise ValueError("optional_string_must_be_nonempty_when_present")
    return str(value)


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("string_sequence_must_be_list_or_tuple")
    result = tuple(str(item) for item in value if strict_nonempty_string(item))
    if len(result) != len(value):
        raise ValueError("string_sequence_items_must_be_nonempty_strings")
    return tuple(sorted(result))


def _reject_forbidden_fields(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in _FORBIDDEN_FIELD_MARKERS):
                raise ValueError("forbidden_field_present")
            _reject_forbidden_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_fields(nested)
    elif isinstance(value, tuple):
        for nested in value:
            _reject_forbidden_fields(nested)
