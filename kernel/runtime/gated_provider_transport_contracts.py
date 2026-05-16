"""Gated provider transport contracts.

This module defines disabled/dry-run transport gate contracts. It does not
perform provider calls, network access, environment reads, secret reads,
SQLite mutation, audit appends, protected storage, real cryptographic
signing, Merkle construction, or production autonomy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "GatedProviderTransportContractViolation",
    "GatedProviderTransportValidationResult",
    "validate_provider_transport_gate",
    "validate_provider_transport_preflight",
    "validate_provider_transport_receipt",
    "validate_provider_transport_blocked_attempt",
    "validate_provider_transport_postcheck",
]

_ALLOWED_TRANSPORT_STATUS = {"disabled", "blocked", "manual_dry_run_only"}
_ALLOWED_MODES = {"disabled", "manual_dry_run"}
_REQUIRED_LINKS = (
    "sealed_receipt_required",
    "failure_quarantine_link_required",
    "post_run_health_required",
)
_FORBIDDEN_TRUE_FLAGS = (
    "provider_enabled",
    "provider_live_call_performed",
    "network_accessed",
    "secret_value_read",
    "secret_value_persisted",
    "env_read_performed",
    "raw_prompt_persisted",
    "raw_response_persisted",
    "sqlite_schema_changed",
    "audit_append_performed",
    "protected_storage_implemented",
    "real_hmac_performed",
    "real_merkle_tree_built",
    "zero_knowledge_proof_built",
    "production_autonomy_enabled",
    "raw_evidence_store_allowed",
)


@dataclass(frozen=True)
class GatedProviderTransportValidationResult:
    accepted: bool
    verdict: str
    failures: tuple[str, ...]


class GatedProviderTransportContractViolation(Exception):
    """Raised when a transport contract receives a non-mapping payload."""


def validate_provider_transport_gate(payload: Mapping[str, Any]) -> GatedProviderTransportValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("gate_type") != "seos_gated_provider_transport_v1":
        failures.append("gate_type_invalid")
    if data.get("status") not in _ALLOWED_TRANSPORT_STATUS:
        failures.append("status_invalid")
    if data.get("transport_mode") not in _ALLOWED_MODES:
        failures.append("transport_mode_invalid")
    if data.get("manual_approval_required") is not True:
        failures.append("manual_approval_required")
    if data.get("default_disabled") is not True:
        failures.append("default_disabled_required")
    for link in _REQUIRED_LINKS:
        if data.get(link) is not True:
            failures.append(f"{link}_missing")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def validate_provider_transport_preflight(payload: Mapping[str, Any]) -> GatedProviderTransportValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    for field in ("preflight_id", "task_id", "transport_gate_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("manual_approval_required") is not True:
        failures.append("manual_approval_required")
    if data.get("manual_approval_present") is not True:
        failures.append("manual_approval_missing")
    if data.get("transport_status") != "disabled":
        failures.append("transport_status_must_be_disabled")
    if data.get("transport_mode") not in _ALLOWED_MODES:
        failures.append("transport_mode_invalid")
    for field in ("sealed_receipt_policy", "failure_quarantine_policy", "postcheck_policy"):
        if data.get(field) != "required":
            failures.append(f"{field}_not_required")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def validate_provider_transport_receipt(payload: Mapping[str, Any]) -> GatedProviderTransportValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    for field in ("receipt_id", "task_id", "transport_gate_id", "preflight_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("preflight_result") != "passed":
        failures.append("preflight_result_not_passed")
    if data.get("transport_attempted") is not False:
        failures.append("transport_attempted_must_be_false")
    if data.get("transport_mode") not in _ALLOWED_MODES:
        failures.append("transport_mode_invalid")
    for field in ("sealed_receipt_refs", "failure_quarantine_refs", "postcheck_refs"):
        if not isinstance(data.get(field), list):
            failures.append(f"{field}_must_be_list")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def validate_provider_transport_blocked_attempt(payload: Mapping[str, Any]) -> GatedProviderTransportValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    for field in ("blocked_attempt_id", "task_id", "transport_gate_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("blocked") is not True:
        failures.append("blocked_required")
    if data.get("block_reason") not in {
        "provider_disabled",
        "manual_approval_missing",
        "policy_missing",
        "forbidden_runtime_claim",
    }:
        failures.append("block_reason_invalid")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def validate_provider_transport_postcheck(payload: Mapping[str, Any]) -> GatedProviderTransportValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    for field in ("postcheck_id", "task_id", "transport_gate_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    for field in ("sealed_receipt_present", "failure_quarantine_link_present", "post_run_health_present"):
        if data.get(field) is not True:
            failures.append(f"{field}_required")
    if data.get("postcheck_result") != "passed":
        failures.append("postcheck_result_not_passed")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise GatedProviderTransportContractViolation("payload must be a mapping")
    return payload


def _reject_forbidden_true_flags(data: Mapping[str, Any], failures: list[str]) -> None:
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True:
            failures.append(f"{flag}_forbidden")


def _result(failures: list[str]) -> GatedProviderTransportValidationResult:
    unique = tuple(sorted(set(failures)))
    return GatedProviderTransportValidationResult(
        accepted=not unique,
        verdict="accepted_contract_only" if not unique else "rejected_fail_closed",
        failures=unique,
    )
