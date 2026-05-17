"""Descriptor-only WAL integrity guard for V12.

The guard validates caller-supplied WAL segment metadata. It never opens a
database, WAL file, or filesystem path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

__all__ = ["WalGuardResult", "WalIntegrityGuard"]


@dataclass(frozen=True)
class WalGuardResult:
    accepted: bool
    failures: tuple[str, ...]


@dataclass
class WalIntegrityGuard:
    seen_segment_ids: set[str] = field(default_factory=set)
    last_sequence: int | None = None
    last_digest: str | None = None

    def validate_descriptor(self, descriptor: Mapping[str, object]) -> WalGuardResult:
        if not isinstance(descriptor, Mapping):
            return WalGuardResult(False, ("wal_descriptor_must_be_mapping",))

        failures: list[str] = []
        segment_id = descriptor.get("segment_id")
        sequence = descriptor.get("sequence")
        digest = descriptor.get("digest")
        previous_digest = descriptor.get("previous_digest")
        expected_digest = descriptor.get("expected_digest")

        if not isinstance(segment_id, str) or not segment_id:
            failures.append("segment_id_required")
        elif segment_id in self.seen_segment_ids:
            failures.append("duplicate_segment_id")

        if not isinstance(sequence, int):
            failures.append("sequence_required")
        elif self.last_sequence is not None and sequence <= self.last_sequence:
            failures.append("sequence_rollback")

        if not _is_digest(digest):
            failures.append("digest_required")
        if not (previous_digest == "GENESIS" or _is_digest(previous_digest)):
            failures.append("previous_digest_required")

        if _is_digest(expected_digest) and _is_digest(digest) and expected_digest != digest:
            failures.append("wal_hash_mismatch")
        if self.last_digest is not None and _is_digest(previous_digest) and previous_digest != self.last_digest:
            failures.append("wal_hash_mismatch")
        if self.last_digest is None and previous_digest != "GENESIS":
            failures.append("wal_hash_mismatch")

        if failures:
            return WalGuardResult(False, tuple(sorted(set(failures))))

        self.seen_segment_ids.add(str(segment_id))
        self.last_sequence = int(sequence)
        self.last_digest = str(digest)
        return WalGuardResult(True, ())


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and len(value) > len("sha256:")
