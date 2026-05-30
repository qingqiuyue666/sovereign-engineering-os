"""zbrush handoff_checklist contract helpers."""

from __future__ import annotations

from creative.common import SCHEMA_VERSION, stable_id

def build_manifest(payload: dict[str, object] | None = None) -> dict[str, object]:
    payload = payload or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "id": stable_id("JOB", "zbrush", "handoff_checklist", payload.get("name", "fixture")),
        "adapter": "zbrush",
        "component": "handoff_checklist",
        "payload": payload,
        "dry_run": True,
        "execute_performed": False,
    }
