"""Production autonomy final gate contracts.

This module validates the final production-autonomy authorization gate. It does
not execute production autonomy, call providers, access network, read secrets,
mutate SQLite, append audit records, or write files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "ProductionAutonomyFinalGateViolation",
    "ProductionAutonomyFinalGateResult",
    "validate_final_gate_policy",
    "validate_final_authorization",
    "validate_bounded_execution_envelope",
    "validate_emergency_brake",
    "validate_post_run_audit_pack",
    "validate_rollback_quarantine_pack",
    "validate_final_100_percent_claim",
    "validate_final_gate_report",
]

_REQUIRED_HEALTH_GATES = (
    "test-root-integrity",
    "test-sealed-evidence-coverage",
    "test-evidence-proof-contract",
    "test-evidence-proof-fixtures",
    "test-final-runtime-contracts",
    "test-gated-provider-transport",
    "test-real-runtime-provider-transport-execution",
    "test-production-autonomy-final-gate",
    "test-runtime-sealed-receipt",
    "test-generic-payload-shadow",
    "test-protected-evidence-storage",
    "test-protected-evidence-storage-implementation",
    "test-real-hmac-policy-realization",
    "test-real-merkle-proof-realization",
    "test-generic-payload-full-enforcement",
    "test-schemas",
    "test-tracer-bullet",
    "test-acceptance",
    "diff-check",
)
_ALLOWED_GATE_MODES = {"default_deny", "explicitly_authorized_bounded"}
_ALLOWED_CLAIM_STATUS = {"claim_ready", "claim_blocked"}
_FORBIDDEN_TRUE_FLAGS = (
    "automatic_unbounded_execution_enabled",
    "background_execution_enabled",
    "silent_operator_bypass_enabled",
    "network_access_without_gate",
    "secret_value_read",
    "secret_value_persisted",
    "env_read_performed",
    "raw_prompt_persisted",
    "raw_response_persisted",
    "sqlite_schema_changed",
    "audit_append_without_receipt",
    "rollback_disabled",
    "quarantine_disabled",
    "emergency_brake_disabled",
    "unbounded_provider_retry_loop_enabled",
)
_HIGH_RISK_KEYS = {"api_key", "token", "password", "secret_value", "env_value", "raw_prompt", "raw_provider_response"}


@dataclass(frozen=True)
class ProductionAutonomyFinalGateResult:
    accepted: bool
    verdict: str
    contract_section: str
    failures: tuple[str, ...]


class ProductionAutonomyFinalGateViolation(Exception):
    """Raised when the final gate receives a non-mapping payload."""


def validate_final_gate_policy(payload: Mapping[str, Any]) -> ProductionAutonomyFinalGateResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "production_autonomy_final_gate_policy_v1":
        failures.append("policy_type_invalid")
    if data.get("gate_mode") not in _ALLOWED_GATE_MODES:
        failures.append("gate_mode_invalid")
    for flag in ("default_deny", "explicit_authorization_required", "bounded_execution_required", "emergency_brake_required", "post_run_audit_required", "rollback_required", "quarantine_required", "human_operator_accountability_required"):
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    if data.get("required_health_gates") != list(_REQUIRED_HEALTH_GATES):
        failures.append("required_health_gates_invalid")
    _reject_forbidden(data, failures)
    return _result(failures, "final_gate_policy")


def validate_final_authorization(payload: Mapping[str, Any]) -> ProductionAutonomyFinalGateResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("authorization_type") != "production_autonomy_final_authorization_v1":
        failures.append("authorization_type_invalid")
    for field in ("authorization_id", "task_id", "operator_id", "policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("operator_explicitly_approved") is not True:
        failures.append("operator_explicitly_approved_required")
    if data.get("scope") != "bounded_production_autonomy":
        failures.append("scope_invalid")
    if data.get("expires_after_single_run") is not True:
        failures.append("expires_after_single_run_required")
    _reject_forbidden(data, failures)
    return _result(failures, "final_authorization")


def validate_bounded_execution_envelope(payload: Mapping[str, Any]) -> ProductionAutonomyFinalGateResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("envelope_type") != "production_autonomy_bounded_execution_envelope_v1":
        failures.append("envelope_type_invalid")
    for field in ("envelope_id", "task_id", "authorization_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("max_provider_calls") != 1:
        failures.append("max_provider_calls_must_be_one")
    if data.get("max_mutating_actions") != 0:
        failures.append("max_mutating_actions_must_be_zero")
    if data.get("manual_final_confirm_required") is not True:
        failures.append("manual_final_confirm_required")
    if data.get("digest_only_payload") is not True:
        failures.append("digest_only_payload_required")
    _reject_forbidden(data, failures)
    return _result(failures, "bounded_execution_envelope")


def validate_emergency_brake(payload: Mapping[str, Any]) -> ProductionAutonomyFinalGateResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("brake_type") != "production_autonomy_emergency_brake_v1":
        failures.append("brake_type_invalid")
    for field in ("brake_id", "task_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    for flag in ("kill_switch_available", "fail_closed_on_brake", "operator_can_abort", "rollback_on_abort"):
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    _reject_forbidden(data, failures)
    return _result(failures, "emergency_brake")


def validate_post_run_audit_pack(payload: Mapping[str, Any]) -> ProductionAutonomyFinalGateResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("audit_pack_type") != "production_autonomy_post_run_audit_pack_v1":
        failures.append("audit_pack_type_invalid")
    for field in ("audit_pack_id", "task_id", "receipt_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    for field in ("sealed_receipt_refs", "quarantine_refs", "rollback_refs", "health_gate_refs"):
        if not isinstance(data.get(field), list) or not data.get(field):
            failures.append(f"{field}_required")
    _reject_forbidden(data, failures)
    return _result(failures, "post_run_audit_pack")


def validate_rollback_quarantine_pack(payload: Mapping[str, Any]) -> ProductionAutonomyFinalGateResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("pack_type") != "production_autonomy_rollback_quarantine_pack_v1":
        failures.append("pack_type_invalid")
    for field in ("pack_id", "task_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("rollback_plan_ready") is not True:
        failures.append("rollback_plan_ready_required")
    if data.get("quarantine_plan_ready") is not True:
        failures.append("quarantine_plan_ready_required")
    if data.get("destructive_rollback_allowed") is not False:
        failures.append("destructive_rollback_allowed_must_be_false")
    _reject_forbidden(data, failures)
    return _result(failures, "rollback_quarantine_pack")


def validate_final_100_percent_claim(payload: Mapping[str, Any]) -> ProductionAutonomyFinalGateResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("claim_type") != "seos_final_100_percent_completion_claim_v1":
        failures.append("claim_type_invalid")
    if data.get("claim_status") not in _ALLOWED_CLAIM_STATUS:
        failures.append("claim_status_invalid")
    if data.get("claim_100_percent_complete") is not True:
        failures.append("claim_100_percent_complete_required")
    if data.get("all_required_health_gates_passed") is not True:
        failures.append("all_required_health_gates_passed_required")
    if data.get("all_runtime_boundaries_authorized") is not True:
        failures.append("all_runtime_boundaries_authorized_required")
    if data.get("production_autonomy_final_gate_passed") is not True:
        failures.append("production_autonomy_final_gate_passed_required")
    if data.get("required_health_gates") != list(_REQUIRED_HEALTH_GATES):
        failures.append("required_health_gates_invalid")
    _reject_forbidden(data, failures)
    return _result(failures, "final_100_percent_claim")


def validate_final_gate_report(payload: Mapping[str, Any]) -> ProductionAutonomyFinalGateResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("report_type") != "production_autonomy_final_gate_report_v1":
        failures.append("report_type_invalid")
    if data.get("final_gate_ready") is not True:
        failures.append("final_gate_ready_required")
    if data.get("final_system_fully_finished") is not True:
        failures.append("final_system_fully_finished_required")
    sections = data.get("validated_sections")
    required = ("final_gate_policy", "final_authorization", "bounded_execution_envelope", "emergency_brake", "post_run_audit_pack", "rollback_quarantine_pack", "final_100_percent_claim")
    if not isinstance(sections, list):
        failures.append("validated_sections_must_be_list")
    else:
        for section in required:
            if section not in sections:
                failures.append(f"{section}_section_missing")
    _reject_forbidden(data, failures)
    return _result(failures, "final_gate_report")


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ProductionAutonomyFinalGateViolation("payload must be a mapping")
    return payload


def _reject_forbidden(data: Mapping[str, Any], failures: list[str]) -> None:
    for key in _HIGH_RISK_KEYS:
        if key in data:
            failures.append("high_risk_key_forbidden")
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True:
            failures.append(f"{flag}_forbidden")


def _result(failures: list[str], section: str) -> ProductionAutonomyFinalGateResult:
    unique = tuple(sorted(set(failures)))
    return ProductionAutonomyFinalGateResult(
        accepted=not unique,
        verdict="accepted_final_gate" if not unique else "rejected_fail_closed",
        contract_section=section,
        failures=unique,
    )
