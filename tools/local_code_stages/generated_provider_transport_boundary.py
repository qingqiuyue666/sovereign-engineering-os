
"""Generated bounded local-only provider transport boundary module.

v1 — contract-only. No real provider calls.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

KNOWN_PROVIDERS = frozenset({"mock-finance", "mock-market-data", "mock-news", "mock-weather"})
FORBIDDEN_PROVIDERS = frozenset({"live-broker", "live-exchange", "live-payment", "live-bank"})
REQUIRED_FIELDS = frozenset({"provider_id", "capability_token", "evidence_binding", "request_payload"})


@dataclass(frozen=True)
class ProviderTransportReceipt:
    receipt_id: str
    provider_id: str
    capability_token: str
    evidence_binding_present: bool
    status: str
    boundary_valid: bool
    preflight_passed: bool
    created_at: str
    module_version: str = "v1"
    no_provider_call: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_provider_transport_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    missing = REQUIRED_FIELDS - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    pid = payload["provider_id"]
    if pid in FORBIDDEN_PROVIDERS:
        raise ValueError(f"forbidden_provider: {pid}")
    if pid not in KNOWN_PROVIDERS:
        raise ValueError(f"unknown_provider: {pid}")
    if not isinstance(payload.get("request_payload"), dict):
        raise TypeError("request_payload must be a mapping")
    rp = payload["request_payload"]
    for forbidden in ("secret", "api_key", "token", "password", "credential"):
        if forbidden in str(rp).lower():
            raise ValueError(f"secret_material_detected: {forbidden}")
    return {"valid": True, "provider_id": pid}


def validate_provider_capability_boundary(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    token = payload.get("capability_token", "")
    valid = isinstance(token, str) and len(token) > 0
    return {"capability_valid": valid, "token_present": valid}


def validate_provider_transport_preflight(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    checks: Dict[str, bool] = {}
    checks["evidence_binding_present"] = bool(payload.get("evidence_binding"))
    checks["capability_token_present"] = bool(payload.get("capability_token"))
    checks["provider_known"] = payload.get("provider_id") in KNOWN_PROVIDERS
    checks["no_forbidden_provider"] = payload.get("provider_id") not in FORBIDDEN_PROVIDERS
    all_pass = all(checks.values())
    return {"preflight_passed": all_pass, "checks": checks}


def produce_provider_transport_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_provider_transport_request(payload)
    cap = validate_provider_capability_boundary(payload)
    preflight = validate_provider_transport_preflight(payload)
    receipt = ProviderTransportReceipt(
        receipt_id=_hash_id(payload.get("provider_id", "unknown"), _utcnow()),
        provider_id=payload.get("provider_id", "unknown"),
        capability_token=payload.get("capability_token", ""),
        evidence_binding_present=bool(payload.get("evidence_binding")),
        status="gated" if (preflight["preflight_passed"] and cap["capability_valid"]) else "rejected",
        boundary_valid=preflight["preflight_passed"],
        preflight_passed=preflight["preflight_passed"],
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "ProviderTransportReceipt",
    "validate_provider_transport_request",
    "validate_provider_capability_boundary",
    "validate_provider_transport_preflight",
    "produce_provider_transport_receipt",
]
