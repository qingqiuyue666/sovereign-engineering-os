"""
P0-33 phase 1 - RecoverySessionHost verdict aggregator acceptance pack.

These tests prove the read-only verdict aggregator consumes realistic
payloads emitted by the frozen RecoverySessionHost operator surface.
They intentionally add no CLI commands, no restore path, and no
production helpers.
"""

from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from uuid import uuid4

from kernel.lifecycle import recovery_session_host_cli
from kernel.lifecycle import recovery_session_host_verdict_aggregator as aggregator_module
from kernel.lifecycle.recovery_session_host_cli import (
    EXIT_FACTORY_ERROR,
    EXIT_OK,
    current_recovery_session_host_cli_readiness_payload,
    current_recovery_session_host_cli_readiness_smoke,
    render_recovery_session_host_cli_readiness_smoke,
)
from kernel.lifecycle.recovery_session_host_verdict_aggregator import (
    aggregate_recovery_session_host_operator_verdicts,
    render_recovery_session_host_verdict_aggregation,
)
from tests.tracer_bullet.test_recovery_session_host_cli import (
    _assert_json_safe_no_runtime_types,
    _assert_no_runtime_repr_strings,
    _assert_single_json_line,
    _invoke,
    _table_row_counts,
)
from tests.tracer_bullet.test_recovery_session_host_factory import (
    _initialize_empty_db,
    _seed_inference_stage,
)


def _collect_real_operator_payloads(
    *,
    tmpdir: Path,
    db_path: Path,
    task_id: str,
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]], Path]:
    missing_path = tmpdir / "missing.db"
    cases = [
        (
            "factory_check_valid",
            ["factory-check", "--db", str(db_path)],
            EXIT_OK,
        ),
        (
            "evaluate_existing",
            ["evaluate", "--db", str(db_path), "--task-id", task_id],
            EXIT_OK,
        ),
        (
            "evaluate_unknown",
            [
                "evaluate",
                "--db",
                str(db_path),
                "--task-id",
                "unknown-task",
            ],
            EXIT_OK,
        ),
        (
            "factory_check_missing",
            ["factory-check", "--db", str(missing_path)],
            EXIT_FACTORY_ERROR,
        ),
        (
            "evaluate_missing",
            [
                "evaluate",
                "--db",
                str(missing_path),
                "--task-id",
                "missing-task",
            ],
            EXIT_FACTORY_ERROR,
        ),
    ]

    by_name: dict[str, dict[str, object]] = {}
    payloads: list[dict[str, object]] = []
    for name, argv, expected_code in cases:
        code, stdout, stderr = _invoke(argv)
        if code != expected_code:
            raise AssertionError(
                f"{name} expected exit code {expected_code}, got {code}"
            )
        if stderr != "":
            raise AssertionError(f"{name} emitted stderr: {stderr!r}")
        payload = _assert_single_json_line(stdout)
        by_name[name] = payload
        payloads.append(payload)

    readiness_payload = current_recovery_session_host_cli_readiness_payload()
    smoke_payload = render_recovery_session_host_cli_readiness_smoke(
        current_recovery_session_host_cli_readiness_smoke()
    )
    by_name["readiness"] = readiness_payload
    by_name["smoke"] = smoke_payload
    payloads.extend([readiness_payload, smoke_payload])
    return payloads, by_name, missing_path


def _render_round_trips(payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    if json.loads(encoded) != payload:
        raise AssertionError("payload did not round-trip through JSON")


class TestRecoverySessionHostVerdictAggregatorAcceptance(unittest.TestCase):
    """Acceptance coverage for real frozen operator payload consumption."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _seeded_db(self) -> tuple[Path, str]:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)
        return db_path, task_id

    def _real_payloads(
        self,
    ) -> tuple[list[dict[str, object]], dict[str, dict[str, object]], Path]:
        db_path, task_id = self._seeded_db()
        return _collect_real_operator_payloads(
            tmpdir=self.tmpdir,
            db_path=db_path,
            task_id=task_id,
        )

    def test_acceptance_aggregator_consumes_real_operator_payloads(
        self,
    ) -> None:
        payloads, _by_name, _missing_path = self._real_payloads()

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        summary = aggregation.summary

        self.assertIs(aggregation.ok, True)
        self.assertEqual(summary["accepted_payloads"], len(payloads))
        self.assertEqual(summary["rejected_payloads"], 0)
        self.assertEqual(
            summary["payload_type_counts"]["factory_check"], 2
        )
        self.assertEqual(summary["payload_type_counts"]["evaluate"], 3)
        self.assertEqual(summary["payload_type_counts"]["readiness"], 1)
        self.assertEqual(summary["payload_type_counts"]["smoke"], 1)
        self.assertEqual(summary["factory"]["failed"], 2)
        self.assertEqual(
            summary["factory"]["reason_code_counts"],
            {"missing_db_file": 2},
        )
        self.assertEqual(
            summary["recovery"]["class_counts"],
            {"safe_to_resume": 1, "unrecoverable": 1},
        )
        self.assertEqual(
            summary["restore_surface"],
            {"restore_supported_true": 0, "restore_command_present": 0},
        )
        self.assertEqual(
            summary["durable_writes"], {"durable_writes_true": 0}
        )

        rendered = render_recovery_session_host_verdict_aggregation(
            aggregation
        )
        _render_round_trips(rendered)

    def test_acceptance_aggregator_preserves_read_only_runtime_boundary(
        self,
    ) -> None:
        db_path, task_id = self._seeded_db()
        before_counts = _table_row_counts(db_path)
        payloads, _by_name, missing_path = _collect_real_operator_payloads(
            tmpdir=self.tmpdir,
            db_path=db_path,
            task_id=task_id,
        )
        files_before_aggregation = {
            path.name for path in self.tmpdir.iterdir()
        }

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        rendered = render_recovery_session_host_verdict_aggregation(
            aggregation
        )

        self.assertIs(aggregation.ok, True)
        self.assertEqual(_table_row_counts(db_path), before_counts)
        self.assertFalse(missing_path.exists())
        self.assertEqual(
            {path.name for path in self.tmpdir.iterdir()},
            files_before_aggregation,
        )
        _render_round_trips(rendered)

    def test_acceptance_aggregator_handles_mixed_real_and_malformed_payloads(
        self,
    ) -> None:
        _payloads, by_name, _missing_path = self._real_payloads()
        payloads: list[object] = [
            by_name["factory_check_valid"],
            by_name["evaluate_existing"],
            "not-a-mapping",
            {"phase": "unknown"},
            {"command": "factory-check"},
            {
                "command": "evaluate",
                "factory": by_name["evaluate_existing"]["factory"],
                "host_state": by_name["evaluate_existing"]["host_state"],
                "recovery": "invalid-recovery",
            },
        ]

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        summary = aggregation.summary

        self.assertIs(aggregation.ok, False)
        self.assertEqual(aggregation.reason_code, "invalid_payloads")
        self.assertEqual(summary["accepted_payloads"], 2)
        self.assertEqual(summary["rejected_payloads"], 4)
        self.assertEqual(
            summary["payload_type_counts"]["factory_check"], 2
        )
        self.assertEqual(summary["payload_type_counts"]["evaluate"], 2)
        self.assertEqual(summary["factory"]["ok"], 2)
        self.assertEqual(summary["recovery"]["present"], 1)
        self.assertEqual(
            [
                error["reason_code"]
                for error in summary["payload_errors"]
            ],
            [
                "payload_not_mapping",
                "unknown_payload_shape",
                "factory_missing_or_invalid",
                "recovery_invalid",
            ],
        )

        rendered = render_recovery_session_host_verdict_aggregation(
            aggregation
        )
        _render_round_trips(rendered)

    def test_acceptance_aggregator_contract_summary_from_real_payloads(
        self,
    ) -> None:
        payloads, _by_name, _missing_path = self._real_payloads()
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        summary = aggregation.summary
        acceptance_summary = {
            "phase": "recovery_session_host_verdict_aggregation",
            "read_only_consumer": True,
            "input_surface": "frozen_recovery_session_host_operator_payloads",
            "ok": aggregation.ok,
            "total_payloads": summary["total_payloads"],
            "accepted_payloads": summary["accepted_payloads"],
            "rejected_payloads": summary["rejected_payloads"],
            "restore_supported_true": summary["restore_surface"][
                "restore_supported_true"
            ],
            "restore_command_present": summary["restore_surface"][
                "restore_command_present"
            ],
            "durable_writes_true": summary["durable_writes"][
                "durable_writes_true"
            ],
        }

        self.assertEqual(
            acceptance_summary["phase"],
            "recovery_session_host_verdict_aggregation",
        )
        self.assertIs(acceptance_summary["read_only_consumer"], True)
        self.assertIs(acceptance_summary["ok"], True)
        self.assertEqual(acceptance_summary["rejected_payloads"], 0)
        self.assertEqual(acceptance_summary["restore_supported_true"], 0)
        self.assertEqual(acceptance_summary["restore_command_present"], 0)
        self.assertEqual(acceptance_summary["durable_writes_true"], 0)
        _render_round_trips(acceptance_summary)

    def test_acceptance_aggregator_output_has_no_runtime_repr_leakage(
        self,
    ) -> None:
        payloads, _by_name, _missing_path = self._real_payloads()
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        rendered = render_recovery_session_host_verdict_aggregation(
            aggregation
        )

        _assert_json_safe_no_runtime_types(rendered)
        _assert_no_runtime_repr_strings(rendered)

    def test_acceptance_aggregator_does_not_call_operator_runtime(
        self,
    ) -> None:
        payloads, _by_name, _missing_path = self._real_payloads()

        with (
            mock.patch.object(
                recovery_session_host_cli,
                "main",
                side_effect=AssertionError("main called"),
            ),
            mock.patch.object(
                recovery_session_host_cli,
                "build_parser",
                side_effect=AssertionError("build_parser called"),
            ),
            mock.patch.object(
                recovery_session_host_cli,
                "try_build_recovery_session_host_from_sqlite",
                side_effect=AssertionError("factory called"),
            ),
        ):
            aggregation = aggregate_recovery_session_host_operator_verdicts(
                payloads
            )
            rendered = render_recovery_session_host_verdict_aggregation(
                aggregation
            )

        self.assertIs(aggregation.ok, True)
        _render_round_trips(rendered)

    def test_acceptance_aggregator_no_restore_or_command_creep(self) -> None:
        public_function_names = {
            name
            for name, value in aggregator_module.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(value)
        }
        for name in public_function_names:
            with self.subTest(name=name):
                self.assertNotIn("restore", name)

        source = inspect.getsource(aggregator_module)
        forbidden_markers = (
            "restore_task",
            "restore_if_allowed",
            "restore_task_from_snapshot",
            "build_parser",
            "try_build_recovery_session_host_from_sqlite",
            "sqlite3",
            "open_connection",
            "apply_migrations",
        )
        for marker in forbidden_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
