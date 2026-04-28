"""
P0-16 phase 1 — RecoverySessionHost operator serialization helpers.

These tests pin pure JSON-safe render helpers for future operator
surfaces without changing factory, recovery, restore, or CLI behavior.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle.recovery_session_host import (
    RecoverySessionHost,
    RecoverySessionHostFactoryResult,
    render_factory_result,
    render_recovery_gate_result,
    render_session_host_state,
    try_build_recovery_session_host_from_sqlite,
)
from kernel.lifecycle.stage_types import Stage
from tests.tracer_bullet.test_recovery_session_host_factory import (
    _audit_count,
    _initialize_empty_db,
    _intent_anchor_count,
    _seed_inference_stage,
)


class TestRecoverySessionHostOperatorSerialization(unittest.TestCase):
    """P0-16 operator serialization helpers."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _build_host_result(
        self, db_path: Path
    ) -> RecoverySessionHostFactoryResult:
        result = try_build_recovery_session_host_from_sqlite(
            db_path=db_path
        )
        self.assertIs(result.ok, True)
        self.assertIsNotNone(result.host)
        return result

    def _require_host(
        self, result: RecoverySessionHostFactoryResult
    ) -> RecoverySessionHost:
        host = result.host
        if host is None:
            self.fail("test setup expected a constructed host")
        return host

    def test_render_factory_result_success_hides_host_object(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        result = self._build_host_result(db_path)
        host = self._require_host(result)
        try:
            payload = render_factory_result(result)
            self.assertIs(payload["ok"], True)
            self.assertEqual(payload["db_path"], str(db_path))
            self.assertIsNone(payload["reason_code"])
            self.assertIsNone(payload["message"])
            self.assertEqual(payload["details"], {})
            self.assertIs(payload["host_present"], True)
            self.assertIs(payload["host_closed"], False)
            self.assertNotIn("host", payload)

            host.close()
            payload = render_factory_result(result)
            self.assertIs(payload["host_closed"], True)
        finally:
            if not host.closed:
                host.close()

    def test_render_factory_result_failure_contains_reason_and_details(
        self,
    ) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        result = try_build_recovery_session_host_from_sqlite(
            db_path=missing_path
        )
        payload = render_factory_result(result)

        self.assertIs(payload["ok"], False)
        self.assertIs(payload["host_present"], False)
        self.assertIsNone(payload["host_closed"])
        self.assertEqual(payload["reason_code"], "missing_db_file")
        self.assertEqual(payload["details"]["db_path"], str(missing_path))
        self.assertIn("database file does not exist", payload["message"])
        self.assertEqual(payload["db_path"], str(missing_path))

    def test_render_factory_result_details_are_copied(self) -> None:
        result = RecoverySessionHostFactoryResult(
            ok=False,
            host=None,
            reason_code="factory_error",
            message="failure",
            details={"x": "y"},
            db_path="db",
        )

        payload = render_factory_result(result)
        details = payload["details"]
        self.assertIsInstance(details, dict)
        details["x"] = "mutated"
        details["new"] = "value"

        self.assertEqual(result.details, {"x": "y"})

    def test_render_session_host_state_open_and_closed(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        result = self._build_host_result(db_path)
        host = self._require_host(result)
        try:
            self.assertEqual(render_session_host_state(host), {"closed": False})
            host.close()
            self.assertEqual(render_session_host_state(host), {"closed": True})
        finally:
            if not host.closed:
                host.close()

    def test_render_recovery_gate_result_unknown_task(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        result = self._build_host_result(db_path)
        host = self._require_host(result)
        try:
            payload = render_recovery_gate_result(
                host.evaluate_task("task-never-existed")
            )

            self.assertEqual(payload["recovery_class"], "unrecoverable")
            self.assertIs(payload["restored"], False)
            self.assertIs(payload["snapshot_present"], False)
            self.assertEqual(payload["artifact_count"], 0)
            self.assertIsNone(payload["current_stage"])
            self.assertIsNone(payload["terminal_state"])
        finally:
            host.close()

    def test_render_recovery_gate_result_safe_to_resume_snapshot(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        result = self._build_host_result(db_path)
        host = self._require_host(result)
        try:
            payload = render_recovery_gate_result(host.evaluate_task(task_id))

            self.assertEqual(payload["recovery_class"], "safe_to_resume")
            self.assertIs(payload["restored"], False)
            self.assertIs(payload["snapshot_present"], True)
            self.assertEqual(payload["current_stage"], "inference")
            self.assertIsNone(payload["terminal_state"])
            self.assertGreaterEqual(payload["artifact_count"], 2)
            self.assertEqual(payload["intent_anchor_count"], 1)
            self.assertEqual(payload["malformed_event_count"], 0)
        finally:
            host.close()

    def test_render_recovery_gate_result_after_restore_marks_restored(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        result = self._build_host_result(db_path)
        host = self._require_host(result)
        try:
            payload = render_recovery_gate_result(host.restore_task(task_id))

            self.assertEqual(payload["recovery_class"], "safe_to_resume")
            self.assertIs(payload["restored"], True)
            self.assertEqual(payload["current_stage"], "inference")
        finally:
            host.close()

    def test_render_helpers_do_not_write_durable_rows(self) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        before_audit = _audit_count(db_path)
        before_intent = _intent_anchor_count(db_path)

        result = self._build_host_result(db_path)
        host = self._require_host(result)
        try:
            render_factory_result(result)
            render_session_host_state(host)
            recovery_result = host.evaluate_task(task_id)
            render_recovery_gate_result(recovery_result)

            after_audit = _audit_count(db_path)
            after_intent = _intent_anchor_count(db_path)
            self.assertEqual(after_audit, before_audit)
            self.assertEqual(after_intent, before_intent)
        finally:
            host.close()


if __name__ == "__main__":
    unittest.main()
