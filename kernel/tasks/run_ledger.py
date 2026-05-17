"""In-memory append-only run ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

__all__ = ["RunLedgerAppendResult", "InMemoryRunLedger"]

_REQUIRED = ("event_id", "run_id", "task_id", "stage", "event_type", "logical_time", "payload_digest")


@dataclass(frozen=True)
class RunLedgerAppendResult:
    accepted: bool
    failures: tuple[str, ...]


@dataclass
class InMemoryRunLedger:
    events: list[dict[str, object]] = field(default_factory=list)
    seen_event_ids: set[str] = field(default_factory=set)
    last_sequence_by_run: dict[str, int] = field(default_factory=dict)

    def append(self, event: Mapping[str, object]) -> RunLedgerAppendResult:
        if not isinstance(event, Mapping):
            return RunLedgerAppendResult(False, ("event_must_be_mapping",))
        failures: list[str] = []
        for field in _REQUIRED:
            if field not in event:
                failures.append(f"{field}_required")
        event_id = event.get("event_id")
        run_id = event.get("run_id")
        logical_time = event.get("logical_time")
        for field in ("event_id", "run_id", "task_id", "stage", "event_type", "payload_digest"):
            if field in event and (not isinstance(event.get(field), str) or not event.get(field)):
                failures.append(f"{field}_must_be_nonempty_string")
        if isinstance(event.get("payload_digest"), str) and not str(event["payload_digest"]).startswith("sha256:"):
            failures.append("payload_digest_required")
        if event_id in self.seen_event_ids:
            failures.append("duplicate_event_id")
        if not isinstance(logical_time, int):
            failures.append("logical_time_must_be_int")
        elif isinstance(run_id, str) and logical_time <= self.last_sequence_by_run.get(run_id, -1):
            failures.append("sequence_regression")
        if failures:
            return RunLedgerAppendResult(False, tuple(sorted(set(failures))))
        self.seen_event_ids.add(str(event_id))
        self.last_sequence_by_run[str(run_id)] = int(logical_time)
        self.events.append(dict(event))
        return RunLedgerAppendResult(True, ())
