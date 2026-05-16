"""Generic audit payload full enforcement contracts.

This module defines contract-only full typed enforcement validation for generic
audit payloads. It does not mutate append behavior, write audit records, mutate
SQLite, access network, read secrets, persist raw material, or perform runtime
execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "GenericAuditPayloadFullEnforcementViolation",
    "GenericAuditPayloadFullEnforcementResult",
    "validate_full_enforcement_policy",
    "validate_compatibility_inventory",
    "validate_migration_receipt",
    "validate_rollback_plan",
    "validate_typed_enforcement_record",
    "validate_enforcement_report",
]

_ALLOWED_CATEGORIES = {
    "classification",
    "lifecycle_transition",
    "validation_receipt",
    "approval",
    "sealed_evidence",
    "provider_transport_receipt",
    "runtime_sealed_receipt",
    "generic_enforcement_report",
}
_HIGH_RISK_KEYS = {
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "raw_traceback",
    "raw_exception_dump",
}
_FORBIDDEN_TRUE_FLAGS = (
    "ordinary_payload_behavior_changed",
    "audit_append_behavior_changed",
    "sqlite_schema_changed",
    "runtime_execution_performed",
    "network_accessed",
    "secret_value_read",
    "secret_value_persisted",
    "raw_material_persistence_allowed",
)
_POLICY_REQUIRED_TRUE = (
    "shadow_validation_retained",
    "compatibility_inventory_required",
    "migration_receipt_required",
    "rollback_plan_required",
    "unknown_payload_fail_closed",
    "high_risk_guard_retained",
)


@dataclass(frozen=True)
class GenericAuditPayloadFullEnforcementResult:
    accepted: bool
    verdict: str
    contract_section: str
    failures: tuple[str, ...]


class GenericAuditPayloadFullEnforcementViolation(Exception):
    """Raised when an enforcement contract receives a non-mapping payload."""


def validate_full_enforcement_policy(payload: Mapping[str, Any]) -> GenericAuditPayloadFullEnforcementResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "seos_generic_audit_payload_full_enforcement_v1":
        failures.append("policy_type_invalid")
    if data.get("status") != "contract_only_enforcement_gate_not_runtime_mutation":
        failures.append("status_invalid")
    if data.get("full_enforcement_enabled") is not False:
        failures.append("full_enforcement_enabled_must_be_false_in_contract_slice")
    for flag in _POLICY_REQUIRED_TRUE:
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    allowed = data.get("allowed_categories")
    if not isinstance(allowed, list) or sorted(allowed) != sorted(_ALLOWED_CATEGORIES):
        failures.append("allowed_categories_invalid")
    _reject_high_risk_keys(data, failures)
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "policy")


def validate_compatibility_inventory(payload: Mapping[str, Any]) -> GenericAuditPayloadFullEnforcementResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("inventory_type") != "generic_payload_compatibility_inventory_v1":
        failures.append("inventory_type_invalid")
    for field in ("inventory_id", "task_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    categories = data.get("covered_categories")
    if not isinstance(categories, list) or sorted(categories) != sorted(_ALLOWED_CATEGORIES - {"generic_enforcement_report"}):
        failures.append("covered_categories_invalid")
    if data.get("unknown_payload_policy") != "fail_closed_after_migration_receipt":
        failures.append("unknown_payload_policy_invalid")
    if data.get("shadow_gap_inventory_complete") is not True:
        failures.append("shadow_gap_inventory_complete_required")
    _reject_high_risk_keys(data, failures)
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "compatibility_inventory")


def validate_migration_receipt(payload: Mapping[str, Any]) -> GenericAuditPayloadFullEnforcementResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("receipt_type") != "generic_payload_enforcement_migration_receipt_v1":
        failures.append("receipt_type_invalid")
    for field in ("receipt_id", "task_id", "inventory_id", "rollback_plan_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    for flag in ("compatibility_inventory_verified", "rollback_plan_verified", "shadow_validation_retained", "high_risk_guard_retained"):
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    if data.get("append_behavior_mutation_authorized") is not False:
        failures.append("append_behavior_mutation_authorized_must_be_false")
    _reject_high_risk_keys(data, failures)
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "migration_receipt")


def validate_rollback_plan(payload: Mapping[str, Any]) -> GenericAuditPayloadFullEnforcementResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("plan_type") != "generic_payload_enforcement_rollback_plan_v1":
        failures.append("plan_type_invalid")
    for field in ("rollback_plan_id", "task_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("rollback_mode") != "restore_shadow_validation_without_payload_loss":
        failures.append("rollback_mode_invalid")
    if data.get("rollback_test_required") is not True:
        failures.append("rollback_test_required_missing")
    if data.get("destructive_rollback_allowed") is not False:
        failures.append("destructive_rollback_allowed_must_be_false")
    _reject_high_risk_keys(data, failures)
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "rollback_plan")


def validate_typed_enforcement_record(payload: Mapping[str, Any]) -> GenericAuditPayloadFullEnforcementResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("record_type") != "generic_payload_typed_enforcement_record_v1":
        failures.append("record_type_invalid")
    category = data.get("category")
    if category not in _ALLOWED_CATEGORIES:
        failures.append("category_invalid")
    if category == "compatibility_gap":
        failures.append("compatibility_gap_not_allowed_in_full_enforcement")
    for field in ("record_id", "task_id", "schema_ref", "migration_receipt_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("unknown_payload") is True:
        failures.append("unknown_payload_fail_closed")
    if data.get("typed_schema_validated") is not True:
        failures.append("typed_schema_validated_required")
    if data.get("high_risk_guard_applied") is not True:
        failures.append("high_risk_guard_applied_required")
    _reject_high_risk_keys(data, failures)
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "typed_enforcement_record")


def validate_enforcement_report(payload: Mapping[str, Any]) -> GenericAuditPayloadFullEnforcementResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("report_type") != "generic_payload_full_enforcement_report_v1":
        failures.append("report_type_invalid")
    if data.get("contract_only") is not True:
        failures.append("contract_only_required")
    sections = data.get("validated_sections")
    required_sections = ("policy", "compatibility_inventory", "migration_receipt", "rollback_plan", "typed_enforcement_record")
    if not isinstance(sections, list):
        failures.append("validated_sections_must_be_list")
    else:
        for section in required_sections:
            if section not in sections:
                failures.append(f"{section}_section_missing")
    if data.get("full_runtime_enforcement_ready") is not False:
        failures.append("full_runtime_enforcement_ready_must_be_false")
    _reject_high_risk_keys(data, failures)
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "report")


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise GenericAuditPayloadFullEnforcementViolation("payload must be a mapping")
    return payload


def _reject_high_risk_keys(data: Mapping[str, Any], failures: list[str]) -> None:
    keys = {str(key).lower() for key in data.keys()}
    if any(key in keys for key in _HIGH_RISK_KEYS):
        failures.append("high_risk_key_forbidden")


def _reject_forbidden_true_flags(data: Mapping[str, Any], failures: list[str]) -> None:
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True:
            failures.append(f"{flag}_forbidden")


def _result(failures: list[str], section: str) -> GenericAuditPayloadFullEnforcementResult:
    unique = tuple(sorted(set(failures)))
    return GenericAuditPayloadFullEnforcementResult(
        accepted=not unique,
        verdict="accepted_contract_only" if not unique else "rejected_fail_closed",
        contract_section=section,
        failures=unique,
    )
