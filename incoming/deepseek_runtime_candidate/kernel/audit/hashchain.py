"""SHA-256 hash chain for tamper-evident audit logs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

__all__ = ["HashChain", "HashChainEntry", "verify_chain"]


@dataclass
class HashChainEntry:
    """A single link in the hash chain."""
    index: int
    prev_hash: str
    content_hash: str
    current_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "prev_hash": self.prev_hash,
            "content_hash": self.content_hash,
            "current_hash": self.current_hash,
        }


class HashChain:
    """Immutable hash chain. Each entry depends on the previous entry's hash."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self) -> None:
        self._entries: list[HashChainEntry] = []
        self._prev_hash = self.GENESIS_HASH

    def append(self, content_hash: str) -> HashChainEntry:
        """Append a new entry to the chain.

        Args:
            content_hash: SHA-256 hash of the content being recorded.

        Returns:
            The new HashChainEntry.
        """
        combined = f"{self._prev_hash}:{content_hash}"
        current_hash = hashlib.sha256(combined.encode()).hexdigest()

        entry = HashChainEntry(
            index=len(self._entries),
            prev_hash=self._prev_hash,
            content_hash=content_hash,
            current_hash=current_hash,
        )
        self._entries.append(entry)
        self._prev_hash = current_hash
        return entry

    @property
    def entries(self) -> list[HashChainEntry]:
        return list(self._entries)

    @property
    def latest_hash(self) -> str:
        return self._prev_hash

    @property
    def length(self) -> int:
        return len(self._entries)


def verify_chain(entries: list[HashChainEntry]) -> bool:
    """Verify the integrity of a hash chain.

    Returns True if the chain is intact, False if tampered.
    """
    if not entries:
        return True  # Empty chain is trivially valid

    expected_prev = HashChain.GENESIS_HASH

    for i, entry in enumerate(entries):
        if entry.index != i:
            return False
        if entry.prev_hash != expected_prev:
            return False
        combined = f"{entry.prev_hash}:{entry.content_hash}"
        recomputed = hashlib.sha256(combined.encode()).hexdigest()
        if recomputed != entry.current_hash:
            return False
        expected_prev = entry.current_hash

    return True
