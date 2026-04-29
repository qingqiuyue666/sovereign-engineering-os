"""
P0-44 phase 1 - RecoverySessionHost cross-phase verdict digest acceptance.

These tests prove the read-only cross-phase digest consumes realistic
rendered contract checks and rendered comparator payloads derived from
the frozen operator payload pipeline.
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
from kernel.lifecycle import (
    recovery_session_host_verdict_cross_phase_digest as digest_module,
)
from kernel.lifecycle import (
    recovery_session_host_verdict_summary as summary_module,
)
from kernel.lifecycle import (
    recovery_session_host_verdict_summary_comparator as comparator_module,
)
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
from kernel.lifecycle.recovery_session_host_verdict_cross_phase_digest import (
    build_recovery_session_host_verdict_cross_phase_digest,
    render_recovery_session_host_verdict_cross_phase_digest,
)
from kernel.lifecycle.recovery_session_host_verdict_summary import (
    build_recovery_session_host_verdict_summary,
    render_recovery_session_host_verdict_summary,
)
from kernel.lifecycle.recovery_session_host_verdict_summary_comparator import (
    compare_recovery_session_host_verdict_summary_checks,
    render_recovery_session_host_verdict_summary_comparison,
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


_INVALID_DIGEST_KEYS = {
    "cross_phase_ok",
    "reason_code",
    "failures",
    "operator_safe",
}


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


def _render_check_from_payloads(payloads: list[object]) -> dict[str, object]:
    _aggregation, _rendered_aggregation, _summary, rendered_summary = (
        _render_summary_from_payloads(payloads)
    )
    check = check_recovery_session_host_verdict_summary_contract(
        rendered_summary
    )
    return render_recovery_session_host_verdict_summary_contract_check(check)


def _render_comparison_for_check(
    rendered_check: dict[str, object],
) -> dict[str, object]:
    comparison = compare_recovery_session_host_verdict_summary_checks(
        rendered_check,
        copy.deepcopy(rendered_check),
    )
    return render_recovery_session_host_verdict_summary_comparison(
        comparison
    )


def _json_round_trips(payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    if json.loads(encoded) != payload:
        raise AssertionError("payload did not round-trip through JSON")


def _relative_files(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(str(path.relative_to(root)) for path in root.rglob("*"))
    )


class TestRecoverySessionHostVerdictCrossPhaseDigestAcceptance(
    unittest.TestCase
):
    """Acceptance coverage for real rendered check/comparison consumption."""

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

    def _real_rendered_check(self) -> dict[str, object]:
        payloads, _by_name, _missing_path = self._real_payloads()
        return _render_check_from_payloads(list(payloads))

    def _safe_real_rendered_check_and_comparison(
        self,
    ) -> tuple[dict[str, object], dict[str, object]]:
        rendered_check = self._real_rendered_check()
        rendered_comparison = _render_comparison_for_check(rendered_check)
        return rendered_check, rendered_comparison

    def test_acceptance_digest_accepts_safe_real_no_drift_pipeline(
        self,
    ) -> None:
        db_path, task_id = self._seeded_db()
        payloads, _by_name, _missing_path = _collect_real_operator_payloads(
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
        summary = build_recovery_session_host_verdict_summary(
            rendered_aggregation
        )
        rendered_summary = render_recovery_session_host_verdict_summary(
            summary
        )
        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        rendered_check = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )
        comparison = compare_recovery_session_host_verdict_summary_checks(
            rendered_check,
            copy.deepcopy(rendered_check),
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            )
        )
        cross_phase = build_recovery_session_host_verdict_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )
        rendered_digest = (
            render_recovery_session_host_verdict_cross_phase_digest(
                cross_phase
            )
        )
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)

        self.assertIs(cross_phase.ok, True)
        self.assertEqual(cross_phase.reason_code, "ok")
        self.assertEqual(cross_phase.failures, ())
        self.assertIs(digest["cross_phase_ok"], True)
        self.assertIs(digest["operator_safe"], True)
        self.assertIs(digest["contract_ready"], True)
        self.assertIs(digest["comparison_ok"], True)
        self.assertIs(digest["comparison_changed"], False)
        self.assertEqual(digest["comparison_change_count"], 0)
        self.assertIs(digest["has_drift"], False)
        self.assertIs(digest["has_contract_failure"], False)
        self.assertIs(digest["has_runtime_dependencies"], False)
        self.assertIs(digest["has_cli_commands"], False)
        self.assertIs(
            digest["has_restore_or_durable_surface"],
            False,
        )
        _json_round_trips(rendered_digest)

    def test_acceptance_digest_detects_real_comparator_drift(self) -> None:
        rendered_check = self._real_rendered_check()
        before = rendered_check
        after = copy.deepcopy(rendered_check)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        manifest["version"] = version + 1

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before,
            after,
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            )
        )
        cross_phase = build_recovery_session_host_verdict_cross_phase_digest(
            before,
            rendered_comparison,
        )
        rendered_digest = (
            render_recovery_session_host_verdict_cross_phase_digest(
                cross_phase
            )
        )
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)

        self.assertIs(cross_phase.ok, True)
        self.assertIs(digest["operator_safe"], False)
        self.assertIs(digest["has_drift"], True)
        self.assertIs(digest["comparison_changed"], True)
        self.assertEqual(digest["comparison_change_count"], 1)
        self.assertNotEqual(
            digest["before_manifest_version"],
            digest["after_manifest_version"],
        )

    def test_acceptance_digest_detects_contract_failure_from_real_invalid_check(
        self,
    ) -> None:
        rendered_check = self._real_rendered_check()
        mutated_check = copy.deepcopy(rendered_check)
        mutated_check["ready"] = False
        mutated_check["reason_code"] = "not_ready"
        mutated_check["failures"] = ["digest_shape_mismatch"]

        comparison = compare_recovery_session_host_verdict_summary_checks(
            mutated_check,
            copy.deepcopy(mutated_check),
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            )
        )
        cross_phase = build_recovery_session_host_verdict_cross_phase_digest(
            mutated_check,
            rendered_comparison,
        )
        rendered_digest = (
            render_recovery_session_host_verdict_cross_phase_digest(
                cross_phase
            )
        )
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)

        self.assertIs(cross_phase.ok, True)
        self.assertIs(digest["contract_ready"], False)
        self.assertEqual(digest["contract_failure_count"], 1)
        self.assertIs(digest["has_contract_failure"], True)
        self.assertIs(digest["operator_safe"], False)

    def test_acceptance_digest_rejects_malformed_real_inputs(self) -> None:
        rendered_check, rendered_comparison = (
            self._safe_real_rendered_check_and_comparison()
        )
        malformed_check = copy.deepcopy(rendered_check)
        malformed_check["extra"] = True
        malformed_comparison = copy.deepcopy(rendered_comparison)
        malformed_comparison["report"] = "bad"

        cross_phase = build_recovery_session_host_verdict_cross_phase_digest(
            malformed_check,
            malformed_comparison,
        )
        rendered_digest = (
            render_recovery_session_host_verdict_cross_phase_digest(
                cross_phase
            )
        )
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)

        self.assertIs(cross_phase.ok, False)
        self.assertEqual(
            cross_phase.reason_code,
            "invalid_cross_phase_digest",
        )
        self.assertIn("check_shape_mismatch", cross_phase.failures)
        self.assertIn("comparison_report_invalid", cross_phase.failures)
        self.assertEqual(set(digest), _INVALID_DIGEST_KEYS)
        _json_round_trips(rendered_digest)

    def test_acceptance_digest_preserves_read_only_runtime_boundary(
        self,
    ) -> None:
        db_path, task_id = self._seeded_db()
        before_counts = _table_row_counts(db_path)
        files_before_pipeline = _relative_files(self.tmpdir)

        payloads, _by_name, missing_path = _collect_real_operator_payloads(
            tmpdir=self.tmpdir,
            db_path=db_path,
            task_id=task_id,
        )
        rendered_check = _render_check_from_payloads(list(payloads))
        rendered_comparison = _render_comparison_for_check(rendered_check)
        files_before_digest = _relative_files(self.tmpdir)

        cross_phase = build_recovery_session_host_verdict_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )
        rendered_digest = (
            render_recovery_session_host_verdict_cross_phase_digest(
                cross_phase
            )
        )

        self.assertEqual(_table_row_counts(db_path), before_counts)
        self.assertFalse(missing_path.exists())
        self.assertEqual(_relative_files(self.tmpdir), files_before_pipeline)
        self.assertEqual(_relative_files(self.tmpdir), files_before_digest)
        self.assertIs(cross_phase.ok, True)
        _json_round_trips(rendered_digest)

    def test_acceptance_digest_handles_valid_failure_comparison_payload(
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
        rendered_check = _render_check_from_payloads(mixed_payloads)
        self.assertIs(rendered_check["ready"], True)

        comparison = compare_recovery_session_host_verdict_summary_checks(
            rendered_check,
            copy.deepcopy(rendered_check),
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            )
        )
        report = rendered_comparison["report"]
        self.assertIsInstance(report, dict)
        cross_phase = build_recovery_session_host_verdict_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )
        rendered_digest = (
            render_recovery_session_host_verdict_cross_phase_digest(
                cross_phase
            )
        )
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)

        self.assertIs(report["comparison_ok"], True)
        self.assertIs(report["changed"], False)
        self.assertIs(cross_phase.ok, True)
        self.assertIs(digest["contract_ready"], True)
        self.assertIs(digest["comparison_ok"], True)
        self.assertIs(digest["has_drift"], False)
        self.assertIs(digest["operator_safe"], True)

    def test_acceptance_digest_detects_runtime_or_cli_or_restore_surface(
        self,
    ) -> None:
        rendered_check, rendered_comparison = (
            self._safe_real_rendered_check_and_comparison()
        )
        cases = (
            (
                "runtime_dependencies",
                lambda manifest: manifest.update(
                    {"runtime_dependencies": ["sqlite3"]}
                ),
                "has_runtime_dependencies",
            ),
            (
                "cli_commands",
                lambda manifest: manifest.update(
                    {"cli_commands": ["status"]}
                ),
                "has_cli_commands",
            ),
            (
                "restore_supported",
                lambda manifest: manifest.update(
                    {"restore_supported": True}
                ),
                "has_restore_or_durable_surface",
            ),
            (
                "durable_writes",
                lambda manifest: manifest.update({"durable_writes": True}),
                "has_restore_or_durable_surface",
            ),
            (
                "json_safe",
                lambda manifest: manifest.update({"json_safe": False}),
                None,
            ),
        )

        for name, mutate, expected_flag in cases:
            with self.subTest(name=name):
                check = copy.deepcopy(rendered_check)
                manifest = check["manifest"]
                self.assertIsInstance(manifest, dict)
                mutate(manifest)

                cross_phase = (
                    build_recovery_session_host_verdict_cross_phase_digest(
                        check,
                        rendered_comparison,
                    )
                )
                rendered_digest = (
                    render_recovery_session_host_verdict_cross_phase_digest(
                        cross_phase
                    )
                )
                digest = rendered_digest["digest"]
                self.assertIsInstance(digest, dict)

                self.assertIs(cross_phase.ok, True)
                self.assertIs(digest["operator_safe"], False)
                if expected_flag is not None:
                    self.assertIs(digest[expected_flag], True)

    def test_acceptance_digest_output_has_no_runtime_repr_leakage(
        self,
    ) -> None:
        rendered_check = self._real_rendered_check()
        after = copy.deepcopy(rendered_check)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        manifest["version"] = version + 1

        comparison = compare_recovery_session_host_verdict_summary_checks(
            rendered_check,
            after,
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            )
        )
        cross_phase = build_recovery_session_host_verdict_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )
        rendered_digest = (
            render_recovery_session_host_verdict_cross_phase_digest(
                cross_phase
            )
        )

        _assert_json_safe_no_runtime_types(rendered_digest)
        _assert_no_runtime_repr_strings(rendered_digest)

    def test_acceptance_digest_does_not_call_comparator_manifest_summary_aggregator_or_operator_runtime(
        self,
    ) -> None:
        rendered_check, rendered_comparison = (
            self._safe_real_rendered_check_and_comparison()
        )

        with (
            mock.patch.object(
                comparator_module,
                "compare_recovery_session_host_verdict_summary_checks",
                side_effect=AssertionError("comparator called"),
            ),
            mock.patch.object(
                comparator_module,
                "render_recovery_session_host_verdict_summary_comparison",
                side_effect=AssertionError("comparison renderer called"),
            ),
            mock.patch.object(
                manifest_module,
                "check_recovery_session_host_verdict_summary_contract",
                side_effect=AssertionError("manifest checker called"),
            ),
            mock.patch.object(
                manifest_module,
                "render_recovery_session_host_verdict_summary_contract_check",
                side_effect=AssertionError("manifest renderer called"),
            ),
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
            cross_phase = (
                build_recovery_session_host_verdict_cross_phase_digest(
                    rendered_check,
                    rendered_comparison,
                )
            )
            rendered_digest = (
                render_recovery_session_host_verdict_cross_phase_digest(
                    cross_phase
                )
            )

        self.assertIs(cross_phase.ok, True)
        self.assertIs(rendered_digest["ok"], True)
        _json_round_trips(rendered_digest)

    def test_acceptance_digest_no_restore_or_command_creep(self) -> None:
        public_function_names = {
            name
            for name, value in digest_module.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(value)
        }
        for name in public_function_names:
            with self.subTest(name=name):
                self.assertNotIn("restore", name)

        source = inspect.getsource(digest_module)
        forbidden_markers = (
            "restore_task",
            "restore_if_allowed",
            "restore_task_from_snapshot",
            "build_parser",
            "try_build_recovery_session_host_from_sqlite",
            "aggregate_recovery_session_host_operator_verdicts",
            "render_recovery_session_host_verdict_aggregation",
            "build_recovery_session_host_verdict_summary",
            "render_recovery_session_host_verdict_summary",
            "check_recovery_session_host_verdict_summary_contract",
            "render_recovery_session_host_verdict_summary_contract_check",
            "compare_recovery_session_host_verdict_summary_checks",
            "render_recovery_session_host_verdict_summary_comparison",
            "recovery_session_host_cli",
            "recovery_session_host_verdict_aggregator",
            "recovery_session_host_verdict_summary",
            "recovery_session_host_verdict_summary_manifest",
            "recovery_session_host_verdict_summary_comparator",
            "sqlite3",
            "open_connection",
            "apply_migrations",
            "KernelUnitOfWork",
        )
        for marker in forbidden_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_acceptance_digest_contract_summary_for_ci_display(self) -> None:
        rendered_check, rendered_comparison = (
            self._safe_real_rendered_check_and_comparison()
        )
        cross_phase = build_recovery_session_host_verdict_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )
        rendered_digest = (
            render_recovery_session_host_verdict_cross_phase_digest(
                cross_phase
            )
        )
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)
        display = {
            "phase": (
                "recovery_session_host_verdict_cross_phase_digest"
            ),
            "cross_phase_ok": digest["cross_phase_ok"],
            "operator_safe": digest["operator_safe"],
            "contract_ready": digest["contract_ready"],
            "comparison_ok": digest["comparison_ok"],
            "has_drift": digest["has_drift"],
            "has_contract_failure": digest["has_contract_failure"],
            "has_runtime_dependencies": digest[
                "has_runtime_dependencies"
            ],
            "has_cli_commands": digest["has_cli_commands"],
            "has_restore_or_durable_surface": digest[
                "has_restore_or_durable_surface"
            ],
        }

        self.assertEqual(
            display["phase"],
            "recovery_session_host_verdict_cross_phase_digest",
        )
        self.assertIs(display["cross_phase_ok"], True)
        self.assertIs(display["operator_safe"], True)
        self.assertIs(display["contract_ready"], True)
        self.assertIs(display["comparison_ok"], True)
        self.assertIs(display["has_drift"], False)
        self.assertIs(display["has_contract_failure"], False)
        self.assertIs(display["has_runtime_dependencies"], False)
        self.assertIs(display["has_cli_commands"], False)
        self.assertIs(display["has_restore_or_durable_surface"], False)
        _json_round_trips(display)


if __name__ == "__main__":
    unittest.main()
