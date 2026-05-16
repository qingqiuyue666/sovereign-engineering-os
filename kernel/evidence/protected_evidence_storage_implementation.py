"""Protected evidence storage implementation boundary.

This module defines a deterministic implementation boundary for protected
evidence storage. It validates digest-only envelopes, manifests, migration
receipts, access decisions, deletion tombstones, recovery plans, and rollback
plans.

It does not write files, mutate SQLite, read key material, persist key material,
read secrets, persist secrets, persist raw prompts, persist raw provider
responses, perform encryption, perform decryption, access network, or append
audit records.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "ProtectedEvidenceStorageImplementationViolation",
    "ProtectedEvidenceStorageImplementationResult",
    "validate_storage_backend_boundary",
    "validate_digest_only_envelope",
    "validate_implementation_manifest",
    "validate_migration_receipt",
    "validate_access_decision",
    "validate_deletion_tombstone",
    "validate_recovery_plan",
    "validate_rollback_plan",
    "validate_implementation_report",
]

_ALLOWED_BACKENDS = {"local_manifest_only", "sealed_digest_index"}
_ALLOWED_DIGEST_ALGORITHMS = {"sha256", "sha384", "sha512"}
_ALLOWED_ACCESS_DECISIONS = {"deny_plaintext", "allow_manifest_metadata_only", "allow_digest_only"}
_FORBIDDEN_TRUE_FLAGS = (
    "plaintext_secret_persisted",
    "raw_prompt_persisted",
    "raw_provider_response_persisted",
    "key_material_read",
    "key_material_persisted",
    "secret_value_read",
    "secret_value_persisted",
    "encrypted_vault_claimed",
    "encryption_performed",
    "decryption_performed",
    "sqlite_schema_changed",
    "audit_append_performed",
    "network_accessed",
    "provider_call_performed",
    "raw_evidence_store_allowed",
)
_REQUIRED_BOUNDARY_TRUE = (
    "digest_only_storage",
    "manifest_required",
    "migration_receipt_required",
    "access_policy_required",
    "deletion_tombstone_required",
    "recovery_plan_required",
    "rollback_plan_required",
)
_HIGH_RISK_KEYS = {
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "plaintext_secret",
    "key_material",
    "private_key",
    "api_key",
    "token",
    "password",
}


@dataclass(frozen=True)
class ProtectedEvidenceStorageImplementationResult:
    accepted: bool
    verdict: str
    contract_section: str
    failures: tuple[str, ...]


class ProtectedEvidenceStorageImplementationViolation(Exception):
    """Raised when a protected storage implementation contract receives a non-mapping payload."""


def validate_storage_backend_boundary(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageImplementationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("boundary_type") != "protected_evidence_storage_backend_boundary_v1":
        failures.append("boundary_type_invalid")
    if data.get("backend_mode") not in _ALLOWED_BACKENDS:
        failures.append("backend_mode_invalid")
    for flag in _REQUIRED_BOUNDARY_TRUE:
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    _reject_forbidden(data, failures)
    return _result(failures, "backend_boundary")


def validate_digest_only_envelope(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageImplementationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("envelope_type") != "protected_digest_only_envelope_v1":
        failures.append("envelope_type_invalid")
    for field in ("envelope_id", "task_id", "artifact_ref", "digest"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("digest_algorithm") not in _ALLOWED_DIGEST_ALGORITHMS:
        failures.append("digest_algorithm_invalid")
    if data.get("payload_material_persisted") is not False:
        failures.append("payload_material_persisted_must_be_false")
    if data.get("digest_only") is not True:
        failures.append("digest_only_required")
    _reject_forbidden(data, failures)
    return _result(failures, "digest_only_envelope")


def validate_implementation_manifest(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageImplementationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("manifest_type") != "protected_storage_implementation_manifest_v1":
        failures.append("manifest_type_invalid")
    for field in ("manifest_id", "task_id", "backend_boundary_id", "migration_receipt_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    envelopes = data.get("envelope_refs")
    if not isinstance(envelopes, list) or not envelopes:
        failures.append("envelope_refs_required")
    if data.get("manifest_metadata_only") is not True:
        failures.append("manifest_metadata_only_required")
    _reject_forbidden(data, failures)
    return _result(failures, "implementation_manifest")


def validate_migration_receipt(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageImplementationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("receipt_type") != "protected_storage_implementation_migration_receipt_v1":
        failures.append("receipt_type_invalid")
    for field in ("receipt_id", "task_id", "contract_policy_id", "rollback_plan_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    for flag in ("contract_policy_verified", "generic_payload_enforcement_verified", "rollback_plan_verified", "plaintext_absence_verified"):
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    if data.get("implementation_authorized") is not True:
        failures.append("implementation_authorized_required")
    _reject_forbidden(data, failures)
    return _result(failures, "migration_receipt")


def validate_access_decision(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageImplementationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("decision_type") != "protected_storage_access_decision_v1":
        failures.append("decision_type_invalid")
    for field in ("decision_id", "task_id", "manifest_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("access_decision") not in _ALLOWED_ACCESS_DECISIONS:
        failures.append("access_decision_invalid")
    if data.get("plaintext_access_allowed") is not False:
        failures.append("plaintext_access_allowed_must_be_false")
    if data.get("key_material_access_allowed") is not False:
        failures.append("key_material_access_allowed_must_be_false")
    _reject_forbidden(data, failures)
    return _result(failures, "access_decision")


def validate_deletion_tombstone(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageImplementationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("tombstone_type") != "protected_storage_deletion_tombstone_v1":
        failures.append("tombstone_type_invalid")
    for field in ("tombstone_id", "task_id", "envelope_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("destructive_delete_performed") is not False:
        failures.append("destructive_delete_performed_must_be_false")
    if data.get("tombstone_recorded") is not True:
        failures.append("tombstone_recorded_required")
    _reject_forbidden(data, failures)
    return _result(failures, "deletion_tombstone")


def validate_recovery_plan(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageImplementationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("plan_type") != "protected_storage_recovery_plan_v1":
        failures.append("plan_type_invalid")
    for field in ("recovery_plan_id", "task_id", "manifest_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("recovery_mode") != "manifest_reconstruction_only":
        failures.append("recovery_mode_invalid")
    if data.get("plaintext_recovery_allowed") is not False:
        failures.append("plaintext_recovery_allowed_must_be_false")
    _reject_forbidden(data, failures)
    return _result(failures, "recovery_plan")


def validate_rollback_plan(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageImplementationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("plan_type") != "protected_storage_implementation_rollback_plan_v1":
        failures.append("plan_type_invalid")
    for field in ("rollback_plan_id", "task_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("rollback_mode") != "disable_protected_storage_implementation_keep_contracts":
        failures.append("rollback_mode_invalid")
    if data.get("destructive_rollback_allowed") is not False:
        failures.append("destructive_rollback_allowed_must_be_false")
    _reject_forbidden(data, failures)
    return _result(failures, "rollback_plan")


def validate_implementation_report(payload: Mapping[str, Any]) -> ProtectedEvidenceStorageImplementationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("report_type") != "protected_storage_implementation_report_v1":
        failures.append("report_type_invalid")
    if data.get("implementation_boundary_ready") is not True:
        failures.append("implementation_boundary_ready_required")
    if data.get("encrypted_vault_ready") is not False:
        failures.append("encrypted_vault_ready_must_be_false")
    sections = data.get("validated_sections")
    required = (
        "backend_boundary",
        "digest_only_envelope",
        "implementation_manifest",
        "migration_receipt",
        "access_decision",
        "deletion_tombstone",
        "recovery_plan",
        "rollback_plan",
    )
    if not isinstance(sections, list):
        failures.append("validated_sections_must_be_list")
    else:
        for section in required:
            if section not in sections:
                failures.append(f"{section}_section_missing")
    _reject_forbidden(data, failures)
    return _result(failures, "implementation_report")


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ProtectedEvidenceStorageImplementationViolation("payload must be a mapping")
    return payload


def _reject_forbidden(data: Mapping[str, Any], failures: list[str]) -> None:
    for key in _HIGH_RISK_KEYS:
        if key in data:
            failures.append("high_risk_key_forbidden")
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True:
            failures.append(f"{flag}_forbidden")


def _result(failures: list[str], section: str) -> ProtectedEvidenceStorageImplementationResult:
    unique = tuple(sorted(set(failures)))
    return ProtectedEvidenceStorageImplementationResult(
        accepted=not unique,
        verdict="accepted_implementation_boundary" if not unique else "rejected_fail_closed",
        contract_section=section,
        failures=unique,
    )
