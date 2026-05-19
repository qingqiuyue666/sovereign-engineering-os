"""Deterministic read-only local operator dashboard contract."""

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
)

__all__ = [
    "OperatorReadonlyDashboard",
    "build_operator_readonly_dashboard",
    "render_operator_readonly_dashboard_markdown",
]

_POLICY_VERSION = "operator-readonly-dashboard-v1"
_CODE_VERSION = "0.1.0"
_STRING_FIELDS = (
    "dashboard_id",
    "repository_url",
    "main_commit",
    "branch",
    "working_tree_status",
    "policy_version",
    "code_version",
)
_DICT_FIELDS = ("registries",)
_LIST_FIELDS = (
    "latest_reports",
    "active_workbenches",
    "blocked_capabilities",
    "verification_commands",
    "next_actions",
    "stop_conditions",
)


@dataclass(frozen=True)
class OperatorReadonlyDashboard:
    """Repository-ready read-only dashboard material."""

    dashboard_id: str
    repository_url: str
    main_commit: str
    branch: str
    working_tree_status: str
    latest_reports: tuple[object, ...]
    registries: dict[str, object]
    active_workbenches: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
    verification_commands: tuple[object, ...]
    next_actions: tuple[object, ...]
    stop_conditions: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "active_workbenches": list(self.active_workbenches),
            "blocked_capabilities": list(self.blocked_capabilities),
            "branch": self.branch,
            "code_version": self.code_version,
            "dashboard_id": self.dashboard_id,
            "latest_reports": list(self.latest_reports),
            "main_commit": self.main_commit,
            "next_actions": list(self.next_actions),
            "policy_version": self.policy_version,
            "registries": self.registries,
            "repository_url": self.repository_url,
            "stop_conditions": list(self.stop_conditions),
            "verification_commands": list(self.verification_commands),
            "working_tree_status": self.working_tree_status,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_readonly_dashboard(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> OperatorReadonlyDashboard:
    """Build deterministic dashboard material without running commands."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="operator_readonly_dashboard_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    require_text_terms(
        normalized["blocked_capabilities"],
        ("provider execution", "production autonomy", "trading automation", "houdini/vfx"),
        error="blocked_capabilities_missing_required_language",
    )

    dashboard = OperatorReadonlyDashboard(
        dashboard_id=normalized["dashboard_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        branch=normalized["branch"],
        working_tree_status=normalized["working_tree_status"],
        latest_reports=tuple(normalized["latest_reports"]),
        registries=normalized["registries"],
        active_workbenches=tuple(normalized["active_workbenches"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        verification_commands=tuple(normalized["verification_commands"]),
        next_actions=tuple(normalized["next_actions"]),
        stop_conditions=tuple(normalized["stop_conditions"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(dashboard, content_hash=compute_content_hash(dashboard.deterministic_material()))


def render_operator_readonly_dashboard_markdown(dashboard: OperatorReadonlyDashboard) -> str:
    """Render deterministic Markdown for a read-only dashboard."""

    if not isinstance(dashboard, OperatorReadonlyDashboard):
        raise ValueError("dashboard_must_be_operator_readonly_dashboard")
    material = dashboard.deterministic_material()
    return render_markdown(
        "Operator Read-Only Dashboard",
        metadata_rows=(
            ("dashboard_id", dashboard.dashboard_id),
            ("repository_url", dashboard.repository_url),
            ("main_commit", dashboard.main_commit),
            ("branch", dashboard.branch),
            ("working_tree_status", dashboard.working_tree_status),
            ("policy_version", dashboard.policy_version),
            ("code_version", dashboard.code_version),
            ("content_hash", dashboard.content_hash),
            ("observed_at", dashboard.observed_at),
        ),
        sections=(
            ("Latest Reports", material["latest_reports"]),
            ("Registries", material["registries"]),
            ("Active Workbenches", material["active_workbenches"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Verification Commands", material["verification_commands"]),
            ("Next Actions", material["next_actions"]),
            ("Stop Conditions", material["stop_conditions"]),
        ),
    )
