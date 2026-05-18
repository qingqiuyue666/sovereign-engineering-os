"""Deterministic local runtime receipts.

Observation timestamps are metadata only and are excluded from content hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = ["LocalRuntimeReceipt", "build_local_runtime_receipt"]

_POLICY_VERSION = "local-runtime-receipt-v1"
_CODE_VERSION = "0.1.0"


@dataclass(frozen=True)
class LocalRuntimeReceipt:
    """Immutable receipt for one bounded local runtime orchestration stage."""

    run_id: str
    task_id: str
    runtime_stage: str
    input_digest: str
    accepted: bool
    rejection_reason: str
    provider_dry_run_receipt_ref: str | None
    failure_bundle_ref: str | None
    content_hash: str
    observed_at: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "code_version": self.code_version,
            "failure_bundle_ref": self.failure_bundle_ref,
            "input_digest": self.input_digest,
            "policy_version": self.policy_version,
            "provider_dry_run_receipt_ref": self.provider_dry_run_receipt_ref,
            "rejection_reason": self.rejection_reason,
            "run_id": self.run_id,
            "runtime_stage": self.runtime_stage,
            "task_id": self.task_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_local_runtime_receipt(
    *,
    run_id: str,
    task_id: str,
    runtime_stage: str,
    input_digest: str,
    accepted: bool,
    rejection_reason: str = "",
    provider_dry_run_receipt_ref: str | None = None,
    failure_bundle_ref: str | None = None,
    observed_at: str | None = None,
    policy_version: str = _POLICY_VERSION,
    code_version: str = _CODE_VERSION,
) -> LocalRuntimeReceipt:
    """Build a receipt whose hash excludes wall-clock observation metadata."""

    _validate_common(run_id, task_id, runtime_stage, input_digest, policy_version, code_version)
    if not isinstance(accepted, bool):
        raise ValueError("accepted_must_be_bool")
    if not isinstance(rejection_reason, str):
        raise ValueError("rejection_reason_must_be_string")
    if accepted and rejection_reason:
        raise ValueError("accepted_receipt_rejection_reason_must_be_empty")
    if not accepted and not rejection_reason:
        raise ValueError("rejected_receipt_rejection_reason_required")
    if provider_dry_run_receipt_ref is not None and not strict_nonempty_string(provider_dry_run_receipt_ref):
        raise ValueError("provider_dry_run_receipt_ref_must_be_nonempty_string")
    if failure_bundle_ref is not None and not strict_nonempty_string(failure_bundle_ref):
        raise ValueError("failure_bundle_ref_must_be_nonempty_string")

    observed = _observed_at(observed_at)
    material = {
        "accepted": accepted,
        "code_version": code_version,
        "failure_bundle_ref": failure_bundle_ref,
        "input_digest": input_digest,
        "policy_version": policy_version,
        "provider_dry_run_receipt_ref": provider_dry_run_receipt_ref,
        "rejection_reason": rejection_reason,
        "run_id": run_id,
        "runtime_stage": runtime_stage,
        "task_id": task_id,
    }
    return LocalRuntimeReceipt(
        run_id=run_id,
        task_id=task_id,
        runtime_stage=runtime_stage,
        input_digest=input_digest,
        accepted=accepted,
        rejection_reason=rejection_reason,
        provider_dry_run_receipt_ref=provider_dry_run_receipt_ref,
        failure_bundle_ref=failure_bundle_ref,
        content_hash=digest_payload(material),
        observed_at=observed,
        policy_version=policy_version,
        code_version=code_version,
    )


def _validate_common(
    run_id: str,
    task_id: str,
    runtime_stage: str,
    input_digest: str,
    policy_version: str,
    code_version: str,
) -> None:
    for field, value in (
        ("run_id", run_id),
        ("task_id", task_id),
        ("runtime_stage", runtime_stage),
        ("policy_version", policy_version),
        ("code_version", code_version),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if not strict_digest(input_digest):
        raise ValueError("input_digest_must_be_valid_digest")


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
