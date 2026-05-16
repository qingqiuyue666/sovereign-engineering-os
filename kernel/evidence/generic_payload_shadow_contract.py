"""Generic payload shadow validation contracts.

This module classifies generic evidence payloads in shadow mode only. It does
not change append behavior, mutate SQLite, perform network access, read secrets,
write files, or enable enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "GenericPayloadShadowContractViolation",
    "GenericPayloadShadowResult",
    "validate_generic_payload_shadow_policy",
    "classify_generic_payload",
    "validate_generic_payload_shadow_record",
    "validate_generic_payload_compatibility_gap",
    "validate_generic_payload_shadow_report",
]

_ALLOWED_CATEGORIES = {
    "classification",
    "lifecycle_transition",
    "validation_receipt",
    "approval",
    "sealed_evidence",
    "provider_transport_receipt",
    "runtime_sealed_receipt",
    "compatibility_gap",
}
_HIGH_RISK_KEYS = {
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "raw_traceback",
    "raw_exception_dump",
}
_FORBIDDEN_TRUE_FLAGS = (
    "enforcement_enabled",
    "ordinary_payload_behavior_changed",
    "audit_append_behavior_changed",
    "sqlite_schema_changed",
    "runtime_execution_performed",
    "network_accessed",
    "secret_value_read",
    "secret_value_persisted",
    "raw_material_persistence_allowed",
)
_CATEGORY_MARKERS = (
    ("runtime_sealed_receipt", ("receipt_chain", "runtime_sealed_receipt", "postcheck_receipt")),
    ("provider_transport_receipt", ("transport_gate_id", "provider_transport", "provider-gate")),
    ("sealed_evidence", ("sealed_evidence", "sealed_redaction", "redacted_digest")),
    ("validation_receipt", ("validation_receipt", "validation_result", "schema_validation")),
    ("approval", ("approval", "approved_by", "approval_id")),
    ("lifecycle_transition", ("lifecycle", "stage_transition", "transition")),
    ("classification", ("classification", "classifier", "record_type")),
)


@dataclass(frozen=True)
class GenericPayloadShadowResult:
    accepted: bool
    verdict: str
    category: str
    failures: tuple[str, ...]


class GenericPayloadShadowContractViolation(Exception):
    """Raised when a shadow contract receives a non-mapping payload."""


def validate_generic_payload_shadow_policy(payload: Mapping[str, Any]) -> GenericPayloadShadowResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "seos_generic_payload_shadow_v1":
        failures.append("policy_type_invalid")
    if data.get("status") != "shadow_validation_only":
        failures.append("status_invalid")
    if data.get("shadow_validation_enabled") is not True:
        failures.append("shadow_validation_enabled_required")
    if data.get("selected_high_risk_guard_retained") is not True:
        failures.append("selected_high_risk_guard_retained_required")
    if data.get("schema_compatibility_inventory_required") is not True:
        failures.append("schema_compatibility_inventory_required")
    if data.get("migration_receipt_required_before_enforcement") is not True:
        failures.append("migration_receipt_required_before_enforcement")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "policy")


def classify_generic_payload(payload: Mapping[str, Any]) -> str:
    data = _require_mapping(payload)
    if _has_high_risk_key(data):
        return "high_risk_forbidden"
    text = " ".join(str(value).lower() for value in data.values())
    keys = " ".join(str(key).lower() for key in data.keys())
    haystack = f"{keys} {text}"
    for category, markers in _CATEGORY_MARKERS:
        if any(marker in haystack for marker in markers):
            return category
    return "compatibility_gap"


def validate_generic_payload_shadow_record(payload: Mapping[str, Any]) -> GenericPayloadShadowResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    category = classify_generic_payload(data)
    if category == "high_risk_forbidden":
        failures.append("high_risk_payload_forbidden")
    if data.get("shadow_mode") is not True:
        failures.append("shadow_mode_required")
    if data.get("enforcement_enabled") is True:
        failures.append("enforcement_enabled_forbidden")
    if data.get("ordinary_payload_behavior_changed") is True:
        failures.append("ordinary_payload_behavior_changed_forbidden")
    claimed = data.get("shadow_category")
    if claimed is not None and claimed not in _ALLOWED_CATEGORIES:
        failures.append("shadow_category_invalid")
    if category != "compatibility_gap" and claimed is not None and claimed != category:
        failures.append("shadow_category_mismatch")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, category)


def validate_generic_payload_compatibility_gap(payload: Mapping[str, Any]) -> GenericPayloadShadowResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if classify_generic_payload(data) != "compatibility_gap":
        failures.append("not_compatibility_gap")
    if data.get("shadow_mode") is not True:
        failures.append("shadow_mode_required")
    if data.get("gap_recorded") is not True:
        failures.append("gap_recorded_required")
    if data.get("enforcement_blocked") is not True:
        failures.append("enforcement_blocked_required")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "compatibility_gap")


def validate_generic_payload_shadow_report(payload: Mapping[str, Any]) -> GenericPayloadShadowResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("report_type") != "generic_payload_shadow_report_v1":
        failures.append("report_type_invalid")
    if data.get("shadow_validation_enabled") is not True:
        failures.append("shadow_validation_enabled_required")
    if data.get("enforcement_enabled") is True:
        failures.append("enforcement_enabled_forbidden")
    counts = data.get("category_counts")
    if not isinstance(counts, Mapping):
        failures.append("category_counts_must_be_mapping")
    else:
        for category in counts:
            if category not in _ALLOWED_CATEGORIES:
                failures.append(f"unknown_category_count::{category}")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "report")


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise GenericPayloadShadowContractViolation("payload must be a mapping")
    return payload


def _has_high_risk_key(data: Mapping[str, Any]) -> bool:
    lowered = {str(key).lower() for key in data.keys()}
    return any(key in lowered for key in _HIGH_RISK_KEYS)


def _reject_forbidden_true_flags(data: Mapping[str, Any], failures: list[str]) -> None:
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True:
            failures.append(f"{flag}_forbidden")


def _result(failures: list[str], category: str) -> GenericPayloadShadowResult:
    unique = tuple(sorted(set(failures)))
    return GenericPayloadShadowResult(
        accepted=not unique,
        verdict="accepted_shadow_only" if not unique else "rejected_fail_closed",
        category=category,
        failures=unique,
    )
