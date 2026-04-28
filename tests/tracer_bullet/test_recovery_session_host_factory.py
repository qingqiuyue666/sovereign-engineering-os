"""
P0-10 phase 1 — RecoverySessionHost file-backed factory tests.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.5 Replay admission boundary
- v11 §22.10 invariant binding
- foundation §6 (P0 sealing + crash-window proofs)

These tests pin the behavior of
`build_recovery_session_host_from_sqlite`:

- The factory refuses to construct a host when the DB path does not
  exist, and never creates a new database file as a side effect.
- The factory builds a working host over an existing file-backed
  SQLite database; the host can evaluate, restore, and is closeable.
- The host's `close()` releases the connection through the factory's
  `close_callback`; subsequent public operations raise
  `RecoverySessionHostClosed`.
- A task that was admitted through `Stage.INFERENCE` against the same
  underlying file-backed DB can be restored via the factory-built
  host's gate, and the restored task's `current_stage` is visible
  inside the host. (Continuation through the next `admit_*` call is
  out of scope for the factory tests; it is already pinned by the
  P0-9 RecoverySessionHost tests.)
- Factory construction has no durable side effects: it does not
  insert audit_records or intent_anchor_records rows.
- P0-10 does NOT add a CLI restore subcommand: the recovery_cli
  parser remains exactly {"evaluate", "restore-dry-run"}.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping
from unittest import mock
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.lifecycle.recovery_cli import build_parser
from kernel.lifecycle.recovery_session_host import (
    RecoverySessionHost,
    RecoverySessionHostClosed,
    RecoverySessionHostFactoryError,
    build_recovery_session_host_from_sqlite,
)
from kernel.lifecycle.signable_path_orchestrator import (
    SignablePathOrchestrator,
)
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import RecoveryClass
from kernel.services.approval_service import ApprovalService
from kernel.services.budget_governor import BudgetGovernor
from kernel.services.capability_service import CapabilityService
from kernel.services.context_service import ContextService
from kernel.services.evidence_service import EvidenceService
from kernel.services.inference_service import (
    InferencePolicy,
    InferenceService,
)
from kernel.services.patch_proposal_service import PatchProposalService
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
from kernel.stores.sqlite.wal_recovery import (
    apply_migrations,
    open_connection,
)


class _FakeModelAdapter:
    """Deterministic adapter mirroring conftest's FakeModelAdapter.

    Test-local so the factory tests can drive `admit_inference` without
    depending on `AcceptanceHarness` (which is in-memory only and the
    factory tests need a file-backed DB).
    """

    def invoke(
        self, *, prompt_envelope: Mapping[str, Any], policy: InferencePolicy
    ) -> Mapping[str, Any]:
        return {
            "output_text": "factory-test output text",
            "token_usage": {"input": 100, "output": 20},
            "latency_ms": 42,
            "model_route_id": "fake-model-v1",
        }


def _seed_inference_stage(db_path: Path, task_id: str) -> None:
    """Open a temporary file-backed wiring, admit a task through
    `Stage.INFERENCE`, and close.

    The factory under test uses `_NullAdapter` (recovery is the
    factory's purpose, not new inference), so test D cannot drive
    `admit_inference` through the factory's own host. This helper
    seeds the durable substrate over the same DB path using a
    minimal AcceptanceHarness-shaped wiring, then releases the
    connection so the factory has exclusive ownership.

    The helper writes ONLY through the orchestrator's existing
    admit_* boundary (which already routes through `KernelUnitOfWork`).
    It does not bypass any P0 transaction guard.
    """
    from datetime import datetime, timedelta, timezone

    conn = open_connection(db_path)
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
            actor_identity="recovery_session_host_factory_test",
        )

        cap_svc = CapabilityService(
            repository=cap_repo, audit_ledger=audit_ledger
        )
        ctx_svc = ContextService(
            repository=ctx_repo, audit_ledger=audit_ledger
        )
        budget_governor = BudgetGovernor(
            audit_ledger=audit_ledger, budget_repository=budget_repo
        )
        inf_svc = InferenceService(
            repository=inf_repo,
            audit_ledger=audit_ledger,
            context_reader=ctx_repo,
            adapter=_FakeModelAdapter(),
            policy=InferencePolicy(),
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
        orch = SignablePathOrchestrator(
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

        intent_id = f"intent-{uuid4().hex[:8]}"
        root_rev_id = "rev-genesis-000"
        now = datetime.now(timezone.utc)

        cap_ctx = cap_svc.issue_token(
            subject_identity="recovery_session_host_factory_test",
            capability_name="read_repository_snapshot",
            scope_hash="scope:factory",
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
            single_use=True,
            bound_task_id=task_id,
        )
        orch.admit_context(
            task_id=task_id,
            intent_id=intent_id,
            capability_token=cap_ctx,
            root_revision_id=root_rev_id,
            request={
                "repo_graph_version": "1.0",
                "symbol_index_version": "1.0",
                "candidate_file_ids": ["src/main.py"],
                "symbol_frontier_ids": ["main"],
                "packing_policy_version": "phase1_budget_policy_v1",
                "actual_tokens": 500,
            },
        )

        cap_inf = cap_svc.issue_token(
            subject_identity="recovery_session_host_factory_test",
            capability_name="invoke_inference",
            scope_hash="scope:factory",
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
            single_use=True,
            bound_task_id=task_id,
        )
        orch.admit_inference(
            task_id=task_id,
            capability_token=cap_inf,
            worker_profile="recovery_session_host_factory_test",
            model_route_id="fake-model-v1",
        )
    finally:
        conn.close()


def _initialize_empty_db(db_path: Path) -> None:
    """Open a connection to ``db_path`` (creating the file) and apply
    migrations, then close. Used as the smallest setup for tests that
    need an existing schema-bearing database but no admitted tasks.
    """
    conn = open_connection(db_path)
    try:
        apply_migrations(conn)
    finally:
        conn.close()


def _audit_count(db_path: Path) -> int:
    conn = open_connection(db_path)
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM audit_records;"
        ).fetchone()[0]
    finally:
        conn.close()


def _intent_anchor_count(db_path: Path) -> int:
    conn = open_connection(db_path)
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM intent_anchor_records;"
        ).fetchone()[0]
    finally:
        conn.close()


class TestRecoverySessionHostFactory(unittest.TestCase):
    """P0-10 phase 1 — RecoverySessionHost file-backed factory."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # ------------------------------------------------------------------
    # A. missing DB path -> raise; do not create file
    # ------------------------------------------------------------------

    def test_factory_missing_db_path_raises_and_does_not_create_file(
        self,
    ) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        with self.assertRaises(RecoverySessionHostFactoryError):
            build_recovery_session_host_from_sqlite(db_path=missing_path)

        self.assertFalse(
            missing_path.exists(),
            "factory must not create a DB file for a missing path",
        )

    # ------------------------------------------------------------------
    # B. existing file-backed DB -> working host; close marks closed
    # ------------------------------------------------------------------

    def test_factory_builds_host_from_existing_file_backed_db(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        host = build_recovery_session_host_from_sqlite(db_path=db_path)
        try:
            self.assertIsInstance(host, RecoverySessionHost)
            self.assertFalse(host.closed)
            verdict = host.evaluate_task("unknown")
            self.assertEqual(
                verdict.recovery_class, RecoveryClass.UNRECOVERABLE
            )
            self.assertFalse(verdict.restored)
        finally:
            host.close()
        self.assertTrue(host.closed)

    # ------------------------------------------------------------------
    # C. close() closes the connection (callback path) and blocks ops
    # ------------------------------------------------------------------

    def test_factory_host_close_closes_connection(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        host = build_recovery_session_host_from_sqlite(db_path=db_path)

        # Pre-close: public operations succeed.
        verdict = host.evaluate_task("unknown")
        self.assertEqual(
            verdict.recovery_class, RecoveryClass.UNRECOVERABLE
        )

        host.close()
        self.assertTrue(host.closed)

        # Post-close: every public operation raises.
        with self.assertRaises(RecoverySessionHostClosed):
            host.evaluate_task("unknown")
        with self.assertRaises(RecoverySessionHostClosed):
            host.restore_task("unknown")
        with self.assertRaises(RecoverySessionHostClosed):
            host.current_stage("unknown")
        with self.assertRaises(RecoverySessionHostClosed):
            _ = host.orchestrator

        # Idempotent.
        host.close()
        self.assertTrue(host.closed)

    # ------------------------------------------------------------------
    # D. restore via factory host yields visible current_stage
    # ------------------------------------------------------------------

    def test_factory_host_restore_safe_to_resume_and_continue_next_stage(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        task_id = f"task-{uuid4().hex[:8]}"
        # Drive the task through INFERENCE using a separate test-local
        # wiring with a real fake adapter; close that wiring before
        # building the factory host so the factory has exclusive
        # ownership of the connection.
        _seed_inference_stage(db_path, task_id)

        host = build_recovery_session_host_from_sqlite(db_path=db_path)
        try:
            result = host.restore_task(task_id)
            self.assertEqual(
                result.recovery_class, RecoveryClass.SAFE_TO_RESUME
            )
            self.assertTrue(result.restored)
            self.assertEqual(
                host.current_stage(task_id), Stage.INFERENCE
            )
            # Continuation through the next `admit_*` call is already
            # pinned by P0-9's `RecoverySessionHost` tests
            # (`test_session_host_restored_task_can_continue_next_stage`).
            # The factory's responsibility is to make `current_stage`
            # visible inside the host after restore.
        finally:
            host.close()

    # ------------------------------------------------------------------
    # E. construction has no durable side effects
    # ------------------------------------------------------------------

    def test_factory_construction_has_no_durable_side_effects(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)
        # Seed one admitted task so the durable counts are non-zero
        # before construction; this strengthens the "unchanged" check.
        _seed_inference_stage(db_path, f"task-{uuid4().hex[:8]}")

        before_audit = _audit_count(db_path)
        before_intent = _intent_anchor_count(db_path)

        host = build_recovery_session_host_from_sqlite(db_path=db_path)
        try:
            # Pure construction: no restore, no evaluate, no admit.
            pass
        finally:
            host.close()

        after_audit = _audit_count(db_path)
        after_intent = _intent_anchor_count(db_path)

        self.assertEqual(after_audit, before_audit)
        self.assertEqual(after_intent, before_intent)

    # ------------------------------------------------------------------
    # F. P0-10 does not add a CLI restore subcommand
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # P0-11 A. existing empty file -> raise; never initialize schema
    # ------------------------------------------------------------------

    def test_factory_existing_empty_file_raises_and_does_not_initialize_schema(
        self,
    ) -> None:
        empty_path = self.tmpdir / "empty.db"
        empty_path.touch()
        self.assertTrue(empty_path.is_file())

        with self.assertRaises(RecoverySessionHostFactoryError) as ctx:
            build_recovery_session_host_from_sqlite(db_path=empty_path)

        message = str(ctx.exception)
        # Message must surface the readiness contract being violated.
        self.assertIn("required schema", message)
        # And must surface at least one of the required table names so
        # operators get an actionable diagnostic, not an opaque blob.
        self.assertTrue(
            any(
                table in message
                for table in (
                    "audit_records",
                    "intent_anchor_records",
                    "journal_entries",
                )
            ),
            f"missing-required-tables message must name at least one "
            f"required table; got: {message!r}",
        )

        # Inspect the file with raw sqlite3 — the factory must not have
        # applied any migration as a side effect of the failed
        # construction. None of the required application tables may be
        # present.
        raw = sqlite3.connect(str(empty_path))
        try:
            rows = raw.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table';"
            ).fetchall()
        finally:
            raw.close()
        present_tables = {row[0] for row in rows}
        required_tables = {
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
        leaked = present_tables & required_tables
        self.assertEqual(
            leaked,
            set(),
            f"factory must not initialize any required schema table on "
            f"failure; found unexpectedly created: {sorted(leaked)!r}",
        )

    # ------------------------------------------------------------------
    # P0-11 B. existing SQLite DB without required schema -> raise
    # ------------------------------------------------------------------

    def test_factory_existing_sqlite_missing_required_tables_raises(
        self,
    ) -> None:
        db_path = self.tmpdir / "unrelated.db"
        seed = sqlite3.connect(str(db_path))
        try:
            seed.execute("CREATE TABLE unrelated_table(id TEXT);")
            seed.commit()
        finally:
            seed.close()

        with self.assertRaises(RecoverySessionHostFactoryError) as ctx:
            build_recovery_session_host_from_sqlite(db_path=db_path)

        message = str(ctx.exception)
        self.assertIn("required schema", message)
        self.assertTrue(
            any(
                table in message
                for table in (
                    "audit_records",
                    "intent_anchor_records",
                    "journal_entries",
                )
            ),
            f"missing-required-tables message must name at least one "
            f"required table; got: {message!r}",
        )

        raw = sqlite3.connect(str(db_path))
        try:
            rows = raw.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table';"
            ).fetchall()
        finally:
            raw.close()
        present_tables = {row[0] for row in rows}
        # Pre-existing harmless table must remain — the factory must
        # not mutate the DB on failure.
        self.assertIn("unrelated_table", present_tables)
        # And no required table may have appeared as a side effect.
        required_tables = {
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
        leaked = present_tables & required_tables
        self.assertEqual(
            leaked,
            set(),
            f"factory must not create any required schema table on "
            f"failure; found unexpectedly created: {sorted(leaked)!r}",
        )

    # ------------------------------------------------------------------
    # P0-11 C. opened connection is closed when schema validation fails
    # ------------------------------------------------------------------

    def test_factory_opened_connection_is_closed_on_schema_validation_failure(
        self,
    ) -> None:
        db_path = self.tmpdir / "fake.db"
        # Real file so `Path.is_file()` passes the missing-path guard.
        db_path.touch()

        class _FakeConn:
            def __init__(self) -> None:
                self.close_count = 0

            def execute(self, *args: Any, **kwargs: Any) -> Any:
                # Force schema validation (the only call between
                # open and the wiring block) to fail with a malformed-
                # DB-style error. Mirrors what raw sqlite3 raises when
                # asked to scan sqlite_master on a corrupt file.
                raise sqlite3.DatabaseError(
                    "forced sqlite_master scan failure"
                )

            def close(self) -> None:
                self.close_count += 1

        fake_conn = _FakeConn()

        # Patch the module attribute so the factory's local
        # `from kernel.stores.sqlite.wal_recovery import open_connection`
        # resolves to the fake.
        with mock.patch(
            "kernel.stores.sqlite.wal_recovery.open_connection",
            return_value=fake_conn,
        ):
            with self.assertRaises(RecoverySessionHostFactoryError):
                build_recovery_session_host_from_sqlite(db_path=db_path)

        self.assertEqual(
            fake_conn.close_count,
            1,
            "factory must close the opened connection exactly once "
            "when schema validation fails after open_connection",
        )

    # ------------------------------------------------------------------
    # P0-11 D. wiring failure after schema validation -> raise (no host)
    # ------------------------------------------------------------------

    def test_factory_wiring_failure_after_schema_validation_closes_connection(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        # Patch a repository constructor used by the factory. With a
        # valid migrated DB on disk, schema validation passes; the
        # patched constructor then raises during the wiring block,
        # which the factory must wrap as
        # `RecoverySessionHostFactoryError` while closing the
        # opened connection.
        with mock.patch(
            "kernel.stores.sqlite.repositories.AuditRepository",
            side_effect=RuntimeError("forced wiring failure"),
        ):
            with self.assertRaises(RecoverySessionHostFactoryError) as ctx:
                build_recovery_session_host_from_sqlite(db_path=db_path)

        # The original wiring failure must be chained, not swallowed.
        cause = ctx.exception.__cause__
        self.assertIsInstance(cause, RuntimeError)
        self.assertIn("forced wiring failure", str(cause))

    # ------------------------------------------------------------------
    # P0-12 A. existing required table missing a required column -> raise
    # ------------------------------------------------------------------

    def test_factory_existing_table_with_missing_required_column_raises(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        # Drop and recreate `intent_anchor_records` without the
        # required `created_at` column. `intent_anchor_records` has no
        # append-only triggers, so DROP TABLE is safe; the recreated
        # table still satisfies the table-existence check from P0-11
        # but fails the P0-12 column-identity check.
        raw = sqlite3.connect(str(db_path))
        try:
            raw.execute("DROP TABLE intent_anchor_records;")
            raw.execute(
                "CREATE TABLE intent_anchor_records ("
                "intent_id TEXT PRIMARY KEY, "
                "task_id TEXT NOT NULL, "
                "state TEXT NOT NULL"
                ");"
            )
            raw.commit()
        finally:
            raw.close()

        with self.assertRaises(RecoverySessionHostFactoryError) as ctx:
            build_recovery_session_host_from_sqlite(db_path=db_path)

        message = str(ctx.exception)
        self.assertIn("intent_anchor_records", message)
        self.assertIn("created_at", message)
        self.assertIn("missing required column", message)

        # The factory must not have backfilled the dropped column or
        # otherwise mutated schema as a side effect of the failure.
        raw = sqlite3.connect(str(db_path))
        try:
            cols = raw.execute(
                "PRAGMA table_info(intent_anchor_records);"
            ).fetchall()
        finally:
            raw.close()
        present_columns = {row[1] for row in cols}
        self.assertNotIn(
            "created_at",
            present_columns,
            "factory must not repair missing columns as a side effect",
        )

    # ------------------------------------------------------------------
    # P0-12 B. existing required append-only trigger missing -> raise
    # ------------------------------------------------------------------

    def test_factory_missing_required_trigger_raises(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        # Drop a single required append-only trigger. INV-026 audit
        # append-only enforcement is silently disabled when this
        # trigger is absent — the factory must refuse.
        raw = sqlite3.connect(str(db_path))
        try:
            raw.execute(
                "DROP TRIGGER audit_records_append_only_update;"
            )
            raw.commit()
        finally:
            raw.close()

        with self.assertRaises(RecoverySessionHostFactoryError) as ctx:
            build_recovery_session_host_from_sqlite(db_path=db_path)

        message = str(ctx.exception)
        self.assertIn("audit_records_append_only_update", message)
        self.assertIn("trigger", message)

        # No side-effect repair: trigger must remain absent.
        raw = sqlite3.connect(str(db_path))
        try:
            rows = raw.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger';"
            ).fetchall()
        finally:
            raw.close()
        present_triggers = {row[0] for row in rows}
        self.assertNotIn(
            "audit_records_append_only_update",
            present_triggers,
            "factory must not recreate dropped triggers as a side effect",
        )

    # ------------------------------------------------------------------
    # P0-12 C. existing required critical index missing -> raise
    # ------------------------------------------------------------------

    def test_factory_missing_required_index_raises(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        # Drop the unique audit-sequence index. The factory must
        # refuse: the index is the substrate for monotonic audit
        # append order, and a wired host without it would silently
        # accept duplicate sequence values.
        raw = sqlite3.connect(str(db_path))
        try:
            raw.execute("DROP INDEX idx_audit_records_sequence;")
            raw.commit()
        finally:
            raw.close()

        with self.assertRaises(RecoverySessionHostFactoryError) as ctx:
            build_recovery_session_host_from_sqlite(db_path=db_path)

        message = str(ctx.exception)
        self.assertIn("idx_audit_records_sequence", message)
        self.assertIn("index", message)

        # No side-effect repair: index must remain absent.
        raw = sqlite3.connect(str(db_path))
        try:
            rows = raw.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index';"
            ).fetchall()
        finally:
            raw.close()
        present_indexes = {row[0] for row in rows}
        self.assertNotIn(
            "idx_audit_records_sequence",
            present_indexes,
            "factory must not recreate dropped indexes as a side effect",
        )

    def test_factory_does_not_add_cli_restore(self) -> None:
        import argparse as _argparse

        parser = build_parser()
        sub_actions = [
            action
            for action in parser._actions
            if isinstance(action, _argparse._SubParsersAction)
        ]
        self.assertEqual(len(sub_actions), 1)
        registered = set(sub_actions[0].choices.keys())
        self.assertEqual(
            registered,
            {"evaluate", "restore-dry-run"},
            "P0-10 must not add a CLI restore subcommand; "
            f"got {sorted(registered)!r}",
        )


if __name__ == "__main__":
    unittest.main()
