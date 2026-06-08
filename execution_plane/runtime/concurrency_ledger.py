"""Concurrency ledger records for run scheduling."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from creative.common import write_jsonl
from execution_plane.runner.result_envelope import utc_now


def concurrency_event(*, job_id: str, adapter: str, event: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "seos.concurrency_event.v1",
        "job_id": job_id,
        "adapter": adapter,
        "event": event,
        "recorded_at": utc_now(),
        "detail": dict(detail or {}),
    }


def write_concurrency_ledger(path: Path, events: list[dict[str, Any]]) -> None:
    write_jsonl(path, events)
