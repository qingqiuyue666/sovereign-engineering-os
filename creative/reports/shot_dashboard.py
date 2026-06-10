"""shot_dashboard report helper."""

from __future__ import annotations

def build_report(records: list[dict[str, object]] | None = None) -> dict[str, object]:
    records = records or []
    return {"ok": True, "report": "shot_dashboard", "record_count": len(records), "private_payload_embedded": False}
