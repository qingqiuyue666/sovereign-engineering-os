"""Fail-closed promotion gate for local runtime manual review eligibility.

This gate evaluates whether a dry-run local runtime result can be promoted
to manual human review. It must reject (fail closed) unless all safety
boundary conditions are proven.

No provider calls, network access, secrets, env reads, subprocess, or
SQLite mutations happen here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "LocalRuntimePromotionResult",
    "evaluate_promotion_gate",
    "validate_promotion_result",
]

_POLICY_VERSION = "local-runtime-promotion-gate-v1"
_CODE_VERSION = "0.1.0"

_REQUIRED_BOUNDARY_FLAGS = (
    "dry_run_only",
    "no_network",
    "no_live_provider_calls",
    "no_subprocess",
    "no_secret_or_env_reads",
    "no_sqlite_mutation",
    "no_production_autonomy",
)


@dataclass(frozen=True)
class LocalRuntimePromotionResult:
    """Deterministic verdict from the manual-review promotion gate."""

    accepted: bool
    decision: str
    reasons: tuple[str, ...]
    review_packet_hash: str
    promotion_receipt_hash: str
    rollback_plan_hash: str | None
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        """Return promotion material excluding observation metadata and self-hash."""

        return _promotion_material(
            accepted=self.accepted,
            code_version=self.code_version,
            decision=self.decision,
            policy_version=self.policy_version,
            reasons=self.reasons,
            review_packet_hash=self.review_packet_hash,
            rollback_plan_hash=self.rollback_plan_hash,
        )

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["promotion_receipt_hash"] = self.promotion_receipt_hash
        payload["observed_at"] = self.observed_at
        return payload


def evaluate_promotion_gate(
    *,
    runtime_accepted: bool,
    guard_accepted: bool,
    boundary_flags: dict[str, bool],
    provider_dry_run_receipt_exists: bool,
    provider_transport_attempted: bool,
    audit_chain_head_exists: bool,
    runtime_receipt_hash: str,
    review_packet_hash: str,
    rollback_plan_hash: str | None = None,
    policy_version: str = _POLICY_VERSION,
    code_version: str = _CODE_VERSION,
    observed_at: str | None = None,
) -> LocalRuntimePromotionResult:
    """Evaluate whether a local runtime result is eligible for human review.

    Returns a fail-closed verdict: accepted=True only when all conditions are met.
    Rejections always carry a deterministic rollback-plan reference. When the
    caller has not supplied one, the gate emits a deterministic symbolic
    required-rollback reference without executing rollback.
    """

    for field, value in (
        ("policy_version", policy_version),
        ("code_version", code_version),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if not strict_digest(runtime_receipt_hash):
        raise ValueError("runtime_receipt_hash_must_be_valid_digest")
    if not strict_digest(review_packet_hash):
        raise ValueError("review_packet_hash_must_be_valid_digest")
    if rollback_plan_hash is not None and not strict_digest(rollback_plan_hash):
        raise ValueError("rollback_plan_hash_must_be_valid_digest")
    if not strict_bool(runtime_accepted):
        raise ValueError("runtime_accepted_must_be_bool")
    if not strict_bool(guard_accepted):
        raise ValueError("guard_accepted_must_be_bool")
    if not strict_bool(provider_dry_run_receipt_exists):
        raise ValueError("provider_dry_run_receipt_exists_must_be_bool")
    if not strict_bool(provider_transport_attempted):
        raise ValueError("provider_transport_attempted_must_be_bool")
    if not strict_bool(audit_chain_head_exists):
        raise ValueError("audit_chain_head_exists_must_be_bool")
    if not isinstance(boundary_flags, dict):
        raise ValueError("boundary_flags_must_be_dict")

    reasons: list[str] = []

    if not runtime_accepted:
        reasons.append("runtime_result_not_accepted")
    if not guard_accepted:
        reasons.append("guard_result_not_accepted")

    for flag_name in _REQUIRED_BOUNDARY_FLAGS:
        flag_value = boundary_flags.get(flag_name)
        if flag_value is not True:
            reasons.append(f"boundary_flag_not_proven:{flag_name}")

    if provider_transport_attempted and not provider_dry_run_receipt_exists:
        reasons.append("provider_transport_attempted_but_receipt_missing")

    if not audit_chain_head_exists:
        reasons.append("audit_chain_head_missing")

    accepted = not reasons
    decision = "eligible_for_human_review" if accepted else "rejected"
    normalized_reasons = tuple(sorted(set(reasons)))
    rollback_ref: str | None = rollback_plan_hash
    if not accepted and rollback_ref is None:
        rollback_ref = _required_rollback_ref(
            code_version=code_version,
            policy_version=policy_version,
            reasons=normalized_reasons,
            review_packet_hash=review_packet_hash,
            runtime_receipt_hash=runtime_receipt_hash,
        )

    observed = _observed_at(observed_at)
    promotion_material = _promotion_material(
        accepted=accepted,
        code_version=code_version,
        decision=decision,
        policy_version=policy_version,
        reasons=normalized_reasons,
        review_packet_hash=review_packet_hash,
        rollback_plan_hash=rollback_ref,
    )
    return LocalRuntimePromotionResult(
        accepted=accepted,
        decision=decision,
        reasons=normalized_reasons,
        review_packet_hash=review_packet_hash,
        promotion_receipt_hash=digest_payload(promotion_material),
        rollback_plan_hash=rollback_ref,
        policy_version=policy_version,
        code_version=code_version,
        observed_at=observed,
    )


def validate_promotion_result(result: LocalRuntimePromotionResult) -> bool:
    """Validate that the promotion result hash matches its deterministic material."""

    if not isinstance(result, LocalRuntimePromotionResult):
        return False
    if not strict_bool(result.accepted):
        return False
    if not strict_nonempty_string(result.decision):
        return False
    if result.decision not in {"eligible_for_human_review", "rejected"}:
        return False
    if not isinstance(result.reasons, tuple):
        return False
    if not strict_digest(result.review_packet_hash):
        return False
    if not strict_digest(result.promotion_receipt_hash):
        return False
    if not strict_nonempty_string(result.policy_version):
        return False
    if not strict_nonempty_string(result.code_version):
        return False
    if result.rollback_plan_hash is not None and not strict_digest(result.rollback_plan_hash):
        return False
    if result.accepted and result.rollback_plan_hash is not None:
        return False
    if not result.accepted and result.rollback_plan_hash is None:
        return False

    return result.promotion_receipt_hash == digest_payload(result.deterministic_material())


def _promotion_material(
    *,
    accepted: bool,
    code_version: str,
    decision: str,
    policy_version: str,
    reasons: tuple[str, ...],
    review_packet_hash: str,
    rollback_plan_hash: str | None,
) -> dict[str, object]:
    return {
        "accepted": accepted,
        "code_version": code_version,
        "decision": decision,
        "policy_version": policy_version,
        "reasons": list(reasons),
        "review_packet_hash": review_packet_hash,
        "rollback_plan_hash": rollback_plan_hash,
    }


def _required_rollback_ref(
    *,
    code_version: str,
    policy_version: str,
    reasons: tuple[str, ...],
    review_packet_hash: str,
    runtime_receipt_hash: str,
) -> str:
    return digest_payload(
        {
            "code_version": code_version,
            "policy_version": policy_version,
            "reasons": list(reasons),
            "review_packet_hash": review_packet_hash,
            "rollback_requirement": "symbolic_rollback_plan_required",
            "runtime_receipt_hash": runtime_receipt_hash,
        }
    )


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value