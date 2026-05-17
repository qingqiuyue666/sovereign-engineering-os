"""Metadata-only WAL integrity contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

__all__ = ["WalIntegrityResult", "WalIntegrityContract"]


@dataclass(frozen=True)
class WalIntegrityResult:
    accepted: bool
    failures: tuple[str, ...]


@dataclass
class WalIntegrityContract:
    seen_segment_ids: set[str] = field(default_factory=set)
    last_logical_sequence: int | None = None

    def validate_segment_metadata(self, metadata: Mapping[str, object]) -> WalIntegrityResult:
        if not isinstance(metadata, Mapping):
            return WalIntegrityResult(False, ("wal_metadata_must_be_mapping",))
        failures: list[str] = []
        segment_id = metadata.get("segment_id")
        sequence = metadata.get("logical_sequence")
        expected_hash = metadata.get("expected_hash")
        observed_hash = metadata.get("observed_hash")
        if not isinstance(segment_id, str) or not segment_id:
            failures.append("segment_id_required")
        elif segment_id in self.seen_segment_ids:
            failures.append("duplicate_segment_id")
        if not isinstance(sequence, int):
            failures.append("logical_sequence_required")
        elif self.last_logical_sequence is not None and sequence <= self.last_logical_sequence:
            failures.append("sequence_regression")
        for field_name, value in (("expected_hash", expected_hash), ("observed_hash", observed_hash)):
            if not isinstance(value, str) or not value.startswith("sha256:"):
                failures.append(f"{field_name}_digest_required")
        if isinstance(expected_hash, str) and isinstance(observed_hash, str) and expected_hash != observed_hash:
            failures.append("wal_hash_mismatch")
        if failures:
            return WalIntegrityResult(False, tuple(sorted(set(failures))))
        self.seen_segment_ids.add(str(segment_id))
        self.last_logical_sequence = int(sequence)
        return WalIntegrityResult(True, ())
