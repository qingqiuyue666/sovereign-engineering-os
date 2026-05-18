"""Provider request contract — validates incoming provider transport requests.

Enforces: provider_id, request_id, capability_token, evidence_binding,
dry_run=true, live_mode=false, network_mode=false. Rejects raw payloads,
secrets, .env markers, and forbidden providers/capabilities.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Mapping

from tools.provider_transport.provider_adapter_registry import (
    FORBIDDEN_CAPABILITIES,
    FORBIDDEN_PROVIDERS,
    KNOWN_CAPABILITIES,
    KNOWN_PROVIDERS,
)

REQUIRED_REQUEST_FIELDS: FrozenSet[str] = frozenset({
    "provider_id",
    "request_id",
    "capability_token",
    "evidence_binding",
    "dry_run",
    "live_mode",
    "network_mode",
})

SECRET_MARKERS: FrozenSet[str] = frozenset({
    "secret", "api_key", "token", "password", "credential",
    "private_key", "access_key", "authorization",
})

ENV_MARKERS: FrozenSet[str] = frozenset({
    ".env", "dotenv", "environ", "os.environ", "getenv",
})

RAW_PAYLOAD_FIELDS: FrozenSet[str] = frozenset({
    "raw_payload", "raw_response", "raw_data", "raw_request",
    "payload", "full_response",
})


@dataclass(frozen=True)
class ProviderRequestContract:
    """Immutable validated provider request."""
    provider_id: str
    request_id: str
    capability_token: str
    evidence_binding: str
    dry_run: bool
    live_mode: bool
    network_mode: bool
    request_digest: str
    capabilities: FrozenSet[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "request_id": self.request_id,
            "capability_token": self.capability_token,
            "evidence_binding": self.evidence_binding,
            "dry_run": self.dry_run,
            "live_mode": self.live_mode,
            "network_mode": self.network_mode,
            "request_digest": self.request_digest,
            "capabilities": sorted(self.capabilities),
        }


def _scan_for_secrets(payload: dict) -> list[str]:
    """Scan payload string values for secret/environment markers."""
    hits: list[str] = []
    for key, value in payload.items():
        if isinstance(value, str):
            lower_val = value.lower()
            for marker in SECRET_MARKERS:
                if marker in lower_val:
                    hits.append(f"secret_marker_detected:{key}:{marker}")
            for marker in ENV_MARKERS:
                if marker in lower_val:
                    hits.append(f"env_marker_detected:{key}:{marker}")
    return hits


def validate_provider_request(payload: Any) -> Dict[str, Any]:
    """Validate a raw provider request payload.

    Returns a dict with 'valid', 'contract' (ProviderRequestContract if valid),
    and 'failures' (tuple of failure strings).
    """
    failures: list[str] = []

    if not isinstance(payload, Mapping):
        return {"valid": False, "contract": None, "failures": ("payload_must_be_mapping",)}

    p = dict(payload)

    # Check required fields
    missing = REQUIRED_REQUEST_FIELDS - set(p.keys())
    for m in sorted(missing):
        failures.append(f"missing_required_field: {m}")

    # Check for raw payload fields
    for rpf in RAW_PAYLOAD_FIELDS:
        if rpf in p:
            failures.append(f"raw_payload_field_rejected: {rpf}")

    # provider_id validation (type/emptiness first, then membership)
    pid = p.get("provider_id")
    if not isinstance(pid, str) or not pid.strip():
        failures.append("provider_id_must_be_nonempty_string")
    elif pid in FORBIDDEN_PROVIDERS:
        failures.append(f"forbidden_provider_rejected: {pid}")
    elif pid not in KNOWN_PROVIDERS:
        failures.append(f"unknown_provider_rejected: {pid}")

    # request_id validation
    rid = p.get("request_id")
    if not isinstance(rid, str) or not rid.strip():
        failures.append("request_id_must_be_nonempty_string")

    # capability_token validation
    cap_token = p.get("capability_token")
    if not isinstance(cap_token, str) or not cap_token.strip():
        failures.append("capability_token_must_be_nonempty_string")
    elif isinstance(cap_token, str):
        cap_list = [c.strip() for c in cap_token.split(",") if c.strip()]
        for cap in cap_list:
            if cap in FORBIDDEN_CAPABILITIES:
                failures.append(f"forbidden_capability_requested: {cap}")

    # evidence_binding validation
    ev = p.get("evidence_binding")
    if not ev or not isinstance(ev, str) or not ev.strip():
        failures.append("evidence_binding_required")

    # dry_run must be True
    dry_run = p.get("dry_run")
    if dry_run is not True:
        if dry_run is False:
            failures.append("dry_run_must_be_true")
        elif not isinstance(dry_run, bool):
            failures.append("dry_run_must_be_bool")

    # live_mode must be False
    live_mode = p.get("live_mode")
    if live_mode is not False:
        if live_mode is True:
            failures.append("live_mode_must_be_false")
        elif not isinstance(live_mode, bool):
            failures.append("live_mode_must_be_bool")

    # network_mode must be False
    network_mode = p.get("network_mode")
    if network_mode is not False:
        if network_mode is True:
            failures.append("network_mode_must_be_false")
        elif not isinstance(network_mode, bool):
            failures.append("network_mode_must_be_bool")

    # Scan for secret/env markers in all string values
    failures.extend(_scan_for_secrets(p))

    if failures:
        return {"valid": False, "contract": None, "failures": tuple(failures)}

    # Parse capabilities from token
    capabilities: FrozenSet[str] = frozenset()
    if isinstance(cap_token, str):
        capabilities = frozenset(
            c.strip() for c in cap_token.split(",") if c.strip()
        )

    # Build request digest (deterministic, no wall-clock)
    digest_parts = [
        f"pid={pid}",
        f"rid={rid}",
        f"cap={','.join(sorted(capabilities))}",
        f"ev={ev}",
        "dry_run=true",
        "live_mode=false",
        "network_mode=false",
    ]
    request_digest = hashlib.sha256("|".join(digest_parts).encode()).hexdigest()

    contract = ProviderRequestContract(
        provider_id=str(pid),
        request_id=str(rid),
        capability_token=str(cap_token),
        evidence_binding=str(ev),
        dry_run=True,
        live_mode=False,
        network_mode=False,
        request_digest=request_digest,
        capabilities=capabilities,
    )

    return {"valid": True, "contract": contract, "failures": ()}
