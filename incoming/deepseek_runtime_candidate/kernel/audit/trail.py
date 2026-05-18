"""Immutable audit trail with hash-chain integrity."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from kernel.audit.hashchain import HashChain, HashChainEntry, verify_chain

__all__ = ["AuditTrail", "AuditEntry", "audit", "get_global_trail"]


@dataclass
class AuditEntry:
    """A single immutable audit record."""
    event: str
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)
    sequence: int = 0
    hash_chain_entry: HashChainEntry | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "sequence": self.sequence,
            "prev_hash": self.hash_chain_entry.prev_hash if self.hash_chain_entry else None,
            "current_hash": self.hash_chain_entry.current_hash if self.hash_chain_entry else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, default=str)


class AuditTrail:
    """Thread-safe, append-only audit trail with hash-chain integrity.

    Every entry is linked to the previous entry via SHA-256 hash,
    forming a tamper-evident chain.
    """

    def __init__(self, name: str = "audit_trail") -> None:
        self.name = name
        self._entries: list[AuditEntry] = []
        self._hash_chain = HashChain()
        self._lock = threading.Lock()
        self._sequence = 0

    def record(self, event: str, **payload: Any) -> AuditEntry:
        """Append an audit entry. Thread-safe."""
        with self._lock:
            self._sequence += 1
            # Compute content hash from audit data only (before chain link exists)
            raw_data = {
                "event": event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": dict(payload),
                "sequence": self._sequence,
            }
            content_hash = hashlib.sha256(
                json.dumps(raw_data, sort_keys=True, default=str).encode()
            ).hexdigest()

            entry = AuditEntry(
                event=event,
                timestamp=raw_data["timestamp"],
                payload=dict(payload),
                sequence=self._sequence,
            )
            entry.hash_chain_entry = self._hash_chain.append(content_hash=content_hash)
            self._entries.append(entry)
            return entry

    @property
    def entries(self) -> list[AuditEntry]:
        with self._lock:
            return list(self._entries)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def verify_integrity(self) -> bool:
        """Verify the hash chain integrity of the entire trail."""
        with self._lock:
            entries = [e.hash_chain_entry for e in self._entries if e.hash_chain_entry is not None]
            return verify_chain(entries)

    def export_json(self) -> str:
        """Export all entries as a JSON array."""
        with self._lock:
            return json.dumps([e.to_dict() for e in self._entries], sort_keys=True, default=str, indent=2)

    def query(self, event_filter: str | None = None, limit: int = 100) -> list[AuditEntry]:
        """Query entries, optionally filtered by event name prefix."""
        with self._lock:
            result = self._entries
            if event_filter:
                result = [e for e in result if e.event.startswith(event_filter)]
            return result[-limit:]

    def clear(self) -> None:
        """Clear all entries. Resets the chain."""
        with self._lock:
            self._entries.clear()
            self._hash_chain = HashChain()
            self._sequence = 0


# ── Global audit trail ─────────────────────────────────────────

_global_trail = AuditTrail(name="sovereign_v12_global")


def get_global_trail() -> AuditTrail:
    return _global_trail


def audit(event: str, **payload: Any) -> AuditEntry:
    """Convenience: record to the global audit trail."""
    return _global_trail.record(event, **payload)
