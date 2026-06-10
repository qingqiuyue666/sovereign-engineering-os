"""Replay report helpers."""

from __future__ import annotations

def build_replay_report(ledger_rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "can_replay": bool(ledger_rows),
        "event_count": len(ledger_rows),
        "missing_refs": [],
        "replay_mode": "metadata_only",
    }
