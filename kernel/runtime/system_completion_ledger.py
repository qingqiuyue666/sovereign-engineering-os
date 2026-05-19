"""Deterministic non-Houdini system completion ledger."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import require_text_terms
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
    "SystemCompletionLedger",
    "build_system_completion_ledger",
    "render_system_completion_ledger_markdown",
]

_POLICY_VERSION = "system-completion-ledger-v1"
_CODE_VERSION = "0.1.0"
_COMPLETION_DECISIONS = ("complete", "in_progress", "blocked")
_REQUIRED_PREVIOUS_ESTIMATES = (
    "Engineering foundation: ~90%",
    "Private operator layer: ~85%",
    "Code Audit Workbench: ~75-80%",
    "Operator Daily Loop: ~45-55%",
    "Asset Registry operationalization: ~40-50%",
    "Business Delivery operationalization: ~25-35%",
    "Macro Research: ~35-45%",
    "Overall system landing excluding Houdini: ~70-78%",
)
_REQUIRED_TARGET_ESTIMATES = (
    "Engineering foundation: 100%",
    "Private operator layer: 100%",
    "Code Audit Workbench: 100%",
    "Operator Daily Loop: 100%",
    "Asset Registry operationalization: 100%",
    "Business Delivery operationalization: 100%",
    "Macro Research: 100%",
    "Overall non-Houdini system closure: 100%",
)
_STRING_FIELDS = (
    "ledger_id",
    "repository_url",
    "main_commit",
    "completion_decision",
    "policy_version",
    "code_version",
)
_DICT_FIELDS = ("achieved_status", "closure_gates")
_LIST_FIELDS = (
    "excluded_lines",
    "modules",
    "previous_estimates",
    "target_estimates",
    "open_gaps",
    "closed_gaps",
    "next_required_runs",
    "blocked_capabilities",
)
_ALLOW_EMPTY_LISTS = ("open_gaps",)


@dataclass(frozen=True)
class SystemCompletionLedger:
    """Repository-ready deterministic ledger for non-Houdini closure state."""

    ledger_id: str
    repository_url: str
    main_commit: str
    excluded_lines: tuple[object, ...]
    modules: tuple[object, ...]
    previous_estimates: tuple[object, ...]
    target_estimates: tuple[object, ...]
    achieved_status: dict[str, object]
    closure_gates: dict[str, object]
    open_gaps: tuple[object, ...]
    closed_gaps: tuple[object, ...]
    next_required_runs: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
    completion_decision: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "achieved_status": self.achieved_status,
            "blocked_capabilities": list(self.blocked_capabilities),
            "closed_gaps": list(self.closed_gaps),
            "closure_gates": self.closure_gates,
            "code_version": self.code_version,
            "completion_decision": self.completion_decision,
            "excluded_lines": list(self.excluded_lines),
            "ledger_id": self.ledger_id,
            "main_commit": self.main_commit,
            "modules": list(self.modules),
            "next_required_runs": list(self.next_required_runs),
            "open_gaps": list(self.open_gaps),
            "policy_version": self.policy_version,
            "previous_estimates": list(self.previous_estimates),
            "repository_url": self.repository_url,
            "target_estimates": list(self.target_estimates),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_system_completion_ledger(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> SystemCompletionLedger:
    """Build a deterministic completion ledger from caller-provided module evidence."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="system_completion_ledger_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    require_valid_choice(
        normalized["completion_decision"],
        field="completion_decision",
        allowed=_COMPLETION_DECISIONS,
    )
    require_text_terms(
        normalized["previous_estimates"],
        _REQUIRED_PREVIOUS_ESTIMATES,
        error="previous_estimates_missing_required_values",
    )
    require_text_terms(
        normalized["target_estimates"],
        _REQUIRED_TARGET_ESTIMATES,
        error="target_estimates_missing_required_values",
    )
    require_text_terms(
        normalized["excluded_lines"],
        ("houdini/vfx execution",),
        error="excluded_lines_missing_houdini_vfx_boundary",
    )
    if normalized["completion_decision"] == "complete" and not _all_modules_complete(normalized["modules"]):
        raise ValueError("incomplete_module_blocks_complete")

    ledger = SystemCompletionLedger(
        ledger_id=normalized["ledger_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        excluded_lines=tuple(normalized["excluded_lines"]),
        modules=tuple(normalized["modules"]),
        previous_estimates=tuple(normalized["previous_estimates"]),
        target_estimates=tuple(normalized["target_estimates"]),
        achieved_status=normalized["achieved_status"],
        closure_gates=normalized["closure_gates"],
        open_gaps=tuple(normalized["open_gaps"]),
        closed_gaps=tuple(normalized["closed_gaps"]),
        next_required_runs=tuple(normalized["next_required_runs"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        completion_decision=normalized["completion_decision"],
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(ledger, content_hash=compute_content_hash(ledger.deterministic_material()))


def render_system_completion_ledger_markdown(ledger: SystemCompletionLedger) -> str:
    """Render deterministic Markdown for the completion ledger."""

    if not isinstance(ledger, SystemCompletionLedger):
        raise ValueError("ledger_must_be_system_completion_ledger")
    material = ledger.deterministic_material()
    return render_markdown(
        "System Completion Ledger",
        metadata_rows=(
            ("ledger_id", ledger.ledger_id),
            ("repository_url", ledger.repository_url),
            ("main_commit", ledger.main_commit),
            ("completion_decision", ledger.completion_decision),
            ("policy_version", ledger.policy_version),
            ("code_version", ledger.code_version),
            ("content_hash", ledger.content_hash),
            ("observed_at", ledger.observed_at),
        ),
        sections=(
            ("Excluded Lines", material["excluded_lines"]),
            ("Modules", material["modules"]),
            ("Previous Estimates", material["previous_estimates"]),
            ("Target Estimates", material["target_estimates"]),
            ("Achieved Status", material["achieved_status"]),
            ("Closure Gates", material["closure_gates"]),
            ("Open Gaps", material["open_gaps"]),
            ("Closed Gaps", material["closed_gaps"]),
            ("Next Required Runs", material["next_required_runs"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Completion Decision", ledger.completion_decision),
        ),
    )


def _all_modules_complete(modules: object) -> bool:
    if not isinstance(modules, list) or not modules:
        return False
    for module in modules:
        if not isinstance(module, dict):
            return False
        if module.get("closure_state") != "complete":
            return False
    return True
