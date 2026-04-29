"""
P0-36 phase 1 - RecoverySessionHost verdict summary acceptance pack.

These tests prove the read-only verdict summary consumes realistic
rendered aggregation output derived from the frozen RecoverySessionHost
operator surface and emits a bounded operator/CI display digest.
"""

from __future__ import annotations

import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from uuid import uuid4

from kernel.lifecycle import recovery_session_host_cli
from kernel.lifecycle import recovery_session_host_verdict_aggregator as aggregator_module
from kernel.lifecycle import recovery_session_host_verdict_summary as summary_module
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
from kernel.lifecycle.recovery_session_host_verdict_summary import (
    build_recovery_session_host_verdict_summary,
    render_recovery_session_host_verdict_summary,
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
    cases = (
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
    )

    payloads: list[dict[str, object]] = []
    by_name: dict[str, dict[str, object]] = {}
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


def _relative_files(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(str(path.relative_to(root)) for path in root.rglob("*"))
    )


class TestRecoverySessionHostVerdictSummaryAcceptance(unittest.TestCase):
    """Acceptance coverage for real rendered aggregation consumption."""

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

    def _real_rendered_aggregation(self) -> dict[str, object]:
        payloads, _by_name, _missing_path = self._real_payloads()
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        return render_recovery_session_host_verdict_aggregation(aggregation)

    def test_acceptance_summary_consumes_real_rendered_aggregation(
        self,
    ) -> None:
        payloads, _by_name, _missing_path = self._real_payloads()

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        rendered_aggregation = render_recovery_session_host_verdict_aggregation(
            aggregation
        )
        summary = build_recovery_session_host_verdict_summary(
            rendered_aggregation
        )
        rendered_summary = render_recovery_session_host_verdict_summary(
            summary
        )
        digest = rendered_summary["digest"]
        self.assertIsInstance(digest, dict)

        self.assertIs(aggregation.ok, True)
        self.assertIs(summary.ok, True)
        self.assertEqual(summary.reason_code, "ok")
        self.assertEqual(summary.failures, ())
        self.assertIs(digest["aggregation_ok"], True)
        self.assertIs(digest["operator_safe"], True)
        self.assertEqual(
            digest["total_payloads"],
            rendered_aggregation["summary"]["total_payloads"],
        )
        self.assertEqual(
            digest["accepted_payloads"],
            rendered_aggregation["summary"]["accepted_payloads"],
        )
        self.assertEqual(digest["rejected_payloads"], 0)
        self.assertEqual(digest["restore_supported_true"], 0)
        self.assertEqual(digest["restore_command_present"], 0)
        self.assertEqual(digest["durable_writes_true"], 0)
        _render_round_trips(rendered_summary)

    def test_acceptance_summary_preserves_read_only_runtime_boundary(
        self,
    ) -> None:
        db_path, task_id = self._seeded_db()
        before_counts = _table_row_counts(db_path)

        payloads, _by_name, missing_path = _collect_real_operator_payloads(
            tmpdir=self.tmpdir,
            db_path=db_path,
            task_id=task_id,
        )
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        rendered_aggregation = render_recovery_session_host_verdict_aggregation(
            aggregation
        )
        files_before_summary = _relative_files(self.tmpdir)

        summary = build_recovery_session_host_verdict_summary(
            rendered_aggregation
        )
        rendered_summary = render_recovery_session_host_verdict_summary(
            summary
        )

        self.assertEqual(_table_row_counts(db_path), before_counts)
        self.assertFalse(missing_path.exists())
        self.assertEqual(_relative_files(self.tmpdir), files_before_summary)
        self.assertIs(summary.ok, True)
        _render_round_trips(rendered_summary)

    def test_acceptance_summary_handles_malformed_aggregation_output(
        self,
    ) -> None:
        rendered_aggregation = self._real_rendered_aggregation()
        del rendered_aggregation["summary"]["factory"]

        summary = build_recovery_session_host_verdict_summary(
            rendered_aggregation
        )
        rendered_summary = render_recovery_session_host_verdict_summary(
            summary
        )
        digest = rendered_summary["digest"]
        self.assertIsInstance(digest, dict)

        self.assertIs(summary.ok, False)
        self.assertEqual(summary.reason_code, "invalid_aggregation")
        self.assertIn(
            "aggregation_summary_shape_mismatch",
            summary.failures,
        )
        self.assertIs(digest["operator_safe"], False)
        _render_round_trips(rendered_summary)

    def test_acceptance_summary_digest_tracks_mixed_valid_invalid_aggregation(
        self,
    ) -> None:
        _payloads, by_name, _missing_path = self._real_payloads()
        mixed_payloads: list[object] = [
            by_name["factory_check_valid"],
            by_name["evaluate_existing"],
            "not-a-mapping",
            {"phase": "unknown"},
            {"command": "factory-check"},
        ]

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            mixed_payloads
        )
        rendered_aggregation = render_recovery_session_host_verdict_aggregation(
            aggregation
        )
        summary = build_recovery_session_host_verdict_summary(
            rendered_aggregation
        )
        rendered_summary = render_recovery_session_host_verdict_summary(
            summary
        )
        digest = rendered_summary["digest"]
        self.assertIsInstance(digest, dict)

        self.assertIs(aggregation.ok, False)
        self.assertIs(summary.ok, True)
        self.assertIs(digest["aggregation_ok"], False)
        self.assertIs(digest["operator_safe"], False)
        self.assertIs(digest["has_payload_errors"], True)
        self.assertEqual(digest["rejected_payloads"], 3)
        payload_error_reason_counts = digest[
            "payload_error_reason_counts"
        ]
        self.assertIsInstance(payload_error_reason_counts, dict)
        self.assertIn("payload_not_mapping", payload_error_reason_counts)
        self.assertIn("unknown_payload_shape", payload_error_reason_counts)
        self.assertIn(
            "factory_missing_or_invalid",
            payload_error_reason_counts,
        )
        _render_round_trips(rendered_summary)

    def test_acceptance_summary_operator_safe_reacts_to_guard_counts(
        self,
    ) -> None:
        base_rendered_aggregation = self._real_rendered_aggregation()

        def set_restore_supported(rendered: dict[str, object]) -> None:
            rendered["summary"]["restore_surface"][
                "restore_supported_true"
            ] = 1

        def set_restore_command(rendered: dict[str, object]) -> None:
            rendered["summary"]["restore_surface"][
                "restore_command_present"
            ] = 1

        def set_durable_write(rendered: dict[str, object]) -> None:
            rendered["summary"]["durable_writes"][
                "durable_writes_true"
            ] = 1

        def set_readiness_false(rendered: dict[str, object]) -> None:
            rendered["summary"]["readiness"]["ready_false"] = 1

        def set_smoke_false(rendered: dict[str, object]) -> None:
            rendered["summary"]["smoke"]["passed_false"] = 1

        def set_rejected_payload(rendered: dict[str, object]) -> None:
            rendered["summary"]["rejected_payloads"] = 1
            rendered["summary"]["payload_errors"] = []

        def set_aggregation_not_ok(rendered: dict[str, object]) -> None:
            rendered["ok"] = False
            rendered["reason_code"] = "invalid_payloads"
            rendered["failures"] = ["acceptance_guard_failure"]

        cases = (
            (
                "restore_supported_true",
                set_restore_supported,
                "has_restore_surface",
            ),
            (
                "restore_command_present",
                set_restore_command,
                "has_restore_surface",
            ),
            ("durable_writes_true", set_durable_write, "has_durable_writes"),
            ("readiness_ready_false", set_readiness_false, None),
            ("smoke_passed_false", set_smoke_false, None),
            ("rejected_payloads", set_rejected_payload, "has_payload_errors"),
            ("aggregation_ok_false", set_aggregation_not_ok, None),
        )

        for name, mutate, expected_flag in cases:
            with self.subTest(name=name):
                rendered_aggregation = copy.deepcopy(
                    base_rendered_aggregation
                )
                mutate(rendered_aggregation)

                summary = build_recovery_session_host_verdict_summary(
                    rendered_aggregation
                )
                rendered_summary = render_recovery_session_host_verdict_summary(
                    summary
                )
                digest = rendered_summary["digest"]
                self.assertIsInstance(digest, dict)

                self.assertIs(summary.ok, True)
                self.assertIs(digest["operator_safe"], False)
                if expected_flag is not None:
                    self.assertIs(digest[expected_flag], True)
                if name == "aggregation_ok_false":
                    self.assertIs(digest["aggregation_ok"], False)
                    self.assertEqual(
                        digest["aggregation_failures"],
                        ["acceptance_guard_failure"],
                    )
                _render_round_trips(rendered_summary)

    def test_acceptance_summary_contract_digest_for_ci_display(self) -> None:
        rendered_aggregation = self._real_rendered_aggregation()
        summary = build_recovery_session_host_verdict_summary(
            rendered_aggregation
        )
        rendered_summary = render_recovery_session_host_verdict_summary(
            summary
        )
        digest = rendered_summary["digest"]
        self.assertIsInstance(digest, dict)
        display = {
            "phase": "recovery_session_host_verdict_summary",
            "operator_safe": digest["operator_safe"],
            "total_payloads": digest["total_payloads"],
            "accepted_payloads": digest["accepted_payloads"],
            "rejected_payloads": digest["rejected_payloads"],
            "factory_failed": digest["factory_failed"],
            "restore_supported_true": digest["restore_supported_true"],
            "restore_command_present": digest["restore_command_present"],
            "durable_writes_true": digest["durable_writes_true"],
            "has_payload_errors": digest["has_payload_errors"],
        }

        self.assertEqual(
            display["phase"],
            "recovery_session_host_verdict_summary",
        )
        self.assertIs(display["operator_safe"], True)
        self.assertEqual(display["rejected_payloads"], 0)
        self.assertEqual(display["restore_supported_true"], 0)
        self.assertEqual(display["restore_command_present"], 0)
        self.assertEqual(display["durable_writes_true"], 0)
        self.assertIs(display["has_payload_errors"], False)
        _render_round_trips(display)

    def test_acceptance_summary_output_has_no_runtime_repr_leakage(
        self,
    ) -> None:
        rendered_aggregation = self._real_rendered_aggregation()
        summary = build_recovery_session_host_verdict_summary(
            rendered_aggregation
        )
        rendered_summary = render_recovery_session_host_verdict_summary(
            summary
        )

        _assert_json_safe_no_runtime_types(rendered_summary)
        _assert_no_runtime_repr_strings(rendered_summary)

    def test_acceptance_summary_does_not_call_aggregator_or_operator_runtime(
        self,
    ) -> None:
        rendered_aggregation = self._real_rendered_aggregation()

        with (
            mock.patch.object(
                aggregator_module,
                "aggregate_recovery_session_host_operator_verdicts",
                side_effect=AssertionError("aggregator called"),
            ),
            mock.patch.object(
                aggregator_module,
                "render_recovery_session_host_verdict_aggregation",
                side_effect=AssertionError("aggregation renderer called"),
            ),
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
            summary = build_recovery_session_host_verdict_summary(
                rendered_aggregation
            )
            rendered_summary = render_recovery_session_host_verdict_summary(
                summary
            )

        self.assertIs(summary.ok, True)
        _render_round_trips(rendered_summary)

    def test_acceptance_summary_no_restore_or_command_creep(self) -> None:
        public_function_names = {
            name
            for name, value in summary_module.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(value)
        }
        for name in public_function_names:
            with self.subTest(name=name):
                self.assertNotIn("restore", name)

        source = inspect.getsource(summary_module)
        forbidden_markers = (
            "restore_task",
            "restore_if_allowed",
            "restore_task_from_snapshot",
            "build_parser",
            "try_build_recovery_session_host_from_sqlite",
            "aggregate_recovery_session_host_operator_verdicts",
            "recovery_session_host_cli",
            "sqlite3",
            "open_connection",
            "apply_migrations",
            "KernelUnitOfWork",
        )
        for marker in forbidden_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
