"""
P0-41 phase 1 - RecoverySessionHost verdict summary comparator acceptance pack.

These tests prove the read-only comparator consumes realistic rendered
contract-check payloads derived from the frozen operator surface,
aggregation, summary, and manifest check pipeline.
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
from kernel.lifecycle.recovery_session_host_verdict_summary import (
    build_recovery_session_host_verdict_summary,
    render_recovery_session_host_verdict_summary,
)
from kernel.lifecycle.recovery_session_host_verdict_summary_comparator import (
    RecoverySessionHostVerdictSummaryComparison,
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


def _json_round_trips(payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    if json.loads(encoded) != payload:
        raise AssertionError("payload did not round-trip through JSON")


def _relative_files(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(str(path.relative_to(root)) for path in root.rglob("*"))
    )


def _change_fields(
    comparison: RecoverySessionHostVerdictSummaryComparison,
) -> list[str]:
    changes = comparison.report["changes"]
    if not isinstance(changes, list):
        raise AssertionError("comparison changes must be a list")
    fields: list[str] = []
    for change in changes:
        if not isinstance(change, dict):
            raise AssertionError(f"change must be a dict: {change!r}")
        field = change.get("field")
        if not isinstance(field, str):
            raise AssertionError(f"change field must be a string: {change!r}")
        fields.append(field)
    return fields


def _source_without_self_referential_api_names() -> str:
    source = inspect.getsource(comparator_module)
    return (
        source.replace(
            "compare_recovery_session_host_verdict_summary_checks",
            "compare_checks",
        )
        .replace(
            "render_recovery_session_host_verdict_summary_comparison",
            "render_comparison",
        )
    )


class TestRecoverySessionHostVerdictSummaryComparatorAcceptance(
    unittest.TestCase
):
    """Acceptance coverage for real rendered manifest check consumption."""

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

    def test_acceptance_comparator_accepts_identical_real_rendered_checks(
        self,
    ) -> None:
        rendered_check = self._real_rendered_check()
        before = copy.deepcopy(rendered_check)
        after = copy.deepcopy(rendered_check)

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            )
        )
        report = rendered_comparison["report"]
        self.assertIsInstance(report, dict)

        self.assertIs(comparison.ok, True)
        self.assertEqual(comparison.reason_code, "ok")
        self.assertEqual(comparison.failures, ())
        self.assertIs(report["comparison_ok"], True)
        self.assertIs(report["changed"], False)
        self.assertEqual(report["change_count"], 0)
        self.assertEqual(report["changes"], [])
        _json_round_trips(rendered_comparison)

    def test_acceptance_comparator_detects_real_check_ready_status_drift(
        self,
    ) -> None:
        before = self._real_rendered_check()
        after = copy.deepcopy(before)
        after["ready"] = False
        after["reason_code"] = "not_ready"
        after["failures"] = ["digest_shape_mismatch"]

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )

        self.assertIs(comparison.ok, True)
        self.assertIs(comparison.report["changed"], True)
        self.assertEqual(
            _change_fields(comparison),
            ["ready", "reason_code", "failures"],
        )

    def test_acceptance_comparator_detects_manifest_contract_drift(
        self,
    ) -> None:
        before = self._real_rendered_check()
        after = copy.deepcopy(before)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        manifest["version"] = version + 1
        manifest["restore_supported"] = True
        manifest["durable_writes"] = True
        manifest["cli_commands"] = ["status"]
        manifest["runtime_dependencies"] = ["sqlite3"]
        top_level_keys = manifest["top_level_keys"]
        digest_keys = manifest["digest_keys"]
        self.assertIsInstance(top_level_keys, list)
        self.assertIsInstance(digest_keys, list)
        manifest["top_level_keys"] = list(top_level_keys) + ["x"]
        if digest_keys:
            manifest["digest_keys"] = list(digest_keys[:-1])

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )

        self.assertIs(comparison.ok, True)
        self.assertIs(comparison.report["changed"], True)
        self.assertEqual(
            _change_fields(comparison),
            [
                "manifest.version",
                "manifest.restore_supported",
                "manifest.durable_writes",
                "manifest.cli_commands",
                "manifest.runtime_dependencies",
                "manifest.top_level_keys",
                "manifest.digest_keys",
            ],
        )

    def test_acceptance_comparator_rejects_malformed_real_check_payloads(
        self,
    ) -> None:
        real_check = self._real_rendered_check()
        before = copy.deepcopy(real_check)
        before["extra"] = True
        after = copy.deepcopy(real_check)
        after["manifest"] = "bad"

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        rendered = render_recovery_session_host_verdict_summary_comparison(
            comparison
        )
        report = rendered["report"]
        self.assertIsInstance(report, dict)

        self.assertIs(comparison.ok, False)
        self.assertEqual(comparison.reason_code, "invalid_comparison")
        self.assertIn("before_shape_mismatch", comparison.failures)
        self.assertIn("after_manifest_invalid", comparison.failures)
        self.assertIs(report["comparison_ok"], False)
        self.assertIsNone(report["changed"])
        self.assertEqual(report["changes"], [])
        _json_round_trips(rendered)

    def test_acceptance_comparator_preserves_read_only_runtime_boundary(
        self,
    ) -> None:
        db_path, task_id = self._seeded_db()
        before_counts = _table_row_counts(db_path)

        payloads, _by_name, missing_path = _collect_real_operator_payloads(
            tmpdir=self.tmpdir,
            db_path=db_path,
            task_id=task_id,
        )
        rendered_check = _render_check_from_payloads(list(payloads))
        files_before_compare = _relative_files(self.tmpdir)

        comparison = compare_recovery_session_host_verdict_summary_checks(
            rendered_check, copy.deepcopy(rendered_check)
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            )
        )

        self.assertEqual(_table_row_counts(db_path), before_counts)
        self.assertFalse(missing_path.exists())
        self.assertEqual(_relative_files(self.tmpdir), files_before_compare)
        self.assertIs(comparison.ok, True)
        _json_round_trips(rendered_comparison)

    def test_acceptance_comparator_handles_valid_failure_check_payloads(
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
        self.assertEqual(rendered_check["reason_code"], "ready")

        comparison = compare_recovery_session_host_verdict_summary_checks(
            rendered_check, copy.deepcopy(rendered_check)
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            )
        )
        report = rendered_comparison["report"]
        self.assertIsInstance(report, dict)
        before_report = report["before"]
        self.assertIsInstance(before_report, dict)

        self.assertIs(comparison.ok, True)
        self.assertIs(report["changed"], False)
        self.assertIs(before_report["ready"], True)
        self.assertEqual(before_report["reason_code"], "ready")
        _json_round_trips(rendered_comparison)

    def test_acceptance_comparator_output_has_no_runtime_repr_leakage(
        self,
    ) -> None:
        before = self._real_rendered_check()
        after = copy.deepcopy(before)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        manifest["version"] = version + 1

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        rendered = render_recovery_session_host_verdict_summary_comparison(
            comparison
        )

        _assert_json_safe_no_runtime_types(rendered)
        _assert_no_runtime_repr_strings(rendered)

    def test_acceptance_comparator_does_not_call_manifest_summary_aggregator_or_operator_runtime(
        self,
    ) -> None:
        before = self._real_rendered_check()
        after = copy.deepcopy(before)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        manifest["version"] = version + 1

        with (
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
            comparison = compare_recovery_session_host_verdict_summary_checks(
                before, after
            )
            rendered = render_recovery_session_host_verdict_summary_comparison(
                comparison
            )

        self.assertIs(comparison.ok, True)
        self.assertIs(rendered["ok"], True)
        _json_round_trips(rendered)

    def test_acceptance_comparator_no_restore_or_command_creep(self) -> None:
        public_function_names = {
            name
            for name, value in comparator_module.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(value)
        }
        for name in public_function_names:
            with self.subTest(name=name):
                self.assertNotIn("restore", name)

        source = _source_without_self_referential_api_names()
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
            "recovery_session_host_cli",
            "recovery_session_host_verdict_aggregator",
            "recovery_session_host_verdict_summary",
            "recovery_session_host_verdict_summary_manifest",
            "sqlite3",
            "open_connection",
            "apply_migrations",
            "KernelUnitOfWork",
        )
        for marker in forbidden_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_acceptance_comparator_contract_summary_for_ci_display(
        self,
    ) -> None:
        before = self._real_rendered_check()
        after = copy.deepcopy(before)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        manifest["version"] = version + 1

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            )
        )
        report = rendered_comparison["report"]
        self.assertIsInstance(report, dict)
        before_report = report["before"]
        after_report = report["after"]
        self.assertIsInstance(before_report, dict)
        self.assertIsInstance(after_report, dict)
        display = {
            "phase": "recovery_session_host_verdict_summary_comparator",
            "comparison_ok": report["comparison_ok"],
            "changed": report["changed"],
            "change_count": report["change_count"],
            "before_ready": before_report["ready"],
            "after_ready": after_report["ready"],
            "before_reason_code": before_report["reason_code"],
            "after_reason_code": after_report["reason_code"],
        }

        self.assertEqual(
            display["phase"],
            "recovery_session_host_verdict_summary_comparator",
        )
        self.assertIs(display["comparison_ok"], True)
        self.assertIs(display["changed"], True)
        self.assertEqual(display["change_count"], 1)
        self.assertEqual(display["before_ready"], display["after_ready"])
        _json_round_trips(display)


if __name__ == "__main__":
    unittest.main()
