"""Deterministic idempotency guard foundation.

This module provides a pure, side-effect-free idempotency validator that
ensures operations with the same idempotency_key and operation_digest are
detected as duplicate-safe, while operations with the same key but different
digest are rejected.

No provider calls, no network, no SQLite, no file mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

__all__ = [
    "IdempotencyGuard",
    "IdempotencyReceipt",
    "IdempotencyRejection",
    "validate_idempotency",
]

_FORBIDDEN_FIELDS: tuple[str, ...] = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
)


class IdempotencyRejection(ValueError):
    """Raised when idempotency input violates a policy boundary."""


@dataclass(frozen=True)
class IdempotencyReceipt:
    """Deterministic receipt produced by the idempotency validator."""

    idempotency_key: str
    operation_digest: str
    accepted: bool
    duplicate_safe: bool
    reasons: tuple[str, ...]
    policy_version: str
    code_version: str

    def as_dict(self) -> dict[str, object]:
        return {
            "idempotency_key": self.idempotency_key,
            "operation_digest": self.operation_digest,
            "accepted": self.accepted,
            "duplicate_safe": self.duplicate_safe,
            "reasons": list(self.reasons),
            "policy_version": self.policy_version,
            "code_version": self.code_version,
        }


def validate_idempotency(payload: Mapping[str, object]) -> IdempotencyReceipt:
    """Pure validation of an idempotency request against policy boundaries.

    Returns an IdempotencyReceipt with accepted=True if:
    - No forbidden fields present
    - idempotency_key is a non-empty string
    - operation_digest is a non-empty string with sha256: prefix

    When accepted, duplicate_safe is always False for the pure validator
    (the caller tracks actual duplicate detection via IdempotencyGuard).
    """
    failures: list[str] = []

    # Gate 1: forbidden fields
    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    idempotency_key = payload.get("idempotency_key")
    operation_digest = payload.get("operation_digest")
    policy_version = str(payload.get("policy_version", ""))
    code_version = str(payload.get("code_version", ""))

    # Gate 2: idempotency_key required, non-empty string
    if idempotency_key is None or not isinstance(idempotency_key, str) or not idempotency_key:
        failures.append("idempotency_key_required_nonempty_string")

    # Gate 3: operation_digest required, non-empty string
    if operation_digest is None or not isinstance(operation_digest, str) or not operation_digest:
        failures.append("operation_digest_required_nonempty_string")

    # Gate 4: operation_digest must start with sha256:
    if isinstance(operation_digest, str) and operation_digest and not operation_digest.startswith("sha256:"):
        failures.append("operation_digest_must_be_sha256_prefixed")

    if failures:
        return IdempotencyReceipt(
            idempotency_key=str(idempotency_key) if idempotency_key is not None else "",
            operation_digest=str(operation_digest) if operation_digest is not None else "",
            accepted=False,
            duplicate_safe=False,
            reasons=tuple(failures),
            policy_version=policy_version,
            code_version=code_version,
        )

    return IdempotencyReceipt(
        idempotency_key=str(idempotency_key),
        operation_digest=str(operation_digest),
        accepted=True,
        duplicate_safe=False,
        reasons=(),
        policy_version=policy_version,
        code_version=code_version,
    )


@dataclass
class IdempotencyGuard:
    """Stateful idempotency guard that tracks seen operations.

    Uses in-memory tracking (no SQLite, no file mutation). Given the same
    sequence of operations, the same guard state is produced.
    """

    _seen: dict[str, str] = field(default_factory=dict)

    def check(self, payload: Mapping[str, object]) -> IdempotencyReceipt:
        """Check an operation for idempotency.

        If the idempotency_key has been seen before with a matching digest,
        returns accepted=True with duplicate_safe=True.
        If seen with a different digest, returns accepted=False.
        If not seen, records it and returns accepted=True, duplicate_safe=False.
        """
        if not isinstance(payload, Mapping):
            return IdempotencyReceipt(
                idempotency_key="",
                operation_digest="",
                accepted=False,
                duplicate_safe=False,
                reasons=("input_must_be_mapping",),
                policy_version="",
                code_version="",
            )

        # Run pure validation first
        receipt = validate_idempotency(payload)
        if not receipt.accepted:
            return receipt

        key = receipt.idempotency_key
        digest = receipt.operation_digest

        if key in self._seen:
            if self._seen[key] == digest:
                return IdempotencyReceipt(
                    idempotency_key=key,
                    operation_digest=digest,
                    accepted=True,
                    duplicate_safe=True,
                    reasons=(),
                    policy_version=receipt.policy_version,
                    code_version=receipt.code_version,
                )
            else:
                return IdempotencyReceipt(
                    idempotency_key=key,
                    operation_digest=digest,
                    accepted=False,
                    duplicate_safe=False,
                    reasons=("idempotency_key_digest_mismatch",),
                    policy_version=receipt.policy_version,
                    code_version=receipt.code_version,
                )

        # First time seeing this key — record and accept
        self._seen[key] = digest
        return receipt

    def seen_count(self) -> int:
        """Return the number of unique idempotency keys seen."""
        return len(self._seen)
