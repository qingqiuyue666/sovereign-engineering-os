"""Read-only operator dashboard model and view rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence
import json

__all__ = [
    "OPERATOR_DASHBOARD_VIEWS",
    "OperatorDashboardModel",
    "build_operator_dashboard_model",
    "render_operator_dashboard_view",
]


OPERATOR_DASHBOARD_VIEWS = (
    "summary",
    "jobs",
    "pr_readiness",
    "artifacts",
    "receipts",
    "failures",
    "approvals",
    "milestones",
)

_SECRET_KEY_PARTS = (
    "api_key",
    "credential",
    "password",
    "raw_prompt",
    "raw_response",
    "secret",
    "token",
)


@dataclass(frozen=True)
class OperatorDashboardModel:
    jobs: tuple[dict[str, object], ...]
    pr_readiness: tuple[dict[str, object], ...]
    artifacts: tuple[dict[str, object], ...]
    receipts: tuple[dict[str, object], ...]
    failures: tuple[dict[str, object], ...]
    approvals: tuple[dict[str, object], ...]
    milestones: tuple[dict[str, object], ...]
    mutation_performed: bool = False
    merge_performed: bool = False
    branch_deleted: bool = False
    execution_performed: bool = False
    network_accessed: bool = False

    def summary(self) -> dict[str, object]:
        return {
            "model_type": "operator_dashboard_model_v1",
            "job_count": len(self.jobs),
            "pr_readiness_count": len(self.pr_readiness),
            "artifact_count": len(self.artifacts),
            "receipt_count": len(self.receipts),
            "failure_count": len(self.failures),
            "approval_count": len(self.approvals),
            "milestone_count": len(self.milestones),
            "open_job_count": _count_by_status(self.jobs, ("queued", "leased", "running")),
            "blocked_pr_count": _count_by_status(self.pr_readiness, ("blocked", "do_not_merge")),
            "pending_approval_count": _count_by_status(self.approvals, ("pending",)),
            "mutation_performed": self.mutation_performed,
            "merge_performed": self.merge_performed,
            "branch_deleted": self.branch_deleted,
            "execution_performed": self.execution_performed,
            "network_accessed": self.network_accessed,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "model_type": "operator_dashboard_model_v1",
            "summary": self.summary(),
            "jobs": list(self.jobs),
            "pr_readiness": list(self.pr_readiness),
            "artifacts": list(self.artifacts),
            "receipts": list(self.receipts),
            "failures": list(self.failures),
            "approvals": list(self.approvals),
            "milestones": list(self.milestones),
            "mutation_performed": self.mutation_performed,
            "merge_performed": self.merge_performed,
            "branch_deleted": self.branch_deleted,
            "execution_performed": self.execution_performed,
            "network_accessed": self.network_accessed,
        }


def build_operator_dashboard_model(payload: Mapping[str, object]) -> OperatorDashboardModel:
    """Normalize caller-provided dashboard data without mutating it."""

    return OperatorDashboardModel(
        jobs=_redacted_records(payload.get("jobs", ())),
        pr_readiness=_redacted_records(payload.get("pr_readiness", ())),
        artifacts=_redacted_records(payload.get("artifacts", ())),
        receipts=_redacted_records(payload.get("receipts", ())),
        failures=_redacted_records(payload.get("failures", ())),
        approvals=_redacted_records(payload.get("approvals", ())),
        milestones=_redacted_records(payload.get("milestones", ())),
    )


def render_operator_dashboard_view(model: OperatorDashboardModel, view: str = "summary") -> str:
    if not isinstance(model, OperatorDashboardModel):
        raise ValueError("model_must_be_operator_dashboard_model")
    if view not in OPERATOR_DASHBOARD_VIEWS:
        raise ValueError("operator_dashboard_view_unknown")
    if view == "summary":
        payload: object = model.summary()
    else:
        payload = model.as_dict()[view]
    return json.dumps(
        {
            "view_type": f"operator_dashboard_{view}_view_v1",
            "view": view,
            "read_only": True,
            "mutation_performed": False,
            "merge_performed": False,
            "branch_deleted": False,
            "execution_performed": False,
            "network_accessed": False,
            "data": payload,
        },
        indent=2,
        sort_keys=True,
    ) + "\n"


def _redacted_records(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    records: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            records.append(
                {
                    str(key): _redact_value(str(key), child)
                    for key, child in sorted(item.items())
                }
            )
    return tuple(records)


def _redact_value(key: str, value: object) -> object:
    if _is_secret_key(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(child_key): _redact_value(str(child_key), child)
            for child_key, child in sorted(value.items())
        }
    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SECRET_KEY_PARTS)


def _count_by_status(records: Sequence[Mapping[str, object]], statuses: Sequence[str]) -> int:
    wanted = set(statuses)
    return sum(1 for record in records if str(record.get("status", "")).lower() in wanted)
