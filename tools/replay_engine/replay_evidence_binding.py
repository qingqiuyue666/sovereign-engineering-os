"""Replay evidence binding — binds replay requests to Evidence Vault records.

Validates that evidence vault bindings are present, well-formed, and
reference actual Evidence Vault records. Rejects missing or corrupted evidence.
No raw payload is stored in binding receipts.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass(frozen=True)
class ReplayEvidenceBinding:
    """Immutable binding between replay anchor and Evidence Vault records."""

    binding_id: str
    anchor_id: str
    evidence_ids: List[str]
    evidence_hash: str
    evidence_content_hashes: List[str]
    evidence_envelope_hashes: List[str]
    is_valid: bool
    canonical_hash: str

    @staticmethod
    def _validate_ids(anchor_id: str, evidence_ids: List[str]) -> List[str]:
        if not isinstance(anchor_id, str) or not anchor_id.strip():
            raise ValueError("anchor_id required")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise ValueError("evidence_ids must not be empty")
        normalized: List[str] = []
        for eid in evidence_ids:
            if not isinstance(eid, str) or not eid.strip():
                raise ValueError(f"invalid evidence_id: {eid}")
            normalized.append(eid.strip())
        return sorted(normalized)

    @staticmethod
    def _build(
        anchor_id: str,
        evidence_ids: List[str],
        content_hashes: List[str],
        envelope_hashes: List[str],
    ) -> "ReplayEvidenceBinding":
        ids = sorted(evidence_ids)
        ch = sorted(content_hashes)
        eh = sorted(envelope_hashes)
        evidence_hash = hashlib.sha256(
            "|".join(ids + ch + eh).encode()
        ).hexdigest()
        raw = "|".join([anchor_id, evidence_hash])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        binding_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()
        return ReplayEvidenceBinding(
            binding_id=binding_id,
            anchor_id=anchor_id,
            evidence_ids=ids,
            evidence_hash=evidence_hash,
            evidence_content_hashes=ch,
            evidence_envelope_hashes=eh,
            is_valid=True,
            canonical_hash=canonical,
        )

    @staticmethod
    def create(
        anchor_id: str,
        evidence_ids: List[str],
    ) -> "ReplayEvidenceBinding":
        """Create an ID-only binding.

        This is retained for compatibility with earlier tests. Use from_vault()
        for exact replay readiness because it verifies artifact existence and
        integrity against LocalEvidenceVault.
        """
        ids = ReplayEvidenceBinding._validate_ids(anchor_id, evidence_ids)
        return ReplayEvidenceBinding._build(anchor_id, ids, [], [])

    @staticmethod
    def from_vault(
        anchor_id: str,
        evidence_ids: List[str],
        vault: Any,
    ) -> "ReplayEvidenceBinding":
        """Create a real Evidence Vault binding.

        The vault must expose read_artifact() and verify_artifact_integrity().
        Missing or corrupted artifacts fail closed. The binding stores only
        artifact IDs and hashes, never raw envelope payloads.
        """
        ids = ReplayEvidenceBinding._validate_ids(anchor_id, evidence_ids)
        if vault is None:
            raise ValueError("vault required")
        if not hasattr(vault, "read_artifact") or not hasattr(vault, "verify_artifact_integrity"):
            raise TypeError("vault must expose read_artifact and verify_artifact_integrity")

        content_hashes: List[str] = []
        envelope_hashes: List[str] = []
        for eid in ids:
            integrity = vault.verify_artifact_integrity(eid)
            if not isinstance(integrity, dict) or not integrity.get("valid"):
                raise ValueError(f"evidence_integrity_failed: {eid}")
            envelope = vault.read_artifact(eid)
            content_hash = envelope.get("content_hash")
            envelope_hash = envelope.get("envelope_hash")
            if not isinstance(content_hash, str) or not content_hash.strip():
                raise ValueError(f"evidence_content_hash_missing: {eid}")
            if not isinstance(envelope_hash, str) or not envelope_hash.strip():
                raise ValueError(f"evidence_envelope_hash_missing: {eid}")
            content_hashes.append(content_hash)
            envelope_hashes.append(envelope_hash)

        return ReplayEvidenceBinding._build(anchor_id, ids, content_hashes, envelope_hashes)

    @staticmethod
    def corrupted(anchor_id: str, reason: str = "evidence_corrupted") -> "ReplayEvidenceBinding":
        return ReplayEvidenceBinding(
            binding_id="",
            anchor_id=anchor_id,
            evidence_ids=[],
            evidence_hash="",
            evidence_content_hashes=[],
            evidence_envelope_hashes=[],
            is_valid=False,
            canonical_hash=hashlib.sha256(
                f"corrupted|{anchor_id}|{reason}".encode()
            ).hexdigest(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
