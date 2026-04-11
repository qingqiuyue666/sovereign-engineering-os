"""
Append-only evidence ledger.

Constitutional anchors:
- v11 §15 (evidence plane obligations)
- v11 §22.11 (taint visibility)
- v11 §23.14 AuditRecord
- v11 §24.1 AT-033
- v11 §24.2 INV-026 (audit records are append-only)
- foundation §8 mapping to `kernel/evidence/append_only_ledger.py`

This module is the single-writer surface over `AuditRecord` (and related
append-only ledgers via composition). It enforces INV-026 at the
application layer in addition to the SQL-level trigger enforcement.

Design rules:
- The only public mutation surface is `append`. There is no `update`,
  no `delete`, no "fix-up" helper, and no soft-update shim.
- Every append composes a version_tuple_hash via
  `kernel.version.version_tuple.compose_version_tuple_hash`, so replay
  queries can reconstruct which policy class admitted each record.
- Actor identity is an explicit required parameter. Silent "system"
  fallback is not admitted; callers must assert who is appending.
- The ledger is the authoritative drop-point for stage transitions,
  capability events, inference-failure audit notes, and replay
  classification decisions.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence
from uuid import uuid4

from kernel.stores.sqlite.repositories import AuditRepository
from kernel.version.version_tuple import compose_version_tuple_hash


class LedgerViolation(Exception):
    """Raised when a caller attempts an illegal append (e.g. empty record_type)."""


class AppendOnlyLedger:
    """Append-only audit ledger facade.

    The orchestrator and all services hold a reference to this ledger
    and call `append(...)` with keyword args. There is no other way to
    emit audit evidence in the phase-1 signable path.
    """

    def __init__(
        self,
        *,
        repository: AuditRepository,
        actor_identity: str,
        version_tuple_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        if not actor_identity:
            raise LedgerViolation("actor_identity is required")
        self._repo = repository
        self._actor = actor_identity
        self._vt_overrides = dict(version_tuple_overrides or {})

    def append(
        self,
        *,
        record_type: str,
        task_id: str | None = None,
        root_revision_id: str | None = None,
        causality_ref: str | None = None,
        artifact_refs: Sequence[str] | None = None,
        taint_set: Sequence[str] | None = None,
        payload: Mapping[str, Any] | None = None,
        failure_bundle_id: str | None = None,
        replay_anchor_id: str | None = None,
        approval_id: str | None = None,
    ) -> str:
        if not record_type:
            raise LedgerViolation("record_type must be non-empty")
        audit_record_id = f"aud-{uuid4().hex}"
        self._repo.append(
            audit_record_id=audit_record_id,
            record_type=record_type,
            actor_identity=self._actor,
            version_tuple_hash=compose_version_tuple_hash(self._vt_overrides),
            task_id=task_id,
            root_revision_id=root_revision_id,
            causality_ref=causality_ref,
            artifact_refs=artifact_refs,
            taint_set=taint_set,
            payload=payload,
            failure_bundle_id=failure_bundle_id,
            replay_anchor_id=replay_anchor_id,
            approval_id=approval_id,
        )
        return audit_record_id
