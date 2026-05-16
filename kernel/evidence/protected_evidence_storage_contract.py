"""Protected evidence storage contracts.

This module defines contract-only protected evidence storage validation. It does
not implement an encrypted vault, read key material, persist key material, read
secrets, mutate SQLite, append audit records, access network, write files, or
perform cryptographic signing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "ProtectedEvidenceStorageContractViolation",
    "ProtectedEvidenceStorageResult",
    "validate_protected_storage_policy",
    "validate_storage_manifest",
    "validate_access_policy",
    "validate_recovery_policy",
    "validate_deletion_policy",
    "validate_storage_contract_report",
]

_FORBIDDEN_TRUE_FLAGS = (
    "implementation_enabled",
    "encrypted_vault_implemented",
    "protected_storage_implemented",
    "key_material_read",
    "key_material_persisted",
    "plaintext_secret_allowed",
    "raw_prompt_allowed",
    "raw_provider_response_allowed",
    "runtime_execution_performed",
    "network_accessed",
    "sqlite_schema_changed",
    "audit_append_performed",
)
_REQUIRED_POLICY_FLAGS = (
    "storage_manifest_required",
    "access_policy_required",
    "recovery_policy_required",
    "deletion_policy_required",
    "migration_receipt_required_before_implementation",
)
_ALLOWED_ACCESS_SCOPES = {"read_none_contract_only", "manifest_only", "policy_only"}
_ALLOWED_RECOVERY_MODES = {"policy_only_no_recovery_execution", "manual_recovery_plan_only"}
_ALLOWED_DELETION_MODES = {"policy_only_no_delete_execution", "tombstone_plan_only"}


@dataclass(frozen=True)
class ProtectedEvidenceStorageResult:
    accepted: bool
    verdict: str
    contract_section: str
    failures: tuple[str, ...]


class ProtectedEvidenceStorageContractViolation(Exception):
    """Raised when a protected storage contract receives a non-mapping payload."""


def validate_protected_storage_policy(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("contract_type") != "seos_protected_evidence_storage_contract_v1":
        failures.append("contract_type_invalid")
    if data.get("status") != "contract_only":
        failures.append("status_invalid")
    for flag in _REQUIRED_POLICY_FLAGS:
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "policy")


def validate_storage_manifest(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("manifest_type") != "protected_storage_manifest_contract_v1":
        failures.append("manifest_type_invalid")
    for field in ("manifest_id", "task_id", "storage_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("contract_only") is not True:
        failures.append("contract_only_required")
    for flag in ("storage_manifest_required", "access_policy_required", "recovery_policy_required", "deletion_policy_required"):
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "storage_manifest")


def validate_access_policy(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "protected_storage_access_policy_contract_v1":
        failures.append("policy_type_invalid")
    for field in ("policy_id", "task_id", "storage_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("access_scope") not in _ALLOWED_ACCESS_SCOPES:
        failures.append("access_scope_invalid")
    if data.get("plaintext_access_allowed") is not False:
        failures.append("plaintext_access_must_be_false")
    if data.get("key_material_access_allowed") is not False:
        failures.append("key_material_access_must_be_false")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "access_policy")


def validate_recovery_policy(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "protected_storage_recovery_policy_contract_v1":
        failures.append("policy_type_invalid")
    for field in ("policy_id", "task_id", "storage_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("recovery_mode") not in _ALLOWED_RECOVERY_MODES:
        failures.append("recovery_mode_invalid")
    if data.get("recovery_execution_allowed") is not False:
        failures.append("recovery_execution_must_be_false")
    if data.get("migration_receipt_required_before_implementation") is not True:
        failures.append("migration_receipt_required_before_implementation_missing")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "recovery_policy")


def validate_deletion_policy(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "protected_storage_deletion_policy_contract_v1":
        failures.append("policy_type_invalid")
    for field in ("policy_id", "task_id", "storage_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("deletion_mode") not in _ALLOWED_DELETION_MODES:
        failures.append("deletion_mode_invalid")
    if data.get("delete_execution_allowed") is not False:
        failures.append("delete_execution_must_be_false")
    if data.get("tombstone_receipt_required") is not True:
        failures.append("tombstone_receipt_required_missing")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "deletion_policy")


def validate_storage_contract_report(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("report_type") != "protected_storage_contract_report_v1":
        failures.append("report_type_invalid")
    if data.get("contract_only") is not True:
        failures.append("contract_only_required")
    sections = data.get("validated_sections")
    if not isinstance(sections, list):
        failures.append("validated_sections_must_be_list")
    else:
        for section in ("policy", "storage_manifest", "access_policy", "recovery_policy", "deletion_policy"):
            if section not in sections:
                failures.append(f"{section}_section_missing")
    if data.get("implementation_ready") is not False:
        failures.append("implementation_ready_must_be_false")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "report")


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ProtectedEvidenceStorageContractViolation("payload must be a mapping")
    return payload


def _reject_forbidden_true_flags(data: Mapping[str, Any], failures: list[str]) -> None:
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True:
            failures.append(f"{flag}_forbidden")


def _result(failures: list[str], section: str) -> ProtectedEvidenceStorageResult:
    unique = tuple(sorted(set(failures)))
    return ProtectedEvidenceStorageResult(
        accepted=not unique,
        verdict="accepted_contract_only" if not unique else "rejected_fail_closed",
        contract_section=section,
        failures=unique,
    )
