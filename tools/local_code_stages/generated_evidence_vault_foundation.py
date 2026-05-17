
"""Generated bounded local-only evidence vault foundation module.

v1 — contract-only. No actual vault storage write.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ALLOWED_HASH_ALGORITHMS = frozenset({"sha256", "sha512", "blake2b"})
FORBIDDEN_ARTIFACT_TYPES = frozenset({"raw_secret", "api_key", "private_key", "token", "password", "credential"})
FORBIDDEN_CONTENT_PATTERNS = ("-----BEGIN", "API_KEY=", "SECRET=", "TOKEN=", "password=")
REQUIRED_FIELDS = frozenset({
    "artifact_id", "artifact_type", "content_hash",
    "hash_algorithm", "created_at", "producer",
    "lineage", "immutable", "append_only",
})


@dataclass(frozen=True)
class EvidenceVaultReceipt:
    receipt_id: str
    artifact_id: str
    artifact_type: str
    content_hash: str
    hash_algorithm: str
    status: str
    hash_valid: bool
    append_only_enforced: bool
    immutable_enforced: bool
    metadata_valid: bool
    created_at: str
    producer: str
    lineage: List[str]
    module_version: str = "v1"
    no_vault_write: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def _check_hash_format(h: str, algo: str) -> bool:
    if algo == "sha256":
        return len(h) == 64 and all(c in "0123456789abcdef" for c in h.lower())
    if algo == "sha512":
        return len(h) == 128 and all(c in "0123456789abcdef" for c in h.lower())
    if algo == "blake2b":
        return len(h) == 128 and all(c in "0123456789abcdef" for c in h.lower())
    return False


def validate_evidence_vault_record(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    missing = REQUIRED_FIELDS - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    atype = payload["artifact_type"]
    if atype in FORBIDDEN_ARTIFACT_TYPES:
        raise ValueError(f"forbidden_artifact_type: {atype}")
    if not isinstance(payload.get("lineage"), list):
        raise TypeError("lineage must be a list")
    if not isinstance(payload.get("immutable"), bool):
        raise TypeError("immutable must be a boolean")
    if not isinstance(payload.get("append_only"), bool):
        raise TypeError("append_only must be a boolean")
    return {"valid": True, "artifact_id": payload["artifact_id"]}


def validate_evidence_hash_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    algo = payload.get("hash_algorithm", "")
    if algo not in ALLOWED_HASH_ALGORITHMS:
        raise ValueError(f"unsupported_hash_algorithm: {algo}")
    content_hash = payload.get("content_hash", "")
    valid = _check_hash_format(content_hash, algo)
    return {"hash_valid": valid, "algorithm": algo, "content_hash": content_hash}


def validate_evidence_append_only_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    if not payload.get("append_only", False):
        raise ValueError("append_only_must_be_true")
    return {"append_only": True}


def validate_evidence_metadata_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    lineage = payload.get("lineage", [])
    valid = isinstance(lineage, list) and len(lineage) > 0
    checks = {
        "lineage_present": valid,
        "producer_present": bool(payload.get("producer")),
        "created_at_present": bool(payload.get("created_at")),
    }
    return {"metadata_valid": all(checks.values()), "checks": checks}


def produce_evidence_vault_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_evidence_vault_record(payload)
    hash_check = validate_evidence_hash_contract(payload)
    append_check = validate_evidence_append_only_contract(payload)
    meta_check = validate_evidence_metadata_contract(payload)
    receipt = EvidenceVaultReceipt(
        receipt_id=_hash_id(payload.get("artifact_id", "unknown"), "v1"),
        artifact_id=payload.get("artifact_id", "unknown"),
        artifact_type=payload.get("artifact_type", "unknown"),
        content_hash=payload.get("content_hash", ""),
        hash_algorithm=payload.get("hash_algorithm", ""),
        status="sealed" if (hash_check["hash_valid"] and meta_check["metadata_valid"]) else "rejected",
        hash_valid=hash_check["hash_valid"],
        append_only_enforced=append_check["append_only"],
        immutable_enforced=payload.get("immutable", False),
        metadata_valid=meta_check["metadata_valid"],
        created_at=_created_at(payload),
        producer=payload.get("producer", "unknown"),
        lineage=payload.get("lineage", []),
    )
    return asdict(receipt)


__all__ = [
    "EvidenceVaultReceipt",
    "validate_evidence_vault_record",
    "validate_evidence_hash_contract",
    "validate_evidence_append_only_contract",
    "validate_evidence_metadata_contract",
    "produce_evidence_vault_receipt",
]
