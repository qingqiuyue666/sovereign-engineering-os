"""Sealed/redacted evidence contract.

This module provides a narrow deterministic contract for evidence payloads that
may carry sensitive material. It does not read secrets, encrypt blobs, access
network, mutate runtime state, or append audit records. It classifies and
validates candidate evidence metadata before a later evidence-vault layer is
allowed to persist sensitive material.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping

__all__ = [
    "EvidenceContractViolation",
    "EvidenceRedactionResult",
    "classify_evidence_payload",
    "redacted_digest",
    "validate_sealed_evidence_record",
]

_ALLOWED_CLASSIFICATIONS = ("public", "restricted", "secret")
_ALLOWED_SECRET_FORMS = ("sha256", "salted_hash", "hmac_placeholder", "sealed_blob_ref", "redacted_digest")
_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer ",
    "cookie",
    "credential",
    "openai_api_key",
    "password",
    "private_key",
    "secret",
    "session_token",
    "token",
)
_FORBIDDEN_RAW_FIELD_NAMES = (
    "api_key",
    "authorization",
    "cookie",
    "credential",
    "password",
    "private_key",
    "raw_prompt",
    "raw_provider_response",
    "secret",
    "session_token",
    "token",
)


class EvidenceContractViolation(Exception):
    """Raised when evidence would leak plaintext sensitive material."""


@dataclass(frozen=True)
class EvidenceRedactionResult:
    classification: str
    accepted: bool
    sealed_required: bool
    redaction_required: bool
    digest: str
    failures: tuple[str, ...]


def classify_evidence_payload(payload: Mapping[str, Any]) -> str:
    """Classify a payload without preserving raw secret values."""

    _assert_mapping(payload)
    if _contains_secret_marker(payload):
        return "secret"
    if payload.get("contains_sensitive_material") is True:
        return "secret"
    if payload.get("classification") == "restricted":
        return "restricted"
    if payload.get("classification") == "secret":
        return "secret"
    return "public"


def redacted_digest(payload: Mapping[str, Any]) -> str:
    """Return a deterministic digest over redacted structure, not raw values."""

    _assert_mapping(payload)
    redacted = _redact_payload(payload)
    canonical = _canonicalize(redacted)
    return "sha256:" + sha256(canonical.encode("utf-8")).hexdigest()


def validate_sealed_evidence_record(record: Mapping[str, Any]) -> EvidenceRedactionResult:
    """Validate a sealed/redacted evidence record.

    Accepted record shape is intentionally small:
    - evidence_id: non-empty string
    - classification: public|restricted|secret
    - digest: sha256:<hex> or redacted digest marker
    - payload: mapping, optional for public/restricted records
    - sealed_ref: required for secret records unless representation is hash-only
    - representation: required for secret records and constrained to safe forms
    """

    _assert_mapping(record)
    failures: list[str] = []
    evidence_id = record.get("evidence_id")
    classification = record.get("classification")
    digest = record.get("digest")
    representation = record.get("representation")
    payload = record.get("payload", {})

    if not isinstance(evidence_id, str) or not evidence_id:
        failures.append("evidence_id_required")
    if classification not in _ALLOWED_CLASSIFICATIONS:
        failures.append("classification_invalid")
    if not _is_sha256_digest(digest):
        failures.append("digest_invalid")
    if not isinstance(payload, Mapping):
        failures.append("payload_must_be_mapping")
        payload = {}

    inferred_classification = classify_evidence_payload(payload)
    if classification == "public" and inferred_classification != "public":
        failures.append("public_evidence_contains_sensitive_material")
    if classification == "restricted" and inferred_classification == "secret":
        failures.append("restricted_evidence_contains_secret_material")

    if _contains_forbidden_raw_field(payload):
        failures.append("forbidden_raw_secret_field_present")
    if _contains_plaintext_secret_value(payload):
        failures.append("plaintext_secret_marker_present")

    sealed_required = classification == "secret"
    redaction_required = classification in {"restricted", "secret"}
    if classification == "secret":
        if representation not in _ALLOWED_SECRET_FORMS:
            failures.append("secret_representation_invalid")
        if representation in {"sealed_blob_ref", "hmac_placeholder"}:
            sealed_ref = record.get("sealed_ref")
            if not isinstance(sealed_ref, str) or not sealed_ref:
                failures.append("sealed_ref_required")
        if "raw_value" in payload:
            failures.append("secret_raw_value_forbidden")

    accepted = not failures
    return EvidenceRedactionResult(
        classification=str(classification),
        accepted=accepted,
        sealed_required=sealed_required,
        redaction_required=redaction_required,
        digest=str(digest) if isinstance(digest, str) else "",
        failures=tuple(sorted(set(failures))),
    )


def _assert_mapping(value: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping):
        raise EvidenceContractViolation("evidence payload must be a mapping")


def _is_sha256_digest(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.split(":", 1)[1]
    return len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)


def _contains_secret_marker(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _text_has_secret_marker(str(key)) or _contains_secret_marker(item):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_secret_marker(item) for item in value)
    if isinstance(value, str):
        return _text_has_secret_marker(value)
    return False


def _contains_forbidden_raw_field(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in _FORBIDDEN_RAW_FIELD_NAMES or lowered.startswith("raw_"):
                return True
            if _contains_forbidden_raw_field(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_raw_field(item) for item in value)
    return False


def _contains_plaintext_secret_value(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_plaintext_secret_value(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_plaintext_secret_value(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        if "sk-" in lowered or "bearer " in lowered:
            return True
        return _text_has_secret_marker(value)
    return False


def _text_has_secret_marker(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _SECRET_MARKERS)


def _redact_payload(value: object) -> object:
    if isinstance(value, Mapping):
        redacted: dict[str, object] = {}
        for key, item in sorted(value.items(), key=lambda entry: str(entry[0])):
            key_text = str(key)
            if _text_has_secret_marker(key_text) or key_text.lower().startswith("raw_"):
                redacted[key_text] = "[redacted]"
            else:
                redacted[key_text] = _redact_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_payload(item) for item in value)
    if isinstance(value, str) and _text_has_secret_marker(value):
        return "[redacted]"
    return value


def _canonicalize(value: object) -> str:
    if isinstance(value, Mapping):
        items = ",".join(
            f"{_canonicalize(str(key))}:{_canonicalize(item)}"
            for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        )
        return "{" + items + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_canonicalize(item) for item in value) + "]"
    return repr(value)
