"""
P0-42 phase 1 - RecoverySessionHost verdict summary comparator checkpoint.

These tests pin the verdict summary comparator boundary as a frozen
read-only drift-report surface over realistic rendered contract-check
payloads.
"""

from __future__ import annotations

import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from kernel.lifecycle import (
    recovery_session_host_verdict_summary_comparator as comparator_module,
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


_EXPECTED_PUBLIC_API = {
    "RecoverySessionHostVerdictSummaryComparison",
    "compare_recovery_session_host_verdict_summary_checks",
    "render_recovery_session_host_verdict_summary_comparison",
}

_FORBIDDEN_RUNTIME_REFERENCES = (
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
    "recovery_cli",
    "sqlite3",
    "open_connection",
    "apply_migrations",
    "KernelUnitOfWork",
)

_EXPECTED_COMPARISON_FIELDS = [
    "ready",
    "reason_code",
    "failures",
    "manifest.surface",
    "manifest.version",
    "manifest.restore_supported",
    "manifest.durable_writes",
    "manifest.cli_commands",
    "manifest.runtime_dependencies",
    "manifest.top_level_keys",
    "manifest.digest_keys",
]


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


def _seeded_db(tmpdir: Path) -> tuple[Path, str]:
    db_path = tmpdir / "factory.db"
    task_id = f"task-{uuid4().hex[:8]}"
    _initialize_empty_db(db_path)
    _seed_inference_stage(db_path, task_id)
    return db_path, task_id


def _collect_real_operator_payloads(
    *,
    tmpdir: Path,
    db_path: Path,
    task_id: str,
) -> tuple[list[dict[str, object]], Path]:
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
    for name, argv, expected_code in cases:
        payloads.append(
            _invoke_json_payload(
                argv,
                expected_code=expected_code,
                name=name,
            )
        )

    payloads.append(current_recovery_session_host_cli_readiness_payload())
    payloads.append(
        render_recovery_session_host_cli_readiness_smoke(
            current_recovery_session_host_cli_readiness_smoke()
        )
    )
    return payloads, missing_path


def _render_check_from_payloads(
    payloads: list[object],
) -> dict[str, object]:
    aggregation = aggregate_recovery_session_host_operator_verdicts(payloads)
    rendered_aggregation = render_recovery_session_host_verdict_aggregation(
        aggregation
    )
    summary = build_recovery_session_host_verdict_summary(
        rendered_aggregation
    )
    rendered_summary = render_recovery_session_host_verdict_summary(summary)
    check = check_recovery_session_host_verdict_summary_contract(
        rendered_summary
    )
    return render_recovery_session_host_verdict_summary_contract_check(check)


def _real_rendered_check(
    tmpdir: Path,
) -> tuple[dict[str, object], Path, Path]:
    db_path, task_id = _seeded_db(tmpdir)
    payloads, missing_path = _collect_real_operator_payloads(
        tmpdir=tmpdir,
        db_path=db_path,
        task_id=task_id,
    )
    rendered_check = _render_check_from_payloads(list(payloads))
    return rendered_check, db_path, missing_path


def _json_round_trips(payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    if json.loads(encoded) != payload:
        raise AssertionError("payload did not round-trip through JSON")


def _relative_files(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(str(path.relative_to(root)) for path in root.rglob("*"))
    )


def _change_fields(rendered_comparison: dict[str, object]) -> list[str]:
    report = rendered_comparison["report"]
    if not isinstance(report, dict):
        raise AssertionError("rendered comparison report must be a dict")
    changes = report["changes"]
    if not isinstance(changes, list):
        raise AssertionError("rendered comparison changes must be a list")
    fields: list[str] = []
    for change in changes:
        if not isinstance(change, dict):
            raise AssertionError(f"change must be a dict: {change!r}")
        field = change.get("field")
        if not isinstance(field, str):
            raise AssertionError(f"change field must be a string: {change!r}")
        fields.append(field)
    return fields


def _comparator_source_without_self_referential_api_names() -> str:
    source = inspect.getsource(comparator_module)
    return (
        source.replace(
            "compare_recovery_session_host_verdict_summary_checks",
            "_compare_checks_self",
        )
        .replace(
            "render_recovery_session_host_verdict_summary_comparison",
            "_render_comparison_self",
        )
    )


class TestRecoverySessionHostVerdictSummaryComparatorPhaseCheckpoint(
    unittest.TestCase
):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_phase_checkpoint_comparator_boundary_is_frozen_read_only(
        self,
    ) -> None:
        rendered_check, _db_path, _missing_path = _real_rendered_check(
            self.tmpdir
        )
        before = copy.deepcopy(rendered_check)
        after = copy.deepcopy(rendered_check)

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(comparison)
        )

        self.assertIs(comparison.ok, True)
        self.assertEqual(comparison.reason_code, "ok")
        self.assertEqual(comparison.failures, ())
        self.assertEqual(
            set(rendered_comparison.keys()),
            {"ok", "reason_code", "failures", "report"},
        )
        report = rendered_comparison["report"]
        self.assertIsInstance(report, dict)
        self.assertIs(report["comparison_ok"], True)
        self.assertIs(report["changed"], False)
        self.assertEqual(report["change_count"], 0)
        self.assertEqual(report["changes"], [])
        _json_round_trips(rendered_comparison)

    def test_phase_checkpoint_comparator_boundary_has_no_runtime_mutation_paths(
        self,
    ) -> None:
        db_path, task_id = _seeded_db(self.tmpdir)
        before_counts = _table_row_counts(db_path)

        payloads, missing_path = _collect_real_operator_payloads(
            tmpdir=self.tmpdir,
            db_path=db_path,
            task_id=task_id,
        )
        rendered_check = _render_check_from_payloads(list(payloads))
        files_before_compare = _relative_files(self.tmpdir)

        comparison = compare_recovery_session_host_verdict_summary_checks(
            rendered_check, copy.deepcopy(rendered_check)
        )
        render_recovery_session_host_verdict_summary_comparison(comparison)

        self.assertEqual(_table_row_counts(db_path), before_counts)
        self.assertFalse(missing_path.exists())
        self.assertEqual(_relative_files(self.tmpdir), files_before_compare)

    def test_phase_checkpoint_comparator_compared_field_set_is_frozen(
        self,
    ) -> None:
        rendered_check, _db_path, _missing_path = _real_rendered_check(
            self.tmpdir
        )
        before = copy.deepcopy(rendered_check)
        after = copy.deepcopy(rendered_check)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        top_level_keys = manifest["top_level_keys"]
        digest_keys = manifest["digest_keys"]
        self.assertIsInstance(top_level_keys, list)
        self.assertIsInstance(digest_keys, list)

        after["ready"] = not after["ready"]
        after["reason_code"] = "drift_reason_code"
        after["failures"] = ["digest_shape_mismatch"]
        manifest["surface"] = manifest["surface"] + "_drift"
        manifest["version"] = version + 1
        manifest["restore_supported"] = not manifest["restore_supported"]
        manifest["durable_writes"] = not manifest["durable_writes"]
        manifest["cli_commands"] = ["status"]
        manifest["runtime_dependencies"] = ["sqlite3"]
        manifest["top_level_keys"] = list(top_level_keys) + ["x"]
        manifest["digest_keys"] = list(digest_keys) + ["y"]

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(comparison)
        )

        self.assertIs(comparison.ok, True)
        self.assertEqual(
            _change_fields(rendered_comparison),
            _EXPECTED_COMPARISON_FIELDS,
        )

    def test_phase_checkpoint_comparator_validation_failure_order_is_frozen(
        self,
    ) -> None:
        before: dict[str, object] = {
            "ready": True,
            "reason_code": "ready",
            "failures": "bad",
            "manifest": {"surface": 1},
            "extra": True,
        }
        after: dict[str, object] = {
            "ready": True,
            "reason_code": "ready",
            "failures": [1],
            "manifest": {"version": True},
            "extra": True,
        }

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )

        self.assertIs(comparison.ok, False)
        self.assertEqual(comparison.reason_code, "invalid_comparison")
        self.assertEqual(
            comparison.failures,
            (
                "before_shape_mismatch",
                "after_shape_mismatch",
                "before_failures_invalid",
                "after_failures_invalid",
                "before_manifest_shape_mismatch",
                "after_manifest_shape_mismatch",
            ),
        )

        non_mapping_comparison = (
            compare_recovery_session_host_verdict_summary_checks("bad", "bad")
        )
        self.assertIs(non_mapping_comparison.ok, False)
        self.assertEqual(
            non_mapping_comparison.failures,
            ("before_not_mapping", "after_not_mapping"),
        )

    def test_phase_checkpoint_comparator_invalid_report_shape_is_frozen(
        self,
    ) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            "bad", "bad"
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(comparison)
        )

        self.assertIs(comparison.ok, False)
        self.assertEqual(comparison.reason_code, "invalid_comparison")
        report = rendered_comparison["report"]
        self.assertIsInstance(report, dict)
        self.assertEqual(
            set(report.keys()),
            {
                "comparison_ok",
                "reason_code",
                "failures",
                "changed",
                "change_count",
                "changes",
            },
        )
        self.assertIs(report["comparison_ok"], False)
        self.assertEqual(report["reason_code"], "invalid_comparison")
        self.assertIsNone(report["changed"])
        self.assertEqual(report["change_count"], 0)
        self.assertEqual(report["changes"], [])
        _json_round_trips(rendered_comparison)

    def test_phase_checkpoint_comparator_valid_report_shape_is_frozen(
        self,
    ) -> None:
        rendered_check, _db_path, _missing_path = _real_rendered_check(
            self.tmpdir
        )
        before = copy.deepcopy(rendered_check)
        after = copy.deepcopy(rendered_check)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        manifest["version"] = version + 1

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(comparison)
        )

        self.assertIs(comparison.ok, True)
        report = rendered_comparison["report"]
        self.assertIsInstance(report, dict)
        self.assertEqual(
            set(report.keys()),
            {
                "comparison_ok",
                "reason_code",
                "failures",
                "changed",
                "change_count",
                "changes",
                "before",
                "after",
            },
        )
        self.assertIs(report["comparison_ok"], True)
        self.assertEqual(report["reason_code"], "ok")
        self.assertEqual(report["failures"], [])
        self.assertIs(report["changed"], True)
        self.assertEqual(report["change_count"], 1)
        before_report = report["before"]
        after_report = report["after"]
        self.assertIsInstance(before_report, dict)
        self.assertIsInstance(after_report, dict)
        expected_summary_keys = {
            "ready",
            "reason_code",
            "failure_count",
            "manifest_surface",
            "manifest_version",
        }
        self.assertEqual(set(before_report.keys()), expected_summary_keys)
        self.assertEqual(set(after_report.keys()), expected_summary_keys)
        _json_round_trips(rendered_comparison)

    def test_phase_checkpoint_comparator_valid_changed_inputs_remain_ok(
        self,
    ) -> None:
        rendered_check, _db_path, _missing_path = _real_rendered_check(
            self.tmpdir
        )
        before = copy.deepcopy(rendered_check)
        after = copy.deepcopy(rendered_check)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)

        after["ready"] = False
        after["reason_code"] = "not_ready"
        after["failures"] = ["digest_shape_mismatch"]
        manifest["version"] = version + 1

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(comparison)
        )

        self.assertIs(comparison.ok, True)
        self.assertEqual(comparison.failures, ())
        report = rendered_comparison["report"]
        self.assertIsInstance(report, dict)
        self.assertIs(report["comparison_ok"], True)
        self.assertIs(report["changed"], True)
        self.assertEqual(report["change_count"], 4)

    def test_phase_checkpoint_comparator_check_output_is_json_safe_and_defensive(
        self,
    ) -> None:
        rendered_check, _db_path, _missing_path = _real_rendered_check(
            self.tmpdir
        )
        before = copy.deepcopy(rendered_check)
        after = copy.deepcopy(rendered_check)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        manifest["version"] = version + 1

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(comparison)
        )
        expected_rendered = copy.deepcopy(rendered_comparison)

        _json_round_trips(rendered_comparison)
        _assert_json_safe_no_runtime_types(rendered_comparison)
        _assert_no_runtime_repr_strings(rendered_comparison)

        rendered_comparison["report"]["changes"].append(
            {"field": "x", "before": None, "after": None}
        )
        fresh_rendered = (
            render_recovery_session_host_verdict_summary_comparison(comparison)
        )

        self.assertNotIn(
            {"field": "x", "before": None, "after": None},
            comparison.report["changes"],
        )
        self.assertEqual(fresh_rendered, expected_rendered)

    def test_phase_checkpoint_comparator_surface_public_api_is_frozen(
        self,
    ) -> None:
        public_api = {
            name
            for name, value in inspect.getmembers(comparator_module)
            if not name.startswith("_")
            and getattr(value, "__module__", None) == comparator_module.__name__
            and (inspect.isclass(value) or inspect.isfunction(value))
        }

        self.assertEqual(public_api, _EXPECTED_PUBLIC_API)

    def test_phase_checkpoint_comparator_surface_has_no_forbidden_runtime_references(
        self,
    ) -> None:
        public_function_names = {
            name
            for name, value in comparator_module.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(value)
        }
        for name in public_function_names:
            with self.subTest(name=name):
                self.assertNotIn("restore", name)

        for marker in _FORBIDDEN_RUNTIME_REFERENCES:
            with self.subTest(module_dict=marker):
                self.assertNotIn(marker, comparator_module.__dict__)

        runtime_source = (
            _comparator_source_without_self_referential_api_names()
        )
        for marker in _FORBIDDEN_RUNTIME_REFERENCES:
            with self.subTest(source=marker):
                self.assertNotIn(marker, runtime_source)

    def test_phase_checkpoint_comparator_contract_summary_for_ci(
        self,
    ) -> None:
        rendered_check, _db_path, _missing_path = _real_rendered_check(
            self.tmpdir
        )
        before = copy.deepcopy(rendered_check)
        after = copy.deepcopy(rendered_check)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        manifest["version"] = version + 1

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        rendered_comparison = (
            render_recovery_session_host_verdict_summary_comparison(comparison)
        )
        report = rendered_comparison["report"]
        self.assertIsInstance(report, dict)
        before_report = report["before"]
        after_report = report["after"]
        self.assertIsInstance(before_report, dict)
        self.assertIsInstance(after_report, dict)
        checkpoint_summary = {
            "phase": (
                "recovery_session_host_verdict_summary_comparator_checkpoint"
            ),
            "comparison_ok": report["comparison_ok"],
            "changed": report["changed"],
            "change_count": report["change_count"],
            "before_ready": before_report["ready"],
            "after_ready": after_report["ready"],
            "before_reason_code": before_report["reason_code"],
            "after_reason_code": after_report["reason_code"],
        }

        self.assertEqual(
            checkpoint_summary["phase"],
            "recovery_session_host_verdict_summary_comparator_checkpoint",
        )
        self.assertIs(checkpoint_summary["comparison_ok"], True)
        self.assertIs(checkpoint_summary["changed"], True)
        self.assertEqual(checkpoint_summary["change_count"], 1)
        self.assertEqual(
            checkpoint_summary["before_ready"],
            checkpoint_summary["after_ready"],
        )
        self.assertEqual(
            checkpoint_summary["before_reason_code"],
            checkpoint_summary["after_reason_code"],
        )
        _json_round_trips(checkpoint_summary)


if __name__ == "__main__":
    unittest.main()
