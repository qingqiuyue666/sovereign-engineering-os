"""Operator run canonical hash — deterministic hash generation for operator artifacts."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


class OperatorRunCanonicalHash:
    """Deterministic hash generation for operator daily run artifacts."""

    ALLOWED_ALGORITHMS = frozenset({"blake2b", "sha256", "sha512"})

    @staticmethod
    def canonical_hash(*parts: str, algorithm: str = "sha256") -> str:
        if algorithm not in OperatorRunCanonicalHash.ALLOWED_ALGORITHMS:
            raise ValueError(f"unsupported algorithm: {algorithm}")
        raw = "|".join(parts)
        h = hashlib.new(algorithm)
        h.update(raw.encode())
        return h.hexdigest()

    @staticmethod
    def run_hash(run_id: str, operator_id: str, evidence_hash: str, replay_hash: str) -> str:
        return OperatorRunCanonicalHash.canonical_hash(run_id, operator_id, evidence_hash, replay_hash)

    @staticmethod
    def receipt_hash(receipt_id: str, run_id: str, status: str) -> str:
        return OperatorRunCanonicalHash.canonical_hash(receipt_id, run_id, status)

    @staticmethod
    def gate_hash(human_review_id: str, approval_id: str) -> str:
        return OperatorRunCanonicalHash.canonical_hash(human_review_id, approval_id)
