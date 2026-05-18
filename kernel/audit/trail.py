"""In-memory audit trail with deterministic content hashes.

Wall-clock timestamps are observation metadata only. They are exported for
operators, but they are never included in deterministic content hashes or the
hash-chain input.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
import json
import threading

from kernel.errors.hierarchy import AuditIntegrityError

from .hashchain import HashChain, HashChainEntry, canonical_json, digest_payload, verify_chain

__all__ = ["AuditEntry", "AuditTrail", "audit", "get_global_trail"]

_FORBIDDEN_KEYS = frozenset(
    {
        ".env",
        "env",
        "env_value",
        "provider_response",
        "raw_input",
        "raw_prompt",
        "raw_provider_response",
        "raw_response",
        "secret",
        "secret_value",
    }
)


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit entry with a deterministic content hash."""

    event: str
    sequence: int
    observed_at: str
    payload_json: str
    content_hash: str
    hash_chain_entry: HashChainEntry

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.payload_json)

    @property
    def timestamp(self) -> str:
        """Compatibility alias. This value is not deterministic hash input."""

        return self.observed_at

    def deterministic_material(self) -> dict[str, object]:
        return {
            "event": self.event,
            "payload": self.payload,
            "sequence": self.sequence,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "event": self.event,
            "sequence": self.sequence,
            "observed_at": self.observed_at,
            "timestamp": self.observed_at,
            "payload": self.payload,
            "content_hash": self.content_hash,
            "hash_chain": self.hash_chain_entry.as_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


class AuditTrail:
    """Thread-safe append-only audit trail."""

    def __init__(self, name: str = "audit_trail") -> None:
        if not isinstance(name, str) or not name:
            raise AuditIntegrityError("audit_trail_name_required")
        self.name = name
        self._entries: list[AuditEntry] = []
        self._hash_chain = HashChain()
        self._sequence = 0
        self._lock = threading.RLock()

    def record(
        self,
        event: str,
        payload: Mapping[str, object] | None = None,
        *,
        observed_at: str | None = None,
        **payload_fields: object,
    ) -> AuditEntry:
        if not isinstance(event, str) or not event:
            raise AuditIntegrityError("audit_event_required")
        normalized_payload = _normalize_payload(payload, payload_fields)
        observed = observed_at if observed_at is not None else datetime.now(timezone.utc).isoformat()
        if not isinstance(observed, str) or not observed:
            raise AuditIntegrityError("observed_at_must_be_nonempty_string")

        with self._lock:
            sequence = self._sequence + 1
            material = {
                "event": event,
                "payload": normalized_payload,
                "sequence": sequence,
            }
            content_hash = digest_payload(material)
            chain_entry = self._hash_chain.append(content_hash)
            entry = AuditEntry(
                event=event,
                sequence=sequence,
                observed_at=observed,
                payload_json=canonical_json(normalized_payload),
                content_hash=content_hash,
                hash_chain_entry=chain_entry,
            )
            self._entries.append(entry)
            self._sequence = sequence
            return entry

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        with self._lock:
            return tuple(self._entries)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def verify_integrity(self) -> bool:
        with self._lock:
            if not verify_chain(entry.hash_chain_entry for entry in self._entries):
                return False
            for entry in self._entries:
                if digest_payload(entry.deterministic_material()) != entry.content_hash:
                    return False
            return True

    def query(self, event_prefix: str | None = None, *, limit: int = 100) -> tuple[AuditEntry, ...]:
        if limit < 0:
            raise AuditIntegrityError("audit_query_limit_must_be_nonnegative")
        with self._lock:
            entries: tuple[AuditEntry, ...] = tuple(self._entries)
        if event_prefix is not None:
            entries = tuple(entry for entry in entries if entry.event.startswith(event_prefix))
        if limit == 0:
            return ()
        return entries[-limit:]

    def export_json(self) -> str:
        with self._lock:
            payload = [entry.to_dict() for entry in self._entries]
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def _normalize_payload(payload: Mapping[str, object] | None, payload_fields: Mapping[str, object]) -> dict[str, Any]:
    combined: dict[str, object] = {}
    if payload is not None:
        if not isinstance(payload, Mapping):
            raise AuditIntegrityError("audit_payload_must_be_mapping")
        combined.update(dict(payload))
    combined.update(dict(payload_fields))
    _reject_forbidden_keys(combined)
    try:
        payload_json = canonical_json(combined)
    except (TypeError, ValueError) as exc:
        raise AuditIntegrityError("audit_payload_must_be_canonical_json") from exc
    return json.loads(payload_json)


def _reject_forbidden_keys(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in _FORBIDDEN_KEYS:
                raise AuditIntegrityError(f"audit_payload_forbidden_key:{key}")
            _reject_forbidden_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_forbidden_keys(item)


_GLOBAL_TRAIL = AuditTrail(name="sovereign_v12_global")


def get_global_trail() -> AuditTrail:
    return _GLOBAL_TRAIL


def audit(event: str, **payload: object) -> AuditEntry:
    return _GLOBAL_TRAIL.record(event, payload)
