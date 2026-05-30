"""Doctor report for local creative pipeline prerequisites."""

from __future__ import annotations

from creative.software.discovery import discover_software

def run_doctor() -> dict[str, object]:
    payload = discover_software()
    software = payload["software"]
    warnings = [
        name for name, entry in software.items()
        if entry.get("status") in {"NOT_FOUND", "CONFIG_REQUIRED"}
    ]
    return {
        **payload,
        "ok": True,
        "warnings": warnings,
        "summary": "Fixture-backed checks can run without DCC licenses; live DCC smoke tests require local installation.",
    }
