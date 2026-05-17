"""Digest-only provider request envelope."""

from __future__ import annotations

from typing import Mapping

from kernel.security.security_classification import normalize_classification
from kernel.tasks.run_id import digest_payload

__all__ = ["build_provider_request_envelope", "validate_provider_request_envelope"]


def build_provider_request_envelope(
    *,
    task_id: str,
    request_digest: str,
    classification: str,
    policy_version: str,
    code_version: str,
    provider_id: str = "mock_provider",
) -> dict[str, object]:
    envelope = {
        "envelope_type": "provider_request_envelope_v1",
        "task_id": task_id,
        "provider_id": provider_id,
        "request_digest": request_digest,
        "classification": classification,
        "policy_version": policy_version,
        "code_version": code_version,
        "digest_only": True,
    }
    envelope["envelope_digest"] = digest_payload(envelope)
    return envelope


def validate_provider_request_envelope(envelope: Mapping[str, object]) -> tuple[str, ...]:
    failures: list[str] = []
    if not isinstance(envelope, Mapping):
        return ("provider_request_envelope_must_be_mapping",)
    if envelope.get("envelope_type") != "provider_request_envelope_v1":
        failures.append("envelope_type_invalid")
    if envelope.get("digest_only") is not True:
        failures.append("digest_only_required")
    if not isinstance(envelope.get("request_digest"), str) or not str(envelope.get("request_digest")).startswith("sha256:"):
        failures.append("request_digest_required")
    if normalize_classification(envelope.get("classification")) in {"SECRET", "CROWN_JEWEL"}:
        failures.append("sensitive_provider_payload_forbidden")
    for field in ("task_id", "provider_id", "policy_version", "code_version"):
        if not isinstance(envelope.get(field), str) or not envelope.get(field):
            failures.append(f"{field}_required")
    if "raw_prompt" in envelope or "raw_payload" in envelope:
        failures.append("raw_payload_forbidden")
    return tuple(sorted(set(failures)))
