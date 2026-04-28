"""
P0-17 phase 1 - RecoverySessionHost operator CLI surface.

These tests pin the separate session-host CLI module. The legacy
``recovery_cli.py`` surface remains unchanged and no restore command is
introduced here.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Sequence
from unittest import mock
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle.recovery_session_host_cli import build_parser, main
from kernel.lifecycle.recovery_session_host import (
    RecoverySessionHostFactoryResult,
)
from tests.tracer_bullet.test_recovery_session_host_factory import (
    _audit_count,
    _initialize_empty_db,
    _intent_anchor_count,
    _seed_inference_stage,
)


def _subparser_choices(parser: argparse.ArgumentParser) -> set[str]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("parser did not expose subparser choices")


def _invoke(argv: Sequence[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(list(argv))
    return code, stdout.getvalue(), stderr.getvalue()


class _CloseFailingHost:
    @property
    def closed(self) -> bool:
        return False

    def close(self) -> None:
        raise RuntimeError("close failed")


class TestRecoverySessionHostCli(unittest.TestCase):
    """P0-17 session-host operator CLI tests."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _json_from_stdout(self, stdout: str) -> dict[str, object]:
        self.assertTrue(stdout.strip())
        return json.loads(stdout)

    def test_session_host_cli_parser_has_only_factory_check_and_evaluate(
        self,
    ) -> None:
        choices = _subparser_choices(build_parser())

        self.assertEqual(choices, {"factory-check", "evaluate"})
        self.assertNotIn("restore", choices)
        self.assertNotIn("restore-dry-run", choices)

    def test_factory_check_success_outputs_closed_host_payload(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        code, stdout, stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        payload = self._json_from_stdout(stdout)

        self.assertEqual(code, 0)
        self.assertEqual(payload["command"], "factory-check")
        factory = payload["factory"]
        self.assertIsInstance(factory, dict)
        self.assertIs(factory["ok"], True)
        self.assertIs(factory["host_present"], True)
        self.assertIs(factory["host_closed"], True)
        self.assertNotIn("host", factory)
        self.assertEqual(stderr, "")

    def test_factory_check_close_failure_returns_4_and_no_success_json(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        result = RecoverySessionHostFactoryResult(
            ok=True,
            host=_CloseFailingHost(),
            reason_code=None,
            message=None,
            details={},
            db_path=str(db_path),
        )

        with mock.patch(
            "kernel.lifecycle.recovery_session_host_cli."
            "try_build_recovery_session_host_from_sqlite",
            return_value=result,
        ):
            code, stdout, stderr = _invoke(
                ["factory-check", "--db", str(db_path)]
            )

        self.assertEqual(code, 4)
        self.assertEqual(stdout, "")
        self.assertIn("close failed", stderr)

    def test_factory_check_missing_db_outputs_failure_json_and_does_not_create_file(
        self,
    ) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        code, stdout, _stderr = _invoke(
            ["factory-check", "--db", str(missing_path)]
        )
        payload = self._json_from_stdout(stdout)

        self.assertEqual(code, 3)
        self.assertEqual(payload["command"], "factory-check")
        factory = payload["factory"]
        self.assertIsInstance(factory, dict)
        self.assertIs(factory["ok"], False)
        self.assertEqual(factory["reason_code"], "missing_db_file")
        self.assertEqual(factory["db_path"], str(missing_path))
        self.assertIs(factory["host_present"], False)
        self.assertIsNone(factory["host_closed"])
        self.assertFalse(missing_path.exists())

    def test_evaluate_unknown_task_outputs_unrecoverable_json(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        code, stdout, stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", "missing-task"]
        )
        payload = self._json_from_stdout(stdout)

        self.assertEqual(code, 0)
        self.assertEqual(payload["command"], "evaluate")
        factory = payload["factory"]
        self.assertIsInstance(factory, dict)
        self.assertIs(factory["ok"], True)
        self.assertIs(factory["host_closed"], True)
        self.assertEqual(payload["host_state"], {"closed": True})
        recovery = payload["recovery"]
        self.assertIsInstance(recovery, dict)
        self.assertEqual(recovery["recovery_class"], "unrecoverable")
        self.assertIs(recovery["restored"], False)
        self.assertIs(recovery["snapshot_present"], False)
        self.assertEqual(recovery["artifact_count"], 0)
        self.assertEqual(stderr, "")

    def test_evaluate_safe_to_resume_outputs_snapshot_json(self) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        code, stdout, stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        payload = self._json_from_stdout(stdout)

        self.assertEqual(code, 0)
        recovery = payload["recovery"]
        self.assertIsInstance(recovery, dict)
        self.assertEqual(recovery["recovery_class"], "safe_to_resume")
        self.assertEqual(recovery["current_stage"], "inference")
        self.assertIs(recovery["snapshot_present"], True)
        self.assertIs(recovery["restored"], False)
        factory = payload["factory"]
        self.assertIsInstance(factory, dict)
        self.assertIs(factory["host_closed"], True)
        self.assertEqual(stderr, "")

    def test_evaluate_missing_db_outputs_factory_failure_json(self) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        code, stdout, _stderr = _invoke(
            [
                "evaluate",
                "--db",
                str(missing_path),
                "--task-id",
                "missing-task",
            ]
        )
        payload = self._json_from_stdout(stdout)

        self.assertEqual(code, 3)
        self.assertEqual(payload["command"], "evaluate")
        factory = payload["factory"]
        self.assertIsInstance(factory, dict)
        self.assertIs(factory["ok"], False)
        self.assertEqual(factory["reason_code"], "missing_db_file")
        self.assertIsNone(payload["recovery"])
        self.assertIsNone(payload["host_state"])
        self.assertFalse(missing_path.exists())

    def test_invalid_args_return_2(self) -> None:
        code, _stdout, _stderr = _invoke([])
        self.assertEqual(code, 2)

        code, _stdout, _stderr = _invoke(["factory-check"])
        self.assertEqual(code, 2)

        code, _stdout, _stderr = _invoke(
            ["evaluate", "--db", str(self.tmpdir / "x.db")]
        )
        self.assertEqual(code, 2)

    def test_session_host_cli_does_not_write_durable_rows(self) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        before_audit = _audit_count(db_path)
        before_intent = _intent_anchor_count(db_path)

        code, _stdout, _stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        self.assertEqual(code, 0)
        code, _stdout, _stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        self.assertEqual(code, 0)

        self.assertEqual(_audit_count(db_path), before_audit)
        self.assertEqual(_intent_anchor_count(db_path), before_intent)

    def test_session_host_cli_does_not_add_legacy_recovery_cli_restore(
        self,
    ) -> None:
        from kernel.lifecycle.recovery_cli import (
            build_parser as build_legacy_parser,
        )

        self.assertEqual(
            _subparser_choices(build_legacy_parser()),
            {"evaluate", "restore-dry-run"},
        )

    def test_session_host_cli_unexpected_exception_returns_4(self) -> None:
        with mock.patch(
            "kernel.lifecycle.recovery_session_host_cli."
            "try_build_recovery_session_host_from_sqlite",
            side_effect=RuntimeError("unexpected defect"),
        ):
            code, stdout, stderr = _invoke(
                ["factory-check", "--db", str(self.tmpdir / "factory.db")]
            )

        self.assertEqual(code, 4)
        self.assertEqual(stdout, "")
        self.assertIn("unexpected defect", stderr)


if __name__ == "__main__":
    unittest.main()
