"""Append-only JSONL evidence ledger helpers."""

from __future__ import annotations

from pathlib import Path
import json
from creative.common import SCHEMA_VERSION, stable_id, utc_now

def evidence_record(kind: str, summary: str, refs: list[str] | None = None) -> dict[str, object]:
    refs = refs or []
    return {
        "schema_version": SCHEMA_VERSION,
        "id": stable_id("EVD", kind, summary, ",".join(refs)),
        "kind": kind,
        "summary": summary,
        "refs": refs,
        "created_at": utc_now(),
        "raw_private_payload_stored": False,
    }

def append_evidence(path: Path, record: dict[str, object]) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record

def load_ledger(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
