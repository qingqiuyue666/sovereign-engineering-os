"""License guard for public demo assets."""

from __future__ import annotations

def commit_allowed(license_payload: dict[str, object]) -> bool:
    return license_payload.get("license_status") == "public_fixture"
