"""contact_sheet report helper."""

from __future__ import annotations

def build_report(records: list[dict[str, object]] | None = None) -> dict[str, object]:
    records = records or []
    return {"ok": True, "report": "contact_sheet", "record_count": len(records), "private_payload_embedded": False}
