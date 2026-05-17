"""Deterministic mock provider. No live provider calls are performed."""

from __future__ import annotations

from typing import Mapping

from .provider_request_envelope import validate_provider_request_envelope
from .provider_response_receipt import build_provider_response_receipt

__all__ = ["run_mock_provider"]


def run_mock_provider(envelope: Mapping[str, object]) -> dict[str, object]:
    failures = validate_provider_request_envelope(envelope)
    if failures:
        return {"accepted": False, "failures": list(failures), "provider_calls_executed": 0}
    receipt = build_provider_response_receipt(
        provider_id=str(envelope["provider_id"]),
        request_digest=str(envelope["request_digest"]),
        response_marker="deterministic_mock_response",
        policy_version=str(envelope["policy_version"]),
        code_version=str(envelope["code_version"]),
    )
    return {"accepted": True, "provider_calls_executed": 0, "receipt": receipt}
