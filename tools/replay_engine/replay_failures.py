"""Replay failures — structured failure capture for replay operations.

Produces immutable failure records. Never includes raw payload data.
Evidence corruption and missing evidence binding trigger fail-closed behavior.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ReplayFailure:
    """Immutable replay failure record."""

    failure_id: str
    anchor_id: str
    failure_code: str
    failure_reason: str
    evidence_corrupted: bool
    fail_closed: bool
    canonical_hash: str

    @staticmethod
    def create(
        anchor_id: str,
        failure_code: str,
        failure_reason: str,
        *,
        evidence_corrupted: bool = False,
    ) -> "ReplayFailure":
        if not isinstance(anchor_id, str):
            raise ValueError("anchor_id must be a string")
        if not failure_code.strip():
            raise ValueError("failure_code required")
        if not failure_reason.strip():
            raise ValueError("failure_reason required")

        valid_codes = {
            "REPLAY_ANCHOR_INVALID", "REPLAY_SNAPSHOT_MISSING",
            "REPLAY_VERSION_MISMATCH", "REPLAY_MODE_INVALID",
            "REPLAY_EVIDENCE_CORRUPTED", "REPLAY_NONDETERMINISTIC",
            "REPLAY_CLOUD_REQUERY", "REPLAY_GATE_FAILED",
            "REPLAY_BINDING_INVALID", "REPLAY_INPUT_CORRUPTED",
            "REPLAY_EVIDENCE_BINDING_MISSING",
            "REPLAY_EVIDENCE_VAULT_BINDING_FAILED",
        }
        if failure_code not in valid_codes:
            raise ValueError(f"invalid failure_code: {failure_code}")

        fail_closed = evidence_corrupted or failure_code in (
            "REPLAY_EVIDENCE_CORRUPTED",
            "REPLAY_INPUT_CORRUPTED",
            "REPLAY_EVIDENCE_BINDING_MISSING",
            "REPLAY_EVIDENCE_VAULT_BINDING_FAILED",
        )
        raw = "|".join([anchor_id, failure_code, failure_reason, str(evidence_corrupted)])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        failure_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return ReplayFailure(
            failure_id=failure_id,
            anchor_id=anchor_id,
            failure_code=failure_code,
            failure_reason=failure_reason,
            evidence_corrupted=evidence_corrupted,
            fail_closed=fail_closed,
            canonical_hash=canonical,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReplayFailures:
    """Registry of replay failures with aggregate reporting."""

    def __init__(self) -> None:
        self._failures: list[ReplayFailure] = []

    def record(self, failure: ReplayFailure) -> None:
        self._failures.append(failure)

    def has_failures(self) -> bool:
        return len(self._failures) > 0

    def fail_closed(self) -> bool:
        return any(f.fail_closed for f in self._failures)

    def aggregate_hash(self) -> str:
        if not self._failures:
            return hashlib.sha256(b"no_failures").hexdigest()
        parts = [f.canonical_hash for f in self._failures]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_count": len(self._failures),
            "fail_closed": self.fail_closed(),
            "failures": [f.to_dict() for f in self._failures],
            "aggregate_hash": self.aggregate_hash(),
        }
