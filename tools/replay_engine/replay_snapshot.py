"""Replay snapshot — input snapshot binding for replay requests.

Binds a replay request to a specific input snapshot identified by its
content hash. Rejects empty or invalid snapshot references.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class ReplaySnapshot:
    """Immutable snapshot binding."""

    snapshot_id: str
    snapshot_hash: str
    artifact_count: int
    evidence_source: str
    created_at: str

    @staticmethod
    def create(
        snapshot_hash: str,
        artifact_count: int,
        evidence_source: str,
        created_at: str = "",
    ) -> ReplaySnapshot:
        if not snapshot_hash or len(snapshot_hash) != 64:
            raise ValueError("snapshot_hash must be 64-char hex sha256")
        if artifact_count < 0:
            raise ValueError("artifact_count must be non-negative")
        if not evidence_source.strip():
            raise ValueError("evidence_source required")

        raw = "|".join([
            snapshot_hash, str(artifact_count), evidence_source, created_at,
        ])
        snapshot_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return ReplaySnapshot(
            snapshot_id=snapshot_id,
            snapshot_hash=snapshot_hash,
            artifact_count=artifact_count,
            evidence_source=evidence_source,
            created_at=created_at or "1970-01-01T00:00:00Z",
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
