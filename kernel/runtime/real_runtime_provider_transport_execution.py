"""Real runtime provider transport execution boundary.

This module defines deterministic validation contracts for the controlled
provider transport execution path. It does not perform provider calls, network
access, environment reads, secret reads, audit appends, SQLite mutation, file
writes, or production autonomy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "RealRuntimeProviderTransportExecutionViolation",
    "RealRuntimeProviderTransportExecutionResult",
    "validate_transport_execution_policy",
    "validate_operator_authorization",
    "validate_execution_preflight",
    "validate_execution_envelope",
    "validate_execution_receipt",
    "validate_execution_postcheck",
    "validate_execution_quarantine_link",
    "validate_execution_report",
]

_ALLOWED_EXECUTION_MODES = {"disabled", "manual_authorized_single_call"}
_ALLOWED_PROVIDER_STATES = {"disabled", "armed_by_operator", "executed_once"}
_ALLOWED_TRANSPORT_TYPES = {"provider_request_metadata_only", "provider_single_call_receipt_only"}
_ALLOWED_RESULTS = {"not_executed", "executed_once_with_receipt", "blocked_fail_closed"}
_FORBIDDEN_TRUE_FLAGS = (
    "automatic_execution_enabled",
    "background_execution_enabled",
    "unbounded_provider_calls_allowed",
    "network_access_without_authorization",
    "secret_value_read",
    "secret_value_persisted",
    "env_read_performed",
    "raw_prompt_persisted",
    "raw_response_persisted",
    "sqlite_schema_changed",
    "audit_append_performed",
    "production_autonomy_enabled",
    "provider_retry_loop_enabled",
    "provider_streaming_enabled",
)
_REQUIRED_POLICY_TRUE = (
    "default_disabled",
    "manual_preflight_required",
    "operator_authorization_required",
    "sealed_receipt_required",
    "post_run_health_required",
    "failure_quarantine_link_required",
    "single_call_limit_required",
)
_HIGH_RISK_KEYS = {
    "api_key",
    "token",
    "password",
    "secret_value",
    "env_value",
    "raw_prompt",
    "raw_provider_response",
}


@dataclass(frozen=True)
class RealRuntimeProviderTransportExecutionResult:
    accepted: bool
    verdict: str
    contract_section: str
    failures: tuple[str, ...]


class RealRuntimeProviderTransportExecutionViolation(Exception):
    """Raised when a transport execution contract receives a non-mapping payload."""


def validate_transport_execution_policy(payload: Mapping[str, Any]) -> RealRuntimeProviderTransportExecutionResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "real_runtime_provider_transport_execution_policy_v1":
        failures.append("policy_type_invalid")
    if data.get("execution_mode") not in _ALLOWED_EXECUTION_MODES:
        failures.append("execution_mode_invalid")
    for flag in _REQUIRED_POLICY_TRUE:
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    if data.get("provider_state") not in _ALLOWED_PROVIDER_STATES:
        failures.append("provider_state_invalid")
    _reject_forbidden(data, failures)
    return _result(failures, "execution_policy")


def validate_operator_authorization(payload: Mapping[str, Any]) -> RealRuntimeProviderTransportExecutionResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("authorization_type") != "operator_runtime_transport_authorization_v1":
        failures.append("authorization_type_invalid")
    for field in ("authorization_id", "task_id", "operator_id", "policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("operator_explicitly_approved") is not True:
        failures.append("operator_explicitly_approved_required")
    if data.get("single_call_authorized") is not True:
        failures.append("single_call_authorized_required")
    if data.get("authorization_scope") != "single_provider_call":
        failures.append("authorization_scope_invalid")
    _reject_forbidden(data, failures)
    return _result(failures, "operator_authorization")


def validate_execution_preflight(payload: Mapping[str, Any]) -> RealRuntimeProviderTransportExecutionResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("preflight_type") != "real_runtime_provider_transport_preflight_v1":
        failures.append("preflight_type_invalid")
    for field in ("preflight_id", "task_id", "authorization_id", "policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    for flag in ("operator_authorization_verified", "sealed_receipt_policy_verified", "post_run_health_policy_verified", "failure_quarantine_policy_verified", "protected_storage_boundary_verified"):
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    if data.get("provider_state") != "armed_by_operator":
        failures.append("provider_state_must_be_armed_by_operator")
    _reject_forbidden(data, failures)
    return _result(failures, "execution_preflight")


def validate_execution_envelope(payload: Mapping[str, Any]) -> RealRuntimeProviderTransportExecutionResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("envelope_type") != "real_runtime_provider_transport_envelope_v1":
        failures.append("envelope_type_invalid")
    for field in ("envelope_id", "task_id", "preflight_id", "authorization_id", "provider_ref"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("transport_type") not in _ALLOWED_TRANSPORT_TYPES:
        failures.append("transport_type_invalid")
    if data.get("request_payload_digest_only") is not True:
        failures.append("request_payload_digest_only_required")
    if data.get("raw_request_payload_persisted") is not False:
        failures.append("raw_request_payload_persisted_must_be_false")
    if data.get("single_call_limit") != 1:
        failures.append("single_call_limit_must_be_one")
    _reject_forbidden(data, failures)
    return _result(failures, "execution_envelope")


def validate_execution_receipt(payload: Mapping[str, Any]) -> RealRuntimeProviderTransportExecutionResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("receipt_type") != "real_runtime_provider_transport_execution_receipt_v1":
        failures.append("receipt_type_invalid")
    for field in ("receipt_id", "task_id", "envelope_id", "authorization_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("execution_result") not in _ALLOWED_RESULTS:
        failures.append("execution_result_invalid")
    if data.get("provider_call_count") not in (0, 1):
        failures.append("provider_call_count_invalid")
    if data.get("provider_call_count") == 1 and data.get("execution_result") != "executed_once_with_receipt":
        failures.append("provider_call_count_result_mismatch")
    if data.get("sealed_receipt_created") is not True:
        failures.append("sealed_receipt_created_required")
    if data.get("raw_response_persisted") is not False:
        failures.append("raw_response_persisted_must_be_false")
    _reject_forbidden(data, failures)
    return _result(failures, "execution_receipt")


def validate_execution_postcheck(payload: Mapping[str, Any]) -> RealRuntimeProviderTransportExecutionResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("postcheck_type") != "real_runtime_provider_transport_postcheck_v1":
        failures.append("postcheck_type_invalid")
    for field in ("postcheck_id", "task_id", "receipt_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    for flag in ("sealed_receipt_present", "post_run_health_passed", "failure_quarantine_link_present"):
        if data.get(flag) is not True:
            failures.append(f"{flag}_required")
    if data.get("postcheck_result") != "passed":
        failures.append("postcheck_result_not_passed")
    _reject_forbidden(data, failures)
    return _result(failures, "execution_postcheck")


def validate_execution_quarantine_link(payload: Mapping[str, Any]) -> RealRuntimeProviderTransportExecutionResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("link_type") != "real_runtime_provider_transport_quarantine_link_v1":
        failures.append("link_type_invalid")
    for field in ("link_id", "task_id", "receipt_id", "quarantine_ref"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("quarantine_policy_status") != "linked":
        failures.append("quarantine_policy_status_invalid")
    _reject_forbidden(data, failures)
    return _result(failures, "execution_quarantine_link")


def validate_execution_report(payload: Mapping[str, Any]) -> RealRuntimeProviderTransportExecutionResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("report_type") != "real_runtime_provider_transport_execution_report_v1":
        failures.append("report_type_invalid")
    if data.get("execution_boundary_ready") is not True:
        failures.append("execution_boundary_ready_required")
    if data.get("production_autonomy_ready") is not False:
        failures.append("production_autonomy_ready_must_be_false")
    sections = data.get("validated_sections")
    required = (
        "execution_policy",
        "operator_authorization",
        "execution_preflight",
        "execution_envelope",
        "execution_receipt",
        "execution_postcheck",
        "execution_quarantine_link",
    )
    if not isinstance(sections, list):
        failures.append("validated_sections_must_be_list")
    else:
        for section in required:
            if section not in sections:
                failures.append(f"{section}_section_missing")
    _reject_forbidden(data, failures)
    return _result(failures, "execution_report")


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise RealRuntimeProviderTransportExecutionViolation("payload must be a mapping")
    return payload


def _reject_forbidden(data: Mapping[str, Any], failures: list[str]) -> None:
    for key in _HIGH_RISK_KEYS:
        if key in data:
            failures.append("high_risk_key_forbidden")
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True:
            failures.append(f"{flag}_forbidden")


def _result(failures: list[str], section: str) -> RealRuntimeProviderTransportExecutionResult:
    unique = tuple(sorted(set(failures)))
    return RealRuntimeProviderTransportExecutionResult(
        accepted=not unique,
        verdict="accepted_execution_boundary" if not unique else "rejected_fail_closed",
        contract_section=section,
        failures=unique,
    )
