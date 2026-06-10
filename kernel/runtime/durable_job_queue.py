"""Durable local job queue implementation V1.

The queue is an append-only JSONL store over the V1 durable queue contract. It
does not execute jobs, start worker loops, or open network surfaces. Every
queue event is bound to the local real WAL storage backend before the queue
record is appended.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from kernel.runtime.durable_job_queue_contract import (
    DURABLE_JOB_QUEUE_CONTRACT_VERSION,
    DURABLE_JOB_QUEUE_REPLAY_POLICY_VERSION,
    DurableQueueEvent,
    DurableQueueJobState,
    DurableQueueProjection,
    project_durable_queue_events,
    validate_durable_queue_event,
)
from kernel.stores.real_wal_storage import (
    FileBackedRealWalStorage,
    RealWalStorageError,
)

__all__ = [
    "DURABLE_JOB_QUEUE_IMPLEMENTATION_VERSION",
    "REAL_WAL_BINDING_STATUS",
    "DurableJobQueue",
    "DurableJobQueueError",
    "DurableJobQueueDuplicateError",
    "DurableJobQueueReplayError",
    "DurableJobQueueRecord",
    "DurableJobQueueTransitionError",
    "RealWalBindingStatus",
    "compute_record_hash",
]

DURABLE_JOB_QUEUE_IMPLEMENTATION_VERSION = "durable_job_queue_implementation_v1"
REAL_WAL_BINDING_STATUS = "real_wal_storage_backend_v1_bound"

_QUEUE_RECORD_VERSION = "durable_job_queue_record_v1"
_PREFLIGHT_WAL_RECORD_HASH = "sha256:" + ("0" * 64)
_QUEUE_RECORD_KEYS = frozenset(
    {
        "event",
        "payload",
        "queue_id",
        "queue_record_version",
        "real_wal_binding_status",
        "record_hash",
    }
)
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)\bsk-[a-z0-9]{20,}"),
    re.compile(
        r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"
    ),
)
_FORBIDDEN_PAYLOAD_FIELDS = frozenset(
    {
        "argv",
        "args",
        "command",
        "command_line",
        "cwd",
        "env",
        "environment",
        "executable",
        "executable_path",
        "network",
        "path",
        "raw_log",
        "raw_stderr",
        "raw_stdout",
        "shell",
        "stderr",
        "stdout",
        "subprocess",
        "timeout",
        "url",
    }
)
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class DurableJobQueueError(RuntimeError):
    """Base exception for durable queue implementation failures."""


class DurableJobQueueReplayError(DurableJobQueueError):
    """Raised when persisted records cannot be replayed safely."""


class DurableJobQueueTransitionError(DurableJobQueueError):
    """Raised when a requested lifecycle transition is invalid."""


class DurableJobQueueDuplicateError(DurableJobQueueError):
    """Raised when duplicate job or idempotency material conflicts."""


@dataclass(frozen=True)
class RealWalBindingStatus:
    available: bool
    blocker: str
    binding_mode: str
    wal_path: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DurableJobQueueRecord:
    queue_record_version: str
    queue_id: str
    event: DurableQueueEvent
    payload: dict[str, object]
    real_wal_binding_status: str
    record_hash: str = ""

    def __post_init__(self) -> None:
        if self.queue_record_version != _QUEUE_RECORD_VERSION:
            raise DurableJobQueueReplayError("queue_record_version_invalid")
        _require_nonempty_string(self.queue_id, "queue_id")
        if not isinstance(self.event, DurableQueueEvent):
            raise DurableJobQueueReplayError("event_must_be_durable_queue_event")
        payload = _normalize_json_mapping(self.payload, "payload")
        object.__setattr__(self, "payload", payload)
        if _sha256_json(payload) != self.event.payload_hash:
            raise DurableJobQueueReplayError("payload_hash_mismatch")
        if self.real_wal_binding_status != REAL_WAL_BINDING_STATUS:
            raise DurableJobQueueReplayError("real_wal_binding_status_invalid")
        if self.record_hash:
            _require_sha256(self.record_hash, "record_hash")
        expected = compute_record_hash(self)
        if self.record_hash and self.record_hash != expected:
            raise DurableJobQueueReplayError("record_hash_mismatch")
        object.__setattr__(self, "record_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return {
            "event": self.event.as_dict(),
            "payload": self.payload,
            "queue_id": self.queue_id,
            "queue_record_version": self.queue_record_version,
            "real_wal_binding_status": self.real_wal_binding_status,
            "record_hash": self.record_hash,
        }


@dataclass(frozen=True)
class _JobMetadata:
    job_id: str
    task_id: str
    run_id: str
    idempotency_key_hash: str
    submit_payload_hash: str
    max_attempts: int
    priority: int


class DurableJobQueue:
    """Append-only durable queue with explicit, human-invoked transitions."""

    def __init__(
        self,
        *,
        path: str | Path,
        queue_id: str,
        wal_path: str | Path | None = None,
    ) -> None:
        if not _nonempty_string(queue_id):
            raise DurableJobQueueError("queue_id_required")
        self.path = _validate_store_path(Path(path))
        self.wal_path = _validate_store_path(
            Path(wal_path) if wal_path is not None else _default_wal_path(self.path)
        )
        if self.wal_path == self.path:
            raise DurableJobQueueError("wal_path_must_be_distinct_from_queue_path")
        self.queue_id = queue_id
        self._records: tuple[DurableJobQueueRecord, ...] = ()
        self._projection = DurableQueueProjection(
            replay_policy_version=DURABLE_JOB_QUEUE_REPLAY_POLICY_VERSION,
            accepted=True,
            rejection_reasons=(),
            projected_jobs=(),
        )
        self._metadata_by_job: dict[str, _JobMetadata] = {}
        self._idempotency_index: dict[str, _JobMetadata] = {}
        self._reload()

    @property
    def records(self) -> tuple[DurableJobQueueRecord, ...]:
        self._reload()
        return self._records

    @property
    def events(self) -> tuple[DurableQueueEvent, ...]:
        self._reload()
        return tuple(record.event for record in self._records)

    @property
    def projection(self) -> DurableQueueProjection:
        self._reload()
        return self._projection

    def wal_binding_status(self) -> RealWalBindingStatus:
        return RealWalBindingStatus(
            available=True,
            blocker="",
            binding_mode="file_backed_real_wal_storage_queue_event_binding_v1",
            wal_path=str(self.wal_path),
        )

    def submit_job(
        self,
        *,
        job_id: str,
        task_id: str,
        run_id: str,
        payload: Mapping[str, object],
        idempotency_key: str,
        max_attempts: int = 1,
        priority: int = 100,
        submitted_at: str | None = None,
    ) -> DurableQueueJobState:
        _require_nonempty_string(job_id, "job_id")
        _require_nonempty_string(task_id, "task_id")
        _require_nonempty_string(run_id, "run_id")
        _require_nonempty_string(idempotency_key, "idempotency_key")
        if not isinstance(max_attempts, int) or isinstance(max_attempts, bool):
            raise DurableJobQueueError("max_attempts_must_be_int")
        if max_attempts <= 0:
            raise DurableJobQueueError("max_attempts_must_be_positive")
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise DurableJobQueueError("priority_must_be_int")

        job_payload = _normalize_json_mapping(payload, "payload")
        event_payload = {
            "job_payload": job_payload,
            "max_attempts": max_attempts,
            "priority": priority,
        }
        idempotency_key_hash = _sha256_text("idempotency:" + idempotency_key)
        payload_hash = _sha256_json(event_payload)
        self._reload()
        existing = self._idempotency_index.get(idempotency_key_hash)
        if existing is not None:
            if (
                existing.job_id == job_id
                and existing.task_id == task_id
                and existing.run_id == run_id
                and existing.submit_payload_hash == payload_hash
                and existing.max_attempts == max_attempts
                and existing.priority == priority
            ):
                return self.get_job_state(job_id)
            raise DurableJobQueueDuplicateError("idempotency_key_conflict")
        if job_id in self._metadata_by_job:
            raise DurableJobQueueDuplicateError("duplicate_job_id")

        record = self._append_event(
            event_type="JOB_SUBMITTED",
            job_id=job_id,
            task_id=task_id,
            run_id=run_id,
            idempotency_key_hash=idempotency_key_hash,
            payload=event_payload,
            attempt=0,
            max_attempts=max_attempts,
            occurred_at=submitted_at,
        )
        return self.get_job_state(record.event.job_id)

    def queue_job(
        self,
        job_id: str,
        *,
        queued_at: str | None = None,
    ) -> DurableQueueJobState:
        state = self._require_state(job_id, {"submitted"})
        metadata = self._require_metadata(job_id)
        self._append_event(
            event_type="JOB_QUEUED",
            job_id=job_id,
            task_id=state.task_id,
            run_id=state.run_id,
            idempotency_key_hash=metadata.idempotency_key_hash,
            payload={"queued": True},
            attempt=state.attempt,
            max_attempts=state.max_attempts,
            occurred_at=queued_at,
        )
        return self.get_job_state(job_id)

    def lease_next(
        self,
        *,
        worker_id: str,
        leased_at: str | None = None,
        lease_timeout_seconds: int = 60,
    ) -> DurableQueueJobState:
        _require_nonempty_string(worker_id, "worker_id")
        if not isinstance(lease_timeout_seconds, int) or isinstance(
            lease_timeout_seconds, bool
        ):
            raise DurableJobQueueError("lease_timeout_seconds_must_be_int")
        if lease_timeout_seconds <= 0:
            raise DurableJobQueueError("lease_timeout_seconds_must_be_positive")
        self._reload()
        queued = [
            state
            for state in self._projection.projected_jobs
            if state.state == "queued"
        ]
        if not queued:
            raise DurableJobQueueTransitionError("no_queued_jobs")
        selected = sorted(
            queued,
            key=lambda state: (
                self._require_metadata(state.job_id).priority,
                self._first_sequence_for_job(state.job_id),
                state.job_id,
            ),
        )[0]
        metadata = self._require_metadata(selected.job_id)
        now = _timestamp(leased_at)
        attempt = selected.attempt + 1
        lease_id = _lease_id(selected.job_id, worker_id, attempt, now)
        expires_at = _add_seconds(now, lease_timeout_seconds)
        self._append_event(
            event_type="JOB_LEASED",
            job_id=selected.job_id,
            task_id=selected.task_id,
            run_id=selected.run_id,
            idempotency_key_hash=metadata.idempotency_key_hash,
            payload={
                "lease_id": lease_id,
                "lease_timeout_seconds": lease_timeout_seconds,
                "worker_id": worker_id,
            },
            attempt=attempt,
            max_attempts=selected.max_attempts,
            worker_id=worker_id,
            lease_id=lease_id,
            lease_expires_at=expires_at,
            occurred_at=now,
        )
        return self.get_job_state(selected.job_id)

    def heartbeat(
        self,
        *,
        job_id: str,
        lease_id: str,
        heartbeat_at: str | None = None,
        lease_timeout_seconds: int = 60,
    ) -> DurableQueueJobState:
        state = self._require_leased(job_id, lease_id)
        metadata = self._require_metadata(job_id)
        now = _timestamp(heartbeat_at)
        expires_at = _add_seconds(now, lease_timeout_seconds)
        self._append_event(
            event_type="JOB_HEARTBEAT",
            job_id=job_id,
            task_id=state.task_id,
            run_id=state.run_id,
            idempotency_key_hash=metadata.idempotency_key_hash,
            payload={
                "lease_id": lease_id,
                "lease_timeout_seconds": lease_timeout_seconds,
                "worker_id": self._worker_id_for_lease(job_id, lease_id),
            },
            attempt=state.attempt,
            max_attempts=state.max_attempts,
            worker_id=self._worker_id_for_lease(job_id, lease_id),
            lease_id=lease_id,
            lease_expires_at=expires_at,
            occurred_at=now,
        )
        return self.get_job_state(job_id)

    def succeed_job(
        self,
        *,
        job_id: str,
        lease_id: str,
        completion_payload: Mapping[str, object] | None = None,
        succeeded_at: str | None = None,
    ) -> DurableQueueJobState:
        state = self._require_leased(job_id, lease_id)
        metadata = self._require_metadata(job_id)
        payload = _normalize_json_mapping(completion_payload or {"succeeded": True}, "payload")
        self._append_event(
            event_type="JOB_SUCCEEDED",
            job_id=job_id,
            task_id=state.task_id,
            run_id=state.run_id,
            idempotency_key_hash=metadata.idempotency_key_hash,
            payload=payload,
            attempt=state.attempt,
            max_attempts=state.max_attempts,
            lease_id=lease_id,
            occurred_at=succeeded_at,
        )
        return self.get_job_state(job_id)

    def fail_job(
        self,
        *,
        job_id: str,
        lease_id: str,
        reason: str,
        failed_at: str | None = None,
        retry_after: str | None = None,
        dead_letter_on_exhaustion: bool = True,
    ) -> DurableQueueJobState:
        _require_nonempty_string(reason, "reason")
        state = self._require_leased(job_id, lease_id)
        metadata = self._require_metadata(job_id)
        now = _timestamp(failed_at)
        if state.attempt < state.max_attempts:
            event_type = "JOB_FAILED_RETRYABLE"
            retry_at = _timestamp(retry_after or now)
            dead_letter_reason = ""
            payload = {"failure_reason": reason, "retry_after": retry_at}
        elif dead_letter_on_exhaustion:
            event_type = "JOB_DEAD_LETTERED"
            retry_at = ""
            dead_letter_reason = reason
            payload = {"dead_letter_reason": reason}
        else:
            event_type = "JOB_FAILED_TERMINAL"
            retry_at = ""
            dead_letter_reason = ""
            payload = {"failure_reason": reason}
        self._append_event(
            event_type=event_type,
            job_id=job_id,
            task_id=state.task_id,
            run_id=state.run_id,
            idempotency_key_hash=metadata.idempotency_key_hash,
            payload=payload,
            attempt=state.attempt,
            max_attempts=state.max_attempts,
            lease_id=lease_id,
            retry_after=retry_at,
            dead_letter_reason=dead_letter_reason,
            occurred_at=now,
        )
        return self.get_job_state(job_id)

    def request_cancellation(
        self,
        job_id: str,
        *,
        reason: str,
        requested_at: str | None = None,
    ) -> DurableQueueJobState:
        _require_nonempty_string(reason, "reason")
        state = self._require_state(job_id, {"submitted", "queued", "leased"})
        metadata = self._require_metadata(job_id)
        self._append_event(
            event_type="JOB_CANCELLATION_REQUESTED",
            job_id=job_id,
            task_id=state.task_id,
            run_id=state.run_id,
            idempotency_key_hash=metadata.idempotency_key_hash,
            payload={"cancellation_reason": reason},
            attempt=state.attempt,
            max_attempts=state.max_attempts,
            cancellation_requested=True,
            occurred_at=requested_at,
        )
        return self.get_job_state(job_id)

    def cancel_job(
        self,
        job_id: str,
        *,
        reason: str,
        cancelled_at: str | None = None,
    ) -> DurableQueueJobState:
        _require_nonempty_string(reason, "reason")
        state = self._require_state(job_id, {"cancellation_requested"})
        metadata = self._require_metadata(job_id)
        self._append_event(
            event_type="JOB_CANCELLED",
            job_id=job_id,
            task_id=state.task_id,
            run_id=state.run_id,
            idempotency_key_hash=metadata.idempotency_key_hash,
            payload={"cancellation_reason": reason},
            attempt=state.attempt,
            max_attempts=state.max_attempts,
            cancellation_requested=True,
            occurred_at=cancelled_at,
        )
        return self.get_job_state(job_id)

    def recover_expired_leases(
        self,
        *,
        now: str | None = None,
        retry_after: str | None = None,
    ) -> tuple[DurableQueueJobState, ...]:
        current_time = _parse_time(_timestamp(now))
        recovered: list[DurableQueueJobState] = []
        self._reload()
        leased = [
            state
            for state in self._projection.projected_jobs
            if state.state == "leased"
        ]
        for state in sorted(leased, key=lambda item: item.job_id):
            lease_event = self._latest_lease_event(state.job_id, state.lease_id)
            if not lease_event.lease_expires_at:
                raise DurableJobQueueReplayError("leased_job_missing_expiry")
            if _parse_time(lease_event.lease_expires_at) > current_time:
                continue
            recovered.append(
                self.fail_job(
                    job_id=state.job_id,
                    lease_id=state.lease_id,
                    reason="lease_expired_without_heartbeat",
                    failed_at=_format_time(current_time),
                    retry_after=retry_after or _format_time(current_time),
                )
            )
        return tuple(recovered)

    def get_job_state(self, job_id: str) -> DurableQueueJobState:
        self._reload()
        for state in self._projection.projected_jobs:
            if state.job_id == job_id:
                return state
        raise DurableJobQueueTransitionError("unknown_job_id")

    def list_job_states(self) -> tuple[DurableQueueJobState, ...]:
        self._reload()
        return self._projection.projected_jobs

    def summary(self) -> dict[str, object]:
        self._reload()
        counts: dict[str, int] = {}
        for state in self._projection.projected_jobs:
            counts[state.state] = counts.get(state.state, 0) + 1
        return {
            "accepted": self._projection.accepted,
            "event_count": len(self._records),
            "job_count": len(self._projection.projected_jobs),
            "queue_id": self.queue_id,
            "real_wal_binding_status": REAL_WAL_BINDING_STATUS,
            "real_wal_path": str(self.wal_path),
            "state_counts": dict(sorted(counts.items())),
        }

    def _append_event(
        self,
        *,
        event_type: str,
        job_id: str,
        task_id: str,
        run_id: str,
        idempotency_key_hash: str,
        payload: Mapping[str, object],
        attempt: int,
        max_attempts: int,
        occurred_at: str | None = None,
        worker_id: str = "",
        lease_id: str = "",
        lease_expires_at: str = "",
        retry_after: str = "",
        cancellation_requested: bool = False,
        dead_letter_reason: str = "",
    ) -> DurableJobQueueRecord:
        safe_payload = _normalize_json_mapping(payload, "payload")
        occurred = _timestamp(occurred_at)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                handle.seek(0)
                records = _records_from_text(handle.read(), queue_id=self.queue_id)
                projection = project_durable_queue_events(
                    tuple(record.event for record in records)
                )
                if not projection.accepted:
                    raise DurableJobQueueReplayError(
                        "stored_queue_replay_rejected:"
                        + ",".join(projection.rejection_reasons)
                    )
                _verify_real_wal_bindings(
                    records,
                    wal_path=self.wal_path,
                    queue_id=self.queue_id,
                )
                sequence = len(records) + 1
                previous_hash = records[-1].event.event_hash if records else None
                payload_hash = _sha256_json(safe_payload)
                preflight_event = _build_queue_event(
                    queue_id=self.queue_id,
                    sequence=sequence,
                    previous_event_hash=previous_hash,
                    event_type=event_type,
                    job_id=job_id,
                    task_id=task_id,
                    run_id=run_id,
                    worker_id=worker_id,
                    idempotency_key_hash=idempotency_key_hash,
                    payload_hash=payload_hash,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    lease_id=lease_id,
                    lease_expires_at=lease_expires_at,
                    retry_after=retry_after,
                    cancellation_requested=cancellation_requested,
                    dead_letter_reason=dead_letter_reason,
                    wal_record_hash=_PREFLIGHT_WAL_RECORD_HASH,
                    occurred_at=occurred,
                )
                preflight_candidate = DurableJobQueueRecord(
                    queue_record_version=_QUEUE_RECORD_VERSION,
                    queue_id=self.queue_id,
                    event=preflight_event,
                    payload=dict(safe_payload),
                    real_wal_binding_status=REAL_WAL_BINDING_STATUS,
                )
                candidate_projection = project_durable_queue_events(
                    tuple(record.event for record in (*records, preflight_candidate))
                )
                if not candidate_projection.accepted:
                    raise DurableJobQueueTransitionError(
                        "queue_transition_rejected:"
                        + ",".join(candidate_projection.rejection_reasons)
                    )
                _metadata_from_records((*records, preflight_candidate))
                wal_record_hash = self._append_real_wal_event(
                    queue_id=self.queue_id,
                    sequence=sequence,
                    previous_event_hash=previous_hash,
                    event_type=event_type,
                    job_id=job_id,
                    task_id=task_id,
                    run_id=run_id,
                    worker_id=worker_id,
                    idempotency_key_hash=idempotency_key_hash,
                    payload_hash=payload_hash,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    lease_id=lease_id,
                    lease_expires_at=lease_expires_at,
                    retry_after=retry_after,
                    cancellation_requested=cancellation_requested,
                    dead_letter_reason=dead_letter_reason,
                    occurred_at=occurred,
                )
                event = _build_queue_event(
                    queue_id=self.queue_id,
                    sequence=sequence,
                    previous_event_hash=previous_hash,
                    event_type=event_type,
                    job_id=job_id,
                    task_id=task_id,
                    run_id=run_id,
                    worker_id=worker_id,
                    idempotency_key_hash=idempotency_key_hash,
                    payload_hash=payload_hash,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    lease_id=lease_id,
                    lease_expires_at=lease_expires_at,
                    retry_after=retry_after,
                    cancellation_requested=cancellation_requested,
                    dead_letter_reason=dead_letter_reason,
                    wal_record_hash=wal_record_hash,
                    occurred_at=occurred,
                )
                candidate = DurableJobQueueRecord(
                    queue_record_version=_QUEUE_RECORD_VERSION,
                    queue_id=self.queue_id,
                    event=event,
                    payload=dict(safe_payload),
                    real_wal_binding_status=REAL_WAL_BINDING_STATUS,
                )
                candidate_projection = project_durable_queue_events(
                    tuple(record.event for record in (*records, candidate))
                )
                if not candidate_projection.accepted:
                    raise DurableJobQueueTransitionError(
                        "queue_transition_rejected:"
                        + ",".join(candidate_projection.rejection_reasons)
                    )
                _metadata_from_records((*records, candidate))
                handle.seek(0, os.SEEK_END)
                handle.write(_canonical_json(candidate.as_dict()))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        self._reload()
        return candidate

    def _append_real_wal_event(
        self,
        *,
        queue_id: str,
        sequence: int,
        previous_event_hash: str | None,
        event_type: str,
        job_id: str,
        task_id: str,
        run_id: str,
        worker_id: str,
        idempotency_key_hash: str,
        payload_hash: str,
        attempt: int,
        max_attempts: int,
        lease_id: str,
        lease_expires_at: str,
        retry_after: str,
        cancellation_requested: bool,
        dead_letter_reason: str,
        occurred_at: str,
    ) -> str:
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        material_hash = _queue_event_material_hash(
            queue_id=queue_id,
            sequence=sequence,
            previous_event_hash=previous_event_hash,
            event_type=event_type,
            job_id=job_id,
            task_id=task_id,
            run_id=run_id,
            worker_id=worker_id,
            idempotency_key_hash=idempotency_key_hash,
            payload_hash=payload_hash,
            attempt=attempt,
            max_attempts=max_attempts,
            lease_id=lease_id,
            lease_expires_at=lease_expires_at,
            retry_after=retry_after,
            cancellation_requested=cancellation_requested,
            dead_letter_reason=dead_letter_reason,
        )
        digest_bindings = {
            "queue_event_material_hash": material_hash,
            "queue_event_type_hash": _sha256_text("event_type:" + event_type),
            "queue_id_hash": _sha256_text("queue_id:" + queue_id),
            "queue_job_hash": _sha256_text("job_id:" + job_id),
        }
        if previous_event_hash is not None:
            digest_bindings["queue_previous_event_hash"] = previous_event_hash
        try:
            receipt = FileBackedRealWalStorage(self.wal_path).append(
                record_type="QUEUE_EVENT",
                task_id=task_id,
                run_id=run_id,
                payload_hash=payload_hash,
                digest_bindings=digest_bindings,
                created_at=occurred_at,
            )
        except RealWalStorageError as exc:
            raise DurableJobQueueReplayError(
                "real_wal_append_failed:" + str(exc)
            ) from exc
        return receipt.record_hash

    def _reload(self) -> None:
        records = _load_records(self.path, queue_id=self.queue_id)
        projection = project_durable_queue_events(tuple(record.event for record in records))
        if not projection.accepted:
            raise DurableJobQueueReplayError(
                "stored_queue_replay_rejected:" + ",".join(projection.rejection_reasons)
            )
        _verify_real_wal_bindings(records, wal_path=self.wal_path, queue_id=self.queue_id)
        metadata_by_job, idempotency_index = _metadata_from_records(records)
        self._records = records
        self._projection = projection
        self._metadata_by_job = metadata_by_job
        self._idempotency_index = idempotency_index

    def _require_state(
        self,
        job_id: str,
        allowed: set[str],
    ) -> DurableQueueJobState:
        state = self.get_job_state(job_id)
        if state.state not in allowed:
            raise DurableJobQueueTransitionError(
                "job_state_invalid:" + state.state
            )
        return state

    def _require_leased(self, job_id: str, lease_id: str) -> DurableQueueJobState:
        _require_nonempty_string(lease_id, "lease_id")
        state = self._require_state(job_id, {"leased"})
        if state.lease_id != lease_id:
            raise DurableJobQueueTransitionError("lease_id_mismatch")
        return state

    def _require_metadata(self, job_id: str) -> _JobMetadata:
        self._reload()
        metadata = self._metadata_by_job.get(job_id)
        if metadata is None:
            raise DurableJobQueueTransitionError("unknown_job_id")
        return metadata

    def _first_sequence_for_job(self, job_id: str) -> int:
        for record in self._records:
            if record.event.job_id == job_id:
                return record.event.sequence
        raise DurableJobQueueTransitionError("unknown_job_id")

    def _worker_id_for_lease(self, job_id: str, lease_id: str) -> str:
        return self._latest_lease_event(job_id, lease_id).worker_id

    def _latest_lease_event(self, job_id: str, lease_id: str) -> DurableQueueEvent:
        for record in reversed(self._records):
            event = record.event
            if event.job_id == job_id and event.lease_id == lease_id and event.worker_id:
                return event
        raise DurableJobQueueTransitionError("lease_worker_missing")


def compute_record_hash(record: DurableJobQueueRecord | Mapping[str, object]) -> str:
    if isinstance(record, DurableJobQueueRecord):
        payload = {
            "event": record.event.as_dict(),
            "payload": record.payload,
            "queue_id": record.queue_id,
            "queue_record_version": record.queue_record_version,
            "real_wal_binding_status": record.real_wal_binding_status,
        }
    else:
        payload = dict(record)
        payload.pop("record_hash", None)
    return _sha256_json(payload)


def _build_queue_event(
    *,
    queue_id: str,
    sequence: int,
    previous_event_hash: str | None,
    event_type: str,
    job_id: str,
    task_id: str,
    run_id: str,
    worker_id: str,
    idempotency_key_hash: str,
    payload_hash: str,
    attempt: int,
    max_attempts: int,
    lease_id: str,
    lease_expires_at: str,
    retry_after: str,
    cancellation_requested: bool,
    dead_letter_reason: str,
    wal_record_hash: str,
    occurred_at: str,
) -> DurableQueueEvent:
    return DurableQueueEvent(
        queue_event_id=f"{queue_id}:{sequence:06d}:{job_id}:{event_type}",
        queue_contract_version=DURABLE_JOB_QUEUE_CONTRACT_VERSION,
        sequence=sequence,
        previous_event_hash=previous_event_hash,
        event_type=event_type,
        job_id=job_id,
        task_id=task_id,
        run_id=run_id,
        worker_id=worker_id,
        idempotency_key_hash=idempotency_key_hash,
        payload_hash=payload_hash,
        attempt=attempt,
        max_attempts=max_attempts,
        lease_id=lease_id,
        lease_expires_at=lease_expires_at,
        retry_after=retry_after,
        cancellation_requested=cancellation_requested,
        dead_letter_reason=dead_letter_reason,
        wal_record_hash=wal_record_hash,
        human_invoked=True,
        occurred_at=occurred_at,
    )


def _verify_real_wal_bindings(
    records: Sequence[DurableJobQueueRecord],
    *,
    wal_path: Path,
    queue_id: str,
) -> None:
    if not records:
        return
    if not wal_path.exists():
        raise DurableJobQueueReplayError("real_wal_file_missing")
    if wal_path.is_symlink():
        raise DurableJobQueueReplayError("real_wal_path_is_symlink")
    try:
        wal_records = FileBackedRealWalStorage(wal_path).read_records()
    except RealWalStorageError as exc:
        raise DurableJobQueueReplayError("real_wal_replay_failed:" + str(exc)) from exc
    wal_by_hash = {record.record_hash: record for record in wal_records}
    for queue_record in records:
        event = queue_record.event
        wal_record = wal_by_hash.get(event.wal_record_hash)
        if wal_record is None:
            raise DurableJobQueueReplayError("real_wal_record_missing")
        if wal_record.record_type != "QUEUE_EVENT":
            raise DurableJobQueueReplayError("real_wal_record_type_mismatch")
        if wal_record.task_id != event.task_id or wal_record.run_id != event.run_id:
            raise DurableJobQueueReplayError("real_wal_identity_mismatch")
        if wal_record.payload_hash != event.payload_hash:
            raise DurableJobQueueReplayError("real_wal_payload_hash_mismatch")
        digest_bindings = dict(wal_record.digest_bindings)
        expected_material_hash = _queue_event_material_hash_from_event(
            event,
            queue_id=queue_id,
        )
        if digest_bindings.get("queue_event_material_hash") != expected_material_hash:
            raise DurableJobQueueReplayError("real_wal_material_hash_mismatch")


def _queue_event_material_hash_from_event(
    event: DurableQueueEvent,
    *,
    queue_id: str,
) -> str:
    return _queue_event_material_hash(
        queue_id=queue_id,
        sequence=event.sequence,
        previous_event_hash=event.previous_event_hash,
        event_type=event.event_type,
        job_id=event.job_id,
        task_id=event.task_id,
        run_id=event.run_id,
        worker_id=event.worker_id,
        idempotency_key_hash=event.idempotency_key_hash,
        payload_hash=event.payload_hash,
        attempt=event.attempt,
        max_attempts=event.max_attempts,
        lease_id=event.lease_id,
        lease_expires_at=event.lease_expires_at,
        retry_after=event.retry_after,
        cancellation_requested=event.cancellation_requested,
        dead_letter_reason=event.dead_letter_reason,
    )


def _queue_event_material_hash(
    *,
    queue_id: str,
    sequence: int,
    previous_event_hash: str | None,
    event_type: str,
    job_id: str,
    task_id: str,
    run_id: str,
    worker_id: str,
    idempotency_key_hash: str,
    payload_hash: str,
    attempt: int,
    max_attempts: int,
    lease_id: str,
    lease_expires_at: str,
    retry_after: str,
    cancellation_requested: bool,
    dead_letter_reason: str,
) -> str:
    return _sha256_json(
        {
            "attempt": attempt,
            "cancellation_requested": cancellation_requested,
            "dead_letter_reason": dead_letter_reason,
            "event_type": event_type,
            "human_invoked": True,
            "idempotency_key_hash": idempotency_key_hash,
            "job_id": job_id,
            "lease_expires_at": lease_expires_at,
            "lease_id": lease_id,
            "max_attempts": max_attempts,
            "payload_hash": payload_hash,
            "previous_event_hash": previous_event_hash,
            "queue_contract_version": DURABLE_JOB_QUEUE_CONTRACT_VERSION,
            "queue_id": queue_id,
            "retry_after": retry_after,
            "run_id": run_id,
            "sequence": sequence,
            "task_id": task_id,
            "worker_id": worker_id,
        }
    )


def _load_records(path: Path, *, queue_id: str) -> tuple[DurableJobQueueRecord, ...]:
    if not path.exists():
        return ()
    if path.is_dir():
        raise DurableJobQueueReplayError("queue_path_is_directory")
    if path.is_symlink():
        raise DurableJobQueueReplayError("queue_path_is_symlink")
    with path.open("r", encoding="utf-8") as handle:
        return _records_from_text(handle.read(), queue_id=queue_id)


def _records_from_text(text: str, *, queue_id: str) -> tuple[DurableJobQueueRecord, ...]:
    records: list[DurableJobQueueRecord] = []
    previous_hash: str | None = None
    for index, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DurableJobQueueReplayError(f"queue_record_line_{index}_invalid_json") from exc
        if not isinstance(raw, dict):
            raise DurableJobQueueReplayError(f"queue_record_line_{index}_must_be_object")
        if set(raw) != _QUEUE_RECORD_KEYS:
            raise DurableJobQueueReplayError(f"queue_record_line_{index}_keys_invalid")
        event_payload = raw.get("event")
        if not isinstance(event_payload, Mapping):
            raise DurableJobQueueReplayError(f"queue_record_line_{index}_event_required")
        event = validate_durable_queue_event(
            event_payload,
            expected_sequence=len(records) + 1,
            expected_previous_event_hash=previous_hash,
        )
        if raw.get("queue_id") != queue_id:
            raise DurableJobQueueReplayError("queue_id_mismatch")
        expected_event_id = f"{queue_id}:{event.sequence:06d}:{event.job_id}:{event.event_type}"
        if event.queue_event_id != expected_event_id:
            raise DurableJobQueueReplayError("queue_event_id_mismatch")
        record = DurableJobQueueRecord(
            queue_record_version=str(raw.get("queue_record_version", "")),
            queue_id=str(raw.get("queue_id", "")),
            event=event,
            payload=_record_payload(raw),
            real_wal_binding_status=str(raw.get("real_wal_binding_status", "")),
            record_hash=str(raw.get("record_hash", "")),
        )
        records.append(record)
        previous_hash = event.event_hash
    return tuple(records)


def _metadata_from_records(
    records: Sequence[DurableJobQueueRecord],
) -> tuple[dict[str, _JobMetadata], dict[str, _JobMetadata]]:
    metadata_by_job: dict[str, _JobMetadata] = {}
    idempotency_index: dict[str, _JobMetadata] = {}
    for record in records:
        event = record.event
        if event.event_type != "JOB_SUBMITTED":
            continue
        priority = _payload_int(record.payload, "priority")
        metadata = _JobMetadata(
            job_id=event.job_id,
            task_id=event.task_id,
            run_id=event.run_id,
            idempotency_key_hash=event.idempotency_key_hash,
            submit_payload_hash=event.payload_hash,
            max_attempts=event.max_attempts,
            priority=priority,
        )
        if event.job_id in metadata_by_job:
            raise DurableJobQueueReplayError("duplicate_job_id")
        if event.idempotency_key_hash in idempotency_index:
            raise DurableJobQueueReplayError("duplicate_idempotency_key_hash")
        metadata_by_job[event.job_id] = metadata
        idempotency_index[event.idempotency_key_hash] = metadata
    return metadata_by_job, idempotency_index


def _record_payload(raw: Mapping[str, object]) -> dict[str, object]:
    payload = raw.get("payload")
    if not isinstance(payload, Mapping):
        raise DurableJobQueueReplayError("payload_required")
    return _normalize_json_mapping(payload, "payload")


def _normalize_json_mapping(value: Mapping[str, object], field_name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise DurableJobQueueError(field_name + "_must_be_mapping")
    normalized = _json_ready(dict(value))
    if not isinstance(normalized, dict):
        raise DurableJobQueueError(field_name + "_must_be_mapping")
    _validate_safe_json(normalized)
    return normalized


def _validate_safe_json(value: object, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_PAYLOAD_FIELDS or _SECRET_KEY_PATTERN.search(key_text):
                raise DurableJobQueueError(
                    "queue_payload_field_forbidden:" + ".".join(path + (key_text,))
                )
            _validate_safe_json(item, path=path + (key_text,))
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_safe_json(item, path=path + (str(index),))
        return
    if isinstance(value, str):
        for pattern in _SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                raise DurableJobQueueError("queue_payload_secret_value_forbidden")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise DurableJobQueueError("queue_payload_type_forbidden:" + type(value).__name__)


def _json_ready(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise DurableJobQueueError("queue_payload_type_forbidden:" + type(value).__name__)


def _payload_int(payload: Mapping[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise DurableJobQueueReplayError(field_name + "_must_be_int")
    return value


def _lease_id(job_id: str, worker_id: str, attempt: int, leased_at: str) -> str:
    return "lease_" + _sha256_json(
        {
            "attempt": attempt,
            "job_id": job_id,
            "leased_at": leased_at,
            "worker_id": worker_id,
        }
    ).split(":", 1)[1][:24]


def _default_wal_path(path: Path) -> Path:
    return path.with_name(path.name + ".real-wal.jsonl")


def _validate_store_path(path: Path) -> Path:
    if not str(path):
        raise DurableJobQueueError("queue_path_required")
    resolved = path.expanduser().resolve(strict=False)
    if resolved.exists() and resolved.is_symlink():
        raise DurableJobQueueError("queue_path_is_symlink")
    if resolved.parent.exists() and resolved.parent.is_symlink():
        raise DurableJobQueueError("queue_parent_is_symlink")
    for part in resolved.parts:
        if part in {".env", ".env.local", ".envrc"}:
            raise DurableJobQueueError("queue_path_secret_like")
    return resolved


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
    if not _nonempty_string(value):
        raise DurableJobQueueError("timestamp_must_be_nonempty_string")
    _parse_time(value)
    return value


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise DurableJobQueueError("timestamp_must_be_isoformat") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _format_time(value: datetime) -> str:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.isoformat()


def _add_seconds(value: str, seconds: int) -> str:
    return (_parse_time(value) + timedelta(seconds=seconds)).isoformat()


def _canonical_json(payload: object) -> str:
    return json.dumps(_json_ready(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_json(payload: object) -> str:
    return _sha256_text(_canonical_json(payload))


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise DurableJobQueueReplayError(field_name + "_must_be_sha256")


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not _nonempty_string(value):
        raise DurableJobQueueError(field_name + "_required")


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)
