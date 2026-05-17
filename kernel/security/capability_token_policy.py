"""Capability token metadata validation only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping
import json

from .secret_scanner import CoreSecretScanner

__all__ = ["CapabilityTokenResult", "validate_capability_token_metadata"]


@dataclass(frozen=True)
class CapabilityTokenResult:
    accepted: bool
    failures: tuple[str, ...]


def validate_capability_token_metadata(
    token: Mapping[str, object],
    *,
    requested_action: str,
    now: datetime | None = None,
    scanner: CoreSecretScanner | None = None,
) -> CapabilityTokenResult:
    if not isinstance(token, Mapping):
        return CapabilityTokenResult(False, ("token_must_be_mapping",))
    failures: list[str] = []
    scopes = token.get("scope")
    if not isinstance(scopes, list) or not scopes or not all(isinstance(scope, str) and scope for scope in scopes):
        failures.append("scope_required")
        scope_values: list[str] = []
    else:
        scope_values = list(scopes)
    if "*" in scope_values:
        failures.append("wildcard_scope_forbidden")
    if requested_action not in scope_values:
        failures.append("unauthorized_action")
    expires_at = token.get("expires_at")
    try:
        expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except Exception:
        failures.append("expires_at_invalid")
        expiry = None
    if expiry is not None:
        active_now = now or datetime.now(timezone.utc)
        if expiry <= active_now:
            failures.append("token_expired")
    serialized = json.dumps(token, sort_keys=True, default=str)
    scan = (scanner or CoreSecretScanner()).scan_text(serialized, path="capability_token_metadata")
    if not scan.clean or any(key in token for key in ("secret", "secret_value", "api_key", "token_value")):
        failures.append("secret_material_forbidden")
    return CapabilityTokenResult(not failures, tuple(sorted(set(failures))))
