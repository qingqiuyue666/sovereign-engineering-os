"""Runtime spine canonical hash — deterministic hash generation for spine artifacts."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


class RuntimeSpineCanonicalHash:
    """Deterministic hash generation for runtime spine artifacts."""

    ALLOWED_ALGORITHMS = frozenset({"blake2b", "sha256", "sha512"})

    @staticmethod
    def canonical_hash(*parts: str, algorithm: str = "sha256") -> str:
        if algorithm not in RuntimeSpineCanonicalHash.ALLOWED_ALGORITHMS:
            raise ValueError(f"unsupported algorithm: {algorithm}")
        raw = "|".join(parts)
        h = hashlib.new(algorithm)
        h.update(raw.encode())
        return h.hexdigest()

    @staticmethod
    def chain_hash(link_hashes: List[str]) -> str:
        return RuntimeSpineCanonicalHash.canonical_hash(*link_hashes)

    @staticmethod
    def pair_hash(left: str, right: str) -> str:
        return RuntimeSpineCanonicalHash.canonical_hash(left, right)

    @staticmethod
    def spine_hash(pair_hashes: List[str]) -> str:
        return RuntimeSpineCanonicalHash.canonical_hash(*sorted(pair_hashes))
