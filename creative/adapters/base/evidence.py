"""Evidence helpers for adapters."""

from __future__ import annotations

from creative.common import stable_id

def build_adapter_evidence(adapter: str, operation: str, refs: list[str] | None = None) -> dict[str, object]:
    refs = refs or []
    return {
        "id": stable_id("EVD", adapter, operation, ",".join(refs)),
        "adapter": adapter,
        "operation": operation,
        "evidence_refs": refs,
        "raw_private_payload_stored": False,
    }
