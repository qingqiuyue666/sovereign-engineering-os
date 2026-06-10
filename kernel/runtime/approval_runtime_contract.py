"""Approval runtime admission contract v1.

This module defines the digest-only boundary for turning a human operator
decision into an auditable approval admission receipt. It does not persist,
execute, queue work, call providers, open browsers, or read local environment
state. Timestamps are metadata and are excluded from deterministic hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "ApprovalRuntimeRequest",
    "ApprovalRuntimeDecision",
    "ApprovalRuntimeAdmissionReceipt",
    "build_approval_runtime_request",
    "build_approval_runtime_decision",
    "admit_approval_runtime_decision",
    "validate_approval_runtime_request",
    "validate_approval_runtime_decision",
    "validate_approval_runtime_admission_receipt",
]

_CONTRACT_VERSION = "approval-runtime-contract-v1"
_CODE_VERSION = "0.1.0"

_ALLOWED_REQUESTED_ACTIONS = frozenset(
    {
        "approve_next_manual_stage",
        "reject_with_rollback",
        "defer_human_review",
    }
)
_ALLOWED_OPERATOR_ACTIONS = frozenset({"approved", "rejected", "deferred"})
_APPROVAL_SCOPE = "manual_next_stage_only"

_FORBIDDEN_KEY_FRAGMENTS = (
    "api_key",
    "argv",
    "body",
    "browser",
    "command",
    "credential",
    "cwd",
    "dcc",
    "env",
    "executable",
    "mcp",
    "password",
    "private_key",
    "provider_response",
    "raw",
    "secret",
    "stderr",
    "stdout",
    "child_process",
    "timeout",
)
_FORBIDDEN_EXACT_KEYS = frozenset(
    {
        "content",
        "filesystem_path",
        "output",
        "path",
        "payload",
        "prompt",
        "text",
        "value",
    }
)


@dataclass(frozen=True)
class ApprovalRuntimeRequest:
    """Digest-only request for an operator approval decision."""

    approval_request_id: str
    task_id: str
    run_id: str
    review_packet_hash: str
    promotion_receipt_hash: str
    wal_head_hash: str
    artifact_manifest_hash: str
    snapshot_reconstruction_hash: str
    capability_token_hash: str
    risk_decision_hash: str
    requested_action: str
    human_invoked: bool
    production_autonomy_requested: bool
    live_execution_requested: bool
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    request_hash: str = ""
    created_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_request_id": self.approval_request_id,
            "artifact_manifest_hash": self.artifact_manifest_hash,
            "capability_token_hash": self.capability_token_hash,
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "human_invoked": self.human_invoked,
            "live_execution_requested": self.live_execution_requested,
            "production_autonomy_requested": self.production_autonomy_requested,
            "promotion_receipt_hash": self.promotion_receipt_hash,
            "requested_action": self.requested_action,
            "review_packet_hash": self.review_packet_hash,
            "risk_decision_hash": self.risk_decision_hash,
            "run_id": self.run_id,
            "snapshot_reconstruction_hash": self.snapshot_reconstruction_hash,
            "task_id": self.task_id,
            "wal_head_hash": self.wal_head_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["created_at"] = self.created_at
        payload["request_hash"] = self.request_hash
        return payload


@dataclass(frozen=True)
class ApprovalRuntimeDecision:
    """Digest-only human decision bound to an approval runtime request."""

    approval_decision_id: str
    approval_request_hash: str
    task_id: str
    run_id: str
    operator_id_hash: str
    operator_action: str
    decision_reason_code: str
    approval_scope: str
    rollback_plan_hash: str | None
    human_attested: bool
    production_autonomy_enabled: bool
    live_execution_enabled: bool
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    decision_hash: str = ""
    decided_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_decision_id": self.approval_decision_id,
            "approval_request_hash": self.approval_request_hash,
            "approval_scope": self.approval_scope,
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "decision_reason_code": self.decision_reason_code,
            "human_attested": self.human_attested,
            "live_execution_enabled": self.live_execution_enabled,
            "operator_action": self.operator_action,
            "operator_id_hash": self.operator_id_hash,
            "production_autonomy_enabled": self.production_autonomy_enabled,
            "rollback_plan_hash": self.rollback_plan_hash,
            "run_id": self.run_id,
            "task_id": self.task_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["decided_at"] = self.decided_at
        payload["decision_hash"] = self.decision_hash
        return payload


@dataclass(frozen=True)
class ApprovalRuntimeAdmissionReceipt:
    """Deterministic receipt emitted after an approval decision is admitted."""

    approval_request_hash: str
    approval_decision_hash: str
    task_id: str
    run_id: str
    operator_action: str
    accepted: bool
    next_state: str
    wal_record_hash: str
    operator_receipt_hash: str | None
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    admission_hash: str = ""
    admitted_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "approval_decision_hash": self.approval_decision_hash,
            "approval_request_hash": self.approval_request_hash,
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "next_state": self.next_state,
            "operator_action": self.operator_action,
            "operator_receipt_hash": self.operator_receipt_hash,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["admission_hash"] = self.admission_hash
        payload["admitted_at"] = self.admitted_at
        return payload


def build_approval_runtime_request(
    payload: Mapping[str, Any],
    *,
    created_at: str | None = None,
) -> ApprovalRuntimeRequest:
    """Build a validated digest-only approval runtime request."""

    _reject_forbidden_material(payload)
    _require_mapping(payload)

    approval_request_id = _string_field(payload, "approval_request_id")
    task_id = _string_field(payload, "task_id")
    run_id = _string_field(payload, "run_id")
    requested_action = _string_field(payload, "requested_action")
    human_invoked = _bool_field(payload, "human_invoked")
    production_autonomy_requested = _bool_field(payload, "production_autonomy_requested")
    live_execution_requested = _bool_field(payload, "live_execution_requested")

    if requested_action not in _ALLOWED_REQUESTED_ACTIONS:
        raise ValueError("requested_action_not_allowed")
    if human_invoked is not True:
        raise ValueError("approval_request_must_be_human_invoked")
    if production_autonomy_requested is not False:
        raise ValueError("production_autonomy_must_not_be_requested")
    if live_execution_requested is not False:
        raise ValueError("live_execution_must_not_be_requested")

    material = {
        "approval_request_id": approval_request_id,
        "artifact_manifest_hash": _digest_field(payload, "artifact_manifest_hash"),
        "capability_token_hash": _digest_field(payload, "capability_token_hash"),
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "human_invoked": human_invoked,
        "live_execution_requested": live_execution_requested,
        "production_autonomy_requested": production_autonomy_requested,
        "promotion_receipt_hash": _digest_field(payload, "promotion_receipt_hash"),
        "requested_action": requested_action,
        "review_packet_hash": _digest_field(payload, "review_packet_hash"),
        "risk_decision_hash": _digest_field(payload, "risk_decision_hash"),
        "run_id": run_id,
        "snapshot_reconstruction_hash": _digest_field(payload, "snapshot_reconstruction_hash"),
        "task_id": task_id,
        "wal_head_hash": _digest_field(payload, "wal_head_hash"),
    }
    observed = _observed_at(created_at)
    return ApprovalRuntimeRequest(
        approval_request_id=approval_request_id,
        task_id=task_id,
        run_id=run_id,
        review_packet_hash=str(material["review_packet_hash"]),
        promotion_receipt_hash=str(material["promotion_receipt_hash"]),
        wal_head_hash=str(material["wal_head_hash"]),
        artifact_manifest_hash=str(material["artifact_manifest_hash"]),
        snapshot_reconstruction_hash=str(material["snapshot_reconstruction_hash"]),
        capability_token_hash=str(material["capability_token_hash"]),
        risk_decision_hash=str(material["risk_decision_hash"]),
        requested_action=requested_action,
        human_invoked=human_invoked,
        production_autonomy_requested=production_autonomy_requested,
        live_execution_requested=live_execution_requested,
        request_hash=digest_payload(material),
        created_at=observed,
    )


def build_approval_runtime_decision(
    payload: Mapping[str, Any],
    *,
    decided_at: str | None = None,
) -> ApprovalRuntimeDecision:
    """Build a validated human approval decision."""

    _reject_forbidden_material(payload)
    _require_mapping(payload)

    approval_decision_id = _string_field(payload, "approval_decision_id")
    task_id = _string_field(payload, "task_id")
    run_id = _string_field(payload, "run_id")
    operator_action = _string_field(payload, "operator_action")
    decision_reason_code = _string_field(payload, "decision_reason_code")
    approval_scope = _string_field(payload, "approval_scope")
    human_attested = _bool_field(payload, "human_attested")
    production_autonomy_enabled = _bool_field(payload, "production_autonomy_enabled")
    live_execution_enabled = _bool_field(payload, "live_execution_enabled")
    rollback_plan_hash = payload.get("rollback_plan_hash")

    if operator_action not in _ALLOWED_OPERATOR_ACTIONS:
        raise ValueError("operator_action_not_allowed")
    if approval_scope != _APPROVAL_SCOPE:
        raise ValueError("approval_scope_must_be_manual_next_stage_only")
    if human_attested is not True:
        raise ValueError("operator_decision_must_be_human_attested")
    if production_autonomy_enabled is not False:
        raise ValueError("production_autonomy_must_remain_disabled")
    if live_execution_enabled is not False:
        raise ValueError("live_execution_must_remain_disabled")
    if operator_action == "rejected" and rollback_plan_hash is None:
        raise ValueError("rejected_decision_requires_rollback_plan_hash")
    if operator_action != "rejected" and rollback_plan_hash is not None:
        raise ValueError("rollback_plan_hash_only_allowed_for_rejected_decision")
    if rollback_plan_hash is not None and not strict_digest(rollback_plan_hash):
        raise ValueError("rollback_plan_hash_must_be_valid_digest")

    material = {
        "approval_decision_id": approval_decision_id,
        "approval_request_hash": _digest_field(payload, "approval_request_hash"),
        "approval_scope": approval_scope,
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "decision_reason_code": decision_reason_code,
        "human_attested": human_attested,
        "live_execution_enabled": live_execution_enabled,
        "operator_action": operator_action,
        "operator_id_hash": _digest_field(payload, "operator_id_hash"),
        "production_autonomy_enabled": production_autonomy_enabled,
        "rollback_plan_hash": rollback_plan_hash,
        "run_id": run_id,
        "task_id": task_id,
    }
    observed = _observed_at(decided_at)
    return ApprovalRuntimeDecision(
        approval_decision_id=approval_decision_id,
        approval_request_hash=str(material["approval_request_hash"]),
        task_id=task_id,
        run_id=run_id,
        operator_id_hash=str(material["operator_id_hash"]),
        operator_action=operator_action,
        decision_reason_code=decision_reason_code,
        approval_scope=approval_scope,
        rollback_plan_hash=rollback_plan_hash,
        human_attested=human_attested,
        production_autonomy_enabled=production_autonomy_enabled,
        live_execution_enabled=live_execution_enabled,
        decision_hash=digest_payload(material),
        decided_at=observed,
    )


def admit_approval_runtime_decision(
    request: ApprovalRuntimeRequest,
    decision: ApprovalRuntimeDecision,
    *,
    wal_record_hash: str,
    operator_receipt_hash: str | None = None,
    admitted_at: str | None = None,
) -> ApprovalRuntimeAdmissionReceipt:
    """Admit a matching approval decision and emit a deterministic receipt."""

    if not validate_approval_runtime_request(request):
        raise ValueError("approval_runtime_request_invalid")
    if not validate_approval_runtime_decision(decision):
        raise ValueError("approval_runtime_decision_invalid")
    if not strict_digest(wal_record_hash):
        raise ValueError("wal_record_hash_must_be_valid_digest")
    if operator_receipt_hash is not None and not strict_digest(operator_receipt_hash):
        raise ValueError("operator_receipt_hash_must_be_valid_digest")
    if decision.approval_request_hash != request.request_hash:
        raise ValueError("decision_request_hash_mismatch")
    if decision.task_id != request.task_id or decision.run_id != request.run_id:
        raise ValueError("decision_identity_mismatch")
    if decision.operator_action == "approved" and request.requested_action != "approve_next_manual_stage":
        raise ValueError("approved_decision_requires_approval_request_action")
    if decision.operator_action == "rejected" and request.requested_action != "reject_with_rollback":
        raise ValueError("rejected_decision_requires_rejection_request_action")

    accepted = decision.operator_action == "approved"
    next_state = {
        "approved": "next_manual_stage_allowed",
        "rejected": "rollback_required",
        "deferred": "human_review_pending",
    }[decision.operator_action]
    material = {
        "accepted": accepted,
        "approval_decision_hash": decision.decision_hash,
        "approval_request_hash": request.request_hash,
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "next_state": next_state,
        "operator_action": decision.operator_action,
        "operator_receipt_hash": operator_receipt_hash,
        "run_id": request.run_id,
        "task_id": request.task_id,
        "wal_record_hash": wal_record_hash,
    }
    observed = _observed_at(admitted_at)
    return ApprovalRuntimeAdmissionReceipt(
        approval_request_hash=request.request_hash,
        approval_decision_hash=decision.decision_hash,
        task_id=request.task_id,
        run_id=request.run_id,
        operator_action=decision.operator_action,
        accepted=accepted,
        next_state=next_state,
        wal_record_hash=wal_record_hash,
        operator_receipt_hash=operator_receipt_hash,
        admission_hash=digest_payload(material),
        admitted_at=observed,
    )


def validate_approval_runtime_request(request: ApprovalRuntimeRequest) -> bool:
    if not isinstance(request, ApprovalRuntimeRequest):
        return False
    if not _common_identity_valid(request.approval_request_id, request.task_id, request.run_id):
        return False
    if request.requested_action not in _ALLOWED_REQUESTED_ACTIONS:
        return False
    if request.human_invoked is not True:
        return False
    if request.production_autonomy_requested is not False:
        return False
    if request.live_execution_requested is not False:
        return False
    for value in (
        request.review_packet_hash,
        request.promotion_receipt_hash,
        request.wal_head_hash,
        request.artifact_manifest_hash,
        request.snapshot_reconstruction_hash,
        request.capability_token_hash,
        request.risk_decision_hash,
    ):
        if not strict_digest(value):
            return False
    if not strict_nonempty_string(request.contract_version):
        return False
    if not strict_nonempty_string(request.code_version):
        return False
    return request.request_hash == digest_payload(request.deterministic_material())


def validate_approval_runtime_decision(decision: ApprovalRuntimeDecision) -> bool:
    if not isinstance(decision, ApprovalRuntimeDecision):
        return False
    if not _common_identity_valid(decision.approval_decision_id, decision.task_id, decision.run_id):
        return False
    if not strict_digest(decision.approval_request_hash):
        return False
    if not strict_digest(decision.operator_id_hash):
        return False
    if decision.operator_action not in _ALLOWED_OPERATOR_ACTIONS:
        return False
    if decision.approval_scope != _APPROVAL_SCOPE:
        return False
    if not strict_nonempty_string(decision.decision_reason_code):
        return False
    if decision.human_attested is not True:
        return False
    if decision.production_autonomy_enabled is not False:
        return False
    if decision.live_execution_enabled is not False:
        return False
    if decision.operator_action == "rejected":
        if not strict_digest(decision.rollback_plan_hash):
            return False
    elif decision.rollback_plan_hash is not None:
        return False
    if not strict_nonempty_string(decision.contract_version):
        return False
    if not strict_nonempty_string(decision.code_version):
        return False
    return decision.decision_hash == digest_payload(decision.deterministic_material())


def validate_approval_runtime_admission_receipt(
    receipt: ApprovalRuntimeAdmissionReceipt,
) -> bool:
    if not isinstance(receipt, ApprovalRuntimeAdmissionReceipt):
        return False
    if not strict_digest(receipt.approval_request_hash):
        return False
    if not strict_digest(receipt.approval_decision_hash):
        return False
    if not strict_nonempty_string(receipt.task_id):
        return False
    if not strict_nonempty_string(receipt.run_id):
        return False
    if receipt.operator_action not in _ALLOWED_OPERATOR_ACTIONS:
        return False
    if not strict_bool(receipt.accepted):
        return False
    if receipt.accepted is not (receipt.operator_action == "approved"):
        return False
    if receipt.next_state not in {
        "next_manual_stage_allowed",
        "rollback_required",
        "human_review_pending",
    }:
        return False
    if not strict_digest(receipt.wal_record_hash):
        return False
    if receipt.operator_receipt_hash is not None and not strict_digest(receipt.operator_receipt_hash):
        return False
    if not strict_nonempty_string(receipt.contract_version):
        return False
    if not strict_nonempty_string(receipt.code_version):
        return False
    return receipt.admission_hash == digest_payload(receipt.deterministic_material())


def _require_mapping(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("approval_runtime_payload_must_be_mapping")


def _string_field(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not strict_nonempty_string(value):
        raise ValueError(f"{field}_must_be_nonempty_string")
    return str(value)


def _digest_field(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not strict_digest(value):
        raise ValueError(f"{field}_must_be_valid_digest")
    return str(value)


def _bool_field(payload: Mapping[str, Any], field: str) -> bool:
    value = payload.get(field)
    if not strict_bool(value):
        raise ValueError(f"{field}_must_be_bool")
    return bool(value)


def _common_identity_valid(record_id: str, task_id: str, run_id: str) -> bool:
    return (
        strict_nonempty_string(record_id)
        and strict_nonempty_string(task_id)
        and strict_nonempty_string(run_id)
    )


def _reject_forbidden_material(value: Any, *, path: str = "") -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("approval_runtime_keys_must_be_strings")
            key = raw_key.lower()
            key_path = f"{path}.{raw_key}" if path else raw_key
            if key in _FORBIDDEN_EXACT_KEYS:
                raise ValueError(f"forbidden_raw_material_field_{key_path}")
            if any(fragment in key for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                raise ValueError(f"forbidden_raw_material_field_{key_path}")
            _reject_forbidden_material(nested, path=key_path)
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_forbidden_material(nested, path=f"{path}[{index}]")


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("timestamp_must_be_nonempty_string")
    return value
