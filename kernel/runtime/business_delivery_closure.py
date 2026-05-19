"""Deterministic private business delivery closure report."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import (
    reject_text_markers,
    require_bool,
    require_bool_gate_map,
    require_complete_has_required_gates,
    require_text_terms,
)
from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_dict_fields,
    require_list_fields,
    require_string_fields,
    require_valid_choice,
)

__all__ = [
    "BusinessDeliveryClosure",
    "build_business_delivery_closure",
    "render_business_delivery_closure_markdown",
]

_POLICY_VERSION = "business-delivery-closure-v1"
_CODE_VERSION = "0.1.0"
_COMPLETION_DECISIONS = ("complete", "incomplete", "blocked", "needs_human_review")
_REQUIRED_CLOSURE_GATES = (
    "delivery_package_exists",
    "service_scope_exists",
    "client_intake_exists",
    "quote_scope_template_exists",
    "delivery_checklist_exists",
    "case_study_template_exists",
    "do_not_offer_list_exists",
    "no_trading_service_offered",
    "no_provider_execution_claim",
    "no_production_autonomy_claim",
    "no_houdini_vfx_delivery_claim_in_this_slice",
    "human_review_required",
)
_UNSAFE_CLAIM_MARKERS = (
    "we offer trading service",
    "trading service included",
    "provider execution included",
    "production autonomy included",
    "autonomous production included",
    "houdini/vfx delivery included",
    "vfx delivery included",
)
_STRING_FIELDS = (
    "closure_id",
    "repository_url",
    "main_commit",
    "completion_decision",
    "policy_version",
    "code_version",
)
_DICT_FIELDS = ("closure_gates",)
_LIST_FIELDS = ("delivery_docs", "blocked_capabilities", "remaining_gaps", "rollback_notes")
_ALLOW_EMPTY_LISTS = ("remaining_gaps",)


@dataclass(frozen=True)
class BusinessDeliveryClosure:
    """Repository-ready safe private delivery closure."""

    closure_id: str
    repository_url: str
    main_commit: str
    closure_gates: dict[str, object]
    delivery_docs: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
    human_review_required: bool
    completion_decision: str
    remaining_gaps: tuple[object, ...]
    rollback_notes: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_capabilities": list(self.blocked_capabilities),
            "closure_gates": self.closure_gates,
            "closure_id": self.closure_id,
            "code_version": self.code_version,
            "completion_decision": self.completion_decision,
            "delivery_docs": list(self.delivery_docs),
            "human_review_required": self.human_review_required,
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "remaining_gaps": list(self.remaining_gaps),
            "repository_url": self.repository_url,
            "rollback_notes": list(self.rollback_notes),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_business_delivery_closure(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> BusinessDeliveryClosure:
    """Build a deterministic business delivery closure from caller-provided evidence."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="business_delivery_closure_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    if "human_review_required" not in normalized:
        raise ValueError("human_review_required_missing")
    require_bool(normalized["human_review_required"], field="human_review_required")
    require_valid_choice(
        normalized["completion_decision"],
        field="completion_decision",
        allowed=_COMPLETION_DECISIONS,
    )
    gates = require_bool_gate_map(
        normalized["closure_gates"],
        field="closure_gates",
        required_gates=_REQUIRED_CLOSURE_GATES,
    )
    require_complete_has_required_gates(
        normalized["completion_decision"],
        gates=gates,
        required_gates=_REQUIRED_CLOSURE_GATES,
    )
    if normalized["completion_decision"] == "complete" and normalized["human_review_required"] is not True:
        raise ValueError("human_review_required_blocks_complete")
    require_text_terms(
        normalized["delivery_docs"],
        ("delivery package", "service scope", "client intake", "do-not-offer"),
        error="delivery_docs_missing_required_surface",
    )
    reject_text_markers(normalized["delivery_docs"], _UNSAFE_CLAIM_MARKERS, error="unsafe_delivery_claim_blocks_complete")

    closure = BusinessDeliveryClosure(
        closure_id=normalized["closure_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        closure_gates=gates,
        delivery_docs=tuple(normalized["delivery_docs"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        human_review_required=normalized["human_review_required"],
        completion_decision=normalized["completion_decision"],
        remaining_gaps=tuple(normalized["remaining_gaps"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(closure, content_hash=compute_content_hash(closure.deterministic_material()))


def render_business_delivery_closure_markdown(closure: BusinessDeliveryClosure) -> str:
    """Render deterministic Markdown for business delivery closure."""

    if not isinstance(closure, BusinessDeliveryClosure):
        raise ValueError("closure_must_be_business_delivery_closure")
    material = closure.deterministic_material()
    return render_markdown(
        "Business Delivery Closure",
        metadata_rows=(
            ("closure_id", closure.closure_id),
            ("repository_url", closure.repository_url),
            ("main_commit", closure.main_commit),
            ("human_review_required", closure.human_review_required),
            ("completion_decision", closure.completion_decision),
            ("policy_version", closure.policy_version),
            ("code_version", closure.code_version),
            ("content_hash", closure.content_hash),
            ("observed_at", closure.observed_at),
        ),
        sections=(
            ("Closure Gates", material["closure_gates"]),
            ("Delivery Docs", material["delivery_docs"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Completion Decision", closure.completion_decision),
            ("Remaining Gaps", material["remaining_gaps"]),
            ("Rollback Notes", material["rollback_notes"]),
        ),
    )
