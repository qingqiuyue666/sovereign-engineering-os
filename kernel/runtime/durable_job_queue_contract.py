"""Durable job queue contract V1.

This module freezes the event envelope and replay projection rules for the
future durable job queue. It is contract-only and performs no execution,
storage writes, scheduling, networking, or background work.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

__all__ = [
    "DURABLE_JOB_QUEUE_CONTRACT_VERSION",
    "DURABLE_JOB_QUEUE_REPLAY_POLICY_VERSION",
    "DURABLE_QUEUE_EVENT_TYPES",
    "DURABLE_QUEUE_TERMINAL_STATES",
    "DurableQueueEvent",
    "DurableQueueJobState",
    "DurableQueueProjection",
    "compute_durable_queue_event_hash",
    "compute_durable_queue_projection_hash",
    "project_durable_queue_events",
    "validate_durable_queue_event",
]

DURABLE_JOB_QUEUE_CONTRACT_VERSION = "durable_job_queue_contract_v1"
DURABLE_JOB_QUEUE_REPLAY_POLICY_VERSION = "durable_job_queue_replay_policy_v1"

DURABLE_QUEUE_EVENT_TYPES = frozenset(
    {
        "JOB_SUBMITTED",
        "JOB_QUEUED",
        "JOB_LEASED",
        "JOB_HEARTBEAT",
        "JOB_SUCCEEDED",
        "JOB_FAILED_RETRYABLE",
        "JOB_FAILED_TERMINAL",
        "JOB_CANCELLATION_REQUESTED",
        "JOB_CANCELLED",
        "JOB_DEAD_LETTERED",
    }
)

DURABLE_QUEUE_TERMINAL_STATES = frozenset(
    {"succeeded", "failed", "cancelled", "dead_lettered"}
)

_EVENT_TO_STATE = {
    "JOB_SUBMITTED": "submitted",
    "JOB_QUEUED": "queued",
    "JOB_LEASED": "leased",
    "JOB_HEARTBEAT": "leased",
    "JOB_SUCCEEDED": "succeeded",
    "JOB_FAILED_RETRYABLE": "queued",
    "JOB_FAILED_TERMINAL": "failed",
    "JOB_CANCELLATION_REQUESTED": "cancellation_requested",
    "JOB_CANCELLED": "cancelled",
    "JOB_DEAD_LETTERED": "dead_lettered",
}

_ALLOWED_TRANSITIONS = {
    None: frozenset({"JOB_SUBMITTED"}),
    "submitted": frozenset({"JOB_QUEUED", "JOB_CANCELLATION_REQUESTED"}),
    "queued": frozenset({"JOB_LEASED", "JOB_CANCELLATION_REQUESTED"}),
    "leased": frozenset(
        {
            "JOB_HEARTBEAT",
            "JOB_SUCCEEDED",
            "JOB_FAILED_RETRYABLE",
            "JOB_FAILED_TERMINAL",
            "JOB_DEAD_LETTERED",
            "JOB_CANCELLATION_REQUESTED",
        }
    ),
    "cancellation_requested": frozenset({"JOB_CANCELLED"}),
}

_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "argv",
        "args",
        "command",
        "command_line",
        "cwd",
        "env",
        "environment",
        "executable",
        "path",
        "raw_log",
        "raw_stdout",
        "raw_stderr",
        "secret",
        "shell",
        "stderr",
        "stdout",
        "timeout",
    }
)


@dataclass(frozen=True)
class DurableQueueEvent:
    queue_event_id: str
    queue_contract_version: str
    sequence: int
    previous_event_hash: str | None
    event_type: str
    job_id: str
    task_id: str
    run_id: str
    worker_id: str
    idempotency_key_hash: str
    payload_hash: str
    attempt: int
    max_attempts: int
    lease_id: str
    lease_expires_at: str
    retry_after: str
    cancellation_requested: bool
    dead_letter_reason: str
    wal_record_hash: str
    human_invoked: bool
    occurred_at: str
    event_hash: str = ""

    def __post_init__(self) -> None:
        _require_nonempty_string(self.queue_event_id, "queue_event_id")
        if self.queue_contract_version != DURABLE_JOB_QUEUE_CONTRACT_VERSION:
            raise ValueError("queue_contract_version_invalid")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool):
            raise ValueError("sequence_must_be_int")
        if self.sequence <= 0:
            raise ValueError("sequence_must_be_positive")
        if self.previous_event_hash is not None:
            _require_sha256(self.previous_event_hash, "previous_event_hash")
        if self.event_type not in DURABLE_QUEUE_EVENT_TYPES:
            raise ValueError("event_type_invalid")
        for field_name in ("job_id", "task_id", "run_id", "occurred_at"):
            _require_nonempty_string(getattr(self, field_name), field_name)
        _require_string(self.worker_id, "worker_id")
        _require_string(self.lease_id, "lease_id")
        _require_string(self.lease_expires_at, "lease_expires_at")
        _require_string(self.retry_after, "retry_after")
        _require_string(self.dead_letter_reason, "dead_letter_reason")
        for field_name in ("idempotency_key_hash", "payload_hash", "wal_record_hash"):
            _require_sha256(getattr(self, field_name), field_name)
        if not isinstance(self.attempt, int) or isinstance(self.attempt, bool):
            raise ValueError("attempt_must_be_int")
        if self.attempt < 0:
            raise ValueError("attempt_must_be_nonnegative")
        if not isinstance(self.max_attempts, int) or isinstance(self.max_attempts, bool):
            raise ValueError("max_attempts_must_be_int")
        if self.max_attempts <= 0:
            raise ValueError("max_attempts_must_be_positive")
        if self.attempt > self.max_attempts:
            raise ValueError("attempt_exceeds_max_attempts")
        if not isinstance(self.cancellation_requested, bool):
            raise ValueError("cancellation_requested_must_be_bool")
        if not isinstance(self.human_invoked, bool):
            raise ValueError("human_invoked_must_be_bool")
        _validate_event_specific_fields(self)
        if self.event_hash:
            _require_sha256(self.event_hash, "event_hash")
        expected = compute_durable_queue_event_hash(self)
        if self.event_hash and self.event_hash != expected:
            raise ValueError("event_hash_mismatch")
        object.__setattr__(self, "event_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class DurableQueueJobState:
    job_id: str
    task_id: str
    run_id: str
    state: str
    attempt: int
    max_attempts: int
    lease_id: str
    retry_after: str
    cancellation_requested: bool
    dead_letter_reason: str
    last_event_hash: str

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class DurableQueueProjection:
    replay_policy_version: str
    accepted: bool
    rejection_reasons: tuple[str, ...]
    projected_jobs: tuple[DurableQueueJobState, ...]
    projection_hash: str = ""

    def __post_init__(self) -> None:
        if self.replay_policy_version != DURABLE_JOB_QUEUE_REPLAY_POLICY_VERSION:
            raise ValueError("replay_policy_version_invalid")
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted_must_be_bool")
        object.__setattr__(
            self,
            "rejection_reasons",
            _normalize_rejection_reasons(self.rejection_reasons),
        )
        object.__setattr__(
            self,
            "projected_jobs",
            tuple(sorted(self.projected_jobs, key=lambda job: job.job_id)),
        )
        if self.accepted and self.rejection_reasons:
            raise ValueError("accepted_projection_cannot_have_rejections")
        if not self.accepted and not self.rejection_reasons:
            raise ValueError("rejected_projection_requires_rejections")
        if self.projection_hash:
            _require_sha256(self.projection_hash, "projection_hash")
        expected = compute_durable_queue_projection_hash(self)
        if self.projection_hash and self.projection_hash != expected:
            raise ValueError("projection_hash_mismatch")
        object.__setattr__(self, "projection_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


def validate_durable_queue_event(
    event: DurableQueueEvent | Mapping[str, object],
    *,
    expected_sequence: int | None = None,
    expected_previous_event_hash: str | None | object = _FORBIDDEN_FIELD_NAMES,
) -> DurableQueueEvent:
    if isinstance(event, Mapping):
        _validate_mapping_keys(event)
        event = DurableQueueEvent(**dict(event))  # type: ignore[arg-type]
    if not isinstance(event, DurableQueueEvent):
        raise ValueError("event_must_be_durable_queue_event")
    if expected_sequence is not None and event.sequence != expected_sequence:
        raise ValueError("queue_sequence_gap_detected")
    if (
        expected_previous_event_hash is not _FORBIDDEN_FIELD_NAMES
        and event.previous_event_hash != expected_previous_event_hash
    ):
        raise ValueError("previous_event_hash_mismatch")
    if event.event_hash != compute_durable_queue_event_hash(event):
        raise ValueError("event_hash_mismatch")
    return event


def project_durable_queue_events(
    events: Sequence[DurableQueueEvent],
) -> DurableQueueProjection:
    failures: list[str] = []
    previous_event_hash: str | None = None
    expected_sequence = 1
    states: dict[str, DurableQueueJobState] = {}

    for event in events:
        failure_count_before_event = len(failures)
        try:
            validate_durable_queue_event(event)
        except ValueError as exc:
            failures.append(str(exc))
        if event.sequence != expected_sequence:
            failures.append("queue_sequence_gap_detected")
        if event.previous_event_hash != previous_event_hash:
            failures.append("previous_event_hash_mismatch")
        if len(failures) == failure_count_before_event:
            try:
                _apply_event(states, event)
            except ValueError as exc:
                failures.append(str(exc))
        previous_event_hash = event.event_hash
        expected_sequence += 1

    return DurableQueueProjection(
        replay_policy_version=DURABLE_JOB_QUEUE_REPLAY_POLICY_VERSION,
        accepted=not failures,
        rejection_reasons=tuple(_dedupe(failures)),
        projected_jobs=tuple(states.values()),
    )


def compute_durable_queue_event_hash(
    event: DurableQueueEvent | Mapping[str, object],
) -> str:
    data = _event_dict(event)
    data.pop("event_hash", None)
    data.pop("occurred_at", None)
    return _sha256(_canonical_json(data))


def compute_durable_queue_projection_hash(
    projection: DurableQueueProjection | Mapping[str, object],
) -> str:
    data = _projection_dict(projection)
    data.pop("projection_hash", None)
    return _sha256(_canonical_json(data))


def _apply_event(states: dict[str, DurableQueueJobState], event: DurableQueueEvent) -> None:
    current = states.get(event.job_id)
    current_state = current.state if current is not None else None
    allowed = _ALLOWED_TRANSITIONS.get(current_state, frozenset())
    if current_state in DURABLE_QUEUE_TERMINAL_STATES:
        raise ValueError("terminal_job_cannot_transition")
    if event.event_type not in allowed:
        raise ValueError("queue_transition_invalid")
    if current is not None and (
        current.task_id != event.task_id or current.run_id != event.run_id
    ):
        raise ValueError("job_identity_mismatch")
    if event.event_type == "JOB_FAILED_RETRYABLE" and event.attempt >= event.max_attempts:
        raise ValueError("retryable_failure_requires_remaining_attempts")
    states[event.job_id] = DurableQueueJobState(
        job_id=event.job_id,
        task_id=event.task_id,
        run_id=event.run_id,
        state=_EVENT_TO_STATE[event.event_type],
        attempt=event.attempt,
        max_attempts=event.max_attempts,
        lease_id=event.lease_id,
        retry_after=event.retry_after,
        cancellation_requested=event.cancellation_requested,
        dead_letter_reason=event.dead_letter_reason,
        last_event_hash=event.event_hash,
    )


def _validate_event_specific_fields(event: DurableQueueEvent) -> None:
    if event.event_type in {"JOB_LEASED", "JOB_HEARTBEAT"}:
        _require_nonempty_string(event.worker_id, "worker_id")
        _require_nonempty_string(event.lease_id, "lease_id")
        _require_nonempty_string(event.lease_expires_at, "lease_expires_at")
        if not event.human_invoked:
            raise ValueError("lease_event_requires_human_invoked")
    if event.event_type == "JOB_FAILED_RETRYABLE":
        _require_nonempty_string(event.retry_after, "retry_after")
    if event.event_type == "JOB_CANCELLATION_REQUESTED" and not event.cancellation_requested:
        raise ValueError("cancellation_event_requires_requested_flag")
    if event.event_type == "JOB_DEAD_LETTERED":
        _require_nonempty_string(event.dead_letter_reason, "dead_letter_reason")


def _validate_mapping_keys(payload: Mapping[str, object]) -> None:
    forbidden = sorted(
        str(key)
        for key in payload
        if str(key) in _FORBIDDEN_FIELD_NAMES or _SECRET_KEY_PATTERN.search(str(key))
    )
    if forbidden:
        raise ValueError("queue_event_field_forbidden:" + ",".join(forbidden))


def _event_dict(event: DurableQueueEvent | Mapping[str, object]) -> dict[str, object]:
    if isinstance(event, DurableQueueEvent):
        return event.as_dict()
    return _json_ready(dict(event))


def _projection_dict(projection: DurableQueueProjection | Mapping[str, object]) -> dict[str, object]:
    if isinstance(projection, DurableQueueProjection):
        return projection.as_dict()
    return _json_ready(dict(projection))


def _normalize_rejection_reasons(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("rejection_reasons_must_be_sequence")
    reasons = tuple(str(item) for item in value)
    for reason in reasons:
        _require_nonempty_string(reason, "rejection_reason")
    return tuple(_dedupe(reasons))


def _require_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise ValueError(field_name + "_must_be_string")


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(field_name + "_required")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(field_name + "_must_be_sha256")


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(_json_ready(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _json_ready(value: object) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return tuple(result)
