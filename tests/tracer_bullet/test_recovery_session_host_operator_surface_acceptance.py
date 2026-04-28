"""
P0-30 phase 1 - RecoverySessionHost operator surface acceptance pack.

This file summarizes the P0-17 through P0-29 session-host operator
surface as a closed read-only phase. It intentionally adds no CLI
commands, no restore path, and no production helpers.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from uuid import uuid4

from kernel.lifecycle import recovery_session_host_cli
from kernel.lifecycle.recovery_cli import build_parser as build_legacy_parser
from kernel.lifecycle.recovery_session_host_cli import (
    EXIT_FACTORY_ERROR,
    EXIT_INVALID_ARGS,
    EXIT_OK,
    EXIT_UNEXPECTED,
    build_parser,
    current_recovery_session_host_cli_readiness_payload,
    current_recovery_session_host_cli_readiness_smoke,
    recovery_session_host_cli_readiness,
    render_recovery_session_host_cli_readiness,
    render_recovery_session_host_cli_readiness_smoke,
    session_host_cli_contract_manifest,
)
from tests.tracer_bullet.test_recovery_session_host_cli import (
    _assert_json_safe_no_runtime_types,
    _assert_no_runtime_repr_strings,
    _assert_single_json_line,
    _invoke,
    _subparser_choices,
    _table_row_counts,
)
from tests.tracer_bullet.test_recovery_session_host_factory import (
    _initialize_empty_db,
    _seed_inference_stage,
)


FORBIDDEN_OPERATOR_COMMANDS = {
    "restore",
    "restore-dry-run",
    "contract",
    "readiness",
    "smoke",
    "status",
    "apply",
    "repair",
}


class TestRecoverySessionHostOperatorSurfaceAcceptance(unittest.TestCase):
    """Acceptance coverage for the frozen read-only operator surface."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_acceptance_operator_surface_phase_is_read_only_ready(
        self,
    ) -> None:
        manifest = session_host_cli_contract_manifest()
        readiness = recovery_session_host_cli_readiness()
        readiness_payload = render_recovery_session_host_cli_readiness(
            readiness
        )
        current_payload = current_recovery_session_host_cli_readiness_payload()
        smoke = current_recovery_session_host_cli_readiness_smoke()
        smoke_payload = render_recovery_session_host_cli_readiness_smoke(
            smoke
        )

        self.assertEqual(manifest["commands"], ["evaluate", "factory-check"])
        self.assertIs(manifest["restore_supported"], False)
        self.assertIs(manifest["durable_writes"], False)
        self.assertIs(readiness.ready, True)
        self.assertEqual(readiness.reason_code, "ready")
        self.assertEqual(readiness.failures, ())
        self.assertEqual(readiness_payload, current_payload)
        self.assertIs(current_payload["ready"], True)
        self.assertIs(smoke.passed, True)
        self.assertEqual(smoke.reason_code, "passed")
        self.assertEqual(smoke.failures, ())
        self.assertEqual(smoke_payload["payload"], current_payload)

    def test_acceptance_operator_surface_cli_runtime_is_read_only(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)
        before_counts = _table_row_counts(db_path)

        invocations = [
            ["factory-check", "--db", str(db_path)],
            ["evaluate", "--db", str(db_path), "--task-id", task_id],
            [
                "evaluate",
                "--db",
                str(db_path),
                "--task-id",
                "unknown-task",
            ],
        ]

        for argv in invocations:
            with self.subTest(argv=argv):
                code, stdout, stderr = _invoke(argv)
                self.assertEqual(code, EXIT_OK)
                _assert_single_json_line(stdout)
                self.assertEqual(stderr, "")

        self.assertEqual(_table_row_counts(db_path), before_counts)

    def test_acceptance_operator_surface_expected_failures_are_safe(
        self,
    ) -> None:
        missing_path = self.tmpdir / "missing.db"
        self.assertFalse(missing_path.exists())

        missing_invocations = [
            ["factory-check", "--db", str(missing_path)],
            [
                "evaluate",
                "--db",
                str(missing_path),
                "--task-id",
                "missing-task",
            ],
        ]
        for argv in missing_invocations:
            with self.subTest(argv=argv):
                code, stdout, stderr = _invoke(argv)
                self.assertEqual(code, EXIT_FACTORY_ERROR)
                _assert_single_json_line(stdout)
                self.assertEqual(stderr, "")
                self.assertFalse(missing_path.exists())

        code, stdout, stderr = _invoke([])
        self.assertEqual(code, EXIT_INVALID_ARGS)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr)

    def test_acceptance_operator_surface_unexpected_failures_are_bounded(
        self,
    ) -> None:
        with mock.patch.object(
            recovery_session_host_cli,
            "try_build_recovery_session_host_from_sqlite",
            side_effect=RuntimeError("acceptance unexpected"),
        ):
            cases = [
                _invoke(["factory-check", "--db", str(self.tmpdir / "x.db")]),
                _invoke(
                    [
                        "evaluate",
                        "--db",
                        str(self.tmpdir / "x.db"),
                        "--task-id",
                        "task-1",
                    ]
                ),
            ]

        for code, stdout, stderr in cases:
            self.assertEqual(code, EXIT_UNEXPECTED)
            self.assertEqual(stdout, "")
            self.assertIn("Traceback", stderr)
            self.assertIn("acceptance unexpected", stderr)

    def test_acceptance_operator_surface_no_restore_or_command_creep(
        self,
    ) -> None:
        session_host_choices = _subparser_choices(build_parser())
        legacy_choices = _subparser_choices(build_legacy_parser())
        manifest = session_host_cli_contract_manifest()
        readiness = recovery_session_host_cli_readiness()
        readiness_payload = render_recovery_session_host_cli_readiness(
            readiness
        )
        current_payload = current_recovery_session_host_cli_readiness_payload()
        smoke = current_recovery_session_host_cli_readiness_smoke()
        smoke_payload = render_recovery_session_host_cli_readiness_smoke(
            smoke
        )

        self.assertEqual(session_host_choices, {"factory-check", "evaluate"})
        self.assertEqual(legacy_choices, {"evaluate", "restore-dry-run"})
        self.assertEqual(manifest["commands"], ["evaluate", "factory-check"])

        command_surfaces = [
            session_host_choices,
            manifest["commands"],
            readiness.manifest["commands"],
            readiness_payload["manifest"]["commands"],
            current_payload["manifest"]["commands"],
            smoke.payload["manifest"]["commands"],
            smoke_payload["payload"]["manifest"]["commands"],
        ]
        for commands in command_surfaces:
            with self.subTest(commands=commands):
                self.assertTrue(
                    FORBIDDEN_OPERATOR_COMMANDS.isdisjoint(set(commands))
                )

        manifests = [
            manifest,
            readiness.manifest,
            readiness_payload["manifest"],
            current_payload["manifest"],
            smoke.payload["manifest"],
            smoke_payload["payload"]["manifest"],
        ]
        for payload_manifest in manifests:
            with self.subTest(payload_manifest=payload_manifest):
                self.assertIs(payload_manifest["restore_supported"], False)

    def test_acceptance_operator_surface_public_payloads_are_json_safe(
        self,
    ) -> None:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        missing_path = self.tmpdir / "missing.db"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)

        readiness = recovery_session_host_cli_readiness()
        smoke = current_recovery_session_host_cli_readiness_smoke()
        factory_success_code, factory_success_stdout, factory_success_stderr = (
            _invoke(["factory-check", "--db", str(db_path)])
        )
        evaluate_success_code, evaluate_success_stdout, evaluate_success_stderr = (
            _invoke(["evaluate", "--db", str(db_path), "--task-id", task_id])
        )
        factory_missing_code, factory_missing_stdout, factory_missing_stderr = (
            _invoke(["factory-check", "--db", str(missing_path)])
        )
        evaluate_missing_code, evaluate_missing_stdout, evaluate_missing_stderr = (
            _invoke(
                [
                    "evaluate",
                    "--db",
                    str(missing_path),
                    "--task-id",
                    "missing-task",
                ]
            )
        )

        self.assertEqual(factory_success_code, EXIT_OK)
        self.assertEqual(evaluate_success_code, EXIT_OK)
        self.assertEqual(factory_missing_code, EXIT_FACTORY_ERROR)
        self.assertEqual(evaluate_missing_code, EXIT_FACTORY_ERROR)
        self.assertEqual(factory_success_stderr, "")
        self.assertEqual(evaluate_success_stderr, "")
        self.assertEqual(factory_missing_stderr, "")
        self.assertEqual(evaluate_missing_stderr, "")

        payloads = [
            session_host_cli_contract_manifest(),
            render_recovery_session_host_cli_readiness(readiness),
            current_recovery_session_host_cli_readiness_payload(),
            render_recovery_session_host_cli_readiness_smoke(smoke),
            _assert_single_json_line(factory_success_stdout),
            _assert_single_json_line(evaluate_success_stdout),
            _assert_single_json_line(factory_missing_stdout),
            _assert_single_json_line(evaluate_missing_stdout),
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                encoded = json.dumps(payload, sort_keys=True)
                self.assertEqual(json.loads(encoded), payload)
                _assert_json_safe_no_runtime_types(payload)
                _assert_no_runtime_repr_strings(payload)

        self.assertFalse(missing_path.exists())

    def test_acceptance_operator_surface_contract_summary(self) -> None:
        manifest = session_host_cli_contract_manifest()
        readiness = recovery_session_host_cli_readiness()
        smoke = current_recovery_session_host_cli_readiness_smoke()
        summary = {
            "phase": "recovery_session_host_operator_surface",
            "read_only": True,
            "restore_supported": False,
            "commands": manifest["commands"],
            "exit_codes": manifest["exit_codes"],
            "readiness_ready": readiness.ready,
            "smoke_passed": smoke.passed,
            "durable_writes": manifest["durable_writes"],
            "legacy_recovery_cli_modified": (
                manifest["legacy_recovery_cli_modified"]
            ),
        }

        self.assertEqual(
            summary["phase"], "recovery_session_host_operator_surface"
        )
        self.assertIs(summary["read_only"], True)
        self.assertIs(summary["restore_supported"], False)
        self.assertEqual(summary["commands"], ["evaluate", "factory-check"])
        self.assertEqual(
            summary["exit_codes"],
            {
                "ok": 0,
                "invalid_args": 2,
                "factory_error": 3,
                "unexpected": 4,
            },
        )
        self.assertIs(summary["readiness_ready"], True)
        self.assertIs(summary["smoke_passed"], True)
        self.assertIs(summary["durable_writes"], False)
        self.assertIs(summary["legacy_recovery_cli_modified"], False)
        encoded = json.dumps(summary, sort_keys=True)
        self.assertEqual(json.loads(encoded), summary)


if __name__ == "__main__":
    unittest.main()
