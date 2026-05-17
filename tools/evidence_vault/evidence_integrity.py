"""Evidence integrity — corruption detection and payload digest validation.

Local-only. No network. No encryption. No key material.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List

STABLE_ENVELOPE_FIELDS = (
    "artifact_id", "artifact_type", "content_hash", "hash_algorithm",
    "created_at", "producer", "lineage", "immutable", "append_only",
)


class EvidenceIntegrityError(ValueError):
    """Raised when evidence integrity checks fail."""


class EvidenceIntegrity:
    """Checks evidence payload and index integrity via deterministic digest comparison."""

    @staticmethod
    def _reject_non_mapping(payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")
        return payload

    @staticmethod
    def compute_digest(data: bytes, algo: str = "sha256") -> str:
        if algo == "sha256":
            return hashlib.sha256(data).hexdigest()
        if algo == "sha512":
            return hashlib.sha512(data).hexdigest()
        if algo == "blake2b":
            return hashlib.blake2b(data, digest_size=64).hexdigest()
        raise EvidenceIntegrityError(f"unsupported_hash_algorithm: {algo}")

    @classmethod
    def verify_payload_integrity(cls, payload_path: str, expected_hash: str, algo: str = "sha256") -> Dict[str, Any]:
        """Verify that a stored payload file matches its expected hash."""
        if not os.path.isfile(payload_path):
            return {
                "valid": False,
                "reason": "payload_file_missing",
                "artifact_id": "unknown",
                "expected_hash": expected_hash,
                "computed_hash": "",
            }

        try:
            with open(payload_path, "rb") as f:
                data = f.read()
        except OSError as e:
            return {
                "valid": False,
                "reason": f"payload_read_error: {e}",
                "artifact_id": "unknown",
                "expected_hash": expected_hash,
                "computed_hash": "",
            }

        computed = cls.compute_digest(data, algo)
        match = computed == expected_hash

        return {
            "valid": match,
            "reason": "hash_match" if match else "hash_mismatch_corruption_detected",
            "artifact_id": "unknown",
            "expected_hash": expected_hash,
            "computed_hash": computed,
            "algorithm": algo,
        }

    @classmethod
    def verify_index_integrity(cls, index_path: str) -> Dict[str, Any]:
        """Check index file for corruption by verifying each line is valid JSON and has required fields."""
        if not os.path.isfile(index_path):
            return {
                "valid": True,
                "reason": "no_index_file_empty_state",
                "total_entries": 0,
                "corrupt_entries": 0,
            }

        total = 0
        corrupt = 0
        corrupt_lines: List[int] = []
        required = {"artifact_id", "index_key", "content_hash"}

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    total += 1
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        corrupt += 1
                        corrupt_lines.append(line_num)
                        continue
                    if not isinstance(entry, dict):
                        corrupt += 1
                        corrupt_lines.append(line_num)
                        continue
                    if required - set(entry.keys()):
                        corrupt += 1
                        corrupt_lines.append(line_num)
        except OSError as e:
            return {
                "valid": False,
                "reason": f"index_read_error: {e}",
                "total_entries": total,
                "corrupt_entries": corrupt,
            }

        valid = corrupt == 0
        return {
            "valid": valid,
            "reason": "index_integrity_clean" if valid else "index_corruption_detected",
            "total_entries": total,
            "corrupt_entries": corrupt,
            "corrupt_line_numbers": corrupt_lines if corrupt else [],
        }

    @classmethod
    def verify_storage_envelope(cls, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that a storage envelope is correct: structure and envelope hash.

        DEFECT-4: recomputes envelope_hash from stable fields and compares
        against the stored value. Returns valid=False on any mismatch.
        """
        cls._reject_non_mapping(envelope)
        checks = {
            "has_artifact_id": bool(envelope.get("artifact_id")),
            "has_content_hash": bool(envelope.get("content_hash")),
            "has_envelope_hash": bool(envelope.get("envelope_hash")),
            "has_hash_algorithm": bool(envelope.get("hash_algorithm")),
            "has_created_at": bool(envelope.get("created_at")),
            "has_producer": bool(envelope.get("producer")),
            "has_lineage": isinstance(envelope.get("lineage"), list),
            "immutable_is_true": envelope.get("immutable") is True,
            "append_only_is_true": envelope.get("append_only") is True,
        }
        structure_valid = all(checks.values())

        # DEFECT-4: recompute envelope hash from stable fields and compare.
        stored_hash = envelope.get("envelope_hash", "")
        rebuild = {k: envelope[k] for k in STABLE_ENVELOPE_FIELDS if k in envelope}
        canonical = json.dumps(rebuild, sort_keys=True, ensure_ascii=False).encode("utf-8")
        computed_hash = hashlib.sha256(canonical).hexdigest()
        hash_match = computed_hash == stored_hash
        checks["envelope_hash_match"] = hash_match

        valid = structure_valid and hash_match
        return {
            "valid": valid,
            "checks": checks,
            "artifact_id": envelope.get("artifact_id", "unknown"),
        }
