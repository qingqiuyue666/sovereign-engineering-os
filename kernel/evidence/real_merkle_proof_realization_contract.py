"""Real Merkle proof realization contracts.

This module defines contract-only Merkle proof validation. It does not build a
Merkle tree, verify Merkle proofs, publish root commitments, mutate evidence
append behavior, persist raw evidence, mutate SQLite, append audit records,
access network, write files, or enable runtime proof authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "RealMerkleProofContractViolation",
    "RealMerkleProofResult",
    "validate_real_merkle_policy",
    "validate_merkle_tree_manifest",
    "validate_merkle_leaf_digest_policy",
    "validate_merkle_node_digest_policy",
    "validate_merkle_proof_path_contract",
    "validate_merkle_verifier_receipt_contract",
    "validate_merkle_root_commitment_receipt_contract",
    "validate_merkle_policy_realization_report",
]

_ALLOWED_DIGEST_ALGORITHMS = {"sha256", "sha384", "sha512"}
_ALLOWED_TREE_MODES = {"contract_only_no_tree_build", "future_authorization_required"}
_ALLOWED_NODE_POLICIES = {"ordered_child_digest_contract_only", "domain_separated_child_digest_contract_only"}
_ALLOWED_PROOF_MODES = {"sibling_digest_path_contract_only", "policy_only_no_verification"}
_FORBIDDEN_TRUE_FLAGS = (
    "real_merkle_tree_built",
    "merkle_proof_verified",
    "root_commitment_published",
    "evidence_append_behavior_changed",
    "raw_evidence_store_allowed",
    "protected_storage_implemented",
    "secret_value_read",
    "secret_value_persisted",
    "runtime_execution_performed",
    "network_accessed",
    "sqlite_schema_changed",
    "audit_append_performed",
)
_REQUIRED_POLICY_FLAGS = (
    "migration_receipt_required_before_tree_mutation",
    "generic_payload_enforcement_required_before_append_mutation",
    "human_authorization_required_before_root_publication",
)


@dataclass(frozen=True)
class RealMerkleProofResult:
    accepted: bool
    verdict: str
    contract_section: str
    failures: tuple[str, ...]


class RealMerkleProofContractViolation(Exception):
    """Raised when a Merkle proof contract receives a non-mapping payload."""


def validate_real_merkle_policy(payload: Mapping[str, Any]) -> RealMerkleProofResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("contract_type") != "seos_real_merkle_proof_realization_contract_v1":
        failures.append("contract_type_invalid")
    if data.get("status") != "contract_only_no_tree_mutation":
        failures.append("status_invalid")
    _validate_digest_algorithms(data, failures)
    for flag in _REQUIRED_POLICY_FLAGS:
        if data.get(flag) is not True:
            failures.append(f"{flag}_missing")
    if data.get("leaf_payload_policy") != "digest_only_no_raw_payload":
        failures.append("leaf_payload_policy_invalid")
    if data.get("node_policy") not in _ALLOWED_NODE_POLICIES:
        failures.append("node_policy_invalid")
    if data.get("proof_path_policy") != "sibling_digest_path_contract_only":
        failures.append("proof_path_policy_invalid")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "policy")


def validate_merkle_tree_manifest(payload: Mapping[str, Any]) -> RealMerkleProofResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("manifest_type") != "merkle_tree_manifest_contract_v1":
        failures.append("manifest_type_invalid")
    for field in ("manifest_id", "task_id", "tree_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("tree_mode") not in _ALLOWED_TREE_MODES:
        failures.append("tree_mode_invalid")
    if data.get("contract_only") is not True:
        failures.append("contract_only_required")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "tree_manifest")


def validate_merkle_leaf_digest_policy(payload: Mapping[str, Any]) -> RealMerkleProofResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "merkle_leaf_digest_policy_contract_v1":
        failures.append("policy_type_invalid")
    for field in ("policy_id", "task_id", "tree_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("leaf_payload_policy") != "digest_only_no_raw_payload":
        failures.append("leaf_payload_policy_invalid")
    if data.get("raw_leaf_payload_allowed") is not False:
        failures.append("raw_leaf_payload_allowed_must_be_false")
    if data.get("digest_algorithm") not in _ALLOWED_DIGEST_ALGORITHMS:
        failures.append("digest_algorithm_invalid")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "leaf_digest_policy")


def validate_merkle_node_digest_policy(payload: Mapping[str, Any]) -> RealMerkleProofResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("policy_type") != "merkle_node_digest_policy_contract_v1":
        failures.append("policy_type_invalid")
    for field in ("policy_id", "task_id", "tree_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("node_policy") not in _ALLOWED_NODE_POLICIES:
        failures.append("node_policy_invalid")
    if data.get("ordered_child_digests_required") is not True:
        failures.append("ordered_child_digests_required_missing")
    if data.get("domain_separation_required_before_real_tree") is not True:
        failures.append("domain_separation_required_before_real_tree_missing")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "node_digest_policy")


def validate_merkle_proof_path_contract(payload: Mapping[str, Any]) -> RealMerkleProofResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("proof_type") != "merkle_proof_path_contract_v1":
        failures.append("proof_type_invalid")
    for field in ("proof_id", "task_id", "tree_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("proof_mode") not in _ALLOWED_PROOF_MODES:
        failures.append("proof_mode_invalid")
    if data.get("sibling_digest_path_recorded") is not True:
        failures.append("sibling_digest_path_recorded_required")
    if data.get("raw_sibling_payload_allowed") is not False:
        failures.append("raw_sibling_payload_allowed_must_be_false")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "proof_path_contract")


def validate_merkle_verifier_receipt_contract(payload: Mapping[str, Any]) -> RealMerkleProofResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("receipt_type") != "merkle_verifier_receipt_contract_v1":
        failures.append("receipt_type_invalid")
    for field in ("receipt_id", "task_id", "proof_id", "tree_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("verification_mode") != "contract_only_no_verification":
        failures.append("verification_mode_invalid")
    if data.get("verification_result_recorded") is not False:
        failures.append("verification_result_recorded_must_be_false")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "verifier_receipt_contract")


def validate_merkle_root_commitment_receipt_contract(payload: Mapping[str, Any]) -> RealMerkleProofResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("receipt_type") != "merkle_root_commitment_receipt_contract_v1":
        failures.append("receipt_type_invalid")
    for field in ("receipt_id", "task_id", "tree_policy_id"):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")
    if data.get("root_commitment_mode") != "contract_only_no_publication":
        failures.append("root_commitment_mode_invalid")
    if data.get("root_digest_material_recorded") is not False:
        failures.append("root_digest_material_recorded_must_be_false")
    if data.get("human_authorization_required_before_root_publication") is not True:
        failures.append("human_authorization_required_before_root_publication_missing")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "root_commitment_receipt_contract")


def validate_merkle_policy_realization_report(payload: Mapping[str, Any]) -> RealMerkleProofResult:
    data = _require_mapping(payload)
    failures: list[str] = []
    if data.get("report_type") != "merkle_policy_realization_report_v1":
        failures.append("report_type_invalid")
    if data.get("contract_only") is not True:
        failures.append("contract_only_required")
    sections = data.get("validated_sections")
    if not isinstance(sections, list):
        failures.append("validated_sections_must_be_list")
    else:
        for section in ("policy", "tree_manifest", "leaf_digest_policy", "node_digest_policy", "proof_path_contract", "verifier_receipt_contract", "root_commitment_receipt_contract"):
            if section not in sections:
                failures.append(f"{section}_section_missing")
    if data.get("real_tree_ready") is not False:
        failures.append("real_tree_ready_must_be_false")
    _reject_forbidden_true_flags(data, failures)
    return _result(failures, "report")


def _validate_digest_algorithms(data: Mapping[str, Any], failures: list[str]) -> None:
    algorithms = data.get("allowed_digest_algorithms")
    if not isinstance(algorithms, list) or not algorithms:
        failures.append("allowed_digest_algorithms_invalid")
        return
    if sorted(set(algorithms) - _ALLOWED_DIGEST_ALGORITHMS):
        failures.append("allowed_digest_algorithms_invalid")


def _require_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise RealMerkleProofContractViolation("payload must be a mapping")
    return payload


def _reject_forbidden_true_flags(data: Mapping[str, Any], failures: list[str]) -> None:
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if data.get(flag) is True:
            failures.append(f"{flag}_forbidden")


def _result(failures: list[str], section: str) -> RealMerkleProofResult:
    unique = tuple(sorted(set(failures)))
    return RealMerkleProofResult(
        accepted=not unique,
        verdict="accepted_contract_only" if not unique else "rejected_fail_closed",
        contract_section=section,
        failures=unique,
    )
