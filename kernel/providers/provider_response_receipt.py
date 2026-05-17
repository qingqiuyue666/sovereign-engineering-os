"""Provider response receipt without raw response persistence."""

from __future__ import annotations

from kernel.tasks.run_id import digest_payload

__all__ = ["build_provider_response_receipt", "validate_provider_response_receipt"]


def build_provider_response_receipt(*, provider_id: str, request_digest: str, response_marker: str, policy_version: str, code_version: str) -> dict[str, object]:
    response_digest = digest_payload({"provider_id": provider_id, "request_digest": request_digest, "response_marker": response_marker})
    return {
        "receipt_type": "provider_response_receipt_v1",
        "provider_id": provider_id,
        "request_digest": request_digest,
        "response_digest": response_digest,
        "policy_version": policy_version,
        "code_version": code_version,
        "raw_response_persisted": False,
    }


def validate_provider_response_receipt(receipt: dict[str, object]) -> tuple[str, ...]:
    failures: list[str] = []
    if receipt.get("receipt_type") != "provider_response_receipt_v1":
        failures.append("receipt_type_invalid")
    for field in ("provider_id", "request_digest", "response_digest", "policy_version", "code_version"):
        if not isinstance(receipt.get(field), str) or not receipt.get(field):
            failures.append(f"{field}_required")
    if receipt.get("raw_response_persisted") is not False:
        failures.append("raw_response_persisted_must_be_false")
    if "raw_response" in receipt:
        failures.append("raw_response_forbidden")
    return tuple(sorted(set(failures)))
