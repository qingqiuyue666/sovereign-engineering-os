"""Provider worker boundary preflight for symbolic local metadata only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string
from kernel.runtime.operator_review_receipt import ApprovalReceipt, validate_approval_receipt

__all__ = ["ProviderWorkerPreflightReceipt", "run_provider_worker_boundary_preflight"]

_POLICY_VERSION = "provider-worker-boundary-preflight-v1"
_CODE_VERSION = "0.1.0"
_FORBIDDEN_FIELD_MARKERS = (
    "raw_prompt",
    "raw_response",
    "raw_provider_response",
    "raw_exception",
    "raw_traceback",
    "env",
    "secret",
    "credential",
    "token",
    "api_key",
    "password",
    "private_key",
    "authorization",
)


@dataclass(frozen=True)
class ProviderWorkerPreflightReceipt:
    preflight_id: str
    task_id: str
    session_id: str
    provider_task_ref: str
    budget_policy_ref: str
    approval_receipt_hash: str
    preflight_passed: bool
    reasons: tuple[str, ...]
    provider_execution_permitted: bool = False
    production_autonomy_enabled: bool = False
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_receipt_hash": self.approval_receipt_hash,
            "budget_policy_ref": self.budget_policy_ref,
            "code_version": self.code_version,
            "preflight_id": self.preflight_id,
            "preflight_passed": self.preflight_passed,
            "production_autonomy_enabled": self.production_autonomy_enabled,
            "provider_execution_permitted": self.provider_execution_permitted,
            "provider_task_ref": self.provider_task_ref,
            "policy_version": self.policy_version,
            "reasons": list(self.reasons),
            "session_id": self.session_id,
            "task_id": self.task_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def run_provider_worker_boundary_preflight(
    *,
    preflight_id: str,
    task_metadata: dict[str, object],
    approval_receipts: tuple[ApprovalReceipt, ...],
    observed_at: str | None = None,
) -> ProviderWorkerPreflightReceipt:
    """Validate symbolic provider-task metadata without executing it."""

    if not strict_nonempty_string(preflight_id):
        raise ValueError("preflight_id_must_be_nonempty_string")
    if not isinstance(task_metadata, dict):
        raise ValueError("task_metadata_must_be_dict")
    if not isinstance(approval_receipts, tuple):
        raise ValueError("approval_receipts_must_be_tuple")

    observed = _observed_at(observed_at)
    reasons: list[str] = []
    task_id = _string_field(task_metadata, "task_id", reasons)
    session_id = _string_field(task_metadata, "session_id", reasons)
    provider_task_ref = _string_field(task_metadata, "provider_task_ref", reasons)
    budget_policy_ref = _string_field(task_metadata, "budget_policy_ref", reasons)
    approval_hash = _string_field(task_metadata, "approval_receipt_hash", reasons)

    try:
        _reject_forbidden_fields(task_metadata)
    except ValueError as exc:
        reasons.append(str(exc))
    for field, value in (
        ("provider_task_ref", provider_task_ref),
        ("budget_policy_ref", budget_policy_ref),
    ):
        if value and not _is_symbolic_ref(value):
            reasons.append(f"{field}_must_be_symbolic_ref")
    if approval_hash and not strict_digest(approval_hash):
        reasons.append("approval_receipt_hash_must_be_valid_digest")
    if not budget_policy_ref:
        reasons.append("budget_policy_ref_missing")
    if task_metadata.get("production_autonomy_requested") is not False:
        reasons.append("production_autonomy_request_forbidden")
    if task_metadata.get("execution_mode") != "preflight_only":
        reasons.append("execution_mode_must_be_preflight_only")

    valid_approval_hashes: set[str] = set()
    for receipt in approval_receipts:
        if not validate_approval_receipt(receipt):
            reasons.append("approval_receipt_invalid")
            continue
        valid_approval_hashes.add(receipt.content_hash)
    if approval_hash not in valid_approval_hashes:
        reasons.append("approval_receipt_missing")

    receipt = ProviderWorkerPreflightReceipt(
        preflight_id=preflight_id,
        task_id=task_id,
        session_id=session_id,
        provider_task_ref=provider_task_ref,
        budget_policy_ref=budget_policy_ref,
        approval_receipt_hash=approval_hash,
        preflight_passed=not reasons,
        reasons=tuple(reasons),
        provider_execution_permitted=False,
        production_autonomy_enabled=False,
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(receipt)


def _string_field(payload: dict[str, object], field: str, reasons: list[str]) -> str:
    value = payload.get(field)
    if not strict_nonempty_string(value):
        reasons.append(f"{field}_must_be_nonempty_string")
        return ""
    return value


def _is_symbolic_ref(value: str) -> bool:
    if not strict_nonempty_string(value):
        return False
    return all(char.isalnum() or char in {"-", "_", ".", ":"} for char in value)


def _with_hash(receipt: ProviderWorkerPreflightReceipt) -> ProviderWorkerPreflightReceipt:
    return ProviderWorkerPreflightReceipt(
        preflight_id=receipt.preflight_id,
        task_id=receipt.task_id,
        session_id=receipt.session_id,
        provider_task_ref=receipt.provider_task_ref,
        budget_policy_ref=receipt.budget_policy_ref,
        approval_receipt_hash=receipt.approval_receipt_hash,
        preflight_passed=receipt.preflight_passed,
        reasons=receipt.reasons,
        provider_execution_permitted=receipt.provider_execution_permitted,
        production_autonomy_enabled=receipt.production_autonomy_enabled,
        policy_version=receipt.policy_version,
        code_version=receipt.code_version,
        content_hash=digest_payload(receipt.deterministic_material()),
        observed_at=receipt.observed_at,
    )


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in _FORBIDDEN_FIELD_MARKERS):
                raise ValueError("forbidden_field_present")
            _reject_forbidden_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_fields(nested)
    elif isinstance(value, tuple):
        for nested in value:
            _reject_forbidden_fields(nested)


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
