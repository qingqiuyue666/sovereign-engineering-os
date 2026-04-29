"""
P0-38 phase 1 - RecoverySessionHost verdict summary manifest acceptance pack.

These tests prove the read-only verdict summary contract manifest/check
surface validates realistic rendered summary payloads derived from the
frozen operator surface, aggregation, and summary pipeline.
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
from kernel.lifecycle import (
    recovery_session_host_verdict_summary_manifest as manifest_module,
)
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
from kernel.lifecycle.recovery_session_host_verdict_summary_manifest import (
    check_recovery_session_host_verdict_summary_contract,
    render_recovery_session_host_verdict_summary_contract_check,
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


def _invoke_json_payload(
    argv: list[str],
    *,
    expected_code: int,
    name: str,
) -> dict[str, object]:
    code, stdout, stderr = _invoke(argv)
    if code != expected_code:
        raise AssertionError(
            f"{name} expected exit code {expected_code}, got {code}"
        )
    if stderr != "":
        raise AssertionError(f"{name} emitted stderr: {stderr!r}")
    return _assert_single_json_line(stdout)


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
        payload = _invoke_json_payload(
            argv,
            expected_code=expected_code,
            name=name,
        )
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


def _render_summary_from_payloads(
    payloads: list[object],
) -> tuple[object, dict[str, object], object, dict[str, object]]:
    aggregation = aggregate_recovery_session_host_operator_verdicts(payloads)
    rendered_aggregation = render_recovery_session_host_verdict_aggregation(
        aggregation
    )
    summary = build_recovery_session_host_verdict_summary(
        rendered_aggregation
    )
    rendered_summary = render_recovery_session_host_verdict_summary(summary)
    return aggregation, rendered_aggregation, summary, rendered_summary


def _json_round_trips(payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    if json.loads(encoded) != payload:
        raise AssertionError("payload did not round-trip through JSON")


def _relative_files(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(str(path.relative_to(root)) for path in root.rglob("*"))
    )


class TestRecoverySessionHostVerdictSummaryManifestAcceptance(
    unittest.TestCase
):
    """Acceptance coverage for rendered summary contract checks."""

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

    def _real_rendered_summary(self) -> dict[str, object]:
        payloads, _by_name, _missing_path = self._real_payloads()
        _aggregation, _rendered_aggregation, _summary, rendered_summary = (
            _render_summary_from_payloads(list(payloads))
        )
        return rendered_summary

    def test_acceptance_manifest_check_accepts_real_rendered_summary(
        self,
    ) -> None:
        rendered_summary = self._real_rendered_summary()

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        rendered_check = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )

        self.assertIs(check.ready, True)
        self.assertEqual(check.reason_code, "ready")
        self.assertEqual(check.failures, ())
        self.assertIs(rendered_check["ready"], True)
        self.assertEqual(rendered_check["reason_code"], "ready")
        self.assertEqual(rendered_check["failures"], [])
        self.assertEqual(
            rendered_check["manifest"]["surface"],
            "recovery_session_host_verdict_summary",
        )
        self.assertEqual(rendered_check["manifest"]["version"], 1)
        _json_round_trips(rendered_check)

    def test_acceptance_manifest_check_preserves_read_only_runtime_boundary(
        self,
    ) -> None:
        db_path, task_id = self._seeded_db()
        before_counts = _table_row_counts(db_path)

        payloads, _by_name, missing_path = _collect_real_operator_payloads(
            tmpdir=self.tmpdir,
            db_path=db_path,
            task_id=task_id,
        )
        _aggregation, _rendered_aggregation, _summary, rendered_summary = (
            _render_summary_from_payloads(list(payloads))
        )
        files_before_manifest = _relative_files(self.tmpdir)

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        render_recovery_session_host_verdict_summary_contract_check(check)

        self.assertEqual(_table_row_counts(db_path), before_counts)
        self.assertFalse(missing_path.exists())
        self.assertEqual(_relative_files(self.tmpdir), files_before_manifest)

    def test_acceptance_manifest_check_rejects_malformed_real_summary(
        self,
    ) -> None:
        rendered_summary = self._real_rendered_summary()
        del rendered_summary["digest"]["operator_safe"]

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        rendered_check = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )

        self.assertIs(check.ready, False)
        self.assertEqual(check.reason_code, "not_ready")
        self.assertIn("digest_shape_mismatch", check.failures)
        _json_round_trips(rendered_check)

    def test_acceptance_manifest_check_detects_unsafe_digest_from_real_summary(
        self,
    ) -> None:
        base_rendered_summary = self._real_rendered_summary()
        base_digest = base_rendered_summary["digest"]
        self.assertIsInstance(base_digest, dict)
        self.assertIs(base_digest["operator_safe"], True)

        cases = (
            ("restore_supported_true", "restore_surface_present"),
            ("restore_command_present", "restore_surface_present"),
            ("durable_writes_true", "durable_writes_present"),
            ("rejected_payloads", None),
            ("readiness_ready_false", None),
            ("smoke_passed_false", None),
        )
        for key, expected_failure in cases:
            with self.subTest(key=key):
                rendered_summary = copy.deepcopy(base_rendered_summary)
                digest = rendered_summary["digest"]
                self.assertIsInstance(digest, dict)
                digest[key] = 1
                digest["operator_safe"] = True

                check = check_recovery_session_host_verdict_summary_contract(
                    rendered_summary
                )

                self.assertIs(check.ready, False)
                self.assertIn(
                    "operator_safe_inconsistent",
                    check.failures,
                )
                if expected_failure is not None:
                    self.assertIn(expected_failure, check.failures)

    def test_acceptance_manifest_check_tracks_mixed_valid_invalid_summary(
        self,
    ) -> None:
        db_path, task_id = self._seeded_db()
        factory_payload = _invoke_json_payload(
            ["factory-check", "--db", str(db_path)],
            expected_code=EXIT_OK,
            name="factory_check_valid",
        )
        evaluate_payload = _invoke_json_payload(
            ["evaluate", "--db", str(db_path), "--task-id", task_id],
            expected_code=EXIT_OK,
            name="evaluate_existing",
        )
        mixed_payloads: list[object] = [
            factory_payload,
            evaluate_payload,
            "not-a-mapping",
            {"phase": "unknown"},
            {"command": "factory-check"},
        ]

        aggregation, _rendered_aggregation, summary, rendered_summary = (
            _render_summary_from_payloads(mixed_payloads)
        )
        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIs(aggregation.ok, False)
        self.assertIs(summary.ok, True)
        self.assertIs(rendered_summary["ok"], True)
        self.assertIs(rendered_summary["digest"]["aggregation_ok"], False)
        self.assertIs(rendered_summary["digest"]["operator_safe"], False)
        self.assertIs(check.ready, True)
        self.assertEqual(check.failures, ())

    def test_acceptance_manifest_check_status_inconsistency_from_real_summary(
        self,
    ) -> None:
        base_rendered_summary = self._real_rendered_summary()
        cases = (
            (
                "ok_true_invalid_reason",
                {"ok": True, "reason_code": "invalid_aggregation"},
            ),
            (
                "ok_true_with_failures",
                {"ok": True, "failures": ["aggregation_not_mapping"]},
            ),
            (
                "ok_false_ok_reason",
                {
                    "ok": False,
                    "reason_code": "ok",
                    "failures": ["aggregation_not_mapping"],
                },
            ),
            (
                "ok_false_empty_failures",
                {
                    "ok": False,
                    "reason_code": "invalid_aggregation",
                    "failures": [],
                },
            ),
        )

        for name, updates in cases:
            with self.subTest(name=name):
                rendered_summary = copy.deepcopy(base_rendered_summary)
                rendered_summary.update(updates)

                check = check_recovery_session_host_verdict_summary_contract(
                    rendered_summary
                )

                self.assertIn(
                    "summary_status_inconsistent",
                    check.failures,
                )

    def test_acceptance_manifest_check_digest_type_inconsistency_from_real_summary(
        self,
    ) -> None:
        base_rendered_summary = self._real_rendered_summary()
        cases = (
            ("total_payloads", True, "digest_counter_invalid"),
            ("aggregation_ok", "yes", "digest_bool_invalid"),
            ("aggregation_reason_code", 123, "digest_string_invalid"),
            ("aggregation_failures", ["x", 1], "digest_list_invalid"),
            (
                "payload_type_counts",
                {"z": 1, "a": 2},
                "digest_count_dict_invalid",
            ),
        )

        for key, value, expected_failure in cases:
            with self.subTest(key=key):
                rendered_summary = copy.deepcopy(base_rendered_summary)
                digest = rendered_summary["digest"]
                self.assertIsInstance(digest, dict)
                digest[key] = value

                check = check_recovery_session_host_verdict_summary_contract(
                    rendered_summary
                )

                self.assertIn(expected_failure, check.failures)

    def test_acceptance_manifest_output_has_no_runtime_repr_leakage(
        self,
    ) -> None:
        rendered_summary = self._real_rendered_summary()

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        rendered_check = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )

        _assert_json_safe_no_runtime_types(rendered_check)
        _assert_no_runtime_repr_strings(rendered_check)

    def test_acceptance_manifest_check_does_not_call_summary_aggregator_or_operator_runtime(
        self,
    ) -> None:
        rendered_summary = self._real_rendered_summary()

        with (
            mock.patch.object(
                summary_module,
                "build_recovery_session_host_verdict_summary",
                side_effect=AssertionError("summary builder called"),
            ),
            mock.patch.object(
                summary_module,
                "render_recovery_session_host_verdict_summary",
                side_effect=AssertionError("summary renderer called"),
            ),
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
            check = check_recovery_session_host_verdict_summary_contract(
                rendered_summary
            )
            rendered_check = (
                render_recovery_session_host_verdict_summary_contract_check(
                    check
                )
            )

        self.assertIs(check.ready, True)
        _json_round_trips(rendered_check)

    def test_acceptance_manifest_no_restore_or_command_creep(self) -> None:
        public_function_names = {
            name
            for name, value in manifest_module.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(value)
        }
        for name in public_function_names:
            with self.subTest(name=name):
                self.assertNotIn("restore", name)

        source = inspect.getsource(manifest_module)
        forbidden_markers = (
            "restore_task",
            "restore_if_allowed",
            "restore_task_from_snapshot",
            "build_parser",
            "try_build_recovery_session_host_from_sqlite",
            "aggregate_recovery_session_host_operator_verdicts",
            "build_recovery_session_host_verdict_summary",
            "recovery_session_host_cli",
            "recovery_session_host_verdict_aggregator",
            "sqlite3",
            "open_connection",
            "apply_migrations",
            "KernelUnitOfWork",
        )
        for marker in forbidden_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

        forbidden_runtime_summary_patterns = (
            "import recovery_session_host_verdict_summary",
            "from kernel.lifecycle.recovery_session_host_verdict_summary",
            "recovery_session_host_verdict_summary.",
        )
        for pattern in forbidden_runtime_summary_patterns:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, source)

    def test_acceptance_manifest_contract_summary_for_ci_display(
        self,
    ) -> None:
        rendered_summary = self._real_rendered_summary()
        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        rendered_check = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )
        display = {
            "phase": "recovery_session_host_verdict_summary_manifest",
            "contract_ready": rendered_check["ready"],
            "contract_reason_code": rendered_check["reason_code"],
            "manifest_surface": rendered_check["manifest"]["surface"],
            "manifest_version": rendered_check["manifest"]["version"],
            "restore_supported": rendered_check["manifest"][
                "restore_supported"
            ],
            "durable_writes": rendered_check["manifest"]["durable_writes"],
            "cli_commands": rendered_check["manifest"]["cli_commands"],
            "runtime_dependencies": rendered_check["manifest"][
                "runtime_dependencies"
            ],
            "json_safe": rendered_check["manifest"]["json_safe"],
        }

        self.assertEqual(
            display["phase"],
            "recovery_session_host_verdict_summary_manifest",
        )
        self.assertIs(display["contract_ready"], True)
        self.assertEqual(
            display["manifest_surface"],
            "recovery_session_host_verdict_summary",
        )
        self.assertEqual(display["manifest_version"], 1)
        self.assertIs(display["restore_supported"], False)
        self.assertIs(display["durable_writes"], False)
        self.assertEqual(display["cli_commands"], [])
        self.assertEqual(display["runtime_dependencies"], [])
        self.assertIs(display["json_safe"], True)
        _json_round_trips(display)


if __name__ == "__main__":
    unittest.main()
