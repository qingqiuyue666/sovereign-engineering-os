"""Runtime recovery canonical hash — deterministic hash generation for recovery artifacts."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


class RuntimeRecoveryCanonicalHash:
    """Deterministic hash generation for recovery artifacts."""

    ALLOWED_ALGORITHMS = frozenset({"blake2b", "sha256", "sha512"})

    @staticmethod
    def canonical_hash(*parts: str, algorithm: str = "sha256") -> str:
        if algorithm not in RuntimeRecoveryCanonicalHash.ALLOWED_ALGORITHMS:
            raise ValueError(f"unsupported algorithm: {algorithm}")
        raw = "|".join(parts)
        h = hashlib.new(algorithm)
        h.update(raw.encode())
        return h.hexdigest()

    @staticmethod
    def bundle_hash(failed_module: str, failure_codes: List[str]) -> str:
        return RuntimeRecoveryCanonicalHash.canonical_hash(
            failed_module, *sorted(failure_codes),
        )

    @staticmethod
    def plan_hash(bundle_id: str, steps: List[str]) -> str:
        return RuntimeRecoveryCanonicalHash.canonical_hash(bundle_id, *steps)

    @staticmethod
    def receipt_hash(bundle_id: str, plan_id: str, status: str) -> str:
        return RuntimeRecoveryCanonicalHash.canonical_hash(bundle_id, plan_id, status)
