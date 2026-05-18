"""Replay canonical hash — deterministic hash generation for replay artifacts.

Uses blake2b and sha256. No wall-clock time. No random nonce.
No raw payload content in hash inputs.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


class ReplayCanonicalHash:
    """Deterministic hash generation for replay artifacts."""

    ALLOWED_ALGORITHMS = frozenset({"blake2b", "sha256", "sha512"})

    @staticmethod
    def canonical_hash(*parts: str, algorithm: str = "sha256") -> str:
        """Deterministic hash from ordered string parts."""
        if algorithm not in ReplayCanonicalHash.ALLOWED_ALGORITHMS:
            raise ValueError(f"unsupported algorithm: {algorithm}")
        raw = "|".join(parts)
        h = hashlib.new(algorithm)
        h.update(raw.encode())
        return h.hexdigest()

    @staticmethod
    def canonical_hash_dict(data: Dict[str, Any], algorithm: str = "sha256") -> str:
        """Deterministic hash from sorted dict entries."""
        parts = [f"{k}={v}" for k, v in sorted(data.items())]
        return ReplayCanonicalHash.canonical_hash(*parts, algorithm=algorithm)

    @staticmethod
    def canonical_hash_list(items: List[str], algorithm: str = "sha256") -> str:
        """Deterministic hash from sorted list."""
        return ReplayCanonicalHash.canonical_hash(*sorted(items), algorithm=algorithm)

    @staticmethod
    def anchor_canonical_hash(
        input_snapshot_hash: str,
        policy_version: str,
        code_version: str,
        environment_fingerprint: str,
    ) -> str:
        return ReplayCanonicalHash.canonical_hash(
            input_snapshot_hash, policy_version, code_version, environment_fingerprint,
        )

    @staticmethod
    def receipt_canonical_hash(
        receipt_id: str,
        anchor_id: str,
        status: str,
        mode: str,
    ) -> str:
        return ReplayCanonicalHash.canonical_hash(receipt_id, anchor_id, status, mode)

    @staticmethod
    def mismatch_report_hash(mismatch_hashes: List[str]) -> str:
        return ReplayCanonicalHash.canonical_hash(*sorted(mismatch_hashes))
