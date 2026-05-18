"""Patch receipt — deterministic dry-run patch receipts.

Generates approval receipts and failure receipts for patch validation.
All receipts are deterministic. No raw payload in receipts.
No actual patch application in v1.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class PatchReceipt:
    """Deterministic patch receipt. No raw payload."""

    receipt_id: str
    request_id: str
    patch_id: str
    target_path: str
    status: str
    preflight_passed: bool
    allowlist_valid: bool
    rollback_bundle_present: bool
    replay_receipt_hash: str
    canonical_hash: str
    created_at: str
    module_version: str = "v1"
    no_patch_application: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PatchFailureReceipt:
    """Deterministic patch failure receipt."""

    receipt_id: str
    request_id: str
    failure_reason: str
    failure_code: str
    canonical_hash: str
    created_at: str
    module_version: str = "v1"
    no_patch_application: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _hash_id(*parts: str) -> str:
    return hashlib.blake2b("|".join(parts).encode(), digest_size=16).hexdigest()


def _hash64(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def produce_patch_receipt(
    request: Any,
    preflight_result: Dict[str, bool],
    created_at: str = "",
) -> PatchReceipt:
    replay_receipt_hash = getattr(request, "replay_receipt_hash", "")
    if replay_receipt_hash and not _hash64(replay_receipt_hash):
        raise ValueError("replay_receipt_hash must be sha256 hex when provided")
    raw = "|".join([
        request.request_id, request.patch_id, request.target_path,
        str(preflight_result.get("preflight_passed", False)),
        str(request.rollback_bundle_hash), replay_receipt_hash,
    ])
    canonical = hashlib.sha256(raw.encode()).hexdigest()
    receipt_id = _hash_id(request.request_id, canonical)

    return PatchReceipt(
        receipt_id=receipt_id,
        request_id=request.request_id,
        patch_id=request.patch_id,
        target_path=request.target_path,
        status="approved" if preflight_result.get("preflight_passed", False) else "rejected",
        preflight_passed=preflight_result.get("preflight_passed", False),
        allowlist_valid=preflight_result.get("target_in_allowlist", False),
        rollback_bundle_present=bool(request.rollback_bundle_hash),
        replay_receipt_hash=replay_receipt_hash,
        canonical_hash=canonical,
        created_at=created_at or "1970-01-01T00:00:00Z",
    )


def produce_patch_failure_receipt(
    request_id: str,
    failure_reason: str,
    failure_code: str,
    created_at: str = "",
) -> PatchFailureReceipt:
    if not failure_reason.strip():
        raise ValueError("failure_reason required")
    if not failure_code.strip():
        raise ValueError("failure_code required")

    raw = "|".join([request_id, failure_reason, failure_code])
    canonical = hashlib.sha256(raw.encode()).hexdigest()
    receipt_id = _hash_id(request_id, "failure", canonical)

    return PatchFailureReceipt(
        receipt_id=receipt_id,
        request_id=request_id,
        failure_reason=failure_reason,
        failure_code=failure_code,
        canonical_hash=canonical,
        created_at=created_at or "1970-01-01T00:00:00Z",
    )
