"""Deterministic closure report for operator asset registries."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import (
    reject_text_markers,
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
    "OperatorAssetRegistryClosure",
    "build_operator_asset_registry_closure",
    "render_operator_asset_registry_closure_markdown",
]

_POLICY_VERSION = "operator-asset-registry-closure-v1"
_CODE_VERSION = "0.1.0"
_COMPLETION_DECISIONS = ("complete", "incomplete", "blocked", "needs_human_review")
_REQUIRED_CLOSURE_GATES = (
    "all_registry_docs_exist",
    "registry_contract_exists",
    "at_least_one_entry_per_registry",
    "blocked_capabilities_preserved",
    "no_houdini_execution_assets_unless_external_line_reference_only",
    "registry_update_policy_defined",
    "rollback_notes_defined",
)
_REGISTRY_TYPES = (
    "code_report_registry",
    "ai_worker_output_registry",
    "decision_log_registry",
    "rollback_registry",
    "evidence_registry",
    "production_asset_registry",
)
_STRING_FIELDS = (
    "closure_id",
    "repository_url",
    "main_commit",
    "completion_decision",
    "policy_version",
    "code_version",
)
_DICT_FIELDS = ("closure_gates", "registry_status")
_LIST_FIELDS = ("registry_docs", "blocked_capabilities", "remaining_gaps", "rollback_notes")
_ALLOW_EMPTY_LISTS = ("remaining_gaps",)


@dataclass(frozen=True)
class OperatorAssetRegistryClosure:
    """Repository-ready closure contract for operator registries."""

    closure_id: str
    repository_url: str
    main_commit: str
    closure_gates: dict[str, object]
    registry_status: dict[str, object]
    registry_docs: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
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
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "registry_docs": list(self.registry_docs),
            "registry_status": self.registry_status,
            "remaining_gaps": list(self.remaining_gaps),
            "repository_url": self.repository_url,
            "rollback_notes": list(self.rollback_notes),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_asset_registry_closure(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> OperatorAssetRegistryClosure:
    """Build a deterministic asset registry closure from caller-provided evidence."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="operator_asset_registry_closure_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
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
    _require_registry_status(normalized["registry_status"])
    require_text_terms(
        normalized["blocked_capabilities"],
        ("provider execution", "trading automation", "houdini/vfx"),
        error="blocked_capabilities_missing_required_language",
    )
    reject_text_markers(
        normalized["registry_docs"],
        ("houdini execution asset", "vfx execution asset"),
        error="registry_docs_include_houdini_vfx_execution_asset",
    )

    closure = OperatorAssetRegistryClosure(
        closure_id=normalized["closure_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        closure_gates=gates,
        registry_status=normalized["registry_status"],
        registry_docs=tuple(normalized["registry_docs"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        completion_decision=normalized["completion_decision"],
        remaining_gaps=tuple(normalized["remaining_gaps"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(closure, content_hash=compute_content_hash(closure.deterministic_material()))


def render_operator_asset_registry_closure_markdown(closure: OperatorAssetRegistryClosure) -> str:
    """Render deterministic Markdown for registry closure."""

    if not isinstance(closure, OperatorAssetRegistryClosure):
        raise ValueError("closure_must_be_operator_asset_registry_closure")
    material = closure.deterministic_material()
    return render_markdown(
        "Operator Asset Registry Closure",
        metadata_rows=(
            ("closure_id", closure.closure_id),
            ("repository_url", closure.repository_url),
            ("main_commit", closure.main_commit),
            ("completion_decision", closure.completion_decision),
            ("policy_version", closure.policy_version),
            ("code_version", closure.code_version),
            ("content_hash", closure.content_hash),
            ("observed_at", closure.observed_at),
        ),
        sections=(
            ("Closure Gates", material["closure_gates"]),
            ("Registry Status", material["registry_status"]),
            ("Registry Docs", material["registry_docs"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Completion Decision", closure.completion_decision),
            ("Remaining Gaps", material["remaining_gaps"]),
            ("Rollback Notes", material["rollback_notes"]),
        ),
    )


def _require_registry_status(status: object) -> None:
    if not isinstance(status, dict):
        raise ValueError("registry_status_must_be_dict")
    for registry_type in _REGISTRY_TYPES:
        if registry_type not in status:
            raise ValueError(f"registry_status_missing:{registry_type}")
        if status[registry_type] is not True:
            raise ValueError(f"registry_status_incomplete:{registry_type}")
