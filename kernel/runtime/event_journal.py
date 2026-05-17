"""Deterministic append-only event journal descriptor foundation.

This module provides an in-memory append-only event journal that enforces:
- deterministic event records via frozen descriptors
- logical_sequence ordering with duplicate detection
- stage regression detection using a canonical stage order
- digest refs only (payload_digest must be sha256: prefixed)
- forbidden field rejection (raw_prompt, raw_provider_response, secret_value, env_value)
- required field validation
- all validation functions are pure and side-effect free
- no SQLite, no provider calls, no network access, no file mutation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

__all__ = [
    "EventJournal",
    "JournalAppendResult",
    "JournalEvent",
    "JournalRejection",
    "validate_event_record",
]

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
)

_REQUIRED_FIELDS = (
    "event_id",
    "run_id",
    "task_id",
    "stage",
    "event_type",
    "logical_sequence",
    "payload_digest",
)

_STRING_FIELDS = (
    "event_id",
    "run_id",
    "task_id",
    "stage",
    "event_type",
    "payload_digest",
)

# Canonical stage ordering for stage regression detection.
# Lower index = earlier stage. Events must not regress to an earlier stage.
_STAGE_ORDER: tuple[str, ...] = (
    "dry_run",
    "context",
    "inference",
    "patch_proposal",
    "validation",
    "review",
    "approval",
    "revision_seal",
    "evidence",
)
_STAGE_INDEX: dict[str, int] = {s: i for i, s in enumerate(_STAGE_ORDER)}


class JournalRejection(ValueError):
    """Raised when a journal operation violates a policy boundary."""


@dataclass(frozen=True)
class JournalEvent:
    """Immutable event descriptor stored in the journal.

    All fields are digest refs only — no raw content is stored.
    """

    event_id: str
    run_id: str
    task_id: str
    stage: str
    event_type: str
    logical_sequence: int
    payload_digest: str

    def as_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "stage": self.stage,
            "event_type": self.event_type,
            "logical_sequence": self.logical_sequence,
            "payload_digest": self.payload_digest,
        }


@dataclass(frozen=True)
class JournalAppendResult:
    """Result of an append operation.

    When accepted is False, event is None and failures contains the reasons.
    When accepted is True, event is the stored JournalEvent and failures is empty.
    """

    accepted: bool
    failures: tuple[str, ...]
    event: JournalEvent | None = None


def _stage_index(stage: str) -> int | None:
    """Return the canonical index of a stage, or None if unknown."""
    return _STAGE_INDEX.get(stage)


def validate_event_record(payload: Mapping[str, object]) -> tuple[str, ...]:
    """Pure validation of an event record against policy boundaries.

    Returns a tuple of failure messages. An empty tuple means valid.

    Checks (in order):
    1. Forbidden fields must be absent
    2. Required fields must be present
    3. String fields must be non-empty strings
    4. logical_sequence must be a non-negative integer
    5. payload_digest must start with "sha256:"
    6. stage must be a known legal stage
    """
    failures: list[str] = []

    # Gate 1: forbidden fields
    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    # Gate 2: required fields present
    for field in _REQUIRED_FIELDS:
        if field not in payload:
            failures.append(f"{field}_required")

    # Gate 3: string fields must be non-empty strings
    for field in _STRING_FIELDS:
        if field in payload:
            value = payload[field]
            if not isinstance(value, str) or not value:
                failures.append(f"{field}_must_be_nonempty_string")

    # Gate 4: logical_sequence must be a non-negative integer
    if "logical_sequence" in payload:
        seq = payload["logical_sequence"]
        if not isinstance(seq, int) or isinstance(seq, bool):
            failures.append("logical_sequence_must_be_int")
        elif seq < 0:
            failures.append("logical_sequence_must_be_nonnegative")

    # Gate 5: payload_digest format
    if "payload_digest" in payload:
        digest = payload["payload_digest"]
        if isinstance(digest, str) and digest and not str(digest).startswith("sha256:"):
            failures.append("payload_digest_must_be_sha256_prefixed")

    # Gate 6: stage must be legal
    if "stage" in payload:
        stage = payload["stage"]
        if isinstance(stage, str) and stage and _stage_index(str(stage)) is None:
            failures.append("stage_not_legal")

    return tuple(failures)


@dataclass
class EventJournal:
    """Append-only in-memory event journal.

    Stores immutable JournalEvent descriptors. All mutating operations are
    deterministic: given the same sequence of appends, the same journal state
    is produced.

    Tracks logical_sequence per run to detect duplicates, and tracks the last
    stage per run to detect illegal regression.
    """

    _events: list[JournalEvent] = field(default_factory=list)
    _seen_sequences_by_run: dict[str, set[int]] = field(default_factory=dict)
    _max_sequence_by_run: dict[str, int] = field(default_factory=dict)
    _last_stage_by_run: dict[str, str] = field(default_factory=dict)

    @property
    def events(self) -> tuple[JournalEvent, ...]:
        """Return a snapshot of all stored events as an immutable tuple."""
        return tuple(self._events)

    def append(self, payload: Mapping[str, object]) -> JournalAppendResult:
        """Validate and append an event to the journal.

        The append is atomic: if validation fails, no state is mutated.

        Returns a JournalAppendResult with the stored JournalEvent on success
        or failures on rejection.
        """
        if not isinstance(payload, Mapping):
            return JournalAppendResult(
                False, ("event_must_be_mapping",), None
            )

        failures: list[str] = list(validate_event_record(payload))

        # If basic validation already failed, stop here.
        if failures:
            return JournalAppendResult(False, tuple(failures), None)

        # Extract fields now that we know they're valid.
        event_id = str(payload["event_id"])
        run_id = str(payload["run_id"])
        task_id = str(payload["task_id"])
        stage = str(payload["stage"])
        event_type = str(payload["event_type"])
        logical_sequence = int(payload["logical_sequence"])
        payload_digest = str(payload["payload_digest"])

        # Duplicate logical_sequence check (per run).
        if run_id not in self._seen_sequences_by_run:
            self._seen_sequences_by_run[run_id] = set()
            self._max_sequence_by_run[run_id] = -1
        if logical_sequence in self._seen_sequences_by_run[run_id]:
            failures.append("duplicate_logical_sequence")

        # Sequence regression check (per run) — reject lower than max seen.
        if run_id in self._max_sequence_by_run:
            if logical_sequence < self._max_sequence_by_run[run_id]:
                failures.append("sequence_regression")

        # Stage regression check (per run).
        current_index = _stage_index(stage)
        if run_id in self._last_stage_by_run:
            last_stage = self._last_stage_by_run[run_id]
            last_index = _stage_index(last_stage)
            if last_index is not None and current_index is not None and current_index < last_index:
                failures.append("stage_regression")

        if failures:
            return JournalAppendResult(False, tuple(failures), None)

        # All checks passed — append.
        event = JournalEvent(
            event_id=event_id,
            run_id=run_id,
            task_id=task_id,
            stage=stage,
            event_type=event_type,
            logical_sequence=logical_sequence,
            payload_digest=payload_digest,
        )
        self._events.append(event)
        self._seen_sequences_by_run[run_id].add(logical_sequence)
        if logical_sequence > self._max_sequence_by_run.get(run_id, -1):
            self._max_sequence_by_run[run_id] = logical_sequence
        self._last_stage_by_run[run_id] = stage

        return JournalAppendResult(True, (), event)

    def event_count(self) -> int:
        """Return the number of events in the journal."""
        return len(self._events)
