"""Runtime sealed receipt contracts.

This module defines sealed receipt contract validators for runtime/provider
transport attempts. It is contract-only: it does not perform live provider
calls, network access, environment reads, secret reads, SQLite mutation, audit
appends, protected storage implementation, real HMAC signing, Merkle tree
construction, zero-knowledge proof generation, or production autonomy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "RuntimeSealedReceiptContractViolation",
    "RuntimeSealedReceiptValidationResult",
    "validate_runtime_sealed_receipt_policy",
    "validate_transport_attempt_receipt",
    "validate_blocked_attempt_receipt",
    "validate_postcheck_receipt",
    "validate_receipt_chain",
]

_ALLOWED_MODES = {"disabled", "manual_dry_run"}
_REQUIRED_CHAIN_REFS = (
    "policy_receipt_ref",
    "transport_receipt_ref",
    "blocked_attempt_receipt_ref",
    "postcheck_receipt_ref",
)
_FORBIDDEN_TRUE_FLAGS = (
    "provider_live_call_performed",
    "transport_attempted",
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
class RuntimeSealedReceiptValidationResult:
    accepted: bool
    verdict: str
    failures: tuple[str, ...]


class RuntimeSealedReceiptContractViolation(Exception):
    """Raised when a sealed receipt contract receives a non-mapping payload."""


def validate_runtime_sealed_receipt_policy(payload: Mapping[str, Any]) -> RuntimeSealedReceiptValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "seos_runtime_sealed_receipt_v1":
        failures.append("policy_type_invalid")
    if data.get("status") != "contract_only":
        failures.append("status_invalid")
    if data.get("runtime_mode") not in _ALLOWED_MODES:
        failures.append("runtime_mode_invalid")
    for field in (
        "sealed_receipt_required",
        "transport_receipt_required",
        "blocked_attempt_receipt_required",
        "postcheck_receipt_required",
        "failure_quarantine_link_required",
        "receipt_chain_required",
    ):
        if data.get(field) is not True:
            failures.append(f"{field}_missing")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def validate_transport_attempt_receipt(payload: Mapping[str, Any]) -> RuntimeSealedReceiptValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    for field in ("receipt_id", "task_id", "transport_gate_id", "policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("receipt_type") != "transport_attempt_receipt":
        failures.append("receipt_type_invalid")
    if data.get("runtime_mode") not in _ALLOWED_MODES:
        failures.append("runtime_mode_invalid")
    if data.get("sealed") is not True:
        failures.append("sealed_required")
    if data.get("postcheck_required") is not True:
        failures.append("postcheck_required")
    if data.get("failure_quarantine_link_required") is not True:
        failures.append("failure_quarantine_link_required")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def validate_blocked_attempt_receipt(payload: Mapping[str, Any]) -> RuntimeSealedReceiptValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    for field in ("receipt_id", "task_id", "transport_gate_id", "policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("receipt_type") != "blocked_attempt_receipt":
        failures.append("receipt_type_invalid")
    if data.get("blocked") is not True:
        failures.append("blocked_required")
    if data.get("block_reason") not in {
        "provider_disabled",
        "manual_approval_missing",
        "policy_missing",
        "forbidden_runtime_claim",
    }:
        failures.append("block_reason_invalid")
    if data.get("sealed") is not True:
        failures.append("sealed_required")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def validate_postcheck_receipt(payload: Mapping[str, Any]) -> RuntimeSealedReceiptValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    for field in ("receipt_id", "task_id", "transport_gate_id", "policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("receipt_type") != "postcheck_receipt":
        failures.append("receipt_type_invalid")
    if data.get("postcheck_result") != "passed":
        failures.append("postcheck_result_not_passed")
    for field in ("sealed_receipt_present", "failure_quarantine_link_present", "health_gate_present"):
        if data.get(field) is not True:
            failures.append(f"{field}_required")
    if data.get("sealed") is not True:
        failures.append("sealed_required")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def validate_receipt_chain(payload: Mapping[str, Any]) -> RuntimeSealedReceiptValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("chain_type") != "runtime_sealed_receipt_chain":
        failures.append("chain_type_invalid")
    if not isinstance(data.get("chain_id"), str) or not data.get("chain_id"):
        failures.append("chain_id_required")
    if not isinstance(data.get("task_id"), str) or not data.get("task_id"):
        failures.append("task_id_required")
    for field in _REQUIRED_CHAIN_REFS:
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("chain_complete") is not True:
        failures.append("chain_complete_required")
    if data.get("final_verdict") not in {"sealed_receipt_chain_contract_ready", "blocked_fail_closed"}:
        failures.append("final_verdict_invalid")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise RuntimeSealedReceiptContractViolation("payload must be a mapping")
    return payload


def _reject_forbidden_true_flags(data: Mapping[str, Any], failures: list[str]) -> None:
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True:
            failures.append(f"{flag}_forbidden")


def _result(failures: list[str]) -> RuntimeSealedReceiptValidationResult:
    unique = tuple(sorted(set(failures)))
    return RuntimeSealedReceiptValidationResult(
        accepted=not unique,
        verdict="accepted_contract_only" if not unique else "rejected_fail_closed",
        failures=unique,
    )
