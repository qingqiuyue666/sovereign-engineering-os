"""
Atomic Approval Barrier contract rules (C22.3).

Constitutional anchors:
- v11 §22.3 Atomic Approval Barrier Contract (full body)
- v11 §23.11 ApprovalArtifact
- v11 §24.1 AT-004 / AT-005 / AT-006 (barrier crash classification)
- v11 §24.2 INV-006 / INV-007 (no approval time-travel across drift)
- foundation §6 step 8 (P1 approval barrier evaluation)

This module holds the *pure rules* that compare a candidate
ApprovalArtifact against the current live truth (current root, reviewed
context, required receipts). It does NOT touch SQLite, emit audit
records, or acquire serialization fences — those are the service layer's
responsibilities.

Fail-closed posture:
- Any drift (root / context / receipt / policy) produces a
  `BarrierVerdict(passes=False, ...)` with a deterministic reason code.
- Any failure to evaluate a mandatory field raises
  `BarrierEvaluationError`. Callers must NEVER interpret an exception as
  "passes".
- `reason_code` is a stable string (not a free-form message), so the
  audit ledger can query on it after the fact (INV-006 audit_query_proof).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Sequence


class BarrierEvaluationError(Exception):
    """Raised when the barrier cannot be evaluated from the given inputs."""


# Stable reason codes. Any new code must be added explicitly; the service
# layer emits these verbatim into the audit ledger so that replay queries
# can bind reactions to reasons.
REASON_PASS = "barrier_pass"
REASON_ROOT_DRIFT = "root_drift"
REASON_CONTEXT_DRIFT = "context_drift"
REASON_RECEIPT_DRIFT = "receipt_drift"
REASON_RECEIPT_MISSING = "receipt_missing"
REASON_RECEIPT_INVALIDATED = "receipt_invalidated"
REASON_RECEIPT_NOT_PASS = "receipt_not_pass"
REASON_POLICY_DRIFT = "policy_drift"
REASON_APPROVAL_EXPIRED = "approval_expired"
REASON_APPROVAL_STATE_INVALID = "approval_state_invalid"
REASON_TASK_SUPERSEDED = "task_superseded"


@dataclass(frozen=True)
class BarrierInputs:
    """All values the barrier rule set must compare.

    Every field is explicit. A silent "was this checked or not?" is not
    admitted: every comparison is either passed or raises.
    """

    # Candidate approval (the artifact whose execution is gated).
    approval_id: str
    approval_state: str
    approval_policy_version: str
    originating_root_revision_id: str
    reviewed_patch_hash: str
    reviewed_context_artifact_id: str
    required_receipt_ids: Sequence[str]
    approval_expires_at: str  # ISO-8601

    # Current live truth as the service observes it at evaluation time.
    current_root_revision_id: str
    current_context_artifact_id: str
    current_patch_hash: str
    current_policy_version: str
    receipts_live: Mapping[str, Mapping[str, object]]
    task_superseded: bool

    now_iso: str | None = None


@dataclass(frozen=True)
class BarrierVerdict:
    passes: bool
    reason_code: str
    detail: str


def _parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def evaluate_barrier(inputs: BarrierInputs) -> BarrierVerdict:
    """Evaluate the §22.3 barrier rule set against `inputs` (pure function)."""
    # 1) Approval state must be `pending` (ready to be gated) or
    #    `approved` (already gated but re-checked during seal). Any other
    #    state forbids execution.
    if inputs.approval_state not in ("pending", "approved"):
        return BarrierVerdict(
            passes=False,
            reason_code=REASON_APPROVAL_STATE_INVALID,
            detail=f"approval_state={inputs.approval_state!r}",
        )

    # 2) Approval expiry.
    try:
        expires_at = _parse_iso(inputs.approval_expires_at)
    except ValueError as exc:
        raise BarrierEvaluationError(
            f"approval_expires_at unparseable: {exc}"
        ) from exc
    now = _parse_iso(inputs.now_iso) if inputs.now_iso else _now()
    if now >= expires_at:
        return BarrierVerdict(
            passes=False,
            reason_code=REASON_APPROVAL_EXPIRED,
            detail=f"now={now.isoformat()} >= expires_at={expires_at.isoformat()}",
        )

    # 3) Task supersession check.
    if inputs.task_superseded:
        return BarrierVerdict(
            passes=False,
            reason_code=REASON_TASK_SUPERSEDED,
            detail="task generation superseded by a newer seal",
        )

    # 4) current_root == originating_root (INV-006).
    if inputs.originating_root_revision_id != inputs.current_root_revision_id:
        return BarrierVerdict(
            passes=False,
            reason_code=REASON_ROOT_DRIFT,
            detail=(
                f"originating_root={inputs.originating_root_revision_id!r}, "
                f"current_root={inputs.current_root_revision_id!r}"
            ),
        )

    # 5) Context drift: the reviewed context artifact must still be the
    #    live one that the approval was reviewed against.
    if inputs.reviewed_context_artifact_id != inputs.current_context_artifact_id:
        return BarrierVerdict(
            passes=False,
            reason_code=REASON_CONTEXT_DRIFT,
            detail=(
                f"reviewed_context={inputs.reviewed_context_artifact_id!r}, "
                f"current_context={inputs.current_context_artifact_id!r}"
            ),
        )

    # 6) Receipt drift: reviewed patch hash must match the live patch
    #    hash that would be executed. A change in patch hash means the
    #    material under review has drifted out from under the approval.
    if inputs.reviewed_patch_hash != inputs.current_patch_hash:
        return BarrierVerdict(
            passes=False,
            reason_code=REASON_RECEIPT_DRIFT,
            detail=(
                f"reviewed_patch_hash={inputs.reviewed_patch_hash!r}, "
                f"current_patch_hash={inputs.current_patch_hash!r}"
            ),
        )

    # 7) Receipt admissibility: every required receipt must be present,
    #    not invalidated, and result == 'pass'. Phase-1 admits only
    #    `pass` on the narrow path; `quarantined` is not admissible into
    #    a passing approval without a policy-admitted override, which
    #    phase-1 does not define.
    for rid in inputs.required_receipt_ids:
        receipt = inputs.receipts_live.get(rid)
        if receipt is None:
            return BarrierVerdict(
                passes=False,
                reason_code=REASON_RECEIPT_MISSING,
                detail=f"receipt {rid!r} not found",
            )
        if receipt.get("invalidated_at") not in (None, ""):
            return BarrierVerdict(
                passes=False,
                reason_code=REASON_RECEIPT_INVALIDATED,
                detail=(
                    f"receipt {rid!r} invalidated: "
                    f"{receipt.get('invalidation_reason')!r}"
                ),
            )
        if receipt.get("result") != "pass":
            return BarrierVerdict(
                passes=False,
                reason_code=REASON_RECEIPT_NOT_PASS,
                detail=f"receipt {rid!r} result={receipt.get('result')!r}",
            )

    # 8) Policy drift check.
    if inputs.approval_policy_version != inputs.current_policy_version:
        return BarrierVerdict(
            passes=False,
            reason_code=REASON_POLICY_DRIFT,
            detail=(
                f"approval_policy={inputs.approval_policy_version!r}, "
                f"current_policy={inputs.current_policy_version!r}"
            ),
        )

    return BarrierVerdict(
        passes=True,
        reason_code=REASON_PASS,
        detail="all barrier checks passed",
    )
