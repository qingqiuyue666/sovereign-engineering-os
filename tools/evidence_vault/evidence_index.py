"""Evidence index — append-only artifact index with deterministic hashing.

Local-only. No network. No encryption. No key material.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional


class EvidenceIndexError(ValueError):
    """Raised when evidence index operations fail."""


class EvidenceIndex:
    """Append-only evidence index backed by a local JSON-lines file."""

    ALLOWED_CONFLICT_POLICIES = frozenset({"KEEP_NEWEST", "REJECT_DUPLICATE"})

    @staticmethod
    def _reject_non_mapping(payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")
        return payload

    @staticmethod
    def _hash_key(*parts: str) -> str:
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

    @classmethod
    def create_index_entry(cls, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deterministic index entry from an evidence envelope."""
        cls._reject_non_mapping(envelope)
        artifact_id = envelope.get("artifact_id")
        if not artifact_id or not isinstance(artifact_id, str):
            raise EvidenceIndexError("artifact_id is required and must be a non-empty string")

        # DEFECT-3: no wall-clock time. Use envelope created_at.
        indexed_at = envelope.get("created_at")
        if not isinstance(indexed_at, str) or not indexed_at.strip():
            indexed_at = "1970-01-01T00:00:00Z"

        envelope_hash = envelope.get("envelope_hash", "")

        entry = {
            "artifact_id": artifact_id,
            "index_key": f"idx-{artifact_id}-{envelope_hash}",
            "content_hash": envelope.get("content_hash", ""),
            "envelope_hash": envelope_hash,
            "hash_algorithm": envelope.get("hash_algorithm", ""),
            "indexed_at": indexed_at,
            "artifact_type": envelope.get("artifact_type", ""),
            "producer": envelope.get("producer", ""),
            "lineage": list(envelope.get("lineage", [])),
            "immutable": envelope.get("immutable", True),
            "append_only": envelope.get("append_only", True),
            # DEFECT-3: deterministic hash based on stable fields only.
            "index_record_hash": cls._hash_key(artifact_id, envelope_hash, indexed_at),
        }
        return entry

    @classmethod
    def lookup(cls, index_path: str, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Look up an artifact in the index by artifact_id. Returns None if not found.

        Raises EvidenceIndexError on corrupt JSON lines (DEFECT-2).
        """
        if not os.path.isfile(index_path):
            return None
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        raise EvidenceIndexError(
                            f"corrupt_index_line: {line_num} — cannot parse JSON"
                        ) from None
                    if entry.get("artifact_id") == artifact_id:
                        return entry
        except OSError:
            raise EvidenceIndexError(f"cannot read index file: {index_path}")
        return None

    @classmethod
    def exists(cls, index_path: str, artifact_id: str) -> bool:
        """Check if an artifact_id already exists in the index."""
        return cls.lookup(index_path, artifact_id) is not None

    @classmethod
    def append_entry(cls, index_path: str, entry: Dict[str, Any], conflict_policy: str = "REJECT_DUPLICATE") -> Dict[str, Any]:
        """Append an index entry to the index file. Rejects duplicates by default."""
        if conflict_policy not in cls.ALLOWED_CONFLICT_POLICIES:
            raise EvidenceIndexError(f"unsupported_conflict_policy: {conflict_policy}")

        artifact_id = entry.get("artifact_id", "")
        existing = cls.lookup(index_path, artifact_id)

        if existing is not None:
            if conflict_policy == "REJECT_DUPLICATE":
                raise EvidenceIndexError(f"duplicate_artifact_id_rejected: {artifact_id}")
            elif conflict_policy == "KEEP_NEWEST":
                return {"status": "kept_existing", "artifact_id": artifact_id}

        os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")

        return {"status": "indexed", "artifact_id": artifact_id, "index_key": entry["index_key"]}

    @classmethod
    def list_all(cls, index_path: str) -> List[Dict[str, Any]]:
        """Return all entries from the index.

        Raises EvidenceIndexError on corrupt JSON lines (DEFECT-2).
        """
        if not os.path.isfile(index_path):
            return []
        results: List[Dict[str, Any]] = []
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        raise EvidenceIndexError(
                            f"corrupt_index_line: {line_num} — cannot parse JSON"
                        ) from None
        except OSError:
            raise EvidenceIndexError(f"cannot read index file: {index_path}")
        return results
