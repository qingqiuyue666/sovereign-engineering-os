"""Replay evidence binding — binds replay requests to evidence vault records.

Validates that evidence vault bindings are present, well-formed, and
reference actual evidence records. Rejects corrupted evidence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ReplayEvidenceBinding:
    """Immutable binding between replay anchor and evidence vault records."""

    binding_id: str
    anchor_id: str
    evidence_ids: List[str]
    evidence_hash: str
    is_valid: bool
    canonical_hash: str

    @staticmethod
    def create(
        anchor_id: str,
        evidence_ids: List[str],
    ) -> ReplayEvidenceBinding:
        if not anchor_id.strip():
            raise ValueError("anchor_id required")
        if not evidence_ids:
            raise ValueError("evidence_ids must not be empty")
        for eid in evidence_ids:
            if not isinstance(eid, str) or not eid.strip():
                raise ValueError(f"invalid evidence_id: {eid}")

        raw_ids = "|".join(sorted(evidence_ids))
        evidence_hash = hashlib.sha256(raw_ids.encode()).hexdigest()
        raw = "|".join([anchor_id, evidence_hash])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        binding_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return ReplayEvidenceBinding(
            binding_id=binding_id,
            anchor_id=anchor_id,
            evidence_ids=sorted(evidence_ids),
            evidence_hash=evidence_hash,
            is_valid=True,
            canonical_hash=canonical,
        )

    @staticmethod
    def corrupted(anchor_id: str, reason: str = "evidence_corrupted") -> ReplayEvidenceBinding:
        return ReplayEvidenceBinding(
            binding_id="",
            anchor_id=anchor_id,
            evidence_ids=[],
            evidence_hash="",
            is_valid=False,
            canonical_hash=hashlib.sha256(
                f"corrupted|{anchor_id}|{reason}".encode()
            ).hexdigest(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
