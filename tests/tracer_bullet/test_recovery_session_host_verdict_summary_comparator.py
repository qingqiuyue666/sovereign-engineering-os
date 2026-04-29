"""P0-40 RecoverySessionHost verdict summary comparator tests."""

from __future__ import annotations

import copy
import inspect
import json
import unittest
from unittest import mock

from kernel.lifecycle import (
    recovery_session_host_verdict_summary_comparator as comparator_module,
)
from kernel.lifecycle.recovery_session_host_verdict_summary_comparator import (
    RecoverySessionHostVerdictSummaryComparison,
    compare_recovery_session_host_verdict_summary_checks,
    render_recovery_session_host_verdict_summary_comparison,
)


_RUNTIME_DEPENDENCY_NAMES = {
    "sqlite3",
    "recovery_session_host_cli",
    "recovery_session_host_verdict_aggregator",
    "recovery_session_host_verdict_summary",
    "recovery_session_host_verdict_summary_manifest",
    "recovery_cli",
    "RecoverySessionHost",
    "RecoveryGate",
    "SignablePathOrchestrator",
    "KernelUnitOfWork",
    "build_parser",
    "main",
    "try_build_recovery_session_host_from_sqlite",
    "aggregate_recovery_session_host_operator_verdicts",
    "build_recovery_session_host_verdict_summary",
    "check_recovery_session_host_verdict_summary_contract",
}
_RUNTIME_CALL_STRINGS = {
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "KernelUnitOfWork",
    "open_connection",
    "sqlite3",
    "apply_migrations",
    "build_parser",
    "try_build_recovery_session_host_from_sqlite",
    "aggregate_recovery_session_host_operator_verdicts",
    "build_recovery_session_host_verdict_summary",
    "check_recovery_session_host_verdict_summary_contract",
    "recovery_session_host_cli",
}


def _rendered_check(
    *,
    ready: bool = True,
    reason_code: str = "ready",
    failures: list[str] | None = None,
    manifest: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "ready": ready,
        "reason_code": reason_code,
        "failures": [] if failures is None else failures,
        "manifest": _manifest() if manifest is None else manifest,
    }


def _manifest(
    *,
    surface: str = "recovery_session_host_verdict_summary",
    version: int = 1,
    top_level_keys: list[str] | None = None,
    digest_keys: list[str] | None = None,
    restore_supported: bool = False,
    durable_writes: bool = False,
    cli_commands: list[str] | None = None,
    runtime_dependencies: list[str] | None = None,
) -> dict[str, object]:
    return {
        "surface": surface,
        "version": version,
        "top_level_keys": ["digest", "failures", "ok", "reason_code"]
        if top_level_keys is None
        else top_level_keys,
        "digest_keys": ["aggregation_ok", "operator_safe"]
        if digest_keys is None
        else digest_keys,
        "restore_supported": restore_supported,
        "durable_writes": durable_writes,
        "cli_commands": [] if cli_commands is None else cli_commands,
        "runtime_dependencies": []
        if runtime_dependencies is None
        else runtime_dependencies,
    }


def _assert_json_round_trips(
    test_case: unittest.TestCase,
    payload: dict[str, object],
) -> None:
    test_case.assertEqual(json.loads(json.dumps(payload)), payload)


def _change_fields(comparison: RecoverySessionHostVerdictSummaryComparison) -> list[str]:
    return [change["field"] for change in comparison.report["changes"]]


def _recursive_values(payload: object) -> list[object]:
    values = [payload]
    if isinstance(payload, dict):
        for key, value in payload.items():
            values.extend(_recursive_values(key))
            values.extend(_recursive_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_recursive_values(value))
    return values


class TestRecoverySessionHostVerdictSummaryComparator(unittest.TestCase):
    def test_comparator_accepts_identical_ready_checks(self) -> None:
        before = _rendered_check()
        after = copy.deepcopy(before)

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )

        self.assertIs(comparison.ok, True)
        self.assertEqual(comparison.reason_code, "ok")
        self.assertEqual(comparison.failures, ())
        self.assertIs(comparison.report["comparison_ok"], True)
        self.assertIs(comparison.report["changed"], False)
        self.assertEqual(comparison.report["change_count"], 0)
        self.assertEqual(comparison.report["changes"], [])
        _assert_json_round_trips(
            self,
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            ),
        )

    def test_comparator_detects_ready_flip(self) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(ready=True),
            _rendered_check(ready=False),
        )

        self.assertEqual(
            comparison.report["changes"],
            [{"field": "ready", "before": True, "after": False}],
        )

    def test_comparator_detects_reason_code_change(self) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(reason_code="ready"),
            _rendered_check(reason_code="not_ready"),
        )

        self.assertEqual(_change_fields(comparison), ["reason_code"])

    def test_comparator_detects_failures_change(self) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(failures=[]),
            _rendered_check(failures=["digest_shape_mismatch"]),
        )

        self.assertEqual(_change_fields(comparison), ["failures"])
        self.assertEqual(
            comparison.report["changes"][0]["after"],
            ["digest_shape_mismatch"],
        )

    def test_comparator_detects_manifest_surface_change(self) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(manifest=_manifest(surface="surface-a")),
            _rendered_check(manifest=_manifest(surface="surface-b")),
        )

        self.assertEqual(_change_fields(comparison), ["manifest.surface"])

    def test_comparator_detects_manifest_version_change(self) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(manifest=_manifest(version=1)),
            _rendered_check(manifest=_manifest(version=2)),
        )

        self.assertEqual(_change_fields(comparison), ["manifest.version"])

    def test_comparator_detects_restore_and_durable_declaration_changes(
        self,
    ) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(
                manifest=_manifest(
                    restore_supported=False,
                    durable_writes=False,
                )
            ),
            _rendered_check(
                manifest=_manifest(
                    restore_supported=True,
                    durable_writes=True,
                )
            ),
        )

        self.assertEqual(
            _change_fields(comparison),
            [
                "manifest.restore_supported",
                "manifest.durable_writes",
            ],
        )

    def test_comparator_detects_cli_and_runtime_dependency_changes(
        self,
    ) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(
                manifest=_manifest(
                    cli_commands=[],
                    runtime_dependencies=[],
                )
            ),
            _rendered_check(
                manifest=_manifest(
                    cli_commands=["status"],
                    runtime_dependencies=["sqlite3"],
                )
            ),
        )

        self.assertEqual(
            _change_fields(comparison),
            [
                "manifest.cli_commands",
                "manifest.runtime_dependencies",
            ],
        )

    def test_comparator_detects_key_contract_changes(self) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(
                manifest=_manifest(
                    top_level_keys=[
                        "digest",
                        "failures",
                        "ok",
                        "reason_code",
                    ],
                    digest_keys=["aggregation_ok", "operator_safe"],
                )
            ),
            _rendered_check(
                manifest=_manifest(
                    top_level_keys=[
                        "digest",
                        "failures",
                        "ok",
                        "reason_code",
                        "x",
                    ],
                    digest_keys=["aggregation_ok"],
                )
            ),
        )

        self.assertEqual(
            _change_fields(comparison),
            ["manifest.top_level_keys", "manifest.digest_keys"],
        )

    def test_comparator_change_order_is_fixed(self) -> None:
        before = _rendered_check(
            ready=True,
            reason_code="ready",
            failures=[],
            manifest=_manifest(
                surface="before",
                version=1,
                restore_supported=False,
                durable_writes=False,
                cli_commands=[],
                runtime_dependencies=[],
                top_level_keys=["digest", "failures", "ok", "reason_code"],
                digest_keys=["aggregation_ok", "operator_safe"],
            ),
        )
        after = _rendered_check(
            manifest=_manifest(
                digest_keys=["aggregation_ok"],
                top_level_keys=[
                    "digest",
                    "failures",
                    "ok",
                    "reason_code",
                    "x",
                ],
                runtime_dependencies=["sqlite3"],
                cli_commands=["status"],
                durable_writes=True,
                restore_supported=True,
                version=2,
                surface="after",
            ),
            failures=["digest_shape_mismatch"],
            reason_code="not_ready",
            ready=False,
        )

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )

        self.assertEqual(
            _change_fields(comparison),
            [
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
            ],
        )

    def test_comparator_rejects_non_mapping_inputs(self) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            "bad", "bad"
        )

        self.assertIs(comparison.ok, False)
        self.assertEqual(comparison.reason_code, "invalid_comparison")
        self.assertEqual(
            comparison.failures,
            ("before_not_mapping", "after_not_mapping"),
        )
        self.assertEqual(
            comparison.report,
            {
                "comparison_ok": False,
                "reason_code": "invalid_comparison",
                "failures": ["before_not_mapping", "after_not_mapping"],
                "changed": None,
                "change_count": 0,
                "changes": [],
            },
        )

    def test_comparator_rejects_top_level_shape_mismatch(self) -> None:
        before = _rendered_check()
        before["extra"] = True
        after = _rendered_check()
        del after["manifest"]

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )

        self.assertIn("before_shape_mismatch", comparison.failures)
        self.assertIn("after_shape_mismatch", comparison.failures)

    def test_comparator_rejects_invalid_failures_lists(self) -> None:
        before = _rendered_check(failures=["x", 1])
        after = _rendered_check()
        after["failures"] = "bad"

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )

        self.assertIn("before_failures_invalid", comparison.failures)
        self.assertIn("after_failures_invalid", comparison.failures)

    def test_comparator_rejects_invalid_manifest_objects(self) -> None:
        before = _rendered_check()
        before["manifest"] = "bad"
        after = _rendered_check()
        after["manifest"] = "bad"

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )

        self.assertIn("before_manifest_invalid", comparison.failures)
        self.assertIn("after_manifest_invalid", comparison.failures)

    def test_comparator_rejects_manifest_shape_mismatch(self) -> None:
        before = _rendered_check(manifest=_manifest())
        before["manifest"]["version"] = True
        after = _rendered_check(manifest=_manifest())
        after["manifest"]["cli_commands"] = [1]

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )

        self.assertIn("before_manifest_shape_mismatch", comparison.failures)
        self.assertIn("after_manifest_shape_mismatch", comparison.failures)

    def test_comparator_failure_order_is_deterministic(self) -> None:
        before = _rendered_check(
            ready=True,
            reason_code="ready",
            failures=[],
            manifest={"surface": 1},
        )
        before["extra"] = True
        before["failures"] = "bad"
        after = _rendered_check(
            ready=True,
            reason_code="ready",
            failures=[],
            manifest={"version": True},
        )
        after["extra"] = True
        after["failures"] = [1]

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )

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

    def test_comparator_valid_inputs_with_changes_are_still_ok(self) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(ready=True),
            _rendered_check(ready=False),
        )

        self.assertIs(comparison.ok, True)
        self.assertIs(comparison.report["comparison_ok"], True)
        self.assertIs(comparison.report["changed"], True)
        self.assertGreater(comparison.report["change_count"], 0)
        self.assertEqual(comparison.failures, ())

    def test_comparator_does_not_mutate_inputs(self) -> None:
        before = _rendered_check()
        after = _rendered_check(ready=False)
        original_before = copy.deepcopy(before)
        original_after = copy.deepcopy(after)

        comparison = compare_recovery_session_host_verdict_summary_checks(
            before, after
        )
        render_recovery_session_host_verdict_summary_comparison(comparison)

        self.assertEqual(before, original_before)
        self.assertEqual(after, original_after)

    def test_comparator_render_returns_defensive_report(self) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(ready=True),
            _rendered_check(ready=False),
        )

        rendered = render_recovery_session_host_verdict_summary_comparison(
            comparison
        )
        rendered["report"]["changes"].append(
            {"field": "x", "before": None, "after": None}
        )
        rendered_again = (
            render_recovery_session_host_verdict_summary_comparison(
                comparison
            )
        )

        self.assertNotIn(
            {"field": "x", "before": None, "after": None},
            comparison.report["changes"],
        )
        self.assertNotIn(
            {"field": "x", "before": None, "after": None},
            rendered_again["report"]["changes"],
        )

    def test_comparator_render_does_not_call_compare(self) -> None:
        comparison = RecoverySessionHostVerdictSummaryComparison(
            ok=True,
            reason_code="ok",
            failures=(),
            report={
                "comparison_ok": True,
                "reason_code": "ok",
                "failures": [],
                "changed": False,
                "change_count": 0,
                "changes": [],
            },
        )

        with mock.patch.object(
            comparator_module,
            "compare_recovery_session_host_verdict_summary_checks",
            side_effect=AssertionError("compare called"),
        ):
            rendered = (
                render_recovery_session_host_verdict_summary_comparison(
                    comparison
                )
            )

        self.assertIs(rendered["ok"], True)

    def test_comparator_output_json_safe_and_no_runtime_repr(self) -> None:
        comparison = compare_recovery_session_host_verdict_summary_checks(
            _rendered_check(ready=True),
            _rendered_check(ready=False),
        )
        rendered = render_recovery_session_host_verdict_summary_comparison(
            comparison
        )

        _assert_json_round_trips(self, rendered)
        values = _recursive_values(rendered)
        self.assertFalse(
            any(isinstance(value, (set, frozenset, tuple)) for value in values)
        )
        forbidden_strings = (
            "object at 0x",
            "sqlite3.Connection",
            "RecoverySessionHost",
            "<kernel.",
            "<sqlite3.",
        )
        for value in values:
            if isinstance(value, str):
                for text in forbidden_strings:
                    with self.subTest(value=value, text=text):
                        self.assertNotIn(text, value)

    def test_comparator_module_has_no_runtime_dependencies(self) -> None:
        for name in _RUNTIME_DEPENDENCY_NAMES:
            with self.subTest(name=name):
                self.assertNotIn(name, comparator_module.__dict__)

    def test_comparator_source_has_no_runtime_call_strings(self) -> None:
        source = inspect.getsource(comparator_module)

        for text in _RUNTIME_CALL_STRINGS:
            with self.subTest(text=text):
                self.assertNotIn(text, source)

    def test_comparator_public_api_is_exact(self) -> None:
        public_api = {
            name
            for name, value in inspect.getmembers(comparator_module)
            if not name.startswith("_")
            and getattr(value, "__module__", None) == comparator_module.__name__
            and (inspect.isclass(value) or inspect.isfunction(value))
        }

        self.assertEqual(
            public_api,
            {
                "RecoverySessionHostVerdictSummaryComparison",
                "compare_recovery_session_host_verdict_summary_checks",
                "render_recovery_session_host_verdict_summary_comparison",
            },
        )
