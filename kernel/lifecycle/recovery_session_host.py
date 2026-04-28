"""
P0-9 phase 1 — RecoverySessionHost.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.5 Replay admission boundary
- v11 §22.10 invariant binding
- foundation §6 (P0 sealing + crash-window proofs)

A bounded in-process owner of a live `SessionOrchestrator` instance
and a pre-built `RecoveryGate`. This is the smallest correct runtime
boundary at which `restore_task_from_snapshot` is meaningful: a
restored task lives in the host-owned orchestrator's `_tasks` dict
and remains available for follow-on admission against the same
instance for the host's lifetime.

P0-8 proved that a one-shot `recovery_cli restore` subcommand would
be ephemeral and misleading — restored orchestrator memory
disappears when the CLI process exits. P0-9 introduces a host that
keeps the orchestrator alive across restore + admission so the
restore has a continuable runtime effect.

This module is NOT a daemon, web server, async runtime, queue, IPC,
scheduler, or background worker. It is a synchronous in-process
owner of three references and a closed flag.

Out of scope (delegated):
- DB connection ownership: caller responsibility (release via
  ``close_callback``).
- Repository / service wiring: caller responsibility.
- Recovery policy: lives in `RecoveryGate` / `TaskRecoveryClassifier`.
- Restore safety: lives in
  `SignablePathOrchestrator.restore_task_from_snapshot` (the gate's
  final authority).
- Artifact integrity: lives in `StageArtifactExistenceResolver`.
- Schema, migration, or audit ``record_type`` additions: not
  introduced here.

This class does not import `SignablePathOrchestrator`. The owned
runtime is protocol-typed via `SessionOrchestrator` so the host
stays a thin runtime boundary rather than a wiring graph.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable, Optional, Protocol, Union

from kernel.lifecycle.recovery_gate import RecoveryGate, RecoveryGateResult
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import (
    RecoveryClass,
    TaskLifecycleSnapshot,
)


# Tables required by every repository wired by
# ``build_recovery_session_host_from_sqlite``. Sourced directly from
# ``kernel/stores/sqlite/migrations/0001_core_signable_path.sql`` and
# the table names embedded in the SELECT/INSERT statements of the
# corresponding repository in ``kernel/stores/sqlite/repositories.py``.
_REQUIRED_RECOVERY_SESSION_HOST_TABLES: frozenset[str] = frozenset(
    {
        "audit_records",
        "budget_records",
        "capability_tokens",
        "context_artifacts",
        "inference_artifacts",
        "intent_anchor_records",
        "patch_proposals",
        "validation_receipts",
        "review_artifacts",
        "approval_artifacts",
        "revisions",
        "snapshot_roots",
        "journal_entries",
        "replay_anchors",
        "taint_records",
        "drift_event_records",
        "failure_bundles",
    }
)


class RecoverySessionHostClosed(RuntimeError):
    """Raised when a public `RecoverySessionHost` operation is
    attempted after `close()` has run.

    Subclass of `RuntimeError` so existing broad-except sites do not
    need to learn a new exception type to fail closed; specific
    callers can still catch this class directly to distinguish
    closed-host errors from other runtime conditions.
    """


class SessionOrchestrator(Protocol):
    """Minimal protocol the host requires of the owned orchestrator.

    Avoids a hard import of `SignablePathOrchestrator` so this module
    does not bind to runtime composition. Concrete callers pass
    their `SignablePathOrchestrator` instance directly; the gate's
    `restore_if_allowed` keeps final authority over restore safety
    via `restore_task_from_snapshot`.
    """

    def restore_task_from_snapshot(
        self,
        *,
        snapshot: TaskLifecycleSnapshot,
        recovery_class: RecoveryClass,
    ) -> None: ...

    def current_stage(self, task_id: str) -> Optional[Stage]: ...


class RecoverySessionHost:
    """Bounded in-process owner of a live orchestrator + RecoveryGate.

    Constructor contract:
    - ``recovery_gate``: a fully composed `RecoveryGate` (e.g. built
      via `build_standard_recovery_gate`). The host does not
      construct gates.
    - ``orchestrator``: a live `SessionOrchestrator` instance the
      caller has already wired against the durable substrate. The
      host does not construct orchestrators, repositories, services,
      or DB connections.
    - ``close_callback``: optional zero-arg callable invoked exactly
      once on the first `close()`. Typical use is releasing the
      caller-owned SQLite connection. Exceptions from the callback
      propagate; the host is still marked closed so a subsequent
      `close()` is a no-op.

    Public surface:
    - ``orchestrator`` (property): the owned live instance, for
      callers that want to continue admission after restore.
    - ``evaluate_task(task_id)``: read-only verdict via the gate.
    - ``restore_task(task_id)``: gate's `restore_if_allowed` against
      the owned orchestrator. Restore exceptions
      (`OrchestratorRejected`, integrity-guard failures inside
      `restore_task_from_snapshot`) propagate unchanged.
    - ``current_stage(task_id)``: pass-through to the orchestrator.
    - ``close()``: idempotent host shutdown.
    - ``closed`` (property): boolean state.

    All public operations except `close()` and `closed` raise
    `RecoverySessionHostClosed` after the host has been closed. The
    host writes no durable rows itself; any durable side effect is
    the responsibility of the wrapped orchestrator's existing
    admission boundary (`KernelUnitOfWork`).
    """

    __slots__ = (
        "_gate",
        "_orchestrator",
        "_close_callback",
        "_closed",
    )

    def __init__(
        self,
        *,
        recovery_gate: RecoveryGate,
        orchestrator: SessionOrchestrator,
        close_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self._gate = recovery_gate
        self._orchestrator = orchestrator
        self._close_callback = close_callback
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def _check_open(self) -> None:
        if self._closed:
            raise RecoverySessionHostClosed(
                "RecoverySessionHost is closed"
            )

    @property
    def orchestrator(self) -> SessionOrchestrator:
        self._check_open()
        return self._orchestrator

    def evaluate_task(self, task_id: str) -> RecoveryGateResult:
        self._check_open()
        return self._gate.evaluate(task_id)

    def restore_task(self, task_id: str) -> RecoveryGateResult:
        self._check_open()
        return self._gate.restore_if_allowed(
            task_id=task_id,
            orchestrator=self._orchestrator,
        )

    def current_stage(self, task_id: str) -> Optional[Stage]:
        self._check_open()
        return self._orchestrator.current_stage(task_id)

    def close(self) -> None:
        if self._closed:
            return
        # Mark closed before invoking the callback so a callback
        # exception still leaves the host closed and a subsequent
        # close() is a no-op (callback runs exactly once even on
        # error, never twice).
        self._closed = True
        if self._close_callback is not None:
            self._close_callback()


def _validate_factory_schema_ready(
    conn: sqlite3.Connection, *, db_path: Path
) -> None:
    """Read-only schema readiness check for the recovery factory.

    Inspects ``sqlite_master`` only — never writes, never creates
    tables, never calls ``apply_migrations``. If any table required
    by the repositories the factory is about to wire is absent, raises
    `RecoverySessionHostFactoryError` so the factory fails closed
    before constructing repositories or services.
    """
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table';"
    ).fetchall()
    present = {row[0] for row in rows}
    missing = _REQUIRED_RECOVERY_SESSION_HOST_TABLES - present
    if missing:
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory refused to construct host: "
            f"SQLite database at {db_path} is missing required schema "
            f"table(s): {sorted(missing)!r}"
        )


class RecoverySessionHostFactoryError(RuntimeError):
    """Raised when `build_recovery_session_host_from_sqlite` cannot
    produce a host.

    Subclass of `RuntimeError` so existing broad-except sites do not
    need to learn a new exception type to fail closed; specific
    callers (operators, integration tests) can still catch this class
    directly to distinguish factory-construction failures (missing DB
    file, repository wiring failure) from other runtime conditions.

    The factory raises this exception strictly BEFORE returning a
    host — successful construction returns the host and never
    raises. If construction fails after the SQLite connection is
    opened, the factory closes that connection before raising so the
    operator never inherits a leaked file handle.
    """


def build_recovery_session_host_from_sqlite(
    *,
    db_path: Union[str, Path],
) -> RecoverySessionHost:
    """Construct a `RecoverySessionHost` over an existing SQLite DB file.

    P0-10 phase 1 — the smallest correct production-side construction
    boundary for `RecoverySessionHost`. Until P0-10 the host could only
    be wired by tests; this factory promotes it to "production code has
    one standard operator construction boundary" without introducing a
    daemon, async runtime, queue, web server, IPC, scheduler, or
    background worker.

    Behavior:

    - The ``db_path`` MUST point at an existing SQLite database file.
      The factory checks ``Path(db_path).is_file()`` before opening,
      and raises `RecoverySessionHostFactoryError` when the path does
      not exist. The factory NEVER creates a new database file as a
      side effect of a typo (mirrors `recovery_cli.main`'s P0-6
      operator-boundary semantics).
    - After opening the connection and before constructing any
      repository, service, orchestrator, or gate, the factory runs a
      read-only schema readiness check
      (``_validate_factory_schema_ready``) against ``sqlite_master``.
      If any required table is missing — empty file, malformed DB,
      pre-migration DB, or wrong DB — the factory closes the opened
      connection and raises `RecoverySessionHostFactoryError`.
    - The factory does NOT call `apply_migrations`. The caller is
      responsible for having initialized schema before construction.
      The schema readiness check inspects metadata only; it never
      creates tables.
    - The factory composes the same production classes used by the
      narrow signable path: kernel-level repositories, the
      `AppendOnlyLedger`, the eight signable-path services, the
      `BudgetGovernor`, a `SignablePathOrchestrator`, and the standard
      `RecoveryGate` built via `build_standard_recovery_gate`.
    - The factory writes NO durable rows during construction. It does
      NOT call `RecoveryGate.restore_if_allowed`. It does NOT call
      `restore_task_from_snapshot`. It does NOT auto-restore any task.
    - The factory owns the SQLite connection it opens. The returned
      host's `close()` releases the connection through
      `close_callback`. If construction fails after the connection
      is opened, the factory closes it before raising.

    The InferenceService is intentionally constructed without a real
    `ModelAdapter` because the factory's purpose is recovery
    evaluation / restore — not new inference. The service falls back
    to its in-module `_NullAdapter`, which raises
    `model_adapter_not_configured` if a caller mistakenly attempts
    `admit_inference` against this host. This matches the
    "evaluate / restore" scope of P0-10 phase 1.
    """
    # Imports are local to keep `RecoverySessionHost` itself a thin
    # runtime boundary: the host class continues to bind only the
    # protocol-typed `SessionOrchestrator`, while the factory pulls in
    # the production wiring graph only when an operator constructs a
    # host through it.
    from kernel.evidence.append_only_ledger import AppendOnlyLedger
    from kernel.lifecycle.recovery_gate import (
        build_standard_recovery_gate,
    )
    from kernel.lifecycle.signable_path_orchestrator import (
        SignablePathOrchestrator,
    )
    from kernel.services.approval_service import ApprovalService
    from kernel.services.budget_governor import BudgetGovernor
    from kernel.services.capability_service import CapabilityService
    from kernel.services.context_service import ContextService
    from kernel.services.evidence_service import EvidenceService
    from kernel.services.inference_service import InferenceService
    from kernel.services.patch_proposal_service import (
        PatchProposalService,
    )
    from kernel.services.review_service import ReviewService
    from kernel.services.revision_seal_service import RevisionSealService
    from kernel.services.validation_service import ValidationService
    from kernel.stores.sqlite.repositories import (
        ApprovalArtifactRepository,
        AuditRepository,
        BudgetRepository,
        CapabilityRepository,
        ContextArtifactRepository,
        DriftEventRecordRepository,
        FailureBundleRepository,
        InferenceArtifactRepository,
        IntentAnchorRepository,
        JournalEntryRepository,
        PatchProposalRepository,
        ReplayAnchorRepository,
        ReviewArtifactRepository,
        RevisionRepository,
        SnapshotRootRepository,
        TaintRepository,
        ValidationReceiptRepository,
    )
    from kernel.stores.sqlite.wal_recovery import open_connection

    path = Path(db_path)
    if not path.is_file():
        raise RecoverySessionHostFactoryError(
            f"database file does not exist: {path}"
        )

    try:
        conn = open_connection(path)
    except Exception as exc:
        raise RecoverySessionHostFactoryError(
            f"failed to open SQLite connection at {path}: {exc}"
        ) from exc

    # Read-only schema readiness check. Runs immediately after the
    # connection is opened and before any repository/service/
    # orchestrator/gate is constructed. Fails closed when required
    # tables are missing — never applies migrations, never creates
    # schema. If the check fails, close the connection so the operator
    # never inherits a leaked file handle.
    try:
        _validate_factory_schema_ready(conn, db_path=path)
    except RecoverySessionHostFactoryError:
        try:
            conn.close()
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            conn.close()
        except Exception:
            pass
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory schema validation failed "
            f"for {path}: {exc}"
        ) from exc

    try:
        audit_repo = AuditRepository(conn)
        budget_repo = BudgetRepository(conn)
        cap_repo = CapabilityRepository(conn)
        ctx_repo = ContextArtifactRepository(conn)
        inf_repo = InferenceArtifactRepository(conn)
        intent_repo = IntentAnchorRepository(conn)
        pp_repo = PatchProposalRepository(conn)
        vr_repo = ValidationReceiptRepository(conn)
        rv_repo = ReviewArtifactRepository(conn)
        ap_repo = ApprovalArtifactRepository(conn)
        rev_repo = RevisionRepository(conn)
        snap_repo = SnapshotRootRepository(conn)
        je_repo = JournalEntryRepository(conn)
        ra_repo = ReplayAnchorRepository(conn)
        taint_repo = TaintRepository(conn)
        drift_repo = DriftEventRecordRepository(conn)
        failure_repo = FailureBundleRepository(conn)

        audit_ledger = AppendOnlyLedger(
            repository=audit_repo,
            actor_identity="recovery_session_host_factory",
        )

        cap_svc = CapabilityService(
            repository=cap_repo,
            audit_ledger=audit_ledger,
        )
        ctx_svc = ContextService(
            repository=ctx_repo,
            audit_ledger=audit_ledger,
        )
        budget_governor = BudgetGovernor(
            audit_ledger=audit_ledger,
            budget_repository=budget_repo,
        )
        # The InferenceService falls back to `_NullAdapter` when no
        # adapter is wired. P0-10 phase 1 is recovery evaluation /
        # restore only — the factory deliberately does not select a
        # real model adapter here.
        inf_svc = InferenceService(
            repository=inf_repo,
            audit_ledger=audit_ledger,
            context_reader=ctx_repo,
            budget_governor=budget_governor,
            failure_bundle_repository=failure_repo,
        )
        pp_svc = PatchProposalService(
            repository=pp_repo,
            inference_reader=inf_repo,
            audit_ledger=audit_ledger,
        )
        val_svc = ValidationService(
            repository=vr_repo,
            patch_reader=pp_repo,
            audit_ledger=audit_ledger,
            taint_repository=taint_repo,
        )
        rv_svc = ReviewService(
            repository=rv_repo,
            patch_reader=pp_repo,
            receipt_reader=vr_repo,
            audit_ledger=audit_ledger,
        )
        ap_svc = ApprovalService(
            repository=ap_repo,
            patch_reader=pp_repo,
            receipt_reader=vr_repo,
            review_reader=rv_repo,
            audit_ledger=audit_ledger,
        )
        seal_svc = RevisionSealService(
            revision_repo=rev_repo,
            snapshot_repo=snap_repo,
            journal_repo=je_repo,
            approval_repo=ap_repo,
            patch_reader=pp_repo,
            approval_service=ap_svc,
            audit_ledger=audit_ledger,
            intent_anchor_reader=intent_repo,
        )
        evidence_svc = EvidenceService(
            replay_anchor_repo=ra_repo,
            revision_repo=rev_repo,
            context_repo=ctx_repo,
            inference_repo=inf_repo,
            approval_repo=ap_repo,
            taint_repo=taint_repo,
            budget_repo=budget_repo,
            drift_repo=drift_repo,
            failure_repo=failure_repo,
            journal_repo=je_repo,
            review_repo=rv_repo,
            capability_repo=cap_repo,
            audit_repo=audit_repo,
            audit_ledger=audit_ledger,
        )

        orchestrator = SignablePathOrchestrator(
            capability_service=cap_svc,
            context_service=ctx_svc,
            inference_service=inf_svc,
            patch_proposal_service=pp_svc,
            validation_service=val_svc,
            review_service=rv_svc,
            approval_service=ap_svc,
            revision_seal_service=seal_svc,
            evidence_service=evidence_svc,
            audit_ledger=audit_ledger,
            budget_governor=budget_governor,
            context_repository=ctx_repo,
            intent_anchor_repository=intent_repo,
            connection=conn,
        )

        recovery_gate = build_standard_recovery_gate(
            audit_repository=audit_repo,
            intent_anchor_repository=intent_repo,
            context_repository=ctx_repo,
            inference_repository=inf_repo,
            patch_proposal_repository=pp_repo,
            validation_receipt_repository=vr_repo,
            review_repository=rv_repo,
            approval_repository=ap_repo,
            revision_repository=rev_repo,
            replay_anchor_repository=ra_repo,
        )
    except Exception as exc:
        try:
            conn.close()
        except Exception:
            pass
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory wiring failed: {exc}"
        ) from exc

    return RecoverySessionHost(
        recovery_gate=recovery_gate,
        orchestrator=orchestrator,
        close_callback=conn.close,
    )
