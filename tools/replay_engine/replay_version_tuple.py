"""Replay version tuple — validates policy, code, and environment versions.

All three components must be present and non-empty. The version tuple is
immutable once validated.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class ReplayVersionTuple:
    """Immutable version tuple binding policy, code, and environment versions."""

    tuple_id: str
    policy_version: str
    code_version: str
    environment_fingerprint: str
    is_valid: bool
    canonical_hash: str

    @staticmethod
    def create(
        policy_version: str,
        code_version: str,
        environment_fingerprint: str,
    ) -> ReplayVersionTuple:
        is_valid = all(
            isinstance(v, str) and len(v.strip()) > 0
            for v in (policy_version, code_version, environment_fingerprint)
        )
        if not is_valid:
            return ReplayVersionTuple(
                tuple_id="",
                policy_version=policy_version or "",
                code_version=code_version or "",
                environment_fingerprint=environment_fingerprint or "",
                is_valid=False,
                canonical_hash="",
            )

        raw = "|".join([policy_version, code_version, environment_fingerprint])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        tuple_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return ReplayVersionTuple(
            tuple_id=tuple_id,
            policy_version=policy_version,
            code_version=code_version,
            environment_fingerprint=environment_fingerprint,
            is_valid=True,
            canonical_hash=canonical,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
