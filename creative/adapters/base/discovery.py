"""Base discovery helpers."""

from __future__ import annotations

from creative.software.discovery import discover_software

def adapter_discovery_status(adapter_name: str) -> dict[str, object]:
    return dict(discover_software()["software"].get(adapter_name, {"status": "ADAPTER_UNSUPPORTED"}))
