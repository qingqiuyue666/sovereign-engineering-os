"""
P0-17 phase 1 - RecoverySessionHost operator CLI surface.

These tests pin the separate session-host CLI module. The legacy
``recovery_cli.py`` surface remains unchanged and no restore command is
introduced here.
"""

from __future__ import annotations

import argparse
import importlib
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


FACTORY_KEYS = {
    "ok",
    "db_path",
    "reason_code",
    "message",
    "details",
    "host_present",
    "host_closed",
}

RECOVERY_KEYS = {
    "task_id",
    "recovery_class",
    "reason",
    "restored",
    "snapshot_present",
    "current_stage",
    "terminal_state",
    "artifact_count",
    "intent_anchor_count",
    "malformed_event_count",
    "last_event_sequence",
}


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


class _EvaluateCloseFailingHost:
    @property
    def closed(self) -> bool:
        return False

    def evaluate_task(self, task_id: str) -> object:
        return object()

    def close(self) -> None:
        raise RuntimeError("close failed")


class _EvaluateFailingHost:
    def __init__(self) -> None:
        self._closed = False
        self.close_count = 0

    @property
    def closed(self) -> bool:
        return self._closed

    def evaluate_task(self, task_id: str) -> object:
        raise RuntimeError("evaluate failed")

    def close(self) -> None:
        self.close_count += 1
        self._closed = True


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

    def _assert_factory_keys_exact(self, factory: object) -> dict[str, object]:
        self.assertIsInstance(factory, dict)
        rendered = factory
        self.assertEqual(set(rendered), FACTORY_KEYS)
        return rendered

    def test_session_host_cli_parser_has_only_factory_check_and_evaluate(
        self,
    ) -> None:
        choices = _subparser_choices(build_parser())

        self.assertEqual(choices, {"factory-check", "evaluate"})
        self.assertNotIn("restore", choices)
        self.assertNotIn("restore-dry-run", choices)

    def test_factory_check_success_json_shape_is_exact(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        code, stdout, stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        payload = self._json_from_stdout(stdout)

        self.assertEqual(code, 0)
        self.assertEqual(set(payload), {"command", "factory"})
        self.assertEqual(payload["command"], "factory-check")
        self._assert_factory_keys_exact(payload["factory"])
        self.assertNotIn("recovery", payload)
        self.assertNotIn("host_state", payload)
        self.assertNotIn("host", payload)
        self.assertEqual(stderr, "")

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

    def test_factory_failure_json_shape_is_exact(self) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        code, stdout, _stderr = _invoke(
            ["factory-check", "--db", str(missing_path)]
        )
        payload = self._json_from_stdout(stdout)

        self.assertEqual(code, 3)
        self.assertEqual(set(payload), {"command", "factory"})
        self.assertEqual(payload["command"], "factory-check")
        factory = self._assert_factory_keys_exact(payload["factory"])
        self.assertIs(factory["ok"], False)
        self.assertEqual(factory["reason_code"], "missing_db_file")
        self.assertIs(factory["host_present"], False)
        self.assertIsNone(factory["host_closed"])
        self.assertFalse(missing_path.exists())

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

    def test_evaluate_success_json_shape_is_exact(self) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        code, stdout, stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        payload = self._json_from_stdout(stdout)

        self.assertEqual(code, 0)
        self.assertEqual(
            set(payload), {"command", "factory", "host_state", "recovery"}
        )
        self.assertEqual(payload["command"], "evaluate")
        self._assert_factory_keys_exact(payload["factory"])
        self.assertEqual(set(payload["host_state"]), {"closed"})
        recovery = payload["recovery"]
        self.assertIsInstance(recovery, dict)
        self.assertEqual(set(recovery), RECOVERY_KEYS)
        self.assertNotIn("host", payload)
        self.assertNotIn("host", payload["factory"])
        self.assertNotIn("host", payload["host_state"])
        self.assertNotIn("host", recovery)
        self.assertEqual(stderr, "")

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

    def test_evaluate_factory_failure_json_shape_is_exact(self) -> None:
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
        self.assertEqual(
            set(payload), {"command", "factory", "host_state", "recovery"}
        )
        self.assertEqual(payload["command"], "evaluate")
        factory = self._assert_factory_keys_exact(payload["factory"])
        self.assertIs(factory["ok"], False)
        self.assertEqual(factory["reason_code"], "missing_db_file")
        self.assertIsNone(payload["host_state"])
        self.assertIsNone(payload["recovery"])
        self.assertFalse(missing_path.exists())

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

    def test_invalid_args_emit_no_json_and_return_2(self) -> None:
        cases = [
            [],
            ["factory-check"],
            ["evaluate", "--db", str(self.tmpdir / "x.db")],
        ]

        for argv in cases:
            with self.subTest(argv=argv):
                code, stdout, _stderr = _invoke(argv)

                self.assertEqual(code, 2)
                self.assertEqual(stdout, "")

    def test_invalid_args_return_2(self) -> None:
        code, _stdout, _stderr = _invoke([])
        self.assertEqual(code, 2)

        code, _stdout, _stderr = _invoke(["factory-check"])
        self.assertEqual(code, 2)

        code, _stdout, _stderr = _invoke(
            ["evaluate", "--db", str(self.tmpdir / "x.db")]
        )
        self.assertEqual(code, 2)

    def test_unknown_subcommand_returns_2_and_no_json(self) -> None:
        missing_path = self.tmpdir / "x.db"

        code, stdout, stderr = _invoke(
            ["restore", "--db", str(missing_path)]
        )

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr)
        self.assertTrue(
            "invalid choice" in stderr or stderr.strip(),
            msg=stderr,
        )
        self.assertFalse(missing_path.exists())

    def test_evaluate_close_failure_returns_4_and_no_success_json(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        result = RecoverySessionHostFactoryResult(
            ok=True,
            host=_EvaluateCloseFailingHost(),
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
                ["evaluate", "--db", str(db_path), "--task-id", "task-1"]
            )

        self.assertEqual(code, 4)
        self.assertEqual(stdout, "")
        self.assertIn("close failed", stderr)

    def test_evaluate_task_failure_closes_host_and_returns_4(self) -> None:
        db_path = self.tmpdir / "factory.db"
        host = _EvaluateFailingHost()
        result = RecoverySessionHostFactoryResult(
            ok=True,
            host=host,
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
                ["evaluate", "--db", str(db_path), "--task-id", "task-1"]
            )

        self.assertEqual(code, 4)
        self.assertEqual(stdout, "")
        self.assertIn("evaluate failed", stderr)
        self.assertEqual(host.close_count, 1)
        self.assertTrue(host.closed)

    def test_factory_check_failure_does_not_attempt_host_close(self) -> None:
        db_path = self.tmpdir / "missing.db"
        result = RecoverySessionHostFactoryResult(
            ok=False,
            host=None,
            reason_code="missing_db_file",
            message="missing",
            details={"db_path": str(db_path)},
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
        payload = self._json_from_stdout(stdout)

        self.assertEqual(code, 3)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["command"], "factory-check")
        factory = self._assert_factory_keys_exact(payload["factory"])
        self.assertIs(factory["ok"], False)
        self.assertIs(factory["host_present"], False)
        self.assertIsNone(factory["host_closed"])

    def test_evaluate_factory_failure_does_not_attempt_evaluate_or_close(
        self,
    ) -> None:
        db_path = self.tmpdir / "missing.db"
        result = RecoverySessionHostFactoryResult(
            ok=False,
            host=None,
            reason_code="missing_db_file",
            message="missing",
            details={"db_path": str(db_path)},
            db_path=str(db_path),
        )

        with mock.patch(
            "kernel.lifecycle.recovery_session_host_cli."
            "try_build_recovery_session_host_from_sqlite",
            return_value=result,
        ):
            code, stdout, stderr = _invoke(
                ["evaluate", "--db", str(db_path), "--task-id", "task-1"]
            )
        payload = self._json_from_stdout(stdout)

        self.assertEqual(code, 3)
        self.assertEqual(stderr, "")
        self.assertIsNone(payload["recovery"])
        self.assertIsNone(payload["host_state"])

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

    def test_session_host_cli_module_import_has_no_side_effects(self) -> None:
        import kernel.lifecycle.recovery_session_host_cli as module

        reloaded = importlib.reload(module)

        self.assertIs(reloaded.build_parser, module.build_parser)
        self.assertIs(reloaded.main, module.main)

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
