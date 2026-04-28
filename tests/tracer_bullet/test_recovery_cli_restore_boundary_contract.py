"""
P0-8 phase 1 — recovery restore boundary contract.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.10 invariant binding
- v11 §24.2 INV-018 (legal lifecycle transitions)
- foundation §6 (P0 sealing + crash-window proofs)

These tests lock the recovery restore boundary after P0-7 by pinning:

- `kernel.lifecycle.recovery_cli` exposes exactly two subcommands:
  `evaluate` and `restore-dry-run`. No `restore` subcommand exists,
  and any invocation of one returns ``EXIT_INVALID_ARGS`` without
  creating a database file as a side effect.
- `restore-dry-run` remains a pure read: it sets
  ``would_restore=True`` for SAFE_TO_RESUME but always reports
  ``restored=False``, and never mutates ``audit_records`` or
  ``intent_anchor_records``.
- `SignablePathOrchestrator.restore_task_from_snapshot` is in-memory
  only: a restore visible on one orchestrator instance is invisible
  to a second fresh orchestrator built over the same connection and
  services.

Together these properties prove that a one-shot
`recovery_cli restore` subcommand would be ephemeral and misleading
(the orchestrator memory restored inside the CLI process disappears
when the process exits), and prevent the subcommand's accidental
introduction before a runtime host exists.

This file adds tests only. It does not modify production semantics.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle.recovery_cli import (
    EXIT_INVALID_ARGS,
    EXIT_OK,
    build_parser,
    main,
)
from kernel.lifecycle.recovery_gate import build_standard_recovery_gate
from kernel.lifecycle.signable_path_orchestrator import SignablePathOrchestrator
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import RecoveryClass
from validation.tests.acceptance.conftest import AcceptanceHarness


def _audit_count_via_path(db_path: str) -> int:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return int(
            conn.execute("SELECT COUNT(*) FROM audit_records;").fetchone()[0]
        )
    finally:
        conn.close()


def _intent_anchor_count_via_path(db_path: str) -> int:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM intent_anchor_records;"
            ).fetchone()[0]
        )
    finally:
        conn.close()


def _build_harness_on_path(db_path: str) -> AcceptanceHarness:
    """Build an `AcceptanceHarness` whose connection is bound to a
    file-backed SQLite database at ``db_path``.

    Mirrors the test-local helper already used by P0-6/P0-7
    (`test_recovery_cli_operator_surface.py`,
    `test_recovery_cli_restore_dry_run.py`) so the boundary contract
    exercises the same end-to-end CLI shape as the merged operator
    surface tests.
    """
    from kernel.stores.sqlite.wal_recovery import open_connection
    import kernel.stores.sqlite.wal_recovery as wr

    original_open = wr.open_connection
    replaced = open_connection(db_path)

    def _stub_first_call(_path):
        wr.open_connection = original_open  # type: ignore[assignment]
        return replaced

    wr.open_connection = _stub_first_call  # type: ignore[assignment]

    from validation.tests.acceptance import conftest as conftest_module

    original_open_in_conftest = conftest_module.open_connection
    conftest_module.open_connection = _stub_first_call  # type: ignore[assignment]

    try:
        harness = AcceptanceHarness()
    finally:
        wr.open_connection = original_open  # type: ignore[assignment]
        conftest_module.open_connection = (  # type: ignore[assignment]
            original_open_in_conftest
        )
    return harness


def _gate_from_harness(harness: AcceptanceHarness):
    return build_standard_recovery_gate(
        audit_repository=harness.audit_repo,
        intent_anchor_repository=harness.intent_repo,
        context_repository=harness.ctx_repo,
        inference_repository=harness.inf_repo,
        patch_proposal_repository=harness.pp_repo,
        validation_receipt_repository=harness.vr_repo,
        review_repository=harness.rv_repo,
        approval_repository=harness.ap_repo,
        revision_repository=harness.rev_repo,
        replay_anchor_repository=harness.ra_repo,
    )


def _fresh_orchestrator_from_harness(
    harness: AcceptanceHarness,
) -> SignablePathOrchestrator:
    """Construct a fresh `SignablePathOrchestrator` over the harness's
    services and connection.

    The returned instance starts with an empty ``_tasks`` dict,
    simulating a process that retained the durable substrate but lost
    its in-memory lifecycle state — the exact precondition for
    `restore_task_from_snapshot`.
    """
    return SignablePathOrchestrator(
        capability_service=harness.cap_svc,
        context_service=harness.ctx_svc,
        inference_service=harness.inf_svc,
        patch_proposal_service=harness.pp_svc,
        validation_service=harness.val_svc,
        review_service=harness.rev_svc,
        approval_service=harness.ap_svc,
        revision_seal_service=harness.seal_svc,
        evidence_service=harness.evidence_svc,
        audit_ledger=harness.audit_ledger,
        budget_governor=harness.budget_governor,
        context_repository=harness.ctx_repo,
        intent_anchor_repository=harness.intent_repo,
        connection=harness.conn,
    )


class TestRecoveryCliRestoreBoundaryContract(unittest.TestCase):
    """P0-8 boundary contract: `recovery_cli` has no `restore`
    subcommand and `restore_task_from_snapshot` is in-memory only."""

    # ------------------------------------------------------------------
    # 1. `restore` is not a CLI subcommand and does not create a DB.
    # ------------------------------------------------------------------

    def test_recovery_cli_has_no_restore_subcommand(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = os.path.join(tmpdir, "missing.db")
            self.assertFalse(os.path.exists(missing_path))

            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                rc = main(
                    [
                        "restore",
                        "--db",
                        missing_path,
                        "--task-id",
                        "task-x",
                    ]
                )
            self.assertEqual(rc, EXIT_INVALID_ARGS)
            self.assertIn("invalid choice", buf_err.getvalue())
            self.assertFalse(
                os.path.exists(missing_path),
                "rejected restore subcommand must not create a "
                "database file as a side effect",
            )

    # ------------------------------------------------------------------
    # 2. CLI subcommand set is exactly {"evaluate", "restore-dry-run"}.
    # ------------------------------------------------------------------

    def test_recovery_cli_subcommand_set_is_evaluate_and_dry_run_only(
        self,
    ) -> None:
        parser = build_parser()
        sub_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        self.assertEqual(
            len(sub_actions),
            1,
            "recovery_cli must register exactly one subparsers group",
        )
        registered = set(sub_actions[0].choices.keys())
        self.assertEqual(
            registered,
            {"evaluate", "restore-dry-run"},
            "recovery_cli subcommands must equal "
            "{'evaluate', 'restore-dry-run'}; "
            f"got {sorted(registered)!r}",
        )

    # ------------------------------------------------------------------
    # 3. `restore-dry-run` remains a pure read: would_restore=True,
    #    restored=False, durable row counts unchanged.
    # ------------------------------------------------------------------

    def test_restore_dry_run_remains_pure_read(self) -> None:
        from kernel.stores.sqlite.wal_recovery import (
            apply_migrations,
            open_connection,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "recovery_p0_8.db")

            # Bootstrap the schema on disk.
            boot = open_connection(db_path)
            apply_migrations(boot)
            boot.close()

            harness = _build_harness_on_path(db_path)
            try:
                task_id = f"task-{uuid4().hex[:8]}"
                harness.run_through_stage(task_id, Stage.INFERENCE)
            finally:
                harness.close()

            before_audit = _audit_count_via_path(db_path)
            before_intent = _intent_anchor_count_via_path(db_path)

            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                rc = main(
                    [
                        "restore-dry-run",
                        "--db",
                        db_path,
                        "--task-id",
                        task_id,
                    ]
                )
            self.assertEqual(rc, EXIT_OK)

            payload = json.loads(buf_out.getvalue().strip())
            self.assertEqual(payload["command"], "restore-dry-run")
            self.assertEqual(
                payload["recovery_class"], "safe_to_resume"
            )
            self.assertTrue(payload["would_restore"])
            self.assertFalse(payload["restored"])

            after_audit = _audit_count_via_path(db_path)
            after_intent = _intent_anchor_count_via_path(db_path)
            self.assertEqual(after_audit, before_audit)
            self.assertEqual(after_intent, before_intent)

    # ------------------------------------------------------------------
    # 4. `restore_task_from_snapshot` is instance-local memory only:
    #    durable rows untouched and a second fresh orchestrator over
    #    the same connection sees no restored task.
    # ------------------------------------------------------------------

    def test_restore_task_from_snapshot_is_in_memory_only(self) -> None:
        harness = AcceptanceHarness()
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            harness.run_through_stage(task_id, Stage.INFERENCE)

            before_audit = harness.conn.execute(
                "SELECT COUNT(*) FROM audit_records;"
            ).fetchone()[0]
            before_intent = harness.conn.execute(
                "SELECT COUNT(*) FROM intent_anchor_records;"
            ).fetchone()[0]

            fresh_orch = _fresh_orchestrator_from_harness(harness)
            gate = _gate_from_harness(harness)
            result = gate.evaluate(task_id)
            self.assertEqual(
                result.recovery_class, RecoveryClass.SAFE_TO_RESUME
            )
            self.assertIsNotNone(result.snapshot)

            fresh_orch.restore_task_from_snapshot(
                snapshot=result.snapshot,
                recovery_class=RecoveryClass.SAFE_TO_RESUME,
            )

            self.assertEqual(
                fresh_orch.current_stage(task_id), Stage.INFERENCE
            )

            after_audit = harness.conn.execute(
                "SELECT COUNT(*) FROM audit_records;"
            ).fetchone()[0]
            after_intent = harness.conn.execute(
                "SELECT COUNT(*) FROM intent_anchor_records;"
            ).fetchone()[0]
            self.assertEqual(after_audit, before_audit)
            self.assertEqual(after_intent, before_intent)

            second_fresh_orch = _fresh_orchestrator_from_harness(harness)
            self.assertIsNone(
                second_fresh_orch.current_stage(task_id),
                "restore_task_from_snapshot must not persist across "
                "orchestrator instances; a second fresh orchestrator "
                "over the same connection must see no restored task",
            )
        finally:
            harness.close()


if __name__ == "__main__":
    unittest.main()
