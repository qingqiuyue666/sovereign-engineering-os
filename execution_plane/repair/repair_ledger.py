"""Append-only patch repair ledger."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import json

from execution_plane.runner.result_envelope import utc_now


def append_repair_event(root: str | Path, event: Mapping[str, Any]) -> dict[str, Any]:
    ledger_root = Path(root)
    ledger_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "seos.patch_repair_ledger_event.v1",
        "recorded_at": utc_now(),
        **dict(event),
    }
    with (ledger_root / "repair_ledger.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return payload


def read_repair_ledger(root: str | Path = "work/repair_jobs") -> list[dict[str, Any]]:
    path = Path(root) / "repair_ledger.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
