"""Conservative license metadata inference for asset records."""

from __future__ import annotations

def infer_license(record: dict[str, object]) -> dict[str, object]:
    public_asset = bool(record.get("public_asset"))
    return {
        "license_status": "public_fixture" if public_asset else "unknown_private_by_default",
        "commercial_use": "unknown" if not public_asset else "allowed_for_fixture_demo",
        "commit_allowed": public_asset,
        "notes": "Real asset licenses require human verification before publication.",
    }
