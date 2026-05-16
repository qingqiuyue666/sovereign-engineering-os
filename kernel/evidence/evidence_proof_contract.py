"""Evidence proof contract foundation.

This module defines a deterministic proof-record contract for evidence digests.
It does not implement an encrypted vault, real HMAC signing, real Merkle tree
construction, zero-knowledge proof systems, secret reads, runtime execution,
network access, SQLite mutation, or audit appends.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "EvidenceProofContractViolation",
    "EvidenceProofValidationResult",
    "validate_evidence_proof_record",
]

_ALLOWED_PROOF_KINDS = (
    "sha256_digest",
    "redacted_digest",
    "hmac_placeholder",
    "merkle_placeholder",
)
_ALLOWED_CLASSIFICATIONS = ("public", "restricted", "secret")
_PLACEHOLDER_PROOF_KINDS = ("hmac_placeholder", "merkle_placeholder")
_FORBIDDEN_RAW_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "raw_traceback",
    "raw_exception_dump",
    "raw_value",
    "secret_value",
    "token",
    "password",
    "api_key",
    "cookie",
    "credential",
    "private_key",
)
_FORBIDDEN_SECRET_MARKERS = (
    "sk-",
    "bearer ",
    "api_key=",
    "password=",
    "secret=",
    "token=",
    "private_key",
)


@dataclass(frozen=True)
class EvidenceProofValidationResult:
    accepted: bool
    proof_kind: str
    classification: str
    placeholder_only: bool
    failures: tuple[str, ...]


class EvidenceProofContractViolation(Exception):
    """Raised when a proof record is not a mapping."""


def validate_evidence_proof_record(record: Mapping[str, Any]) -> EvidenceProofValidationResult:
    """Validate an evidence proof record without performing cryptographic proof work."""

    if not isinstance(record, Mapping):
        raise EvidenceProofContractViolation("proof record must be a mapping")

    failures: list[str] = []
    proof_id = record.get("proof_id")
    proof_kind = record.get("proof_kind")
    classification = record.get("classification")
    subject_evidence_id = record.get("subject_evidence_id")
    digest = record.get("digest")
    algorithm = record.get("algorithm")
    payload = record.get("payload", {})

    if not isinstance(proof_id, str) or not proof_id:
        failures.append("proof_id_required")
    if proof_kind not in _ALLOWED_PROOF_KINDS:
        failures.append("proof_kind_invalid")
    if classification not in _ALLOWED_CLASSIFICATIONS:
        failures.append("classification_invalid")
    if not isinstance(subject_evidence_id, str) or not subject_evidence_id:
        failures.append("subject_evidence_id_required")
    if not isinstance(payload, Mapping):
        failures.append("payload_must_be_mapping")
        payload = {}

    if proof_kind in {"sha256_digest", "redacted_digest"}:
        if not _is_sha256_digest(digest):
            failures.append("digest_invalid")
        if algorithm not in {"sha256", "redacted_sha256"}:
            failures.append("algorithm_invalid")
    elif proof_kind == "hmac_placeholder":
        if digest not in {"hmac_placeholder", "sha256:hmac-placeholder"}:
            failures.append("hmac_placeholder_digest_required")
        if algorithm != "hmac_sha256_placeholder":
            failures.append("algorithm_invalid")
        if record.get("key_id") not in {None, "placeholder"}:
            failures.append("real_hmac_key_forbidden")
    elif proof_kind == "merkle_placeholder":
        if digest not in {"merkle_placeholder", "sha256:merkle-placeholder"}:
            failures.append("merkle_placeholder_digest_required")
        if algorithm != "merkle_sha256_placeholder":
            failures.append("algorithm_invalid")
        if record.get("merkle_root") not in {None, "placeholder"}:
            failures.append("real_merkle_root_forbidden")

    if record.get("encrypted_vault_implemented") is True:
        failures.append("encrypted_vault_implementation_forbidden")
    if record.get("real_hmac_key_read") is True:
        failures.append("real_hmac_key_read_forbidden")
    if record.get("real_merkle_tree_built") is True:
        failures.append("real_merkle_tree_build_forbidden")
    if record.get("zero_knowledge_proof_built") is True:
        failures.append("zero_knowledge_proof_build_forbidden")
    if record.get("secret_value_read") is True:
        failures.append("secret_value_read_forbidden")
    if record.get("runtime_execution_performed") is True:
        failures.append("runtime_execution_forbidden")
    if record.get("network_accessed") is True:
        failures.append("network_access_forbidden")
    if _contains_forbidden_raw_field(record):
        failures.append("forbidden_raw_field_present")
    if _contains_plaintext_secret_marker(record):
        failures.append("plaintext_secret_marker_present")

    return EvidenceProofValidationResult(
        accepted=not failures,
        proof_kind=str(proof_kind) if isinstance(proof_kind, str) else "",
        classification=str(classification) if isinstance(classification, str) else "",
        placeholder_only=proof_kind in _PLACEHOLDER_PROOF_KINDS,
        failures=tuple(sorted(set(failures))),
    )


def _is_sha256_digest(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.split(":", 1)[1]
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


def _contains_forbidden_raw_field(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered_key = str(key).lower()
            if lowered_key in _FORBIDDEN_RAW_FIELDS:
                return True
            if lowered_key.startswith("raw_") and not (
                lowered_key.endswith("_persisted") and item is False
            ):
                return True
            if _contains_forbidden_raw_field(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_raw_field(item) for item in value)
    return False


def _contains_plaintext_secret_marker(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_plaintext_secret_marker(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_plaintext_secret_marker(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in _FORBIDDEN_SECRET_MARKERS)
    return False
