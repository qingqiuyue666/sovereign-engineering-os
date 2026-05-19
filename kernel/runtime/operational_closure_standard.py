"""Deterministic standard for non-Houdini operational closure claims."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import (
    require_bool_gate_map,
    require_complete_has_required_gates,
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
    "OperationalClosureStandard",
    "build_operational_closure_standard",
    "render_operational_closure_standard_markdown",
]

_POLICY_VERSION = "operational-closure-standard-v1"
_CODE_VERSION = "0.1.0"
_CLOSURE_STATUSES = ("not_started", "in_progress", "blocked", "closure_path_defined", "complete")
_REQUIRED_CLOSURE_GATES = (
    "engineering_foundation_closure_complete",
    "private_operator_layer_closure_complete",
    "code_audit_workbench_closure_complete",
    "operator_daily_loop_closure_complete",
    "asset_registry_closure_complete",
    "business_delivery_closure_complete",
    "macro_research_closure_complete",
    "read_only_dashboard_closure_complete",
    "system_completion_ledger_generated",
    "full_tests_green",
    "make_ci_green",
    "git_diff_check_clean",
    "git_status_clean",
    "protected_files_preserved",
    "blocked_capabilities_preserved",
    "no_fake_green_claims",
    "no_provider_execution",
    "no_production_autonomy",
    "no_financial_execution",
    "no_trading_automation",
    "no_houdini_vfx_execution_in_this_slice",
)
_STRING_FIELDS = (
    "standard_id",
    "repository_url",
    "main_commit",
    "closure_status",
    "run_001_status",
    "policy_version",
    "code_version",
)
_DICT_FIELDS = ("closure_gates",)
_LIST_FIELDS = ("follow_up_packets", "blocked_capabilities", "remaining_gaps", "rollback_notes")
_ALLOW_EMPTY_LISTS = ("remaining_gaps",)


@dataclass(frozen=True)
class OperationalClosureStandard:
    """Repository-ready standard for claiming operational closure."""

    standard_id: str
    repository_url: str
    main_commit: str
    closure_status: str
    closure_gates: dict[str, object]
    run_001_status: str
    follow_up_packets: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
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
            "closure_status": self.closure_status,
            "code_version": self.code_version,
            "follow_up_packets": list(self.follow_up_packets),
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "remaining_gaps": list(self.remaining_gaps),
            "repository_url": self.repository_url,
            "rollback_notes": list(self.rollback_notes),
            "run_001_status": self.run_001_status,
            "standard_id": self.standard_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operational_closure_standard(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> OperationalClosureStandard:
    """Build a deterministic closure standard from caller-provided evidence."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="operational_closure_standard_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    require_valid_choice(normalized["closure_status"], field="closure_status", allowed=_CLOSURE_STATUSES)
    gates = require_bool_gate_map(
        normalized["closure_gates"],
        field="closure_gates",
        required_gates=_REQUIRED_CLOSURE_GATES,
    )
    require_complete_has_required_gates(
        normalized["closure_status"],
        gates=gates,
        required_gates=_REQUIRED_CLOSURE_GATES,
    )
    if normalized["closure_status"] == "closure_path_defined":
        if normalized["run_001_status"] != "complete":
            raise ValueError("run_001_complete_required_for_closure_path_defined")
        if not normalized["follow_up_packets"]:
            raise ValueError("follow_up_packets_required_for_closure_path_defined")

    standard = OperationalClosureStandard(
        standard_id=normalized["standard_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        closure_status=normalized["closure_status"],
        closure_gates=gates,
        run_001_status=normalized["run_001_status"],
        follow_up_packets=tuple(normalized["follow_up_packets"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        remaining_gaps=tuple(normalized["remaining_gaps"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(standard, content_hash=compute_content_hash(standard.deterministic_material()))


def render_operational_closure_standard_markdown(standard: OperationalClosureStandard) -> str:
    """Render deterministic Markdown for the operational closure standard."""

    if not isinstance(standard, OperationalClosureStandard):
        raise ValueError("standard_must_be_operational_closure_standard")
    material = standard.deterministic_material()
    return render_markdown(
        "Operational Closure Standard",
        metadata_rows=(
            ("standard_id", standard.standard_id),
            ("repository_url", standard.repository_url),
            ("main_commit", standard.main_commit),
            ("closure_status", standard.closure_status),
            ("run_001_status", standard.run_001_status),
            ("policy_version", standard.policy_version),
            ("code_version", standard.code_version),
            ("content_hash", standard.content_hash),
            ("observed_at", standard.observed_at),
        ),
        sections=(
            ("Closure Gates", material["closure_gates"]),
            ("Follow-Up Packets", material["follow_up_packets"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Remaining Gaps", material["remaining_gaps"]),
            ("Rollback Notes", material["rollback_notes"]),
        ),
    )
