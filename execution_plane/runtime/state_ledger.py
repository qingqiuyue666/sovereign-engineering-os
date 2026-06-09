"""Append-only runtime state ledger helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from creative.common import write_jsonl
from execution_plane.runner.result_envelope import utc_now

CANONICAL_STATES = (
    "CREATED",
    "VALIDATING",
    "QUEUED",
    "PREFLIGHTING",
    "PROVISIONING",
    "READY",
    "RUNNING",
    "COLLECTING",
    "SUCCEEDED",
    "FAILED",
    "TIMED_OUT",
    "CANCELED",
    "RETRYING",
    "PATCHING",
    "RERUNNING",
    "PACKAGING",
    "TERMINAL_SUCCEEDED",
    "TERMINAL_FAILED",
)


def state_event(*, run_id: str, adapter: str, state: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    if state not in CANONICAL_STATES:
        raise ValueError(f"unsupported runtime state:{state}")
    return {
        "schema_version": "seos.runtime_state_event.v1",
        "run_id": run_id,
        "adapter": adapter,
        "state": state,
        "recorded_at": utc_now(),
        "detail": dict(detail or {}),
    }


def append_state_events(path: Path, events: list[dict[str, Any]]) -> None:
    existing: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                import json

                existing.append(json.loads(line))
    write_jsonl(path, [*existing, *events])
