"""zbrush export_manifest contract helpers."""

from __future__ import annotations

from creative.common import SCHEMA_VERSION, stable_id

def build_manifest(payload: dict[str, object] | None = None) -> dict[str, object]:
    payload = payload or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "id": stable_id("JOB", "zbrush", "export_manifest", payload.get("name", "fixture")),
        "adapter": "zbrush",
        "component": "export_manifest",
        "payload": payload,
        "dry_run": True,
        "execute_performed": False,
    }
