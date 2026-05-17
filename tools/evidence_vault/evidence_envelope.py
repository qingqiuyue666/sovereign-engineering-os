"""Evidence envelope — deterministic artifact envelope creation and hash verification.

Local-only. No network. No encryption. No key material.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ALLOWED_HASH_ALGORITHMS = frozenset({"sha256", "sha512", "blake2b"})
FORBIDDEN_ARTIFACT_TYPES = frozenset({
    "raw_secret", "api_key", "private_key", "token", "password", "credential",
})
FORBIDDEN_CONTENT_MARKERS = (
    "-----BEGIN",
    "API_KEY=",
    "SECRET=",
    "TOKEN=",
    "password=",
    "sk-",
    "Bearer ",
)
REQUIRED_FIELDS = frozenset({
    "artifact_id", "artifact_type", "content_hash",
    "hash_algorithm", "created_at", "producer",
    "lineage", "immutable", "append_only",
})


class EvidenceEnvelopeError(ValueError):
    """Raised when evidence envelope validation fails."""


class EvidenceEnvelope:
    """Deterministic evidence artifact envelope."""

    @staticmethod
    def _validate_field_types(payload: Dict[str, Any]) -> None:
        if not isinstance(payload.get("lineage"), list):
            raise TypeError("lineage must be a list")
        if not isinstance(payload.get("immutable"), bool):
            raise TypeError("immutable must be a boolean")
        if not isinstance(payload.get("append_only"), bool):
            raise TypeError("append_only must be a boolean")
        if not isinstance(payload.get("artifact_id"), str) or not payload["artifact_id"].strip():
            raise EvidenceEnvelopeError("artifact_id must be a non-empty string")
        if not isinstance(payload.get("artifact_type"), str) or not payload["artifact_type"].strip():
            raise EvidenceEnvelopeError("artifact_type must be a non-empty string")

    @staticmethod
    def _reject_non_mapping(payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")
        return payload

    @staticmethod
    def _reject_secret_material(payload: Dict[str, Any]) -> None:
        atype = payload.get("artifact_type", "")
        if atype in FORBIDDEN_ARTIFACT_TYPES:
            raise EvidenceEnvelopeError(f"forbidden_artifact_type: {atype}")
        content_str = json.dumps(payload, sort_keys=True)
        for marker in FORBIDDEN_CONTENT_MARKERS:
            if marker.lower() in content_str.lower():
                raise EvidenceEnvelopeError(f"forbidden_content_marker: {marker}")

    @staticmethod
    def _reject_mutable(payload: Dict[str, Any]) -> None:
        if not payload.get("immutable", False):
            raise EvidenceEnvelopeError("immutable_must_be_true — mutable records rejected")
        if not payload.get("append_only", False):
            raise EvidenceEnvelopeError("append_only_must_be_true — overwrite-capable records rejected")

    @staticmethod
    def _check_hash_format(h: str, algo: str) -> bool:
        if algo == "sha256":
            return len(h) == 64 and all(c in "0123456789abcdef" for c in h.lower())
        if algo == "sha512":
            return len(h) == 128 and all(c in "0123456789abcdef" for c in h.lower())
        if algo == "blake2b":
            return len(h) == 128 and all(c in "0123456789abcdef" for c in h.lower())
        return False

    @staticmethod
    def _hash_payload(content: bytes, algo: str) -> str:
        if algo == "sha256":
            return hashlib.sha256(content).hexdigest()
        if algo == "sha512":
            return hashlib.sha512(content).hexdigest()
        if algo == "blake2b":
            return hashlib.blake2b(content, digest_size=64).hexdigest()
        raise EvidenceEnvelopeError(f"unsupported_hash_algorithm: {algo}")

    @classmethod
    def create_envelope(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deterministic evidence envelope from the given payload."""
        cls._reject_non_mapping(payload)

        # Check required fields BEFORE type validation so missing fields
        # get the correct error message.
        missing = REQUIRED_FIELDS - set(payload.keys())
        if missing:
            raise EvidenceEnvelopeError(f"missing_required_fields: {sorted(missing)}")

        cls._validate_field_types(payload)
        cls._reject_secret_material(payload)
        cls._reject_mutable(payload)

        algo = payload["hash_algorithm"]
        if algo not in ALLOWED_HASH_ALGORITHMS:
            raise EvidenceEnvelopeError(f"unsupported_hash_algorithm: {algo}")

        content_hash = payload["content_hash"]
        if not cls._check_hash_format(content_hash, algo):
            raise EvidenceEnvelopeError("content_hash_mismatch — hash format invalid for algorithm")

        created_at = payload.get("created_at")
        if not isinstance(created_at, str) or not created_at.strip():
            created_at = "1970-01-01T00:00:00Z"

        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        envelope_hash = hashlib.sha256(canonical).hexdigest()

        return {
            "artifact_id": payload["artifact_id"],
            "artifact_type": payload["artifact_type"],
            "content_hash": content_hash,
            "hash_algorithm": algo,
            "created_at": created_at,
            "producer": payload["producer"],
            "lineage": list(payload["lineage"]),
            "immutable": True,
            "append_only": True,
            "envelope_hash": envelope_hash,
            "envelope_created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "module_version": "v1",
        }

    @classmethod
    def verify_hash(cls, envelope: Dict[str, Any], content: bytes) -> Dict[str, Any]:
        """Verify that the content hash matches the envelope content_hash."""
        cls._reject_non_mapping(envelope)
        algo = envelope.get("hash_algorithm", "")
        if algo not in ALLOWED_HASH_ALGORITHMS:
            raise EvidenceEnvelopeError(f"unsupported_hash_algorithm: {algo}")

        expected = envelope.get("content_hash", "")
        computed = cls._hash_payload(content, algo)

        match = computed == expected
        return {
            "hash_match": match,
            "algorithm": algo,
            "expected_hash": expected,
            "computed_hash": computed,
            "artifact_id": envelope.get("artifact_id", "unknown"),
        }
