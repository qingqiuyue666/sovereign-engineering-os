"""
P0-6 phase 1 — recovery CLI / operator surface (read-only).

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.10 invariant binding
- v11 §24.2 INV-018 (legal lifecycle transitions)
- foundation §6 (P0 sealing + crash-window proofs)

These tests pin the read-only operator CLI behavior:

- `evaluate_task` + `render_result` are the pure helpers tests exercise
  directly when the harness is in-memory.
- `main` opens a file-backed SQLite database, evaluates one task_id,
  and emits deterministic JSON to stdout.
- `main` returns 0 on every successful evaluation (including
  UNRECOVERABLE / NEEDS_MANUAL_REVIEW), 2 on argparse failure, 3 on
  database open errors, 4 on unexpected runtime errors.
- The CLI never calls `restore_if_allowed`, never writes durable rows,
  and always closes the database connection.
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
    EXIT_OK,
    EXIT_INVALID_ARGS,
    evaluate_task,
    main,
    render_result,
)
from kernel.lifecycle.stage_types import Stage
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


class TestRecoveryCliPureHelpers(unittest.TestCase):
    """`evaluate_task` + `render_result` against the in-memory harness.

    The acceptance harness opens an in-memory `:memory:` SQLite that is
    not file-backed, so subprocess-style CLI tests cannot share that
    connection. These tests exercise the pure helpers `main` calls
    after opening the file-backed DB.
    """

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    # ------------------------------------------------------------------
    # A — unknown task via pure helpers (file-backed counterpart in TestRecoveryCliMainEntry)
    # ------------------------------------------------------------------

    def test_evaluate_task_unknown_returns_unrecoverable(self) -> None:
        result = evaluate_task(self.harness.conn, "task-never-existed")
        rendered = render_result(result)
        self.assertEqual(rendered["recovery_class"], "unrecoverable")
        self.assertEqual(rendered["reason"], "unrecoverable")
        self.assertFalse(rendered["restored"])
        self.assertFalse(rendered["snapshot_present"])
        self.assertIsNone(rendered["current_stage"])
        self.assertIsNone(rendered["terminal_state"])
        self.assertEqual(rendered["artifact_count"], 0)
        self.assertIsNone(rendered["intent_anchor_count"])
        self.assertIsNone(rendered["malformed_event_count"])
        self.assertIsNone(rendered["last_event_sequence"])

    # ------------------------------------------------------------------
    # B — safe-to-resume contextual JSON
    # ------------------------------------------------------------------

    def test_evaluate_task_safe_to_resume_outputs_contextual_json(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)

        result = evaluate_task(self.harness.conn, task_id)
        rendered = render_result(result)
        self.assertEqual(rendered["recovery_class"], "safe_to_resume")
        self.assertEqual(rendered["reason"], "safe_to_resume")
        self.assertFalse(rendered["restored"])
        self.assertTrue(rendered["snapshot_present"])
        self.assertEqual(rendered["current_stage"], "inference")
        self.assertIsNone(rendered["terminal_state"])
        self.assertGreaterEqual(rendered["artifact_count"], 2)
        self.assertEqual(rendered["intent_anchor_count"], 1)
        self.assertEqual(rendered["malformed_event_count"], 0)
        self.assertIsInstance(rendered["last_event_sequence"], int)

    # ------------------------------------------------------------------
    # C — sealed terminal JSON
    # ------------------------------------------------------------------

    def test_evaluate_task_sealed_outputs_terminal_json(self) -> None:
        ids = self.harness.run_full_happy_path()
        result = evaluate_task(self.harness.conn, ids["task_id"])
        rendered = render_result(result)
        self.assertEqual(rendered["recovery_class"], "sealed")
        self.assertEqual(rendered["reason"], "sealed")
        self.assertEqual(rendered["terminal_state"], "sealed")
        self.assertEqual(rendered["current_stage"], "sealed")
        self.assertFalse(rendered["restored"])
        self.assertEqual(rendered["intent_anchor_count"], 1)
        self.assertEqual(rendered["malformed_event_count"], 0)

    # ------------------------------------------------------------------
    # D — pure helpers do not write durable rows
    # ------------------------------------------------------------------

    def test_evaluate_task_does_not_write_durable_rows(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)

        before_audit = self.harness.conn.execute(
            "SELECT COUNT(*) FROM audit_records;"
        ).fetchone()[0]
        before_intent = self.harness.conn.execute(
            "SELECT COUNT(*) FROM intent_anchor_records;"
        ).fetchone()[0]

        evaluate_task(self.harness.conn, task_id)

        after_audit = self.harness.conn.execute(
            "SELECT COUNT(*) FROM audit_records;"
        ).fetchone()[0]
        after_intent = self.harness.conn.execute(
            "SELECT COUNT(*) FROM intent_anchor_records;"
        ).fetchone()[0]
        self.assertEqual(after_audit, before_audit)
        self.assertEqual(after_intent, before_intent)


class TestRecoveryCliMainEntry(unittest.TestCase):
    """`main(argv)` end-to-end with a file-backed SQLite database."""

    def setUp(self) -> None:
        # Prepare a file-backed DB so `main` can open it via
        # `open_connection(path)`. Wire all repositories used by
        # AcceptanceHarness against that same connection so
        # admit_*-driven setup writes there.
        from kernel.stores.sqlite.wal_recovery import (
            apply_migrations,
            open_connection,
        )

        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "recovery_cli.db")

        # Bootstrap the schema in the file-backed DB.
        boot = open_connection(self.db_path)
        apply_migrations(boot)
        boot.close()

        # Build a harness that uses this file-backed DB instead of
        # `:memory:`. We bypass AcceptanceHarness.__init__ since it
        # hard-codes `:memory:`; instead replicate the wiring with the
        # file-backed connection.
        self.harness = self._build_harness_on_path(self.db_path)

    def tearDown(self) -> None:
        try:
            self.harness.close()
        finally:
            self._tmpdir.cleanup()

    @staticmethod
    def _build_harness_on_path(db_path: str) -> AcceptanceHarness:
        """Return an AcceptanceHarness whose `self.conn` is file-backed.

        Constructing AcceptanceHarness normally with `:memory:` and
        swapping the connection would cascade through every wired
        repository. We instead instantiate the harness, then patch its
        `__init__`-time connection to one opened on `db_path`, then
        rebuild the repository / service / orchestrator graph against
        that connection.
        """
        from kernel.stores.sqlite.wal_recovery import open_connection

        # Monkey-patch open_connection to return our file-backed handle
        # for the harness's first call, then restore the original.
        import kernel.stores.sqlite.wal_recovery as wr

        original_open = wr.open_connection
        replaced = open_connection(db_path)

        def _stub_first_call(_path):
            wr.open_connection = original_open  # type: ignore[assignment]
            return replaced

        wr.open_connection = _stub_first_call  # type: ignore[assignment]

        # Also patch the import inside the conftest module to ensure
        # the same first-call substitution applies there.
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

    # ------------------------------------------------------------------
    # A — unknown task via main (exit 0, JSON correct)
    # ------------------------------------------------------------------

    def test_cli_evaluate_unknown_task_outputs_unrecoverable_json(
        self,
    ) -> None:
        # Close harness's connection before invoking main so the
        # operator-style separate-connection open path is exercised.
        self.harness.conn.close()

        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            rc = main(
                ["evaluate", "--db", self.db_path, "--task-id", "task-never"]
            )
        self.assertEqual(rc, EXIT_OK)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload["recovery_class"], "unrecoverable")
        self.assertFalse(payload["restored"])
        self.assertFalse(payload["snapshot_present"])

        # Reopen the harness connection so tearDown can close cleanly.
        import sqlite3

        self.harness.conn = sqlite3.connect(self.db_path)

    # ------------------------------------------------------------------
    # B — safe-to-resume via main (exit 0, JSON populated)
    # ------------------------------------------------------------------

    def test_cli_evaluate_safe_to_resume_outputs_contextual_json(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        # Close harness conn so file is flushed and main can re-open.
        self.harness.conn.close()

        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            rc = main(
                ["evaluate", "--db", self.db_path, "--task-id", task_id]
            )
        self.assertEqual(rc, EXIT_OK)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload["recovery_class"], "safe_to_resume")
        self.assertFalse(payload["restored"])
        self.assertTrue(payload["snapshot_present"])
        self.assertEqual(payload["current_stage"], "inference")
        self.assertGreaterEqual(payload["artifact_count"], 2)
        self.assertEqual(payload["intent_anchor_count"], 1)
        self.assertEqual(payload["malformed_event_count"], 0)

        import sqlite3

        self.harness.conn = sqlite3.connect(self.db_path)

    # ------------------------------------------------------------------
    # C — sealed via main
    # ------------------------------------------------------------------

    def test_cli_evaluate_sealed_outputs_terminal_json(self) -> None:
        ids = self.harness.run_full_happy_path()
        task_id = ids["task_id"]
        self.harness.conn.close()

        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            rc = main(
                ["evaluate", "--db", self.db_path, "--task-id", task_id]
            )
        self.assertEqual(rc, EXIT_OK)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload["recovery_class"], "sealed")
        self.assertEqual(payload["terminal_state"], "sealed")
        self.assertEqual(payload["current_stage"], "sealed")
        self.assertFalse(payload["restored"])

        import sqlite3

        self.harness.conn = sqlite3.connect(self.db_path)

    # ------------------------------------------------------------------
    # D — main does not write durable rows
    # ------------------------------------------------------------------

    def test_cli_does_not_write_durable_rows(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        self.harness.conn.close()

        before_audit = _audit_count_via_path(self.db_path)
        before_intent = _intent_anchor_count_via_path(self.db_path)

        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            rc = main(
                ["evaluate", "--db", self.db_path, "--task-id", task_id]
            )
        self.assertEqual(rc, EXIT_OK)

        after_audit = _audit_count_via_path(self.db_path)
        after_intent = _intent_anchor_count_via_path(self.db_path)
        self.assertEqual(after_audit, before_audit)
        self.assertEqual(after_intent, before_intent)

        import sqlite3

        self.harness.conn = sqlite3.connect(self.db_path)

    # ------------------------------------------------------------------
    # E — invalid args returns 2
    # ------------------------------------------------------------------

    def test_cli_invalid_args_returns_2(self) -> None:
        # No --db flag.
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = main(["evaluate", "--task-id", "task-x"])
        self.assertEqual(rc, EXIT_INVALID_ARGS)


if __name__ == "__main__":
    unittest.main()
