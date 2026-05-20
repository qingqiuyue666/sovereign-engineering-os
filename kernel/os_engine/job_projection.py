"""Replay projection for event-sourced OS engine job state."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from kernel.os_engine.database import stable_content_hash, validate_no_secret_like
from kernel.os_engine.event_types import HARD_TERMINAL_EVENT_TYPES, JobEventType


class JobProjectionError(RuntimeError):
    """Raised when job event history cannot be replayed safely."""


@dataclass(frozen=True, slots=True)
class ProjectedJobState:
    job_id: str
    current_status: str
    worker_name: str | None
    artifact_ids: tuple[str, ...]
    failure_reason: str | None
    quarantine_reason: str | None
    human_review_required: bool
    final_claim_allowed: bool
    last_event_type: str
    event_count: int
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def project_job_state(events: Iterable[object]) -> ProjectedJobState:
    normalized = [_normalize_event(event) for event in events]
    if not normalized:
        raise JobProjectionError("job history is empty")
    normalized.sort(key=lambda item: int(item["sequence"]))
    first = normalized[0]
    if first["sequence"] != 1 or first["event_type"] != JobEventType.JOB_CREATED.value:
        raise JobProjectionError("job history must start with JobCreated sequence 1")

    job_id = str(first["job_id"])
    status = "created"
    worker_name: str | None = None
    artifact_ids: list[str] = []
    failure_reason: str | None = None
    quarantine_reason: str | None = None
    human_review_required = bool(first["payload"].get("human_review_required", False))
    dry_run = bool(first["payload"].get("dry_run", False))
    pending_review = False
    review_approved = False
    review_rejected = False
    pre_review_status = "running"
    hard_terminal = False
    terminal_event_seen: str | None = None
    completion_evidence_seen = False
    expected_sequence = 1

    for event in normalized:
        event_type = str(event["event_type"])
        payload = dict(event["payload"])
        reason = event.get("reason")
        sequence = int(event["sequence"])
        if str(event["job_id"]) != job_id:
            raise JobProjectionError("project_job_state received events for multiple jobs")
        if sequence != expected_sequence:
            raise JobProjectionError("job event sequence must be contiguous")
        expected_sequence += 1
        if event_type == JobEventType.JOB_CREATED.value and sequence != 1:
            raise JobProjectionError("duplicate JobCreated event rejected")
        if hard_terminal:
            raise JobProjectionError(f"event after terminal state rejected: {event_type}")
        if pending_review and event_type not in {
            JobEventType.HUMAN_APPROVED.value,
            JobEventType.HUMAN_REJECTED.value,
        }:
            raise JobProjectionError(f"execution is blocked while human review is pending: {event_type}")

        if event_type == JobEventType.JOB_CREATED.value:
            status = "created"
            continue
        if event_type == JobEventType.JOB_ADMITTED.value:
            _require_status(status, {"created"}, event_type)
            status = "admitted"
        elif event_type == JobEventType.JOB_QUEUED.value:
            _require_status(status, {"admitted"}, event_type)
            status = "pending"
        elif event_type == JobEventType.WORKER_SELECTED.value:
            _require_status(status, {"admitted", "pending"}, event_type)
            worker_name = _payload_text(payload, "worker_name", required=True)
        elif event_type == JobEventType.JOB_STARTED.value:
            _require_status(status, {"pending"}, event_type)
            status = "running"
        elif event_type == JobEventType.SUBPROCESS_STARTED.value:
            _require_status(status, {"running"}, event_type)
        elif event_type == JobEventType.ARTIFACT_DISCOVERED.value:
            _require_status(status, {"running"}, event_type)
            for artifact_id in _artifact_ids_from_payload(payload):
                if artifact_id not in artifact_ids:
                    artifact_ids.append(artifact_id)
        elif event_type == JobEventType.ARTIFACT_VALIDATED.value:
            _require_status(status, {"running"}, event_type)
            for artifact_id in _artifact_ids_from_payload(payload):
                if artifact_id not in artifact_ids:
                    artifact_ids.append(artifact_id)
        elif event_type == JobEventType.HUMAN_REVIEW_REQUESTED.value:
            _require_status(status, {"admitted", "pending", "running"}, event_type)
            human_review_required = True
            pending_review = True
            pre_review_status = status
            status = "requires_human_review"
        elif event_type == JobEventType.HUMAN_APPROVED.value:
            if not artifact_ids:
                raise JobProjectionError("HumanApproved requires at least one discovered artifact")
            review_approved = True
            pending_review = False
            status = pre_review_status
        elif event_type == JobEventType.HUMAN_REJECTED.value:
            if not reason:
                raise JobProjectionError("HumanRejected requires reason")
            review_rejected = True
            pending_review = False
            status = "requires_human_review"
            terminal_event_seen = event_type
            hard_terminal = True
        elif event_type == JobEventType.JOB_SUCCEEDED.value:
            _require_status(status, {"running"}, event_type)
            if dry_run and payload.get("physical_proof") is True:
                raise JobProjectionError("dry_run jobs cannot produce physical proof claims")
            if human_review_required and not review_approved:
                raise JobProjectionError("human review approval is required before success")
            if not (_artifact_ids_from_payload(payload) or payload.get("completion_evidence") or payload.get("completion_record")):
                raise JobProjectionError("JobSucceeded requires artifact or completion evidence")
            for artifact_id in _artifact_ids_from_payload(payload):
                if artifact_id not in artifact_ids:
                    artifact_ids.append(artifact_id)
            completion_evidence_seen = True
            status = "succeeded"
            terminal_event_seen = event_type
            hard_terminal = True
        elif event_type == JobEventType.JOB_FAILED.value:
            _require_status(status, {"admitted", "pending", "running"}, event_type)
            if not reason:
                raise JobProjectionError("JobFailed requires reason")
            failure_reason = reason
            status = "failed"
            terminal_event_seen = event_type
            hard_terminal = True
        elif event_type == JobEventType.JOB_QUARANTINED.value:
            _require_status(status, {"admitted", "pending", "running"}, event_type)
            if not reason:
                raise JobProjectionError("JobQuarantined requires reason")
            quarantine_reason = reason
            status = "quarantined"
            terminal_event_seen = event_type
            hard_terminal = True
        elif event_type == JobEventType.JOB_CANCELLED.value:
            _require_status(status, {"created", "admitted", "pending", "running"}, event_type)
            status = "cancelled"
            terminal_event_seen = event_type
            hard_terminal = True
        else:
            raise JobProjectionError(f"unknown job event type: {event_type}")

        if event_type in HARD_TERMINAL_EVENT_TYPES and terminal_event_seen not in {None, event_type}:
            raise JobProjectionError("duplicate terminal events rejected")

    final_claim_allowed = (
        status == "succeeded"
        and bool(artifact_ids or completion_evidence_seen)
        and not pending_review
        and not review_rejected
        and (not human_review_required or review_approved)
    )
    payload_for_hash = {
        "artifact_ids": tuple(sorted(artifact_ids)),
        "current_status": status,
        "event_count": len(normalized),
        "failure_reason": failure_reason,
        "final_claim_allowed": final_claim_allowed,
        "human_review_required": human_review_required,
        "job_id": job_id,
        "last_event_type": str(normalized[-1]["event_type"]),
        "quarantine_reason": quarantine_reason,
        "worker_name": worker_name,
    }
    return ProjectedJobState(
        job_id=job_id,
        current_status=status,
        worker_name=worker_name,
        artifact_ids=tuple(sorted(artifact_ids)),
        failure_reason=failure_reason,
        quarantine_reason=quarantine_reason,
        human_review_required=human_review_required,
        final_claim_allowed=final_claim_allowed,
        last_event_type=str(normalized[-1]["event_type"]),
        event_count=len(normalized),
        content_hash=stable_content_hash(payload_for_hash),
    )


def project_all_jobs(events: Iterable[object]) -> dict[str, ProjectedJobState]:
    grouped: dict[str, list[object]] = {}
    for event in events:
        normalized = _normalize_event(event)
        grouped.setdefault(str(normalized["job_id"]), []).append(normalized)
    return {job_id: project_job_state(grouped[job_id]) for job_id in sorted(grouped)}


def _normalize_event(event: object) -> dict[str, Any]:
    if hasattr(event, "to_dict") and callable(getattr(event, "to_dict")):
        raw = dict(event.to_dict())  # type: ignore[call-arg]
    elif hasattr(event, "keys"):
        raw = dict(event)  # type: ignore[arg-type]
    else:
        raise JobProjectionError("event must be mapping-like")
    try:
        payload = raw.get("payload")
        if payload is None and "payload_json" in raw:
            payload = json.loads(str(raw["payload_json"]))
        if not isinstance(payload, dict):
            raise JobProjectionError("event payload must be a JSON object")
        validate_no_secret_like(payload)
        return {
            "event_id": raw.get("event_id"),
            "job_id": str(raw["job_id"]),
            "sequence": int(raw["sequence"]),
            "event_type": str(raw["event_type"]),
            "payload": payload,
            "reason": raw.get("reason"),
        }
    except KeyError as exc:
        raise JobProjectionError(f"malformed event missing {exc}") from exc


def _require_status(current: str, allowed: set[str], event_type: str) -> None:
    if current not in allowed:
        raise JobProjectionError(f"{event_type} is illegal after status {current}")


def _payload_text(payload: dict[str, Any], key: str, *, required: bool = False) -> str | None:
    value = payload.get(key)
    if value is None:
        if required:
            raise JobProjectionError(f"{key} is required")
        return None
    if not isinstance(value, str) or not value.strip():
        raise JobProjectionError(f"{key} must be a non-empty string")
    return value


def _artifact_ids_from_payload(payload: dict[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(payload.get("artifact_id"), str):
        values.append(str(payload["artifact_id"]))
    raw_ids = payload.get("artifact_ids")
    if raw_ids is not None:
        if not isinstance(raw_ids, list) or not all(isinstance(item, str) and item for item in raw_ids):
            raise JobProjectionError("artifact_ids must be a list of non-empty strings")
        values.extend(raw_ids)
    return tuple(sorted(set(values)))
