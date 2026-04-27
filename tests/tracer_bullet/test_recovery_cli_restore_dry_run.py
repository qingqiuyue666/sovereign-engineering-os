"""
P0-7 phase 1 — recovery CLI restore dry-run / restore plan.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.10 invariant binding
- v11 §24.2 INV-018 (legal lifecycle transitions)
- foundation §6 (P0 sealing + crash-window proofs)

These tests pin the read-only restore-dry-run subcommand:

- Evaluation routes through `RecoveryGate.evaluate` only; never
  `restore_if_allowed` and never `restore_task_from_snapshot`.
- `restored` is always `False`.
- `restore_allowed` / `would_restore` are `True` only for
  `SAFE_TO_RESUME`, `SEALED`, `ABANDONED`.
- `restore_mode` is `"resume"` (SAFE_TO_RESUME),
  `"terminal_introspection"` (SEALED, ABANDONED), or `"refused"`
  (UNRECOVERABLE, NEEDS_MANUAL_REVIEW).
- `refusal_reason` is set only for refused classes.
- The CLI never writes a durable row.
- Missing `--db` path returns `EXIT_DB_ERROR (3)` and creates no file.
- Existing P0-6 `evaluate` JSON shape does not gain restore-dry-run
  keys.
"""

from __future__ import annotations

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
    EXIT_DB_ERROR,
    EXIT_INVALID_ARGS,
    EXIT_OK,
    main,
    render_restore_dry_run,
    render_result,
)
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import RecoveryClass
from kernel.lifecycle.recovery_gate import build_standard_recovery_gate
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


class TestRestoreDryRunPureHelpers(unittest.TestCase):
    """`render_restore_dry_run` against the in-memory harness."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()
        self.gate = _gate_from_harness(self.harness)

    def tearDown(self) -> None:
        self.harness.close()

    # ------------------------------------------------------------------
    # 1. Unknown task -> refused / unrecoverable
    # ------------------------------------------------------------------

    def test_restore_dry_run_unknown_task_refused(self) -> None:
        result = self.gate.evaluate("task-never-existed")
        rendered = render_restore_dry_run(result)
        self.assertEqual(rendered["command"], "restore-dry-run")
        self.assertEqual(rendered["recovery_class"], "unrecoverable")
        self.assertFalse(rendered["restore_allowed"])
        self.assertFalse(rendered["would_restore"])
        self.assertFalse(rendered["restored"])
        self.assertEqual(rendered["restore_mode"], "refused")
        self.assertEqual(rendered["refusal_reason"], "unrecoverable")
        self.assertFalse(rendered["snapshot_present"])

    # ------------------------------------------------------------------
    # 2. Safe-to-resume -> allowed / resume
    # ------------------------------------------------------------------

    def test_restore_dry_run_safe_to_resume_allowed(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        result = self.gate.evaluate(task_id)
        rendered = render_restore_dry_run(result)
        self.assertEqual(rendered["recovery_class"], "safe_to_resume")
        self.assertEqual(rendered["current_stage"], "inference")
        self.assertTrue(rendered["restore_allowed"])
        self.assertTrue(rendered["would_restore"])
        self.assertFalse(rendered["restored"])
        self.assertEqual(rendered["restore_mode"], "resume")
        self.assertIsNone(rendered["refusal_reason"])

    # ------------------------------------------------------------------
    # 3. SEALED -> allowed / terminal_introspection
    # ------------------------------------------------------------------

    def test_restore_dry_run_sealed_allowed_for_terminal_introspection(
        self,
    ) -> None:
        ids = self.harness.run_full_happy_path()
        result = self.gate.evaluate(ids["task_id"])
        rendered = render_restore_dry_run(result)
        self.assertEqual(rendered["recovery_class"], "sealed")
        self.assertEqual(rendered["terminal_state"], "sealed")
        self.assertEqual(rendered["current_stage"], "sealed")
        self.assertTrue(rendered["restore_allowed"])
        self.assertTrue(rendered["would_restore"])
        self.assertFalse(rendered["restored"])
        self.assertEqual(rendered["restore_mode"], "terminal_introspection")
        self.assertIsNone(rendered["refusal_reason"])

    # ------------------------------------------------------------------
    # 4. ABANDONED -> allowed / terminal_introspection
    # ------------------------------------------------------------------

    def test_restore_dry_run_abandoned_allowed_for_terminal_introspection(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        self.harness.orch.abandon(
            task_id=task_id, reason="dry_run_test_abandon"
        )
        result = self.gate.evaluate(task_id)
        rendered = render_restore_dry_run(result)
        self.assertEqual(rendered["recovery_class"], "abandoned")
        self.assertEqual(rendered["current_stage"], "abandoned")
        self.assertTrue(rendered["restore_allowed"])
        self.assertTrue(rendered["would_restore"])
        self.assertFalse(rendered["restored"])
        self.assertEqual(rendered["restore_mode"], "terminal_introspection")
        self.assertIsNone(rendered["refusal_reason"])

    # ------------------------------------------------------------------
    # 5. Duplicate intent anchor -> needs_manual_review / refused
    # ------------------------------------------------------------------

    def test_restore_dry_run_needs_manual_review_refused(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        # Inject duplicate intent anchor row -> NEEDS_MANUAL_REVIEW.
        self.harness.intent_repo.insert(
            intent_id=f"intent-dup-{uuid4().hex[:8]}",
            task_id=task_id,
            state="admitted",
        )
        result = self.gate.evaluate(task_id)
        rendered = render_restore_dry_run(result)
        self.assertEqual(rendered["recovery_class"], "needs_manual_review")
        self.assertFalse(rendered["restore_allowed"])
        self.assertFalse(rendered["would_restore"])
        self.assertFalse(rendered["restored"])
        self.assertEqual(rendered["restore_mode"], "refused")
        self.assertEqual(rendered["refusal_reason"], "needs_manual_review")

    # ------------------------------------------------------------------
    # 9. evaluate JSON shape unchanged (does not include dry-run keys)
    # ------------------------------------------------------------------

    def test_evaluate_command_json_shape_unchanged(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        result = self.gate.evaluate(task_id)
        rendered = render_result(result)
        for forbidden in (
            "restore_allowed",
            "would_restore",
            "restore_mode",
            "refusal_reason",
            "command",
        ):
            self.assertNotIn(
                forbidden,
                rendered,
                f"evaluate JSON must not include {forbidden!r}",
            )


class TestRestoreDryRunMainEntry(unittest.TestCase):
    """`main(['restore-dry-run', ...])` end-to-end with file-backed DB."""

    def setUp(self) -> None:
        from kernel.stores.sqlite.wal_recovery import (
            apply_migrations,
            open_connection,
        )

        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "recovery_dry_run.db")

        boot = open_connection(self.db_path)
        apply_migrations(boot)
        boot.close()

        self.harness = self._build_harness_on_path(self.db_path)

    def tearDown(self) -> None:
        try:
            self.harness.close()
        finally:
            self._tmpdir.cleanup()

    @staticmethod
    def _build_harness_on_path(db_path: str) -> AcceptanceHarness:
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

    def _reopen_harness_conn(self) -> None:
        import sqlite3

        self.harness.conn = sqlite3.connect(self.db_path)

    # ------------------------------------------------------------------
    # 6. dry-run does not write durable rows
    # ------------------------------------------------------------------

    def test_restore_dry_run_does_not_write_durable_rows(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        self.harness.conn.close()

        before_audit = _audit_count_via_path(self.db_path)
        before_intent = _intent_anchor_count_via_path(self.db_path)

        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            rc = main(
                [
                    "restore-dry-run",
                    "--db",
                    self.db_path,
                    "--task-id",
                    task_id,
                ]
            )
        self.assertEqual(rc, EXIT_OK)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload["command"], "restore-dry-run")
        self.assertTrue(payload["restore_allowed"])
        self.assertTrue(payload["would_restore"])
        self.assertFalse(payload["restored"])

        after_audit = _audit_count_via_path(self.db_path)
        after_intent = _intent_anchor_count_via_path(self.db_path)
        self.assertEqual(after_audit, before_audit)
        self.assertEqual(after_intent, before_intent)

        self._reopen_harness_conn()

    # ------------------------------------------------------------------
    # 7. missing db path returns 3 and does not create file
    # ------------------------------------------------------------------

    def test_restore_dry_run_missing_db_path_returns_3_and_does_not_create_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = os.path.join(tmpdir, "missing.db")
            self.assertFalse(os.path.exists(missing_path))

            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                rc = main(
                    [
                        "restore-dry-run",
                        "--db",
                        missing_path,
                        "--task-id",
                        "task-x",
                    ]
                )
            self.assertEqual(rc, EXIT_DB_ERROR)
            self.assertIn(
                "database file does not exist", buf_err.getvalue()
            )
            self.assertFalse(
                os.path.exists(missing_path),
                "restore-dry-run must not create a new SQLite file",
            )

    # ------------------------------------------------------------------
    # 8. invalid args returns 2
    # ------------------------------------------------------------------

    def test_restore_dry_run_invalid_args_returns_2(self) -> None:
        # Missing --db.
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = main(["restore-dry-run", "--task-id", "task-x"])
        self.assertEqual(rc, EXIT_INVALID_ARGS)

        # Missing --task-id.
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = main(["restore-dry-run", "--db", self.db_path])
        self.assertEqual(rc, EXIT_INVALID_ARGS)


if __name__ == "__main__":
    unittest.main()
