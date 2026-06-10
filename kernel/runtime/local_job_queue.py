"""Manual local job queue state machine.

This queue is a contract implementation for controlled local tasks. It does
not execute jobs, start a background worker, open network/browser surfaces, or
schedule autonomous work.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Mapping, Sequence

from kernel.runtime._strict_validation import strict_nonempty_string
from kernel.runtime.real_local_runner_boundary import REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST

__all__ = [
    "JOB_STATES",
    "TERMINAL_JOB_STATES",
    "CrashRecoveryClassification",
    "JobDescriptor",
    "JobEvent",
    "JobLease",
    "JobRecord",
    "LocalJobQueue",
    "summarize_job_event_records",
]

_POLICY_VERSION = "local-job-queue-v1"
_CODE_VERSION = "0.1.0"
REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID = "real_local_runner_boundary_v1"
TOKEN_INTEGRATION_STATUS_WAITING = "WAITING_FOR_TOKEN_MERGE"
ALLOWED_LOCAL_RUNNER_COMMAND_IDS: tuple[str, ...] = tuple(
    REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST.keys()
)

JOB_STATES: tuple[str, ...] = ("queued", "leased", "completed", "failed", "canceled")
TERMINAL_JOB_STATES: tuple[str, ...] = ("completed", "failed", "canceled")
_FORBIDDEN_DESCRIPTOR_FIELDS = frozenset(
    {
        "args",
        "argv",
        "browser",
        "command",
        "command_line",
        "command_text",
        "network",
        "provider_api",
        "shell",
        "shell_command",
        "url",
    }
)


@dataclass(frozen=True)
class JobDescriptor:
    """Static job request metadata."""

    job_id: str
    task_id: str
    command_id: str
    scope: str
    priority: int
    max_attempts: int
    lease_timeout_seconds: int
    created_at: str
    run_id: str = ""
    approval_artifact_ref: str = ""
    token_id: str = ""
    token_receipt_ref: str = ""
    runner_receipt_ref: str = ""
    runner_policy_id: str = REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID
    token_integration_status: str = TOKEN_INTEGRATION_STATUS_WAITING
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION

    def as_dict(self) -> dict[str, object]:
        return {
            "approval_artifact_ref": self.approval_artifact_ref,
            "code_version": self.code_version,
            "command_id": self.command_id,
            "created_at": self.created_at,
            "job_id": self.job_id,
            "lease_timeout_seconds": self.lease_timeout_seconds,
            "max_attempts": self.max_attempts,
            "policy_version": self.policy_version,
            "priority": self.priority,
            "run_id": self.run_id,
            "runner_policy_id": self.runner_policy_id,
            "runner_receipt_ref": self.runner_receipt_ref,
            "scope": self.scope,
            "task_id": self.task_id,
            "token_id": self.token_id,
            "token_integration_status": self.token_integration_status,
            "token_receipt_ref": self.token_receipt_ref,
        }


@dataclass(frozen=True)
class JobLease:
    lease_id: str
    job_id: str
    worker_id: str
    leased_at: str
    heartbeat_at: str
    expires_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "expires_at": self.expires_at,
            "heartbeat_at": self.heartbeat_at,
            "job_id": self.job_id,
            "lease_id": self.lease_id,
            "leased_at": self.leased_at,
            "worker_id": self.worker_id,
        }


@dataclass(frozen=True)
class JobEvent:
    sequence: int
    event_id: str
    event_type: str
    job_id: str
    from_state: str | None
    to_state: str
    attempt: int
    reason: str
    observed_at: str
    event_hash: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION

    def deterministic_material(self) -> dict[str, object]:
        return {
            "attempt": self.attempt,
            "code_version": self.code_version,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "from_state": self.from_state,
            "job_id": self.job_id,
            "policy_version": self.policy_version,
            "reason": self.reason,
            "sequence": self.sequence,
            "to_state": self.to_state,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["event_hash"] = self.event_hash
        payload["observed_at"] = self.observed_at
        return payload


@dataclass(frozen=True)
class JobRecord:
    descriptor: JobDescriptor
    state: str
    attempts: int
    lease: JobLease | None = None
    terminal_reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "attempts": self.attempts,
            "descriptor": self.descriptor.as_dict(),
            "lease": self.lease.as_dict() if self.lease is not None else None,
            "state": self.state,
            "terminal_reason": self.terminal_reason,
        }


@dataclass(frozen=True)
class CrashRecoveryClassification:
    job_id: str
    classification: str
    retry_allowed: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification,
            "job_id": self.job_id,
            "reason": self.reason,
            "retry_allowed": self.retry_allowed,
        }


class LocalJobQueue:
    """Manual queue state machine with append-only event history."""

    def __init__(self, *, queue_id: str) -> None:
        if not strict_nonempty_string(queue_id):
            raise ValueError("queue_id_required")
        self.queue_id = queue_id
        self._jobs: dict[str, JobRecord] = {}
        self._events: list[JobEvent] = []

    @property
    def events(self) -> tuple[JobEvent, ...]:
        return tuple(self._events)

    @property
    def jobs(self) -> tuple[JobRecord, ...]:
        return tuple(self._jobs[job_id] for job_id in sorted(self._jobs))

    def enqueue(
        self,
        *,
        job_id: str,
        task_id: str,
        command_id: str,
        scope: str,
        priority: int = 100,
        max_attempts: int = 1,
        lease_timeout_seconds: int = 60,
        run_id: str = "",
        approval_artifact_ref: str = "",
        token_id: str = "",
        token_receipt_ref: str = "",
        runner_receipt_ref: str = "",
        runner_policy_id: str = REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID,
        token_integration_status: str = TOKEN_INTEGRATION_STATUS_WAITING,
        created_at: str | None = None,
    ) -> JobRecord:
        if job_id in self._jobs:
            raise ValueError("duplicate_job_id")
        descriptor = JobDescriptor(
            job_id=job_id,
            task_id=task_id,
            command_id=command_id,
            scope=scope,
            priority=priority,
            max_attempts=max_attempts,
            lease_timeout_seconds=lease_timeout_seconds,
            created_at=_timestamp(created_at),
            run_id=run_id,
            approval_artifact_ref=approval_artifact_ref,
            token_id=token_id,
            token_receipt_ref=token_receipt_ref,
            runner_receipt_ref=runner_receipt_ref,
            runner_policy_id=runner_policy_id,
            token_integration_status=token_integration_status,
        )
        _validate_descriptor(descriptor)
        record = JobRecord(descriptor=descriptor, state="queued", attempts=0)
        self._jobs[job_id] = record
        self._append_event(
            event_type="enqueued",
            job_id=job_id,
            from_state=None,
            to_state="queued",
            attempt=0,
            reason="",
            observed_at=descriptor.created_at,
        )
        return record

    def enqueue_from_mapping(self, payload: Mapping[str, object]) -> JobRecord:
        """Enqueue from a descriptor mapping while rejecting execution surfaces."""

        if not isinstance(payload, Mapping):
            raise ValueError("job_descriptor_must_be_mapping")
        forbidden = sorted(
            field for field in payload if str(field) in _FORBIDDEN_DESCRIPTOR_FIELDS
        )
        if forbidden:
            raise ValueError("job_descriptor_forbidden_fields:" + ",".join(forbidden))
        return self.enqueue(
            job_id=_required_string(payload, "job_id"),
            task_id=_required_string(payload, "task_id"),
            command_id=_required_string(payload, "command_id"),
            scope=_required_string(payload, "scope"),
            priority=_optional_int(payload, "priority", 100),
            max_attempts=_optional_int(payload, "max_attempts", 1),
            lease_timeout_seconds=_optional_int(
                payload,
                "lease_timeout_seconds",
                60,
            ),
            run_id=_optional_string(payload, "run_id"),
            approval_artifact_ref=_optional_string(payload, "approval_artifact_ref"),
            token_id=_optional_string(payload, "token_id"),
            token_receipt_ref=_optional_string(payload, "token_receipt_ref"),
            runner_receipt_ref=_optional_string(payload, "runner_receipt_ref"),
            runner_policy_id=_optional_string(
                payload,
                "runner_policy_id",
                REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID,
            ),
            token_integration_status=_optional_string(
                payload,
                "token_integration_status",
                TOKEN_INTEGRATION_STATUS_WAITING,
            ),
            created_at=_optional_string(payload, "created_at") or None,
        )

    def lease_next(
        self,
        *,
        worker_id: str,
        leased_at: str | None = None,
    ) -> JobRecord:
        if not strict_nonempty_string(worker_id):
            raise ValueError("worker_id_required")
        queued = [job for job in self._jobs.values() if job.state == "queued"]
        if not queued:
            raise ValueError("no_queued_jobs")
        selected = sorted(
            queued,
            key=lambda job: (job.descriptor.priority, job.descriptor.created_at, job.descriptor.job_id),
        )[0]
        now = _timestamp(leased_at)
        attempts = selected.attempts + 1
        lease = JobLease(
            lease_id=_lease_id(selected.descriptor.job_id, worker_id, attempts, now),
            job_id=selected.descriptor.job_id,
            worker_id=worker_id,
            leased_at=now,
            heartbeat_at=now,
            expires_at=_add_seconds(now, selected.descriptor.lease_timeout_seconds),
        )
        updated = replace(selected, state="leased", attempts=attempts, lease=lease)
        self._jobs[selected.descriptor.job_id] = updated
        self._append_event(
            event_type="leased",
            job_id=selected.descriptor.job_id,
            from_state="queued",
            to_state="leased",
            attempt=attempts,
            reason=lease.lease_id,
            observed_at=now,
        )
        return updated

    def heartbeat(
        self,
        *,
        job_id: str,
        lease_id: str,
        heartbeat_at: str | None = None,
    ) -> JobRecord:
        record = self._require_state(job_id, "leased")
        if record.lease is None or record.lease.lease_id != lease_id:
            raise ValueError("lease_id_mismatch")
        now = _timestamp(heartbeat_at)
        lease = replace(
            record.lease,
            heartbeat_at=now,
            expires_at=_add_seconds(now, record.descriptor.lease_timeout_seconds),
        )
        updated = replace(record, lease=lease)
        self._jobs[job_id] = updated
        self._append_event(
            event_type="heartbeat",
            job_id=job_id,
            from_state="leased",
            to_state="leased",
            attempt=record.attempts,
            reason=lease.lease_id,
            observed_at=now,
        )
        return updated

    def complete(
        self,
        *,
        job_id: str,
        lease_id: str,
        completed_at: str | None = None,
    ) -> JobRecord:
        record = self._require_matching_lease(job_id, lease_id)
        now = _timestamp(completed_at)
        updated = replace(record, state="completed", lease=None, terminal_reason="completed")
        self._jobs[job_id] = updated
        self._append_event(
            event_type="completed",
            job_id=job_id,
            from_state="leased",
            to_state="completed",
            attempt=record.attempts,
            reason="completed",
            observed_at=now,
        )
        return updated

    def fail(
        self,
        *,
        job_id: str,
        lease_id: str,
        reason: str,
        failed_at: str | None = None,
    ) -> JobRecord:
        if not strict_nonempty_string(reason):
            raise ValueError("failure_reason_required")
        record = self._require_matching_lease(job_id, lease_id)
        now = _timestamp(failed_at)
        retry_allowed = record.attempts < record.descriptor.max_attempts
        if retry_allowed:
            updated = replace(record, state="queued", lease=None, terminal_reason="")
            to_state = "queued"
            event_type = "retry_scheduled"
        else:
            updated = replace(record, state="failed", lease=None, terminal_reason=reason)
            to_state = "failed"
            event_type = "failed"
        self._jobs[job_id] = updated
        self._append_event(
            event_type=event_type,
            job_id=job_id,
            from_state="leased",
            to_state=to_state,
            attempt=record.attempts,
            reason=reason,
            observed_at=now,
        )
        return updated

    def cancel(
        self,
        *,
        job_id: str,
        reason: str,
        canceled_at: str | None = None,
    ) -> JobRecord:
        if not strict_nonempty_string(reason):
            raise ValueError("cancel_reason_required")
        record = self._get_job(job_id)
        if record.state in TERMINAL_JOB_STATES:
            raise ValueError("terminal_job_cannot_cancel")
        now = _timestamp(canceled_at)
        updated = replace(record, state="canceled", lease=None, terminal_reason=reason)
        self._jobs[job_id] = updated
        self._append_event(
            event_type="canceled",
            job_id=job_id,
            from_state=record.state,
            to_state="canceled",
            attempt=record.attempts,
            reason=reason,
            observed_at=now,
        )
        return updated

    def classify_expired_leases(self, *, now: str | None = None) -> tuple[CrashRecoveryClassification, ...]:
        active_now = _parse_time(_timestamp(now))
        classifications: list[CrashRecoveryClassification] = []
        for record in self._jobs.values():
            if record.state != "leased" or record.lease is None:
                continue
            if _parse_time(record.lease.expires_at) > active_now:
                continue
            retry_allowed = record.attempts < record.descriptor.max_attempts
            classifications.append(
                CrashRecoveryClassification(
                    job_id=record.descriptor.job_id,
                    classification="expired_lease_retryable" if retry_allowed else "expired_lease_terminal",
                    retry_allowed=retry_allowed,
                    reason="lease_expired_without_heartbeat",
                )
            )
        return tuple(sorted(classifications, key=lambda item: item.job_id))

    def summary(self) -> dict[str, object]:
        counts = {state: 0 for state in JOB_STATES}
        for job in self._jobs.values():
            counts[job.state] += 1
        return {
            "event_count": len(self._events),
            "job_count": len(self._jobs),
            "queue_id": self.queue_id,
            "state_counts": counts,
        }

    def _require_matching_lease(self, job_id: str, lease_id: str) -> JobRecord:
        record = self._require_state(job_id, "leased")
        if record.lease is None or record.lease.lease_id != lease_id:
            raise ValueError("lease_id_mismatch")
        return record

    def _require_state(self, job_id: str, state: str) -> JobRecord:
        record = self._get_job(job_id)
        if record.state != state:
            raise ValueError(f"job_state_must_be_{state}")
        return record

    def _get_job(self, job_id: str) -> JobRecord:
        if not strict_nonempty_string(job_id):
            raise ValueError("job_id_required")
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise ValueError("unknown_job_id") from exc

    def _append_event(
        self,
        *,
        event_type: str,
        job_id: str,
        from_state: str | None,
        to_state: str,
        attempt: int,
        reason: str,
        observed_at: str,
    ) -> None:
        sequence = len(self._events) + 1
        event_id = f"{self.queue_id}:{sequence:06d}:{job_id}:{event_type}"
        material = {
            "attempt": attempt,
            "code_version": _CODE_VERSION,
            "event_id": event_id,
            "event_type": event_type,
            "from_state": from_state,
            "job_id": job_id,
            "policy_version": _POLICY_VERSION,
            "reason": reason,
            "sequence": sequence,
            "to_state": to_state,
        }
        event = JobEvent(
            sequence=sequence,
            event_id=event_id,
            event_type=event_type,
            job_id=job_id,
            from_state=from_state,
            to_state=to_state,
            attempt=attempt,
            reason=reason,
            observed_at=observed_at,
            event_hash=_digest_payload(material),
        )
        self._events.append(event)


def summarize_job_event_records(records: Sequence[Mapping[str, object]]) -> dict[str, object]:
    latest_state_by_job: dict[str, str] = {}
    event_count = 0
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("event_record_must_be_mapping")
        job_id = record.get("job_id")
        to_state = record.get("to_state")
        if not strict_nonempty_string(job_id):
            raise ValueError("event_job_id_required")
        if to_state not in JOB_STATES:
            raise ValueError("event_to_state_invalid")
        latest_state_by_job[str(job_id)] = str(to_state)
        event_count += 1
    counts = {state: 0 for state in JOB_STATES}
    for state in latest_state_by_job.values():
        counts[state] += 1
    return {
        "event_count": event_count,
        "job_count": len(latest_state_by_job),
        "state_counts": counts,
    }


def _validate_descriptor(descriptor: JobDescriptor) -> None:
    for field, value in (
        ("job_id", descriptor.job_id),
        ("task_id", descriptor.task_id),
        ("command_id", descriptor.command_id),
        ("scope", descriptor.scope),
        ("created_at", descriptor.created_at),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_required")
    if not isinstance(descriptor.priority, int):
        raise ValueError("priority_must_be_int")
    if not isinstance(descriptor.max_attempts, int) or descriptor.max_attempts < 1:
        raise ValueError("max_attempts_must_be_positive_int")
    if not isinstance(descriptor.lease_timeout_seconds, int) or descriptor.lease_timeout_seconds < 1:
        raise ValueError("lease_timeout_seconds_must_be_positive_int")
    if descriptor.command_id not in ALLOWED_LOCAL_RUNNER_COMMAND_IDS:
        raise ValueError("command_id_not_allowlisted")
    for field, value in (
        ("run_id", descriptor.run_id),
        ("approval_artifact_ref", descriptor.approval_artifact_ref),
        ("token_id", descriptor.token_id),
        ("token_receipt_ref", descriptor.token_receipt_ref),
        ("runner_receipt_ref", descriptor.runner_receipt_ref),
    ):
        if value and not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if descriptor.runner_policy_id != REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID:
        raise ValueError("runner_policy_id_mismatch")
    if descriptor.token_integration_status != TOKEN_INTEGRATION_STATUS_WAITING:
        raise ValueError("token_integration_status_must_wait_for_token_merge")
    _parse_time(descriptor.created_at)


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not strict_nonempty_string(value):
        raise ValueError(field_name + "_required")
    return str(value)


def _optional_string(
    payload: Mapping[str, object],
    field_name: str,
    default: str = "",
) -> str:
    value = payload.get(field_name, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(field_name + "_must_be_string")
    return value


def _optional_int(
    payload: Mapping[str, object],
    field_name: str,
    default: int,
) -> int:
    value = payload.get(field_name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(field_name + "_must_be_int")
    return value


def _lease_id(job_id: str, worker_id: str, attempt: int, leased_at: str) -> str:
    return "lease_" + _digest_payload(
        {
            "attempt": attempt,
            "job_id": job_id,
            "leased_at": leased_at,
            "worker_id": worker_id,
        }
    ).split(":", 1)[1][:24]


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("timestamp_must_be_nonempty_string")
    _parse_time(value)
    return value


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError("timestamp_must_be_isoformat") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _add_seconds(value: str, seconds: int) -> str:
    return (_parse_time(value) + timedelta(seconds=seconds)).isoformat()


def _digest_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
