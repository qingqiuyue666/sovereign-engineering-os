"""Execution receipt — deterministic execution receipts.

Generates approval receipts, dry-run receipts, and failure receipts.
All receipts deterministic. No actual execution in v1.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class ExecutionReceipt:
    """Deterministic execution receipt. No actual execution performed."""

    receipt_id: str
    execution_id: str
    status: str
    category: str
    command_valid: bool
    preflight_passed: bool
    allowlist_validated: bool
    patch_receipt_hash: str
    canonical_hash: str
    created_at: str
    module_version: str = "v1"
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionFailureReceipt:
    """Deterministic execution failure receipt."""

    receipt_id: str
    execution_id: str
    failure_reason: str
    failure_code: str
    canonical_hash: str
    created_at: str
    module_version: str = "v1"
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _hash_id(*parts: str) -> str:
    return hashlib.blake2b("|".join(parts).encode(), digest_size=16).hexdigest()


def _hash64(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def produce_execution_receipt(
    execution_id: str,
    status: str,
    category: str,
    preflight_result: Dict[str, Any],
    patch_receipt_hash: str = "",
    created_at: str = "",
) -> ExecutionReceipt:
    if status not in ("approved", "rejected"):
        raise ValueError(f"invalid status: {status}")
    if patch_receipt_hash and not _hash64(patch_receipt_hash):
        raise ValueError("patch_receipt_hash must be sha256 hex when provided")

    raw = "|".join([
        execution_id, status, category,
        str(preflight_result.get("preflight_passed", False)),
        str(preflight_result.get("allowlist_valid", False)),
        patch_receipt_hash,
    ])
    canonical = hashlib.sha256(raw.encode()).hexdigest()
    receipt_id = _hash_id(execution_id, canonical)

    return ExecutionReceipt(
        receipt_id=receipt_id,
        execution_id=execution_id,
        status=status,
        category=category,
        command_valid=preflight_result.get("preflight_passed", False),
        preflight_passed=preflight_result.get("preflight_passed", False),
        allowlist_validated=preflight_result.get("allowlist_valid", False),
        patch_receipt_hash=patch_receipt_hash,
        canonical_hash=canonical,
        created_at=created_at or "1970-01-01T00:00:00Z",
    )


def produce_execution_failure_receipt(
    execution_id: str,
    failure_reason: str,
    failure_code: str,
    created_at: str = "",
) -> ExecutionFailureReceipt:
    if not failure_reason.strip():
        raise ValueError("failure_reason required")
    if not failure_code.strip():
        raise ValueError("failure_code required")

    raw = "|".join([execution_id, failure_reason, failure_code])
    canonical = hashlib.sha256(raw.encode()).hexdigest()
    receipt_id = _hash_id(execution_id, "failure", canonical)

    return ExecutionFailureReceipt(
        receipt_id=receipt_id,
        execution_id=execution_id,
        failure_reason=failure_reason,
        failure_code=failure_code,
        canonical_hash=canonical,
        created_at=created_at or "1970-01-01T00:00:00Z",
    )