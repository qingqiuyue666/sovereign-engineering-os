"""P0-43 RecoverySessionHost cross-phase verdict digest tests."""

from __future__ import annotations

import copy
import inspect
import json
import unittest
from unittest import mock

from kernel.lifecycle import (
    recovery_session_host_verdict_cross_phase_digest as digest_module,
)
from kernel.lifecycle.recovery_session_host_verdict_cross_phase_digest import (
    RecoverySessionHostVerdictCrossPhaseDigest,
    build_recovery_session_host_verdict_cross_phase_digest,
    render_recovery_session_host_verdict_cross_phase_digest,
)


_VALID_DIGEST_KEYS = {
    "cross_phase_ok",
    "reason_code",
    "failures",
    "operator_safe",
    "contract_ready",
    "contract_reason_code",
    "contract_failure_count",
    "manifest_surface",
    "manifest_version",
    "restore_supported",
    "durable_writes",
    "cli_command_count",
    "runtime_dependency_count",
    "json_safe",
    "comparison_ok",
    "comparison_reason_code",
    "comparison_failure_count",
    "comparison_changed",
    "comparison_change_count",
    "before_ready",
    "after_ready",
    "before_reason_code",
    "after_reason_code",
    "before_manifest_version",
    "after_manifest_version",
    "has_drift",
    "has_contract_failure",
    "has_runtime_dependencies",
    "has_cli_commands",
    "has_restore_or_durable_surface",
}
_INVALID_DIGEST_KEYS = {
    "cross_phase_ok",
    "reason_code",
    "failures",
    "operator_safe",
}
_RUNTIME_DEPENDENCY_NAMES = {
    "sqlite3",
    "recovery_session_host_cli",
    "recovery_session_host_verdict_aggregator",
    "recovery_session_host_verdict_summary",
    "recovery_session_host_verdict_summary_manifest",
    "recovery_session_host_verdict_summary_comparator",
    "recovery_cli",
    "RecoverySessionHost",
    "RecoveryGate",
    "SignablePathOrchestrator",
    "KernelUnitOfWork",
    "build_parser",
    "main",
    "try_build_recovery_session_host_from_sqlite",
    "aggregate_recovery_session_host_operator_verdicts",
    "render_recovery_session_host_verdict_aggregation",
    "build_recovery_session_host_verdict_summary",
    "render_recovery_session_host_verdict_summary",
    "recovery_session_host_verdict_summary_contract_manifest",
    "check_recovery_session_host_verdict_summary_contract",
    "render_recovery_session_host_verdict_summary_contract_check",
    "compare_recovery_session_host_verdict_summary_checks",
    "render_recovery_session_host_verdict_summary_comparison",
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
    "compare_recovery_session_host_verdict_summary_checks",
    "recovery_session_host_cli",
}
_RUNTIME_REPR_STRINGS = {
    "object at 0x",
    "sqlite3.Connection",
    "RecoverySessionHost",
    "<kernel.",
    "<sqlite3.",
}


def _manifest(
    *,
    surface: object = "recovery_session_host_verdict_summary",
    version: object = 1,
    restore_supported: object = False,
    durable_writes: object = False,
    cli_commands: object | None = None,
    runtime_dependencies: object | None = None,
    json_safe: object = True,
) -> dict[str, object]:
    return {
        "surface": surface,
        "version": version,
        "restore_supported": restore_supported,
        "durable_writes": durable_writes,
        "cli_commands": [] if cli_commands is None else cli_commands,
        "runtime_dependencies": []
        if runtime_dependencies is None
        else runtime_dependencies,
        "json_safe": json_safe,
    }


def _rendered_check(
    *,
    ready: object = True,
    reason_code: object = "ready",
    failures: object | None = None,
    manifest: object | None = None,
) -> dict[str, object]:
    return {
        "ready": ready,
        "reason_code": reason_code,
        "failures": [] if failures is None else failures,
        "manifest": _manifest() if manifest is None else manifest,
    }


def _summary(
    *,
    ready: object = True,
    reason_code: object = "ready",
    failure_count: object = 0,
    manifest_surface: object = "recovery_session_host_verdict_summary",
    manifest_version: object = 1,
) -> dict[str, object]:
    return {
        "ready": ready,
        "reason_code": reason_code,
        "failure_count": failure_count,
        "manifest_surface": manifest_surface,
        "manifest_version": manifest_version,
    }


def _comparison_report(
    *,
    comparison_ok: object = True,
    reason_code: object = "ok",
    failures: object | None = None,
    changed: object = False,
    change_count: object = 0,
    changes: object | None = None,
    before: object | None = None,
    after: object | None = None,
) -> dict[str, object]:
    report = {
        "comparison_ok": comparison_ok,
        "reason_code": reason_code,
        "failures": [] if failures is None else failures,
        "changed": changed,
        "change_count": change_count,
        "changes": [] if changes is None else changes,
    }
    if comparison_ok is True:
        report["before"] = _summary() if before is None else before
        report["after"] = _summary() if after is None else after
    return report


def _invalid_comparison_report(
    *,
    failures: object | None = None,
    changed: object = None,
    change_count: object = 0,
    changes: object | None = None,
) -> dict[str, object]:
    return {
        "comparison_ok": False,
        "reason_code": "invalid_comparison",
        "failures": [] if failures is None else failures,
        "changed": changed,
        "change_count": change_count,
        "changes": [] if changes is None else changes,
    }


def _rendered_comparison(
    *,
    ok: object = True,
    reason_code: object = "ok",
    failures: object | None = None,
    report: object | None = None,
) -> dict[str, object]:
    return {
        "ok": ok,
        "reason_code": reason_code,
        "failures": [] if failures is None else failures,
        "report": _comparison_report() if report is None else report,
    }


def _build_safe_digest() -> RecoverySessionHostVerdictCrossPhaseDigest:
    return build_recovery_session_host_verdict_cross_phase_digest(
        _rendered_check(),
        _rendered_comparison(),
    )


def _assert_json_round_trips(
    test_case: unittest.TestCase,
    payload: dict[str, object],
) -> None:
    test_case.assertEqual(json.loads(json.dumps(payload)), payload)


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


class TestRecoverySessionHostVerdictCrossPhaseDigest(unittest.TestCase):
    def test_digest_accepts_safe_no_drift_payloads(self) -> None:
        digest = build_recovery_session_host_verdict_cross_phase_digest(
            _rendered_check(),
            _rendered_comparison(),
        )

        self.assertIs(digest.ok, True)
        self.assertEqual(digest.reason_code, "ok")
        self.assertEqual(digest.failures, ())
        self.assertIs(digest.digest["cross_phase_ok"], True)
        self.assertIs(digest.digest["operator_safe"], True)
        self.assertIs(digest.digest["contract_ready"], True)
        self.assertIs(digest.digest["comparison_ok"], True)
        self.assertIs(digest.digest["has_drift"], False)
        self.assertIs(digest.digest["has_contract_failure"], False)
        self.assertIs(digest.digest["has_runtime_dependencies"], False)
        self.assertIs(digest.digest["has_cli_commands"], False)
        self.assertIs(
            digest.digest["has_restore_or_durable_surface"], False
        )
        _assert_json_round_trips(
            self,
            render_recovery_session_host_verdict_cross_phase_digest(digest),
        )

    def test_digest_exact_shape_success(self) -> None:
        digest = _build_safe_digest()

        self.assertEqual(set(digest.digest), _VALID_DIGEST_KEYS)

    def test_digest_rejects_non_mapping_inputs(self) -> None:
        digest = build_recovery_session_host_verdict_cross_phase_digest(
            "bad",
            "bad",
        )

        self.assertIs(digest.ok, False)
        self.assertEqual(digest.reason_code, "invalid_cross_phase_digest")
        self.assertEqual(
            digest.failures,
            ("check_not_mapping", "comparison_not_mapping"),
        )
        self.assertEqual(set(digest.digest), _INVALID_DIGEST_KEYS)

    def test_digest_rejects_top_level_shape_mismatch(self) -> None:
        rendered_check = _rendered_check()
        rendered_check["extra"] = True
        rendered_comparison = _rendered_comparison()
        del rendered_comparison["report"]

        digest = build_recovery_session_host_verdict_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )

        self.assertIn("check_shape_mismatch", digest.failures)
        self.assertIn("comparison_shape_mismatch", digest.failures)

    def test_digest_rejects_failures_invalid(self) -> None:
        digest = build_recovery_session_host_verdict_cross_phase_digest(
            _rendered_check(failures=["x", 1]),
            _rendered_comparison(failures="bad"),
        )

        self.assertIn("check_failures_invalid", digest.failures)
        self.assertIn("comparison_failures_invalid", digest.failures)

    def test_digest_rejects_manifest_and_report_invalid(self) -> None:
        digest = build_recovery_session_host_verdict_cross_phase_digest(
            _rendered_check(manifest="bad"),
            _rendered_comparison(report="bad"),
        )

        self.assertIn("check_manifest_invalid", digest.failures)
        self.assertIn("comparison_report_invalid", digest.failures)

    def test_digest_rejects_manifest_shape_mismatch(self) -> None:
        cases = [
            _manifest(version=True),
            _manifest(restore_supported="no"),
            _manifest(durable_writes="no"),
            _manifest(cli_commands=[1]),
            _manifest(runtime_dependencies=[1]),
            _manifest(json_safe="yes"),
        ]
        for manifest in cases:
            with self.subTest(manifest=manifest):
                digest = (
                    build_recovery_session_host_verdict_cross_phase_digest(
                        _rendered_check(manifest=manifest),
                        _rendered_comparison(),
                    )
                )

                self.assertEqual(
                    digest.failures,
                    ("check_manifest_shape_mismatch",),
                )

    def test_digest_rejects_comparison_report_shape_mismatch_success_report(
        self,
    ) -> None:
        cases = [
            _comparison_report(change_count=True),
            _comparison_report(changed="no"),
            _comparison_report(changes=["bad"]),
            _comparison_report(before={"reason_code": "ready"}),
            _comparison_report(before=_summary(failure_count=True)),
            _comparison_report(after=_summary(manifest_version=True)),
        ]
        for report in cases:
            with self.subTest(report=report):
                digest = (
                    build_recovery_session_host_verdict_cross_phase_digest(
                        _rendered_check(),
                        _rendered_comparison(report=report),
                    )
                )

                self.assertEqual(
                    digest.failures,
                    ("comparison_report_shape_mismatch",),
                )

    def test_digest_rejects_comparison_report_shape_mismatch_invalid_report(
        self,
    ) -> None:
        report = _invalid_comparison_report(
            changed=True,
            change_count=1,
            changes=[{"field": "x"}],
        )

        digest = build_recovery_session_host_verdict_cross_phase_digest(
            _rendered_check(),
            _rendered_comparison(ok=False, report=report),
        )

        self.assertEqual(
            digest.failures,
            ("comparison_report_shape_mismatch",),
        )

    def test_digest_failure_order_is_deterministic(self) -> None:
        rendered_check = _rendered_check(
            failures=["x", 1],
            manifest=_manifest(version=True),
        )
        rendered_check["extra"] = True
        rendered_comparison = _rendered_comparison(
            failures=["x", 1],
            report=_comparison_report(change_count=True),
        )
        rendered_comparison["extra"] = True

        digest = build_recovery_session_host_verdict_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )

        self.assertEqual(
            digest.failures,
            (
                "check_shape_mismatch",
                "comparison_shape_mismatch",
                "check_failures_invalid",
                "comparison_failures_invalid",
                "check_manifest_shape_mismatch",
                "comparison_report_shape_mismatch",
            ),
        )

    def test_digest_operator_safe_false_for_drift(self) -> None:
        report = _comparison_report(
            changed=True,
            change_count=1,
            changes=[{"field": "ready", "before": True, "after": False}],
        )

        digest = build_recovery_session_host_verdict_cross_phase_digest(
            _rendered_check(),
            _rendered_comparison(report=report),
        )

        self.assertIs(digest.ok, True)
        self.assertIs(digest.digest["operator_safe"], False)
        self.assertIs(digest.digest["has_drift"], True)

    def test_digest_operator_safe_false_for_contract_failure(self) -> None:
        cases = [
            (
                _rendered_check(ready=False, reason_code="not_ready"),
                _rendered_comparison(),
            ),
            (
                _rendered_check(failures=["digest_shape_mismatch"]),
                _rendered_comparison(),
            ),
            (
                _rendered_check(),
                _rendered_comparison(
                    ok=False,
                    reason_code="invalid_comparison",
                    report=_invalid_comparison_report(),
                ),
            ),
            (
                _rendered_check(),
                _rendered_comparison(
                    report=_comparison_report(
                        failures=["before_shape_mismatch"]
                    ),
                ),
            ),
        ]
        for rendered_check, rendered_comparison in cases:
            with self.subTest(
                rendered_check=rendered_check,
                rendered_comparison=rendered_comparison,
            ):
                digest = (
                    build_recovery_session_host_verdict_cross_phase_digest(
                        rendered_check,
                        rendered_comparison,
                    )
                )

                self.assertIs(digest.ok, True)
                self.assertIs(digest.digest["has_contract_failure"], True)
                self.assertIs(digest.digest["operator_safe"], False)

    def test_digest_operator_safe_false_for_runtime_or_cli_or_restore_surface(
        self,
    ) -> None:
        cases = [
            (
                _manifest(runtime_dependencies=["sqlite3"]),
                "has_runtime_dependencies",
            ),
            (_manifest(cli_commands=["status"]), "has_cli_commands"),
            (
                _manifest(restore_supported=True),
                "has_restore_or_durable_surface",
            ),
            (
                _manifest(durable_writes=True),
                "has_restore_or_durable_surface",
            ),
            (_manifest(json_safe=False), None),
        ]
        for manifest, flag in cases:
            with self.subTest(manifest=manifest):
                digest = (
                    build_recovery_session_host_verdict_cross_phase_digest(
                        _rendered_check(manifest=manifest),
                        _rendered_comparison(),
                    )
                )

                self.assertIs(digest.ok, True)
                self.assertIs(digest.digest["operator_safe"], False)
                if flag is not None:
                    self.assertIs(digest.digest[flag], True)

    def test_digest_before_after_fields_none_for_invalid_comparison_report(
        self,
    ) -> None:
        digest = build_recovery_session_host_verdict_cross_phase_digest(
            _rendered_check(),
            _rendered_comparison(
                ok=False,
                reason_code="invalid_comparison",
                report=_invalid_comparison_report(),
            ),
        )

        self.assertIsNone(digest.digest["before_ready"])
        self.assertIsNone(digest.digest["after_ready"])
        self.assertIsNone(digest.digest["before_reason_code"])
        self.assertIsNone(digest.digest["after_reason_code"])
        self.assertIsNone(digest.digest["before_manifest_version"])
        self.assertIsNone(digest.digest["after_manifest_version"])

    def test_digest_does_not_mutate_inputs(self) -> None:
        rendered_check = _rendered_check()
        rendered_comparison = _rendered_comparison()
        original_check = copy.deepcopy(rendered_check)
        original_comparison = copy.deepcopy(rendered_comparison)

        digest = build_recovery_session_host_verdict_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )
        render_recovery_session_host_verdict_cross_phase_digest(digest)

        self.assertEqual(rendered_check, original_check)
        self.assertEqual(rendered_comparison, original_comparison)

    def test_digest_render_returns_defensive_digest(self) -> None:
        digest = _build_safe_digest()

        rendered = render_recovery_session_host_verdict_cross_phase_digest(
            digest
        )
        rendered["digest"]["failures"].append("mutated")
        rendered["digest"]["operator_safe"] = False
        rendered_again = (
            render_recovery_session_host_verdict_cross_phase_digest(digest)
        )

        self.assertEqual(rendered_again["digest"]["failures"], [])
        self.assertIs(rendered_again["digest"]["operator_safe"], True)

    def test_digest_render_does_not_call_builder(self) -> None:
        digest = RecoverySessionHostVerdictCrossPhaseDigest(
            ok=True,
            reason_code="ok",
            failures=(),
            digest={"cross_phase_ok": True},
        )

        with mock.patch.object(
            digest_module,
            "build_recovery_session_host_verdict_cross_phase_digest",
            side_effect=AssertionError("builder called"),
        ):
            rendered = (
                render_recovery_session_host_verdict_cross_phase_digest(
                    digest
                )
            )

        self.assertEqual(rendered["digest"], {"cross_phase_ok": True})

    def test_digest_output_json_safe_and_no_runtime_repr(self) -> None:
        report = _comparison_report(
            changed=True,
            change_count=1,
            changes=[{"field": "reason_code"}],
        )

        digest = build_recovery_session_host_verdict_cross_phase_digest(
            _rendered_check(),
            _rendered_comparison(report=report),
        )
        rendered = render_recovery_session_host_verdict_cross_phase_digest(
            digest
        )

        _assert_json_round_trips(self, rendered)
        values = _recursive_values(rendered)
        self.assertFalse(
            any(isinstance(value, (set, frozenset, tuple)) for value in values)
        )
        for value in values:
            if isinstance(value, str):
                self.assertFalse(
                    any(item in value for item in _RUNTIME_REPR_STRINGS)
                )

    def test_digest_module_has_no_runtime_dependencies(self) -> None:
        for name in _RUNTIME_DEPENDENCY_NAMES:
            with self.subTest(name=name):
                self.assertNotIn(name, digest_module.__dict__)

    def test_digest_source_has_no_runtime_call_strings(self) -> None:
        source = inspect.getsource(digest_module)

        for text in _RUNTIME_CALL_STRINGS:
            with self.subTest(text=text):
                self.assertNotIn(text, source)

    def test_digest_public_api_is_exact(self) -> None:
        public_api = {
            name
            for name, value in digest_module.__dict__.items()
            if not name.startswith("_")
            and getattr(value, "__module__", None) == digest_module.__name__
            and (inspect.isclass(value) or inspect.isfunction(value))
        }

        self.assertEqual(
            public_api,
            {
                "RecoverySessionHostVerdictCrossPhaseDigest",
                "build_recovery_session_host_verdict_cross_phase_digest",
                "render_recovery_session_host_verdict_cross_phase_digest",
            },
        )


if __name__ == "__main__":
    unittest.main()
