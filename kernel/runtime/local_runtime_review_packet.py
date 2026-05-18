"""Deterministic manual review packet for local runtime results.

This module builds review packets that are eligible for human review gates.
No provider calls, network access, secrets, env reads, or execution happen here.

Observation timestamps are metadata only and are excluded from content hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "LocalRuntimeReviewPacket",
    "build_review_packet",
    "validate_review_packet_material",
]

_POLICY_VERSION = "local-runtime-review-packet-v1"
_CODE_VERSION = "0.1.0"


@dataclass(frozen=True)
class LocalRuntimeReviewPacket:
    """Immutable review packet for manual inspection of a dry-run local runtime result."""

    run_id: str
    task_id: str
    runtime_receipt_hash: str
    runtime_accepted: bool
    guard_result_summary: str
    failure_bundle_ref: str | None
    provider_dry_run_receipt_ref: str | None
    audit_chain_head: str
    state_transition_hashes: tuple[str, ...]
    deterministic_input_digest: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "audit_chain_head": self.audit_chain_head,
            "code_version": self.code_version,
            "deterministic_input_digest": self.deterministic_input_digest,
            "failure_bundle_ref": self.failure_bundle_ref,
            "guard_result_summary": self.guard_result_summary,
            "policy_version": self.policy_version,
            "provider_dry_run_receipt_ref": self.provider_dry_run_receipt_ref,
            "run_id": self.run_id,
            "runtime_accepted": self.runtime_accepted,
            "runtime_receipt_hash": self.runtime_receipt_hash,
            "state_transition_hashes": list(self.state_transition_hashes),
            "task_id": self.task_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_review_packet(
    *,
    run_id: str,
    task_id: str,
    runtime_receipt_hash: str,
    runtime_accepted: bool,
    guard_result_summary: str,
    audit_chain_head: str,
    state_transition_hashes: tuple[str, ...] = (),
    deterministic_input_digest: str,
    failure_bundle_ref: str | None = None,
    provider_dry_run_receipt_ref: str | None = None,
    policy_version: str = _POLICY_VERSION,
    code_version: str = _CODE_VERSION,
    observed_at: str | None = None,
) -> LocalRuntimeReviewPacket:
    """Build a deterministic review packet whose hash excludes observation metadata."""

    for field, value in (
        ("run_id", run_id),
        ("task_id", task_id),
        ("guard_result_summary", guard_result_summary),
        ("audit_chain_head", audit_chain_head),
        ("policy_version", policy_version),
        ("code_version", code_version),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if not strict_digest(runtime_receipt_hash):
        raise ValueError("runtime_receipt_hash_must_be_valid_digest")
    if not strict_digest(deterministic_input_digest):
        raise ValueError("deterministic_input_digest_must_be_valid_digest")
    if not strict_digest(audit_chain_head):
        raise ValueError("audit_chain_head_must_be_valid_digest")
    if not strict_bool(runtime_accepted):
        raise ValueError("runtime_accepted_must_be_bool")
    if not isinstance(state_transition_hashes, tuple):
        raise ValueError("state_transition_hashes_must_be_tuple")
    for entry in state_transition_hashes:
        if not strict_digest(entry):
            raise ValueError("state_transition_hash_entry_must_be_valid_digest")
    if failure_bundle_ref is not None and not strict_nonempty_string(failure_bundle_ref):
        raise ValueError("failure_bundle_ref_must_be_nonempty_string")
    if provider_dry_run_receipt_ref is not None and not strict_nonempty_string(provider_dry_run_receipt_ref):
        raise ValueError("provider_dry_run_receipt_ref_must_be_nonempty_string")

    observed = _observed_at(observed_at)
    material = {
        "audit_chain_head": audit_chain_head,
        "code_version": code_version,
        "deterministic_input_digest": deterministic_input_digest,
        "failure_bundle_ref": failure_bundle_ref,
        "guard_result_summary": guard_result_summary,
        "policy_version": policy_version,
        "provider_dry_run_receipt_ref": provider_dry_run_receipt_ref,
        "run_id": run_id,
        "runtime_accepted": runtime_accepted,
        "runtime_receipt_hash": runtime_receipt_hash,
        "state_transition_hashes": list(state_transition_hashes),
        "task_id": task_id,
    }
    return LocalRuntimeReviewPacket(
        run_id=run_id,
        task_id=task_id,
        runtime_receipt_hash=runtime_receipt_hash,
        runtime_accepted=runtime_accepted,
        guard_result_summary=guard_result_summary,
        failure_bundle_ref=failure_bundle_ref,
        provider_dry_run_receipt_ref=provider_dry_run_receipt_ref,
        audit_chain_head=audit_chain_head,
        state_transition_hashes=state_transition_hashes,
        deterministic_input_digest=deterministic_input_digest,
        policy_version=policy_version,
        code_version=code_version,
        content_hash=digest_payload(material),
        observed_at=observed,
    )


def validate_review_packet_material(packet: LocalRuntimeReviewPacket) -> bool:
    """Validate that the review packet content hash matches its deterministic material."""

    if not isinstance(packet, LocalRuntimeReviewPacket):
        return False
    if not strict_nonempty_string(packet.run_id):
        return False
    if not strict_nonempty_string(packet.task_id):
        return False
    if not strict_digest(packet.runtime_receipt_hash):
        return False
    if not strict_bool(packet.runtime_accepted):
        return False
    if not strict_nonempty_string(packet.guard_result_summary):
        return False
    if not strict_digest(packet.deterministic_input_digest):
        return False
    if not strict_digest(packet.audit_chain_head):
        return False
    if not strict_nonempty_string(packet.policy_version):
        return False
    if not strict_nonempty_string(packet.code_version):
        return False
    if packet.failure_bundle_ref is not None and not strict_nonempty_string(packet.failure_bundle_ref):
        return False
    if packet.provider_dry_run_receipt_ref is not None and not strict_nonempty_string(packet.provider_dry_run_receipt_ref):
        return False
    if not isinstance(packet.state_transition_hashes, tuple):
        return False
    for entry in packet.state_transition_hashes:
        if not strict_digest(entry):
            return False
    return packet.content_hash == digest_payload(packet.deterministic_material())


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
