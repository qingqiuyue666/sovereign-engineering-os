"""Final runtime completion contracts.

This module defines disabled-by-default final runtime track contracts. It does
not execute provider calls, access network, read secrets, mutate SQLite, append
audit records, implement protected storage, generate real HMAC signatures,
build Merkle trees, or provide production autonomy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "FinalRuntimeContractViolation",
    "FinalRuntimeValidationResult",
    "validate_final_runtime_track_map",
    "validate_runtime_preflight",
    "validate_runtime_receipt",
    "validate_post_run_health",
    "validate_failure_quarantine_link",
]

_ALLOWED_TRACK_STATUS = {"disabled_by_default", "manual_preflight_required"}
_ALLOWED_RUNTIME_MODES = {"disabled", "manual_dry_run"}
_REQUIRED_HEALTH_GATES = (
    "test-root-integrity",
    "test-sealed-evidence-coverage",
    "test-evidence-proof-contract",
    "test-evidence-proof-fixtures",
    "test-final-runtime-contracts",
    "test-gated-provider-transport",
    "test-runtime-sealed-receipt",
    "test-generic-payload-shadow",
    "test-protected-evidence-storage",
    "test-real-hmac-policy-realization",
    "test-schemas",
    "test-tracer-bullet",
    "test-acceptance",
    "diff-check",
)
_FORBIDDEN_TRUE_FLAGS = (
    "provider_call_performed",
    "network_accessed",
    "secret_value_read",
    "secret_value_persisted",
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
class FinalRuntimeValidationResult:
    accepted: bool
    verdict: str
    failures: tuple[str, ...]


class FinalRuntimeContractViolation(Exception):
    """Raised when a runtime contract receives a non-mapping payload."""


def validate_final_runtime_track_map(payload: Mapping[str, Any]) -> FinalRuntimeValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("track_type") != "seos_final_runtime_completion_track_v1": failures.append("track_type_invalid")
    if data.get("status") not in _ALLOWED_TRACK_STATUS: failures.append("track_status_invalid")
    if data.get("runtime_mode") not in _ALLOWED_RUNTIME_MODES: failures.append("runtime_mode_invalid")
    _reject_forbidden_true_flags(data, failures)
    if data.get("manual_preflight_required") is not True: failures.append("manual_preflight_required")
    if data.get("default_disabled") is not True: failures.append("default_disabled_required")
    stages = data.get("allowed_stages")
    if not isinstance(stages, list) or "preflight" not in stages or "receipt" not in stages: failures.append("allowed_stages_invalid")
    if data.get("required_health_gates") != list(_REQUIRED_HEALTH_GATES): failures.append("required_health_gates_invalid")
    return _result(failures)


def validate_runtime_preflight(payload: Mapping[str, Any]) -> FinalRuntimeValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    for field in ("preflight_id", "task_id", "runtime_track_id"):
        if not isinstance(data.get(field), str) or not data.get(field): failures.append(f"{field}_required")
    if data.get("operator_approval_required") is not True: failures.append("operator_approval_required")
    if data.get("operator_approval_present") is not True: failures.append("operator_approval_missing")
    if data.get("runtime_mode") not in _ALLOWED_RUNTIME_MODES: failures.append("runtime_mode_invalid")
    if data.get("provider_transport_status") != "disabled": failures.append("provider_transport_must_be_disabled")
    for field in ("evidence_policy_status", "proof_policy_status", "failure_quarantine_policy_status", "health_gate_status"):
        if data.get(field) != "passed": failures.append(f"{field}_not_passed")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def validate_runtime_receipt(payload: Mapping[str, Any]) -> FinalRuntimeValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    for field in ("receipt_id", "task_id", "runtime_track_id", "preflight_id"):
        if not isinstance(data.get(field), str) or not data.get(field): failures.append(f"{field}_required")
    if data.get("preflight_result") != "passed": failures.append("preflight_result_not_passed")
    if data.get("execution_attempted") is not False: failures.append("execution_attempted_must_be_false")
    if data.get("execution_mode") not in _ALLOWED_RUNTIME_MODES: failures.append("execution_mode_invalid")
    _reject_forbidden_true_flags(data, failures)
    for field in ("sealed_evidence_refs", "proof_refs", "failure_quarantine_refs"):
        if not isinstance(data.get(field), list): failures.append(f"{field}_must_be_list")
    if data.get("post_run_health_result") not in {"not_run", "passed"}: failures.append("post_run_health_result_invalid")
    if data.get("final_verdict") not in {"manual_dry_run_receipt_only", "blocked_fail_closed"}: failures.append("final_verdict_invalid")
    return _result(failures)


def validate_post_run_health(payload: Mapping[str, Any]) -> FinalRuntimeValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if not isinstance(data.get("post_run_health_id"), str) or not data.get("post_run_health_id"): failures.append("post_run_health_id_required")
    if data.get("required_health_gates") != list(_REQUIRED_HEALTH_GATES): failures.append("required_health_gates_invalid")
    results = data.get("gate_results")
    if not isinstance(results, Mapping):
        failures.append("gate_results_must_be_mapping"); results = {}
    for gate in _REQUIRED_HEALTH_GATES:
        if results.get(gate) != "passed": failures.append(f"{gate}_not_passed")
    if data.get("worktree_clean") is not True: failures.append("worktree_not_clean")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def validate_failure_quarantine_link(payload: Mapping[str, Any]) -> FinalRuntimeValidationResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    for field in ("link_id", "task_id", "runtime_track_id", "failure_quarantine_policy_status"):
        if not isinstance(data.get(field), str) or not data.get(field): failures.append(f"{field}_required")
    if data.get("failure_quarantine_policy_status") != "linked_contract_only": failures.append("failure_quarantine_policy_status_invalid")
    for field in ("sealed_evidence_refs", "proof_refs", "quarantine_refs"):
        if not isinstance(data.get(field), list): failures.append(f"{field}_must_be_list")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures)


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping): raise FinalRuntimeContractViolation("payload must be a mapping")
    return payload


def _reject_forbidden_true_flags(data: Mapping[str, Any], failures: list[str]) -> None:
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True: failures.append(f"{flag}_forbidden")


def _result(failures: list[str]) -> FinalRuntimeValidationResult:
    unique = tuple(sorted(set(failures)))
    return FinalRuntimeValidationResult(accepted=not unique, verdict="accepted_contract_only" if not unique else "rejected_fail_closed", failures=unique)
