"""Deterministic full-system readiness matrix."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_nonempty_string

__all__ = ["SystemReadinessSection", "SystemReadinessMatrix", "build_system_readiness_matrix"]

_POLICY_VERSION = "system-readiness-matrix-v1"
_CODE_VERSION = "0.1.0"

_REQUIRED_SECTIONS = (
    "governance_integrity",
    "local_runtime",
    "review_gate",
    "operator_review_host",
    "decision_ledger",
    "durable_decision_store",
    "durable_review_store",
    "recovery",
    "audit_export",
    "read_only_status",
    "work_queue",
    "runbook_shell",
    "provider_worker_preflight",
    "real_provider_execution_blocked",
    "production_autonomy_blocked",
)
_AVAILABLE_SECTIONS = frozenset(
    {
        "governance_integrity",
        "local_runtime",
        "review_gate",
        "operator_review_host",
        "decision_ledger",
        "durable_decision_store",
        "durable_review_store",
        "recovery",
        "audit_export",
        "read_only_status",
        "work_queue",
        "runbook_shell",
        "provider_worker_preflight",
    }
)
_BLOCKED_SECTIONS = frozenset(
    {
        "real_provider_execution_blocked",
        "production_autonomy_blocked",
    }
)


@dataclass(frozen=True)
class SystemReadinessSection:
    section_name: str
    status: str
    available: bool
    reason_code: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "available": self.available,
            "code_version": self.code_version,
            "policy_version": self.policy_version,
            "reason_code": self.reason_code,
            "section_name": self.section_name,
            "status": self.status,
        }


@dataclass(frozen=True)
class SystemReadinessMatrix:
    matrix_id: str
    sections: tuple[SystemReadinessSection, ...]
    available_count: int
    blocked_count: int
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "available_count": self.available_count,
            "blocked_count": self.blocked_count,
            "code_version": self.code_version,
            "matrix_id": self.matrix_id,
            "policy_version": self.policy_version,
            "section_hashes": [section.content_hash for section in self.sections],
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["sections"] = [section.deterministic_material() for section in self.sections]
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_system_readiness_matrix(
    *,
    matrix_id: str = "full-system-readiness-matrix-v1",
    observed_at: str | None = None,
) -> SystemReadinessMatrix:
    """Build a deterministic local readiness matrix without executing checks."""

    if not strict_nonempty_string(matrix_id):
        raise ValueError("matrix_id_must_be_nonempty_string")
    observed = _observed_at(observed_at)
    sections = tuple(_build_section(name) for name in _REQUIRED_SECTIONS)
    available_count = sum(1 for section in sections if section.available)
    blocked_count = sum(1 for section in sections if section.status == "blocked")
    matrix = SystemReadinessMatrix(
        matrix_id=matrix_id,
        sections=sections,
        available_count=available_count,
        blocked_count=blocked_count,
        content_hash="",
        observed_at=observed,
    )
    return SystemReadinessMatrix(
        matrix_id=matrix.matrix_id,
        sections=matrix.sections,
        available_count=matrix.available_count,
        blocked_count=matrix.blocked_count,
        policy_version=matrix.policy_version,
        code_version=matrix.code_version,
        content_hash=digest_payload(matrix.deterministic_material()),
        observed_at=matrix.observed_at,
    )


def _build_section(section_name: str) -> SystemReadinessSection:
    if section_name in _AVAILABLE_SECTIONS:
        section = SystemReadinessSection(
            section_name=section_name,
            status="available",
            available=True,
            reason_code="local_control_plane_layer_present",
            content_hash="",
        )
    elif section_name in _BLOCKED_SECTIONS:
        section = SystemReadinessSection(
            section_name=section_name,
            status="blocked",
            available=False,
            reason_code="intentionally_blocked_without_future_authorized_slice",
            content_hash="",
        )
    else:
        raise ValueError("unknown_readiness_section")
    return SystemReadinessSection(
        section_name=section.section_name,
        status=section.status,
        available=section.available,
        reason_code=section.reason_code,
        policy_version=section.policy_version,
        code_version=section.code_version,
        content_hash=digest_payload(section.deterministic_material()),
    )


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
