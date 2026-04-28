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
import sqlite3
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

from kernel.lifecycle.recovery_session_host_cli import (
    EXIT_FACTORY_ERROR,
    EXIT_INVALID_ARGS,
    EXIT_OK,
    EXIT_UNEXPECTED,
    SESSION_HOST_CLI_COMMANDS,
    SESSION_HOST_CLI_EXIT_CODES,
    SESSION_HOST_CLI_FACTORY_KEYS,
    SESSION_HOST_CLI_HOST_STATE_KEYS,
    SESSION_HOST_CLI_RECOVERY_KEYS,
    SESSION_HOST_CLI_STDIO_CONTRACT,
    SESSION_HOST_CLI_TOP_LEVEL_KEYS,
    build_parser,
    main,
    session_host_cli_contract_manifest,
)
from kernel.lifecycle.recovery_session_host import (
    RecoverySessionHostFactoryResult,
)
from kernel.stores.sqlite.repositories import IntentAnchorRepository
from kernel.stores.sqlite.wal_recovery import open_connection
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

RAW_REPR_MARKERS = (
    "<",
    "object at",
    "RecoverySessionHost",
    "sqlite3.Connection",
)

RECURSIVE_REPR_MARKERS = (
    "RecoverySessionHost",
    "sqlite3.Connection",
    "object at 0x",
    "<kernel.",
    "<sqlite3.",
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


def _assert_single_json_line(stdout: str) -> dict[str, object]:
    if not stdout.endswith("\n"):
        raise AssertionError("stdout must end with exactly one newline")
    if stdout.count("\n") != 1:
        raise AssertionError(f"stdout must contain one JSON line: {stdout!r}")

    raw = stdout[:-1]
    if not raw:
        raise AssertionError("stdout JSON line must be non-empty")

    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise AssertionError(f"stdout JSON must be an object: {payload!r}")
    return payload


def _assert_code_json_stderr(
    code: int,
    stdout: str,
    stderr: str,
    *,
    expected_code: int,
    expect_json: bool,
) -> dict[str, object] | None:
    if code != expected_code:
        raise AssertionError(
            f"expected exit code {expected_code}, got {code}"
        )

    if expect_json:
        if stderr != "":
            raise AssertionError(f"stderr must be empty: {stderr!r}")
        return _assert_single_json_line(stdout)

    if stdout != "":
        raise AssertionError(f"stdout must be empty: {stdout!r}")
    return None


def _assert_no_forbidden_strings(raw: str) -> None:
    for marker in RAW_REPR_MARKERS:
        if marker in raw:
            raise AssertionError(
                f"raw JSON leaked forbidden marker {marker!r}: {raw!r}"
            )


def _assert_no_repr_leak(payload: object) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "host":
                raise AssertionError("payload must not expose a host key")
            _assert_no_repr_leak(key)
            _assert_no_repr_leak(value)
        return

    if isinstance(payload, list):
        for value in payload:
            _assert_no_repr_leak(value)
        return

    if isinstance(payload, str):
        for marker in RECURSIVE_REPR_MARKERS:
            if marker in payload:
                raise AssertionError(
                    f"payload leaked forbidden marker {marker!r}: "
                    f"{payload!r}"
                )


def _assert_no_set_values(value: object) -> None:
    if isinstance(value, (set, frozenset)):
        raise AssertionError(f"manifest exposed a set value: {value!r}")

    if isinstance(value, dict):
        for key, nested in value.items():
            _assert_no_set_values(key)
            _assert_no_set_values(nested)
        return

    if isinstance(value, list):
        for nested in value:
            _assert_no_set_values(nested)


def _stdio_contract_observation(
    stdout: str, stderr: str
) -> dict[str, bool]:
    try:
        _assert_single_json_line(stdout)
        stdout_json = True
    except (AssertionError, json.JSONDecodeError):
        stdout_json = False

    return {
        "stdout_json": stdout_json,
        "stderr_empty": stderr == "",
    }


def _quote_sql_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_row_counts(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        table_names = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name;"
            )
        ]
        return {
            table_name: conn.execute(
                f"SELECT COUNT(*) FROM {_quote_sql_identifier(table_name)};"
            ).fetchone()[0]
            for table_name in table_names
        }
    finally:
        conn.close()


def _insert_duplicate_intent_anchor(db_path: Path, task_id: str) -> None:
    conn = open_connection(db_path)
    try:
        IntentAnchorRepository(conn).insert(
            intent_id=f"intent-dup-{uuid4().hex[:8]}",
            task_id=task_id,
            state="admitted",
        )
    finally:
        conn.close()


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


class _ExitContractEvaluateFailingHost:
    def __init__(self) -> None:
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def evaluate_task(self, task_id: str) -> object:
        raise RuntimeError("unexpected evaluate defect")

    def close(self) -> None:
        self._closed = True


class _ExitContractCloseFailingHost:
    @property
    def closed(self) -> bool:
        return False

    def evaluate_task(self, task_id: str) -> object:
        return object()

    def close(self) -> None:
        raise RuntimeError("unexpected close defect")


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

    def test_exit_code_factory_check_success_is_0_and_emits_json(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        code, stdout, stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        payload = _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=0,
            expect_json=True,
        )

        self.assertIsNotNone(payload)
        self.assertEqual(payload["command"], "factory-check")
        factory = payload["factory"]
        self.assertIsInstance(factory, dict)
        self.assertIs(factory["ok"], True)

    def test_exit_code_factory_check_expected_factory_error_is_3_and_emits_json(
        self,
    ) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        code, stdout, stderr = _invoke(
            ["factory-check", "--db", str(missing_path)]
        )
        payload = _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=3,
            expect_json=True,
        )

        self.assertIsNotNone(payload)
        factory = payload["factory"]
        self.assertIsInstance(factory, dict)
        self.assertIs(factory["ok"], False)
        self.assertEqual(factory["reason_code"], "missing_db_file")
        self.assertFalse(missing_path.exists())

    def test_exit_code_evaluate_unknown_task_is_0_and_emits_json(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        code, stdout, stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", "missing-task"]
        )
        payload = _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=0,
            expect_json=True,
        )

        self.assertIsNotNone(payload)
        recovery = payload["recovery"]
        self.assertIsInstance(recovery, dict)
        self.assertEqual(recovery["recovery_class"], "unrecoverable")
        self.assertIs(recovery["restored"], False)

    def test_exit_code_evaluate_safe_to_resume_is_0_and_emits_json(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        code, stdout, stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        payload = _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=0,
            expect_json=True,
        )

        self.assertIsNotNone(payload)
        recovery = payload["recovery"]
        self.assertIsInstance(recovery, dict)
        self.assertEqual(recovery["recovery_class"], "safe_to_resume")
        self.assertEqual(recovery["current_stage"], "inference")

    def test_exit_code_evaluate_needs_manual_review_is_0_and_emits_json(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)
        _insert_duplicate_intent_anchor(db_path, task_id)

        code, stdout, stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        payload = _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=0,
            expect_json=True,
        )

        self.assertIsNotNone(payload)
        recovery = payload["recovery"]
        self.assertIsInstance(recovery, dict)
        self.assertEqual(recovery["recovery_class"], "needs_manual_review")

    def test_exit_code_evaluate_factory_error_is_3_and_emits_json(
        self,
    ) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        code, stdout, stderr = _invoke(
            [
                "evaluate",
                "--db",
                str(missing_path),
                "--task-id",
                "missing-task",
            ]
        )
        payload = _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=3,
            expect_json=True,
        )

        self.assertIsNotNone(payload)
        factory = payload["factory"]
        self.assertIsInstance(factory, dict)
        self.assertIs(factory["ok"], False)
        self.assertEqual(factory["reason_code"], "missing_db_file")
        self.assertIsNone(payload["recovery"])
        self.assertIsNone(payload["host_state"])
        self.assertFalse(missing_path.exists())

    def test_exit_code_invalid_args_is_2_and_emits_no_json(self) -> None:
        restore_path = self.tmpdir / "x.db"
        cases = [
            [],
            ["factory-check"],
            ["evaluate", "--db", str(self.tmpdir / "x.db")],
            ["restore", "--db", str(restore_path)],
        ]

        for argv in cases:
            with self.subTest(argv=argv):
                code, stdout, stderr = _invoke(argv)

                _assert_code_json_stderr(
                    code,
                    stdout,
                    stderr,
                    expected_code=2,
                    expect_json=False,
                )
                self.assertTrue(stderr)

        self.assertFalse(restore_path.exists())

    def test_exit_code_unexpected_factory_check_error_is_4_and_emits_no_json(
        self,
    ) -> None:
        with mock.patch(
            "kernel.lifecycle.recovery_session_host_cli."
            "try_build_recovery_session_host_from_sqlite",
            side_effect=RuntimeError("unexpected factory-check defect"),
        ):
            code, stdout, stderr = _invoke(
                ["factory-check", "--db", str(self.tmpdir / "factory.db")]
            )

        _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=4,
            expect_json=False,
        )
        self.assertIn("Traceback", stderr)
        self.assertIn("unexpected factory-check defect", stderr)

    def test_exit_code_unexpected_evaluate_error_is_4_and_emits_no_json(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        host = _ExitContractEvaluateFailingHost()
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

        _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=4,
            expect_json=False,
        )
        self.assertIn("Traceback", stderr)
        self.assertIn("unexpected evaluate defect", stderr)
        self.assertTrue(host.closed)

    def test_exit_code_evaluate_close_failure_is_4_and_emits_no_json(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        result = RecoverySessionHostFactoryResult(
            ok=True,
            host=_ExitContractCloseFailingHost(),
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

        _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=4,
            expect_json=False,
        )
        self.assertIn("Traceback", stderr)
        self.assertIn("unexpected close defect", stderr)

    def test_exit_code_contract_summary_table(self) -> None:
        expected_contract = {
            "factory_check_success": 0,
            "factory_check_expected_failure": 3,
            "evaluate_unknown": 0,
            "evaluate_safe_to_resume": 0,
            "evaluate_needs_manual_review": 0,
            "evaluate_factory_failure": 3,
            "invalid_args": 2,
            "unexpected": 4,
        }

        valid_db_path = self.tmpdir / "valid.db"
        _initialize_empty_db(valid_db_path)

        safe_db_path = self.tmpdir / "safe.db"
        safe_task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(safe_db_path)
        _seed_inference_stage(safe_db_path, safe_task_id)

        manual_db_path = self.tmpdir / "manual.db"
        manual_task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(manual_db_path)
        _seed_inference_stage(manual_db_path, manual_task_id)
        _insert_duplicate_intent_anchor(manual_db_path, manual_task_id)

        factory_success, _stdout, _stderr = _invoke(
            ["factory-check", "--db", str(valid_db_path)]
        )
        factory_failure, _stdout, _stderr = _invoke(
            ["factory-check", "--db", str(self.tmpdir / "missing.db")]
        )
        evaluate_unknown, _stdout, _stderr = _invoke(
            ["evaluate", "--db", str(valid_db_path), "--task-id", "missing"]
        )
        evaluate_safe, _stdout, _stderr = _invoke(
            ["evaluate", "--db", str(safe_db_path), "--task-id", safe_task_id]
        )
        evaluate_manual, _stdout, _stderr = _invoke(
            [
                "evaluate",
                "--db",
                str(manual_db_path),
                "--task-id",
                manual_task_id,
            ]
        )
        evaluate_factory_failure, _stdout, _stderr = _invoke(
            [
                "evaluate",
                "--db",
                str(self.tmpdir / "missing-evaluate.db"),
                "--task-id",
                "missing",
            ]
        )
        invalid_args, _stdout, _stderr = _invoke([])
        with mock.patch(
            "kernel.lifecycle.recovery_session_host_cli."
            "try_build_recovery_session_host_from_sqlite",
            side_effect=RuntimeError("unexpected defect"),
        ):
            unexpected, _stdout, _stderr = _invoke(
                ["factory-check", "--db", str(self.tmpdir / "factory.db")]
            )

        actual_contract = {
            "factory_check_success": factory_success,
            "factory_check_expected_failure": factory_failure,
            "evaluate_unknown": evaluate_unknown,
            "evaluate_safe_to_resume": evaluate_safe,
            "evaluate_needs_manual_review": evaluate_manual,
            "evaluate_factory_failure": evaluate_factory_failure,
            "invalid_args": invalid_args,
            "unexpected": unexpected,
        }
        self.assertEqual(actual_contract, expected_contract)

    def test_exit_code_contract_does_not_add_restore_command(self) -> None:
        from kernel.lifecycle.recovery_cli import (
            build_parser as build_legacy_parser,
        )

        self.assertEqual(
            _subparser_choices(build_parser()),
            {"factory-check", "evaluate"},
        )
        self.assertEqual(
            _subparser_choices(build_legacy_parser()),
            {"evaluate", "restore-dry-run"},
        )

    def test_factory_check_success_stdout_is_single_sorted_json_line(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        code, stdout, stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        _assert_single_json_line(stdout)
        raw = stdout[:-1]

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(raw.startswith('{"command":'), msg=raw)
        _assert_no_forbidden_strings(raw)

    def test_evaluate_success_stdout_is_single_sorted_json_line(self) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        code, stdout, stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        _assert_single_json_line(stdout)
        raw = stdout[:-1]

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(raw.startswith('{"command":'), msg=raw)
        _assert_no_forbidden_strings(raw)

    def test_factory_failure_stdout_is_single_sorted_json_line_and_stderr_empty(
        self,
    ) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        code, stdout, stderr = _invoke(
            ["factory-check", "--db", str(missing_path)]
        )
        _assert_single_json_line(stdout)
        raw = stdout[:-1]

        self.assertEqual(code, 3)
        self.assertEqual(stderr, "")
        self.assertTrue(raw.startswith('{"command":'), msg=raw)
        self.assertFalse(missing_path.exists())

    def test_evaluate_factory_failure_stdout_is_single_sorted_json_line_and_stderr_empty(
        self,
    ) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        code, stdout, stderr = _invoke(
            [
                "evaluate",
                "--db",
                str(missing_path),
                "--task-id",
                "missing-task",
            ]
        )
        _assert_single_json_line(stdout)
        raw = stdout[:-1]

        self.assertEqual(code, 3)
        self.assertEqual(stderr, "")
        self.assertTrue(raw.startswith('{"command":'), msg=raw)
        self.assertFalse(missing_path.exists())

    def test_repeated_factory_check_output_shape_is_stable(self) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)

        before_counts = _table_row_counts(db_path)
        first_code, first_stdout, first_stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        after_first_counts = _table_row_counts(db_path)
        second_code, second_stdout, second_stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        after_second_counts = _table_row_counts(db_path)

        first = _assert_single_json_line(first_stdout)
        second = _assert_single_json_line(second_stdout)

        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 0)
        self.assertEqual(first_stderr, "")
        self.assertEqual(second_stderr, "")
        self.assertEqual(set(first), set(second))
        self.assertEqual(set(first["factory"]), set(second["factory"]))
        self.assertEqual(first["command"], "factory-check")
        self.assertEqual(second["command"], "factory-check")
        self.assertEqual(after_first_counts, before_counts)
        self.assertEqual(after_second_counts, before_counts)

    def test_repeated_evaluate_output_shape_is_stable(self) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        before_counts = _table_row_counts(db_path)
        first_code, first_stdout, first_stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        after_first_counts = _table_row_counts(db_path)
        second_code, second_stdout, second_stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        after_second_counts = _table_row_counts(db_path)

        first = _assert_single_json_line(first_stdout)
        second = _assert_single_json_line(second_stdout)
        first_recovery = first["recovery"]
        second_recovery = second["recovery"]

        self.assertIsInstance(first_recovery, dict)
        self.assertIsInstance(second_recovery, dict)
        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 0)
        self.assertEqual(first_stderr, "")
        self.assertEqual(second_stderr, "")
        self.assertEqual(set(first), set(second))
        self.assertEqual(set(first["factory"]), set(second["factory"]))
        self.assertEqual(set(first["host_state"]), set(second["host_state"]))
        self.assertEqual(set(first_recovery), set(second_recovery))
        self.assertEqual(first_recovery["current_stage"], "inference")
        self.assertEqual(second_recovery["current_stage"], "inference")
        self.assertEqual(after_first_counts, before_counts)
        self.assertEqual(after_second_counts, before_counts)

    def test_success_payloads_do_not_expose_host_or_connection_strings_recursively(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        factory_code, factory_stdout, factory_stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        evaluate_code, evaluate_stdout, evaluate_stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        factory_payload = _assert_single_json_line(factory_stdout)
        evaluate_payload = _assert_single_json_line(evaluate_stdout)

        self.assertEqual(factory_code, 0)
        self.assertEqual(evaluate_code, 0)
        self.assertEqual(factory_stderr, "")
        self.assertEqual(evaluate_stderr, "")
        _assert_no_repr_leak(factory_payload)
        _assert_no_repr_leak(evaluate_payload)

    def test_failure_payloads_do_not_expose_traceback_or_python_repr(
        self,
    ) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        invocations = [
            ["factory-check", "--db", str(missing_path)],
            [
                "evaluate",
                "--db",
                str(missing_path),
                "--task-id",
                "missing-task",
            ],
        ]
        forbidden = (
            "Traceback",
            "object at 0x",
            "<",
            "sqlite3.Connection",
            "RecoverySessionHost",
        )

        for argv in invocations:
            with self.subTest(argv=argv):
                code, stdout, stderr = _invoke(argv)
                _assert_single_json_line(stdout)
                raw = stdout[:-1]

                self.assertEqual(code, 3)
                self.assertEqual(stderr, "")
                for marker in forbidden:
                    self.assertNotIn(marker, raw)
                self.assertFalse(missing_path.exists())

    def test_unexpected_error_stdout_empty_and_stderr_traceback(self) -> None:
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
        self.assertIn("Traceback", stderr)
        self.assertIn("unexpected defect", stderr)

    def test_no_restore_command_remains_true_after_json_stability_hardening(
        self,
    ) -> None:
        from kernel.lifecycle.recovery_cli import (
            build_parser as build_legacy_parser,
        )

        self.assertEqual(
            _subparser_choices(build_parser()),
            {"factory-check", "evaluate"},
        )
        self.assertEqual(
            _subparser_choices(build_legacy_parser()),
            {"evaluate", "restore-dry-run"},
        )

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

    def test_session_host_cli_contract_manifest_is_json_safe_and_deterministic(
        self,
    ) -> None:
        manifest = session_host_cli_contract_manifest()
        manifest_again = session_host_cli_contract_manifest()

        self.assertEqual(manifest_again, manifest)
        json.dumps(manifest, sort_keys=True)
        _assert_no_set_values(manifest)

        commands = manifest["commands"]
        self.assertIsInstance(commands, list)
        self.assertEqual(commands, sorted(commands))

        top_level_keys = manifest["top_level_keys"]
        self.assertIsInstance(top_level_keys, dict)
        for command, keys in top_level_keys.items():
            with self.subTest(command=command):
                self.assertIsInstance(keys, list)
                self.assertEqual(keys, sorted(keys))

        for key_list_name in (
            "factory_keys",
            "host_state_keys",
            "recovery_keys",
        ):
            with self.subTest(key_list_name=key_list_name):
                key_list = manifest[key_list_name]
                self.assertIsInstance(key_list, list)
                self.assertEqual(key_list, sorted(key_list))

    def test_session_host_cli_contract_manifest_commands_match_parser(
        self,
    ) -> None:
        manifest = session_host_cli_contract_manifest()
        parser_choices = _subparser_choices(build_parser())

        self.assertEqual(set(manifest["commands"]), parser_choices)
        self.assertEqual(parser_choices, {"factory-check", "evaluate"})
        self.assertNotIn("restore", manifest["commands"])

    def test_session_host_cli_contract_manifest_exit_codes_match_module_constants(
        self,
    ) -> None:
        expected = {
            "ok": 0,
            "invalid_args": 2,
            "factory_error": 3,
            "unexpected": 4,
        }
        manifest = session_host_cli_contract_manifest()

        self.assertEqual(manifest["exit_codes"], expected)
        self.assertEqual(expected["ok"], EXIT_OK)
        self.assertEqual(expected["invalid_args"], EXIT_INVALID_ARGS)
        self.assertEqual(expected["factory_error"], EXIT_FACTORY_ERROR)
        self.assertEqual(expected["unexpected"], EXIT_UNEXPECTED)

    def test_session_host_cli_contract_manifest_keys_match_actual_factory_check_success_payload(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)
        manifest = session_host_cli_contract_manifest()

        code, stdout, stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        payload = _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=EXIT_OK,
            expect_json=True,
        )

        self.assertIsNotNone(payload)
        self.assertEqual(
            set(payload), set(manifest["top_level_keys"]["factory-check"])
        )
        factory = payload["factory"]
        self.assertIsInstance(factory, dict)
        self.assertEqual(set(factory), set(manifest["factory_keys"]))

    def test_session_host_cli_contract_manifest_keys_match_actual_evaluate_success_payload(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)
        manifest = session_host_cli_contract_manifest()

        code, stdout, stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        payload = _assert_code_json_stderr(
            code,
            stdout,
            stderr,
            expected_code=EXIT_OK,
            expect_json=True,
        )

        self.assertIsNotNone(payload)
        self.assertEqual(
            set(payload), set(manifest["top_level_keys"]["evaluate"])
        )
        factory = payload["factory"]
        host_state = payload["host_state"]
        recovery = payload["recovery"]
        self.assertIsInstance(factory, dict)
        self.assertIsInstance(host_state, dict)
        self.assertIsInstance(recovery, dict)
        self.assertEqual(set(factory), set(manifest["factory_keys"]))
        self.assertEqual(set(host_state), set(manifest["host_state_keys"]))
        self.assertEqual(set(recovery), set(manifest["recovery_keys"]))

    def test_session_host_cli_contract_manifest_stdio_contract_matches_runtime(
        self,
    ) -> None:
        valid_db_path = self.tmpdir / "valid.db"
        _initialize_empty_db(valid_db_path)
        missing_path = self.tmpdir / "missing.db"
        manifest = session_host_cli_contract_manifest()

        cases: list[tuple[str, int, str, str]] = []
        code, stdout, stderr = _invoke(
            ["factory-check", "--db", str(valid_db_path)]
        )
        cases.append(("factory-check success", code, stdout, stderr))

        code, stdout, stderr = _invoke(
            ["factory-check", "--db", str(missing_path)]
        )
        cases.append(("factory-check missing DB", code, stdout, stderr))

        code, stdout, stderr = _invoke([])
        cases.append(("invalid args", code, stdout, stderr))

        with mock.patch(
            "kernel.lifecycle.recovery_session_host_cli."
            "try_build_recovery_session_host_from_sqlite",
            side_effect=RuntimeError("unexpected manifest defect"),
        ):
            code, stdout, stderr = _invoke(
                ["factory-check", "--db", str(self.tmpdir / "factory.db")]
            )
        cases.append(("unexpected error", code, stdout, stderr))

        for label, code, stdout, stderr in cases:
            with self.subTest(label=label):
                self.assertEqual(
                    _stdio_contract_observation(stdout, stderr),
                    manifest["stdio_contract"][str(code)],
                )

    def test_session_host_cli_contract_manifest_does_not_add_restore_or_durable_write(
        self,
    ) -> None:
        manifest = session_host_cli_contract_manifest()
        self.assertIs(manifest["restore_supported"], False)
        self.assertIs(manifest["durable_writes"], False)
        self.assertNotIn("restore", manifest["commands"])

        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)
        before_counts = _table_row_counts(db_path)

        code, _stdout, _stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        self.assertEqual(code, EXIT_OK)
        code, _stdout, _stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        self.assertEqual(code, EXIT_OK)

        self.assertEqual(_table_row_counts(db_path), before_counts)
        self.assertEqual(session_host_cli_contract_manifest(), manifest)

    def test_session_host_cli_contract_manifest_returns_defensive_copies(
        self,
    ) -> None:
        manifest = session_host_cli_contract_manifest()
        manifest["commands"].append("restore")
        manifest["factory_keys"].append("host")
        manifest["exit_codes"]["ok"] = 99

        fresh_manifest = session_host_cli_contract_manifest()
        self.assertEqual(
            fresh_manifest["commands"], ["evaluate", "factory-check"]
        )
        self.assertNotIn("host", fresh_manifest["factory_keys"])
        self.assertEqual(fresh_manifest["exit_codes"]["ok"], EXIT_OK)

    def test_contract_manifest_does_not_call_parser_factory_or_serializers(
        self,
    ) -> None:
        with mock.patch(
            "kernel.lifecycle.recovery_session_host_cli.build_parser",
            side_effect=RuntimeError("parser should not be called"),
        ), mock.patch(
            "kernel.lifecycle.recovery_session_host_cli."
            "try_build_recovery_session_host_from_sqlite",
            side_effect=RuntimeError("factory should not be called"),
        ), mock.patch(
            "kernel.lifecycle.recovery_session_host_cli."
            "render_factory_result",
            side_effect=RuntimeError(
                "render_factory_result should not be called"
            ),
        ), mock.patch(
            "kernel.lifecycle.recovery_session_host_cli."
            "render_recovery_gate_result",
            side_effect=RuntimeError(
                "render_recovery_gate_result should not be called"
            ),
        ), mock.patch(
            "kernel.lifecycle.recovery_session_host_cli."
            "render_session_host_state",
            side_effect=RuntimeError(
                "render_session_host_state should not be called"
            ),
        ):
            manifest = session_host_cli_contract_manifest()

        self.assertEqual(
            manifest["commands"], ["evaluate", "factory-check"]
        )

    def test_contract_manifest_does_not_touch_stdout_or_stderr(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            session_host_cli_contract_manifest()

        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_contract_manifest_does_not_touch_filesystem_or_db(self) -> None:
        missing_path = self.tmpdir / "missing.db"

        before_entries = {path.name for path in self.tmpdir.iterdir()}
        for _ in range(3):
            session_host_cli_contract_manifest()

        self.assertEqual(
            {path.name for path in self.tmpdir.iterdir()}, before_entries
        )
        self.assertFalse(missing_path.exists())

        db_path = self.tmpdir / "factory.db"
        _initialize_empty_db(db_path)
        before_counts = _table_row_counts(db_path)

        for _ in range(5):
            session_host_cli_contract_manifest()

        self.assertEqual(_table_row_counts(db_path), before_counts)

    def test_contract_manifest_is_stable_before_and_after_cli_invocations(
        self,
    ) -> None:
        manifest_before = session_host_cli_contract_manifest()
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        code, _stdout, _stderr = _invoke(
            ["factory-check", "--db", str(db_path)]
        )
        self.assertEqual(code, EXIT_OK)
        code, _stdout, _stderr = _invoke(
            ["evaluate", "--db", str(db_path), "--task-id", task_id]
        )
        self.assertEqual(code, EXIT_OK)
        code, _stdout, _stderr = _invoke([])
        self.assertEqual(code, EXIT_INVALID_ARGS)
        code, _stdout, _stderr = _invoke(
            ["factory-check", "--db", str(self.tmpdir / "missing.db")]
        )
        self.assertEqual(code, EXIT_FACTORY_ERROR)

        manifest_after = session_host_cli_contract_manifest()
        self.assertEqual(manifest_after, manifest_before)

    def test_contract_manifest_defensive_copy_is_deep_enough_for_nested_stdio_contract(
        self,
    ) -> None:
        manifest1 = session_host_cli_contract_manifest()
        manifest1["stdio_contract"]["0"]["stdout_json"] = False
        manifest1["top_level_keys"]["evaluate"].append("host")

        manifest2 = session_host_cli_contract_manifest()

        self.assertIs(
            manifest2["stdio_contract"]["0"]["stdout_json"], True
        )
        self.assertNotIn("host", manifest2["top_level_keys"]["evaluate"])

    def test_contract_manifest_matches_current_module_constants_after_mutating_returned_manifest(
        self,
    ) -> None:
        manifest = session_host_cli_contract_manifest()
        manifest["commands"].append("restore")
        manifest["exit_codes"]["ok"] = 99
        manifest["top_level_keys"]["factory-check"].append("host")
        manifest["factory_keys"].append("host")
        manifest["host_state_keys"].append("anything")
        manifest["recovery_keys"].append("anything")
        manifest["stdio_contract"]["4"]["stderr_empty"] = True

        fresh = session_host_cli_contract_manifest()

        self.assertEqual(
            fresh["commands"], sorted(SESSION_HOST_CLI_COMMANDS)
        )
        self.assertEqual(fresh["exit_codes"], SESSION_HOST_CLI_EXIT_CODES)
        self.assertEqual(
            fresh["top_level_keys"],
            {
                command: sorted(keys)
                for command, keys in sorted(
                    SESSION_HOST_CLI_TOP_LEVEL_KEYS.items()
                )
            },
        )
        self.assertEqual(
            fresh["factory_keys"], sorted(SESSION_HOST_CLI_FACTORY_KEYS)
        )
        self.assertEqual(
            fresh["host_state_keys"],
            sorted(SESSION_HOST_CLI_HOST_STATE_KEYS),
        )
        self.assertEqual(
            fresh["recovery_keys"], sorted(SESSION_HOST_CLI_RECOVERY_KEYS)
        )
        self.assertEqual(
            fresh["stdio_contract"],
            {
                str(code): dict(contract)
                for code, contract in sorted(
                    SESSION_HOST_CLI_STDIO_CONTRACT.items()
                )
            },
        )

    def test_contract_manifest_has_no_restore_surface(self) -> None:
        from kernel.lifecycle.recovery_cli import (
            build_parser as build_legacy_parser,
        )

        manifest = session_host_cli_contract_manifest()

        self.assertIs(manifest["restore_supported"], False)
        self.assertNotIn("restore", manifest["commands"])
        self.assertNotIn("restore-dry-run", manifest["commands"])
        self.assertEqual(
            _subparser_choices(build_parser()), {"factory-check", "evaluate"}
        )
        self.assertEqual(
            _subparser_choices(build_legacy_parser()),
            {"evaluate", "restore-dry-run"},
        )

    def test_contract_manifest_output_can_be_round_tripped_through_json(
        self,
    ) -> None:
        manifest = session_host_cli_contract_manifest()
        encoded = json.dumps(manifest, sort_keys=True)
        decoded = json.loads(encoded)

        self.assertEqual(decoded, manifest)

    def test_contract_manifest_repeated_calls_allocate_independent_objects(
        self,
    ) -> None:
        manifest1 = session_host_cli_contract_manifest()
        manifest2 = session_host_cli_contract_manifest()

        self.assertEqual(manifest1, manifest2)
        self.assertIsNot(manifest1, manifest2)
        self.assertIsNot(manifest1["commands"], manifest2["commands"])
        self.assertIsNot(
            manifest1["top_level_keys"], manifest2["top_level_keys"]
        )
        self.assertIsNot(
            manifest1["top_level_keys"]["evaluate"],
            manifest2["top_level_keys"]["evaluate"],
        )
        self.assertIsNot(
            manifest1["stdio_contract"]["0"],
            manifest2["stdio_contract"]["0"],
        )

    def test_contract_manifest_does_not_depend_on_environment_variables(
        self,
    ) -> None:
        environment = {
            "RECOVERY_SESSION_HOST_CLI_RESTORE": "1",
            "SOVEREIGN_ENGINEERING_OS_ENABLE_RESTORE": "1",
            "PYTHONHASHSEED": "random",
        }

        with mock.patch.dict(os.environ, environment, clear=False):
            manifest = session_host_cli_contract_manifest()

        self.assertEqual(
            manifest["commands"], ["evaluate", "factory-check"]
        )
        self.assertIs(manifest["restore_supported"], False)
        self.assertIs(manifest["durable_writes"], False)

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
