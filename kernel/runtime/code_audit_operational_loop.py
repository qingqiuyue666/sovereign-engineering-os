"""Deterministic manifest for the private code audit operational loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_list_fields,
    require_required_members,
    require_string_fields,
)

__all__ = [
    "CODE_AUDIT_REQUIRED_LOOP_STEPS",
    "CodeAuditOperationalLoop",
    "build_code_audit_operational_loop",
    "render_code_audit_operational_loop_markdown",
]

_POLICY_VERSION = "code-audit-operational-loop-v1"
_CODE_VERSION = "0.1.0"

CODE_AUDIT_REQUIRED_LOOP_STEPS = (
    "AI worker receives handoff packet.",
    "AI worker implements branch.",
    "AI worker returns final report.",
    "Operator builds AI worker result review packet.",
    "Operator builds branch audit report.",
    "Operator builds merge readiness report.",
    "Human reviews.",
    "Merge only if approved.",
    "Post-merge retrospective is generated.",
    "Daily report is updated.",
)

_STRING_FIELDS = ("loop_id", "repository_url", "main_commit", "policy_version", "code_version")
_LIST_FIELDS = (
    "loop_steps",
    "required_reports",
    "required_verification",
    "human_review_points",
    "blocked_actions",
    "success_criteria",
    "stop_conditions",
)


@dataclass(frozen=True)
class CodeAuditOperationalLoop:
    """Repository-ready code audit loop manifest."""

    loop_id: str
    repository_url: str
    main_commit: str
    loop_steps: tuple[object, ...]
    required_reports: tuple[object, ...]
    required_verification: tuple[object, ...]
    human_review_points: tuple[object, ...]
    blocked_actions: tuple[object, ...]
    success_criteria: tuple[object, ...]
    stop_conditions: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_actions": list(self.blocked_actions),
            "code_version": self.code_version,
            "human_review_points": list(self.human_review_points),
            "loop_id": self.loop_id,
            "loop_steps": list(self.loop_steps),
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "repository_url": self.repository_url,
            "required_reports": list(self.required_reports),
            "required_verification": list(self.required_verification),
            "stop_conditions": list(self.stop_conditions),
            "success_criteria": list(self.success_criteria),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_code_audit_operational_loop(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> CodeAuditOperationalLoop:
    """Build a deterministic manifest for the code audit operational loop."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="code_audit_operational_loop_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    require_required_members(
        normalized["loop_steps"],
        CODE_AUDIT_REQUIRED_LOOP_STEPS,
        field="loop_steps",
    )

    loop = CodeAuditOperationalLoop(
        loop_id=normalized["loop_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        loop_steps=tuple(normalized["loop_steps"]),
        required_reports=tuple(normalized["required_reports"]),
        required_verification=tuple(normalized["required_verification"]),
        human_review_points=tuple(normalized["human_review_points"]),
        blocked_actions=tuple(normalized["blocked_actions"]),
        success_criteria=tuple(normalized["success_criteria"]),
        stop_conditions=tuple(normalized["stop_conditions"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(loop)


def render_code_audit_operational_loop_markdown(loop: CodeAuditOperationalLoop) -> str:
    """Render code audit loop Markdown deterministically."""

    if not isinstance(loop, CodeAuditOperationalLoop):
        raise ValueError("loop_must_be_code_audit_operational_loop")
    material = loop.deterministic_material()
    return render_markdown(
        "Code Audit Operational Loop",
        metadata_rows=(
            ("loop_id", loop.loop_id),
            ("repository_url", loop.repository_url),
            ("main_commit", loop.main_commit),
            ("policy_version", loop.policy_version),
            ("code_version", loop.code_version),
            ("content_hash", loop.content_hash),
            ("observed_at", loop.observed_at),
        ),
        sections=(
            ("Loop Steps", material["loop_steps"]),
            ("Required Reports", material["required_reports"]),
            ("Required Verification", material["required_verification"]),
            ("Human Review Points", material["human_review_points"]),
            ("Blocked Actions", material["blocked_actions"]),
            ("Success Criteria", material["success_criteria"]),
            ("Stop Conditions", material["stop_conditions"]),
        ),
    )


def _with_hash(loop: CodeAuditOperationalLoop) -> CodeAuditOperationalLoop:
    return CodeAuditOperationalLoop(
        loop_id=loop.loop_id,
        repository_url=loop.repository_url,
        main_commit=loop.main_commit,
        loop_steps=loop.loop_steps,
        required_reports=loop.required_reports,
        required_verification=loop.required_verification,
        human_review_points=loop.human_review_points,
        blocked_actions=loop.blocked_actions,
        success_criteria=loop.success_criteria,
        stop_conditions=loop.stop_conditions,
        policy_version=loop.policy_version,
        code_version=loop.code_version,
        content_hash=compute_content_hash(loop.deterministic_material()),
        observed_at=loop.observed_at,
    )
