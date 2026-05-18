"""Replay mismatch — captures and reports replay output mismatches.

Produces deterministic mismatch reports with hashed report content.
Never includes raw payload data in reports.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass(frozen=True)
class ReplayMismatch:
    """Immutable mismatch report. No raw payload content."""

    mismatch_id: str
    anchor_id: str
    field: str
    expected_hash: str
    actual_hash: str
    severity: str
    report_hash: str

    @staticmethod
    def create(
        anchor_id: str,
        field: str,
        expected_hash: str,
        actual_hash: str,
        severity: str = "error",
    ) -> ReplayMismatch:
        if severity not in ("error", "warning", "info"):
            raise ValueError(f"invalid severity: {severity}")
        if not field.strip():
            raise ValueError("field required")
        if not expected_hash or not actual_hash:
            raise ValueError("expected_hash and actual_hash required")
        if expected_hash == actual_hash:
            raise ValueError("mismatch requires different hashes")

        report_content = "|".join([anchor_id, field, expected_hash, actual_hash, severity])
        report_hash = hashlib.sha256(report_content.encode()).hexdigest()
        raw = "|".join([anchor_id, field, expected_hash, actual_hash])
        mismatch_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return ReplayMismatch(
            mismatch_id=mismatch_id,
            anchor_id=anchor_id,
            field=field,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            severity=severity,
            report_hash=report_hash,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MismatchReport:
    """Collection of ReplayMismatch entries with aggregate report hash."""

    def __init__(self, anchor_id: str) -> None:
        self.anchor_id = anchor_id
        self.mismatches: List[ReplayMismatch] = []

    def add(self, mismatch: ReplayMismatch) -> None:
        self.mismatches.append(mismatch)

    def has_mismatches(self) -> bool:
        return len(self.mismatches) > 0

    def aggregate_hash(self) -> str:
        if not self.mismatches:
            return hashlib.sha256(f"{self.anchor_id}|no_mismatches".encode()).hexdigest()
        parts = [m.report_hash for m in self.mismatches]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "mismatch_count": len(self.mismatches),
            "mismatches": [m.to_dict() for m in self.mismatches],
            "aggregate_hash": self.aggregate_hash(),
        }
