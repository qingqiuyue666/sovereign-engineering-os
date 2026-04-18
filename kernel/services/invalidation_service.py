"""
Incremental invalidation service: minimum honest enforcement surface.

Constitutional anchors:
- v11 §22.3 Atomic Approval Barrier Contract (drift consequence invalidation)
- v11 §22.11 Taint Propagation Graph Contract (drift as explicit signal)
- v11 §23.7 ValidationReceipt (`invalidated_at`, `invalidation_reason`)
- v11 §23.11 ApprovalArtifact (`approval_state='invalidated'`)
- v11 §23.19 DriftEventRecord
- v11 §24.1 AT-017 (incremental invalidation behavior)
- v11 §24.2 INV-017 (stale artifacts cannot silently remain admissible) /
  INV-028 (drift consequence invalidation)
- foundation §9 "Incremental invalidation behavior (optional in first
  tracer bullet, hardening-adjacent)" — this module is the minimum
  honest, current-path-only implementation.

Scope lock:
- This service covers ONLY the minimum invalidation cases the current
  narrow signable path exposes today:
    1. ValidationReceipt invalidation on upstream patch drift.
    2. ApprovalArtifact cascade invalidation when a required receipt is
       invalidated.
- No dependency-graph generality. No validator-run reuse heuristics.
- No build/semantic receipt breadth beyond phase-1 slice.
- No cross-project, cross-lane, or distributed propagation.
- The service is side-effect-limited: it writes only to the three
  persistence surfaces it was given (receipt repo, approval repo, drift
  repo) plus the append-only audit ledger. It never mutates artifacts
  outside those surfaces, never advances the orchestrator, never touches
  sealed revisions.

Fail-closed posture:
- `mark_invalidated` on either repository is idempotent; this service
  emits audit/drift evidence ONLY on the single row that actually
  transitioned (repository returns True). Replays of the same drift
  signal therefore cannot duplicate evidence.
- `_derive_input_hash_from_patch_hash` mirrors `ValidationService`'s
  static.input_hash derivation exactly. The one-line helper is colocated
  here on purpose: extracting a shared module would be premature
  abstraction for two callers on the narrow path. If ValidationService
  changes its derivation, this file must follow — that coupling is
  explicit in `_derive_input_hash_from_patch_hash`'s docstring.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    DriftEventRecordRepository,
    ValidationReceiptRepository,
)


# Stable reason codes (mirror the barrier's stable-string posture so that
# audit/replay queries can bind reactions to reasons).
REASON_UPSTREAM_PATCH_DRIFT = "upstream_patch_drift"
REASON_REQUIRED_RECEIPT_INVALIDATED = "required_receipt_invalidated"

DRIFT_CLASS_UPSTREAM_PATCH_DRIFT = "upstream_patch_drift"
DRIFT_CLASS_RECEIPT_INVALIDATED_CASCADE = "receipt_invalidated_cascade"

CONSEQUENCE_RECEIPT_INVALIDATED = "receipt_invalidated"
CONSEQUENCE_APPROVAL_INVALIDATED = "approval_invalidated"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_input_hash_from_patch_hash(patch_group_hash: str) -> str:
    """Mirror `ValidationService._hash_str(proposal["patch_group_hash"])`.

    ValidationService composes a receipt's `input_hash` as
    `"sha256:" + sha256(patch_group_hash_utf8)`. We recompute the same
    derivation here so that the invalidation service can decide whether a
    newly-persisted patch proposal supersedes a prior live receipt
    without calling into the validation service.

    This coupling is intentional: if ValidationService changes how it
    derives `input_hash` from a patch, this function must change in
    lockstep.
    """
    return "sha256:" + hashlib.sha256(patch_group_hash.encode("utf-8")).hexdigest()


class InvalidationService:
    """Minimum honest incremental-invalidation surface.

    Wire-in contract:
    - PatchProposalService calls `on_new_patch_proposal(...)` after a
      proposal is persisted. This is the only authority-bearing trigger
      in phase 1.
    - Any service that chooses to invalidate a receipt directly (future
      hardening) calls `invalidate_receipt(...)`. For phase 1 the
      cascade is triggered indirectly via `on_new_patch_proposal`.
    """

    def __init__(
        self,
        *,
        receipt_repo: ValidationReceiptRepository,
        approval_repo: ApprovalArtifactRepository,
        drift_repo: DriftEventRecordRepository,
        audit_ledger: Any,
    ) -> None:
        self._receipts = receipt_repo
        self._approvals = approval_repo
        self._drifts = drift_repo
        self._audit = audit_ledger

    # ------------------------------------------------------------------
    # Case A: upstream patch drift → receipt invalidation
    # ------------------------------------------------------------------

    def on_new_patch_proposal(
        self,
        *,
        task_id: str,
        root_revision_id: str,
        new_patch_group_hash: str,
        new_patch_proposal_id: str,
        intent_id: str | None = None,
    ) -> list[str]:
        """Invalidate any live receipts whose upstream patch hash drifted.

        Called by `PatchProposalService.propose(...)` after the new
        proposal has been inserted. For every live receipt bound to the
        same `(task_id, root_revision_id)` whose `input_hash` does not
        match the input_hash derived from the new `patch_group_hash`, the
        receipt is marked invalidated and (via `invalidate_receipt`) the
        approval cascade is triggered.

        Returns the list of validation_receipt_ids that were actually
        invalidated by this call (empty in the common single-proposal
        tracer-bullet path).

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        threaded in by ``PatchProposalService.propose`` (which already
        carries it from the orchestrator). It is forwarded unchanged to
        ``invalidate_receipt`` so the ``validation_receipt_invalidated``
        audit record names it in both ``artifact_refs`` and ``payload``
        (AUDIT-003 / §22.1). This service performs no independent
        verification; authoritative fail-closed verification of
        ``intent_id`` against ``intent_anchor_records`` remains with
        ``RevisionSealService`` downstream. Absent / empty ``intent_id``
        preserves the prior audit shape exactly.
        """
        new_input_hash = _derive_input_hash_from_patch_hash(new_patch_group_hash)
        invalidated: list[str] = []
        for receipt in self._receipts.list_active_for_task_root(
            task_id, root_revision_id
        ):
            if receipt["input_hash"] == new_input_hash:
                # Not stale: the receipt is bound to this very patch hash.
                continue
            rid = receipt["validation_receipt_id"]
            if self.invalidate_receipt(
                validation_receipt_id=rid,
                reason=REASON_UPSTREAM_PATCH_DRIFT,
                drift_class=DRIFT_CLASS_UPSTREAM_PATCH_DRIFT,
                source_artifact_id=new_patch_proposal_id,
                task_id=task_id,
                root_revision_id=root_revision_id,
                intent_id=intent_id,
            ):
                invalidated.append(rid)
        return invalidated

    # ------------------------------------------------------------------
    # Case B: receipt invalidation → approval cascade
    # ------------------------------------------------------------------

    def invalidate_receipt(
        self,
        *,
        validation_receipt_id: str,
        reason: str,
        drift_class: str,
        source_artifact_id: str,
        task_id: str,
        root_revision_id: str,
        intent_id: str | None = None,
    ) -> bool:
        """Mark a receipt invalidated + cascade to gated approvals.

        Returns True iff this call actually transitioned the receipt
        (idempotent: a second call on an already-invalidated receipt
        returns False and emits no duplicate evidence).

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        threaded in by the caller. When supplied and non-empty it is
        named in both ``artifact_refs`` and ``payload`` of the
        ``validation_receipt_invalidated`` audit record and forwarded to
        ``_invalidate_approval_cascade`` so the cascaded
        ``approval_invalidated`` record names it as well, so a reviewer
        reading only either record can recover the AUDIT-003 / §22.1
        linkage without a second fetch. Authoritative fail-closed
        verification of ``intent_id`` against ``intent_anchor_records``
        remains the responsibility of ``RevisionSealService`` downstream;
        this service performs no independent verification. Absent /
        empty ``intent_id`` preserves the prior audit shape exactly on
        both records.
        """
        now = _now_iso()
        transitioned = self._receipts.mark_invalidated(
            validation_receipt_id=validation_receipt_id,
            invalidation_reason=reason,
            invalidated_at=now,
        )
        if not transitioned:
            return False

        # Drift record for the receipt-level consequence.
        drift_id = f"dr-{uuid4().hex}"
        self._drifts.insert(
            {
                "drift_event_id": drift_id,
                "task_id": task_id,
                "root_revision_id": root_revision_id,
                "drift_class": drift_class,
                "detected_at": now,
                "affected_artifact_ids": [validation_receipt_id],
                "consequence_class": CONSEQUENCE_RECEIPT_INVALIDATED,
                "required_reconciliation_action": "revalidate_against_current_patch",
            }
        )

        # Audit: the append-only ledger records the receipt transition.
        audit_artifact_refs: list[str] = [validation_receipt_id, source_artifact_id]
        audit_payload: dict[str, Any] = {
            "reason": reason,
            "drift_class": drift_class,
            "drift_event_id": drift_id,
            "source_artifact_id": source_artifact_id,
        }
        if isinstance(intent_id, str) and intent_id:
            audit_artifact_refs.append(intent_id)
            audit_payload["intent_id"] = intent_id
        self._audit.append(
            record_type="validation_receipt_invalidated",
            task_id=task_id,
            root_revision_id=root_revision_id,
            artifact_refs=audit_artifact_refs,
            payload=audit_payload,
        )

        # Cascade to approvals.
        affected_approvals = self._approvals.list_live_referencing_receipt(
            validation_receipt_id
        )
        for approval in affected_approvals:
            self._invalidate_approval_cascade(
                approval=approval,
                invalidating_receipt_id=validation_receipt_id,
                now=now,
                intent_id=intent_id,
            )
        return True

    # ------------------------------------------------------------------
    # internal: approval cascade
    # ------------------------------------------------------------------

    def _invalidate_approval_cascade(
        self,
        *,
        approval: dict[str, Any],
        invalidating_receipt_id: str,
        now: str,
        intent_id: str | None = None,
    ) -> None:
        """Cascade invalidation to a live approval that referenced a
        newly-invalidated receipt.

        ``intent_id`` is the durable ``intent_anchor_records.intent_id``
        threaded in by ``invalidate_receipt``. When supplied and
        non-empty it is named in both ``artifact_refs`` and ``payload``
        of the ``approval_invalidated`` audit record so a reviewer
        reading only that cascade record can recover the AUDIT-003 /
        §22.1 linkage without a second fetch. Authoritative fail-closed
        verification of ``intent_id`` against ``intent_anchor_records``
        remains the responsibility of ``RevisionSealService`` downstream;
        this service performs no independent verification. Absent /
        empty ``intent_id`` preserves the prior audit shape exactly.
        """
        approval_id = approval["approval_id"]
        transitioned = self._approvals.mark_invalidated(
            approval_id=approval_id,
            invalidation_reason=REASON_REQUIRED_RECEIPT_INVALIDATED,
            invalidated_at=now,
        )
        if not transitioned:
            return  # already invalidated; nothing more to emit

        drift_id = f"dr-{uuid4().hex}"
        self._drifts.insert(
            {
                "drift_event_id": drift_id,
                "task_id": approval.get("task_id"),
                "root_revision_id": approval.get("originating_root_revision_id"),
                "drift_class": DRIFT_CLASS_RECEIPT_INVALIDATED_CASCADE,
                "detected_at": now,
                "affected_artifact_ids": [approval_id],
                "consequence_class": CONSEQUENCE_APPROVAL_INVALIDATED,
                "approval_id": approval_id,
                "required_reconciliation_action": "reissue_approval_after_revalidation",
            }
        )

        audit_artifact_refs: list[str] = [approval_id, invalidating_receipt_id]
        audit_payload: dict[str, Any] = {
            "reason": REASON_REQUIRED_RECEIPT_INVALIDATED,
            "drift_class": DRIFT_CLASS_RECEIPT_INVALIDATED_CASCADE,
            "drift_event_id": drift_id,
            "invalidating_receipt_id": invalidating_receipt_id,
        }
        if isinstance(intent_id, str) and intent_id:
            audit_artifact_refs.append(intent_id)
            audit_payload["intent_id"] = intent_id
        self._audit.append(
            record_type="approval_invalidated",
            task_id=approval.get("task_id"),
            root_revision_id=approval.get("originating_root_revision_id"),
            artifact_refs=audit_artifact_refs,
            approval_id=approval_id,
            payload=audit_payload,
        )
