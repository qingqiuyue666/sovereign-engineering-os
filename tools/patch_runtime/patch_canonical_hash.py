"""Patch canonical hash — deterministic hash generation for patch artifacts."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


class PatchCanonicalHash:
    """Deterministic hash generation for patch artifacts."""

    ALLOWED_ALGORITHMS = frozenset({"blake2b", "sha256", "sha512"})

    @staticmethod
    def canonical_hash(*parts: str, algorithm: str = "sha256") -> str:
        if algorithm not in PatchCanonicalHash.ALLOWED_ALGORITHMS:
            raise ValueError(f"unsupported algorithm: {algorithm}")
        raw = "|".join(parts)
        h = hashlib.new(algorithm)
        h.update(raw.encode())
        return h.hexdigest()

    @staticmethod
    def request_hash(patch_id: str, target_path: str, patch_content_hash: str, rollback_bundle_hash: str) -> str:
        return PatchCanonicalHash.canonical_hash(patch_id, target_path, patch_content_hash, rollback_bundle_hash)

    @staticmethod
    def receipt_hash(receipt_id: str, request_id: str, status: str) -> str:
        return PatchCanonicalHash.canonical_hash(receipt_id, request_id, status)

    @staticmethod
    def rollback_hash(patch_id: str, rollback_hash: str) -> str:
        return PatchCanonicalHash.canonical_hash(patch_id, rollback_hash)

    @staticmethod
    def allowlist_hash(allowed_paths: List[str]) -> str:
        return PatchCanonicalHash.canonical_hash(*sorted(allowed_paths))
