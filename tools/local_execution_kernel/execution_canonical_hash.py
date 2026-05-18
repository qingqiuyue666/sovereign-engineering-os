"""Execution canonical hash — deterministic hash generation for execution artifacts."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


class ExecutionCanonicalHash:
    """Deterministic hash generation for execution artifacts."""

    ALLOWED_ALGORITHMS = frozenset({"blake2b", "sha256", "sha512"})

    @staticmethod
    def canonical_hash(*parts: str, algorithm: str = "sha256") -> str:
        if algorithm not in ExecutionCanonicalHash.ALLOWED_ALGORITHMS:
            raise ValueError(f"unsupported algorithm: {algorithm}")
        raw = "|".join(parts)
        h = hashlib.new(algorithm)
        h.update(raw.encode())
        return h.hexdigest()

    @staticmethod
    def request_hash(execution_id: str, category: str, first_token: str) -> str:
        return ExecutionCanonicalHash.canonical_hash(execution_id, category, first_token)

    @staticmethod
    def receipt_hash(receipt_id: str, execution_id: str, status: str) -> str:
        return ExecutionCanonicalHash.canonical_hash(receipt_id, execution_id, status)

    @staticmethod
    def allowlist_hash(allowed_commands: List[str]) -> str:
        return ExecutionCanonicalHash.canonical_hash(*sorted(allowed_commands))
