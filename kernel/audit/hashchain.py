"""Deterministic hash chain for tamper-evident audit material.

The chain only accepts canonical digest strings. Observation metadata such as
timestamps must be kept outside the content hash passed to this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import hashlib
import json
import re

from kernel.errors.hierarchy import AuditIntegrityError

__all__ = ["HashChain", "HashChainEntry", "canonical_json", "digest_payload", "verify_chain"]

_SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


def canonical_json(payload: Any) -> str:
    """Return canonical JSON suitable for deterministic hashing."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest_payload(payload: Any) -> str:
    """Return a normalized sha256 digest for canonical JSON material."""

    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _normalize_digest(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise AuditIntegrityError(f"{field}_must_be_sha256_digest")
    if value.startswith("sha256:"):
        return value
    return "sha256:" + value


@dataclass(frozen=True)
class HashChainEntry:
    """A single immutable link in a deterministic hash chain."""

    index: int
    previous_hash: str
    content_hash: str
    current_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "content_hash": self.content_hash,
            "current_hash": self.current_hash,
        }

    @property
    def prev_hash(self) -> str:
        """Compatibility alias for the audited candidate naming."""

        return self.previous_hash


class HashChain:
    """Append-only deterministic hash chain."""

    GENESIS_HASH = "sha256:" + ("0" * 64)

    def __init__(self) -> None:
        self._entries: list[HashChainEntry] = []
        self._latest_hash = self.GENESIS_HASH

    def append(self, content_hash: str) -> HashChainEntry:
        normalized_content_hash = _normalize_digest(content_hash, field="content_hash")
        index = len(self._entries)
        current_hash = digest_payload(
            {
                "content_hash": normalized_content_hash,
                "index": index,
                "previous_hash": self._latest_hash,
            }
        )
        entry = HashChainEntry(
            index=index,
            previous_hash=self._latest_hash,
            content_hash=normalized_content_hash,
            current_hash=current_hash,
        )
        self._entries.append(entry)
        self._latest_hash = current_hash
        return entry

    @property
    def entries(self) -> tuple[HashChainEntry, ...]:
        return tuple(self._entries)

    @property
    def latest_hash(self) -> str:
        return self._latest_hash

    @property
    def length(self) -> int:
        return len(self._entries)


def verify_chain(entries: Iterable[HashChainEntry]) -> bool:
    """Return True only when every link matches the deterministic chain."""

    expected_previous = HashChain.GENESIS_HASH
    for expected_index, entry in enumerate(entries):
        try:
            previous_hash = _normalize_digest(entry.previous_hash, field="previous_hash")
            content_hash = _normalize_digest(entry.content_hash, field="content_hash")
            current_hash = _normalize_digest(entry.current_hash, field="current_hash")
        except AuditIntegrityError:
            return False
        if entry.index != expected_index:
            return False
        if previous_hash != expected_previous:
            return False
        recomputed = digest_payload(
            {
                "content_hash": content_hash,
                "index": expected_index,
                "previous_hash": previous_hash,
            }
        )
        if current_hash != recomputed:
            return False
        expected_previous = current_hash
    return True
