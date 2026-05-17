"""Real local evidence vault runtime.

Append-only local filesystem evidence storage with deterministic hashing,
integrity checking, and recovery receipt generation.

v1 — local-only. No network. No encryption. No key management.
"""

from __future__ import annotations

from .local_evidence_vault import LocalEvidenceVault
from .evidence_envelope import EvidenceEnvelope
from .evidence_index import EvidenceIndex
from .evidence_integrity import EvidenceIntegrity
from .evidence_recovery import EvidenceRecovery

__all__ = [
    "LocalEvidenceVault",
    "EvidenceEnvelope",
    "EvidenceIndex",
    "EvidenceIntegrity",
    "EvidenceRecovery",
]
