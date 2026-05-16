"""Real HMAC policy-realization contracts.

This module defines contract-only HMAC policy realization validation. It does
not import hmac, read key material, generate keys, create real signatures,
verify signatures, mutate SQLite, append audit records, access network, write
files, or enable runtime signing authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "RealHmacPolicyContractViolation",
    "RealHmacPolicyResult",
    "validate_real_hmac_policy",
    "validate_hmac_key_policy",
    "validate_hmac_signing_authority_policy",
    "validate_hmac_verifier_policy",
    "validate_hmac_signature_receipt_contract",
    "validate_hmac_rotation_policy",
    "validate_hmac_policy_realization_report",
]

_ALLOWED_DIGEST_ALGORITHMS = {"sha256", "sha384", "sha512"}
_ALLOWED_KEY_STATES = {"not_accessed_contract_only", "external_key_provider_required", "protected_storage_required"}
_ALLOWED_SIGNING_AUTHORITY = {"disabled_contract_only", "explicit_future_authorization_required"}
_ALLOWED_VERIFIER_MODES = {"policy_only_no_verification", "constant_time_compare_required_before_real_verification"}
_ALLOWED_ROTATION_MODES = {"policy_only_no_rotation_execution", "manual_rotation_plan_only"}
_FORBIDDEN_TRUE_FLAGS = (
    "real_hmac_signature_created",
    "hmac_verification_performed",
    "key_material_read",
    "key_material_persisted",
    "key_generation_performed",
    "signing_runtime_enabled",
    "verification_runtime_enabled",
    "secret_value_read",
    "secret_value_persisted",
    "plaintext_secret_allowed",
    "runtime_execution_performed",
    "network_accessed",
    "sqlite_schema_changed",
    "audit_append_performed",
)
_REQUIRED_POLICY_FLAGS = (
    "migration_receipt_required_before_real_signature",
    "protected_storage_contract_required",
    "human_authorization_required_before_key_access",
)


@dataclass(frozen=True)
class RealHmacPolicyResult:
    accepted: bool
    verdict: str
    contract_section: str
    failures: tuple[str, ...]


class RealHmacPolicyContractViolation(Exception):
    """Raised when a real HMAC policy contract receives a non-mapping payload."""


def validate_real_hmac_policy(payload: Mapping[str, Any]) -> RealHmacPolicyResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("contract_type") != "seos_real_hmac_policy_realization_contract_v1":
        failures.append("contract_type_invalid")
    if data.get("status") != "contract_only_no_real_signature":
        failures.append("status_invalid")
    _validate_digest_algorithms(data, failures)
    for flag in _REQUIRED_POLICY_FLAGS:
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    if data.get("verification_compare_rule") != "constant_time_compare_required_before_real_verification":
        failures.append("verification_compare_rule_invalid")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "policy")


def validate_hmac_key_policy(payload: Mapping[str, Any]) -> RealHmacPolicyResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "hmac_key_policy_contract_v1":
        failures.append("policy_type_invalid")
    for field in ("policy_id", "task_id", "key_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("key_state") not in _ALLOWED_KEY_STATES:
        failures.append("key_state_invalid")
    if data.get("key_material_location") != "not_recorded_in_this_slice":
        failures.append("key_material_location_invalid")
    if data.get("key_identifier_allowed") is not True:
        failures.append("key_identifier_allowed_required")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "key_policy")


def validate_hmac_signing_authority_policy(payload: Mapping[str, Any]) -> RealHmacPolicyResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "hmac_signing_authority_policy_contract_v1":
        failures.append("policy_type_invalid")
    for field in ("policy_id", "task_id", "signing_authority_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("signing_authority_state") not in _ALLOWED_SIGNING_AUTHORITY:
        failures.append("signing_authority_state_invalid")
    if data.get("real_signature_allowed") is not False:
        failures.append("real_signature_allowed_must_be_false")
    if data.get("human_authorization_required_before_signing") is not True:
        failures.append("human_authorization_required_before_signing_missing")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "signing_authority_policy")


def validate_hmac_verifier_policy(payload: Mapping[str, Any]) -> RealHmacPolicyResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "hmac_verifier_policy_contract_v1":
        failures.append("policy_type_invalid")
    for field in ("policy_id", "task_id", "verifier_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("verifier_mode") not in _ALLOWED_VERIFIER_MODES:
        failures.append("verifier_mode_invalid")
    if data.get("constant_time_compare_required") is not True:
        failures.append("constant_time_compare_required_missing")
    if data.get("verification_runtime_allowed") is not False:
        failures.append("verification_runtime_allowed_must_be_false")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "verifier_policy")


def validate_hmac_signature_receipt_contract(payload: Mapping[str, Any]) -> RealHmacPolicyResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("receipt_type") != "hmac_signature_receipt_contract_v1":
        failures.append("receipt_type_invalid")
    for field in ("receipt_id", "task_id", "key_policy_id", "signing_authority_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("receipt_mode") != "contract_only_no_real_signature":
        failures.append("receipt_mode_invalid")
    if data.get("signature_material_recorded") is not False:
        failures.append("signature_material_recorded_must_be_false")
    if data.get("digest_algorithm") not in _ALLOWED_DIGEST_ALGORITHMS:
        failures.append("digest_algorithm_invalid")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "signature_receipt_contract")


def validate_hmac_rotation_policy(payload: Mapping[str, Any]) -> RealHmacPolicyResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "hmac_rotation_policy_contract_v1":
        failures.append("policy_type_invalid")
    for field in ("policy_id", "task_id", "rotation_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("rotation_mode") not in _ALLOWED_ROTATION_MODES:
        failures.append("rotation_mode_invalid")
    if data.get("rotation_execution_allowed") is not False:
        failures.append("rotation_execution_allowed_must_be_false")
    if data.get("rotation_receipt_required_before_execution") is not True:
        failures.append("rotation_receipt_required_before_execution_missing")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "rotation_policy")


def validate_hmac_policy_realization_report(payload: Mapping[str, Any]) -> RealHmacPolicyResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("report_type") != "hmac_policy_realization_report_v1":
        failures.append("report_type_invalid")
    if data.get("contract_only") is not True:
        failures.append("contract_only_required")
    sections = data.get("validated_sections")
    if not isinstance(sections, list):
        failures.append("validated_sections_must_be_list")
    else:
        for section in ("policy", "key_policy", "signing_authority_policy", "verifier_policy", "signature_receipt_contract", "rotation_policy"):
            if section not in sections:
                failures.append(f"{section}_section_missing")
    if data.get("real_signature_ready") is not False:
        failures.append("real_signature_ready_must_be_false")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "report")


def _validate_digest_algorithms(data: Mapping[str, Any], failures: list[str]) -> None:
    algorithms = data.get("allowed_digest_algorithms")
    if not isinstance(algorithms, list) or not algorithms:
        failures.append("allowed_digest_algorithms_invalid")
        return
    unknown = sorted(set(algorithms) - _ALLOWED_DIGEST_ALGORITHMS)
    if unknown:
        failures.append("allowed_digest_algorithms_invalid")


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise RealHmacPolicyContractViolation("payload must be a mapping")
    return payload


def _reject_forbidden_true_flags(data: Mapping[str, Any], failures: list[str]) -> None:
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True:
            failures.append(f"{flag}_forbidden")


def _result(failures: list[str], section: str) -> RealHmacPolicyResult:
    unique = tuple(sorted(set(failures)))
    return RealHmacPolicyResult(
        accepted=not unique,
        verdict="accepted_contract_only" if not unique else "rejected_fail_closed",
        contract_section=section,
        failures=unique,
    )
