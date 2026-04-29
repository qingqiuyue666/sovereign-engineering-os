"""P0-34 read-only RecoverySessionHost verdict summary tests."""

from __future__ import annotations

import copy
import inspect
import json
import unittest
from unittest import mock

from kernel.lifecycle import recovery_session_host_verdict_summary as summary_module
from kernel.lifecycle.recovery_session_host_verdict_aggregator import (
    aggregate_recovery_session_host_operator_verdicts,
    render_recovery_session_host_verdict_aggregation,
)
from kernel.lifecycle.recovery_session_host_verdict_summary import (
    RecoverySessionHostVerdictSummary,
    build_recovery_session_host_verdict_summary,
    render_recovery_session_host_verdict_summary,
)


_DIGEST_KEYS = {
    "aggregation_ok",
    "aggregation_reason_code",
    "aggregation_failures",
    "total_payloads",
    "accepted_payloads",
    "rejected_payloads",
    "payload_type_counts",
    "factory_failed",
    "factory_failure_reason_counts",
    "recovery_class_counts",
    "readiness_ready_false",
    "readiness_failure_counts",
    "smoke_passed_false",
    "smoke_failure_counts",
    "restore_supported_true",
    "restore_command_present",
    "durable_writes_true",
    "payload_error_reason_counts",
    "has_restore_surface",
    "has_durable_writes",
    "has_payload_errors",
    "operator_safe",
}


def _factory(
    *,
    ok: bool = True,
    reason_code: str = "ok",
) -> dict[str, object]:
    return {
        "ok": ok,
        "reason_code": reason_code,
        "host_closed": True if ok else None,
    }


def _readiness_payload(
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
        "manifest": {
            "commands": ["evaluate", "factory-check"],
            "restore_supported": False,
            "durable_writes": False,
        }
        if manifest is None
        else manifest,
    }


def _smoke_payload(
    *,
    passed: bool = True,
    reason_code: str = "passed",
    failures: list[str] | None = None,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "passed": passed,
        "reason_code": reason_code,
        "failures": [] if failures is None else failures,
        "payload": _readiness_payload() if payload is None else payload,
    }


def _success_rendered_aggregation() -> dict[str, object]:
    aggregation = aggregate_recovery_session_host_operator_verdicts(
        [
            {"command": "factory-check", "factory": _factory()},
            {
                "command": "evaluate",
                "factory": _factory(),
                "host_state": {"closed": True},
                "recovery": {
                    "task_id": "task-safe",
                    "recovery_class": "safe_to_resume",
                    "reason": "classified",
                    "restored": False,
                },
            },
            _readiness_payload(),
            _smoke_payload(),
        ]
    )
    return render_recovery_session_host_verdict_aggregation(aggregation)


def _build_success_summary() -> RecoverySessionHostVerdictSummary:
    return build_recovery_session_host_verdict_summary(
        _success_rendered_aggregation()
    )


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


class TestRecoverySessionHostVerdictSummary(unittest.TestCase):
    def test_summary_accepts_rendered_aggregation_success(self) -> None:
        summary = _build_success_summary()

        self.assertIs(summary.ok, True)
        self.assertEqual(summary.reason_code, "ok")
        self.assertEqual(summary.failures, ())
        self.assertIs(summary.digest["aggregation_ok"], True)
        self.assertIs(summary.digest["operator_safe"], True)
        self.assertGreater(summary.digest["total_payloads"], 0)
        self.assertIs(summary.digest["has_restore_surface"], False)
        self.assertIs(summary.digest["has_durable_writes"], False)
        self.assertIs(summary.digest["has_payload_errors"], False)

        rendered = render_recovery_session_host_verdict_summary(summary)
        self.assertEqual(json.loads(json.dumps(rendered)), rendered)

    def test_summary_exact_digest_shape_success(self) -> None:
        summary = _build_success_summary()

        self.assertEqual(set(summary.digest), _DIGEST_KEYS)

    def test_summary_rejects_non_mapping_input(self) -> None:
        summary = build_recovery_session_host_verdict_summary("bad")

        self.assertIs(summary.ok, False)
        self.assertEqual(summary.reason_code, "invalid_aggregation")
        self.assertIn("aggregation_not_mapping", summary.failures)
        self.assertIs(summary.digest["operator_safe"], False)

    def test_summary_rejects_top_level_shape_mismatch(self) -> None:
        rendered = _success_rendered_aggregation()
        rendered["extra"] = True

        summary = build_recovery_session_host_verdict_summary(rendered)

        self.assertIs(summary.ok, False)
        self.assertEqual(summary.reason_code, "invalid_aggregation")
        self.assertIn("aggregation_shape_mismatch", summary.failures)

    def test_summary_rejects_failures_not_string_list(self) -> None:
        rendered = _success_rendered_aggregation()
        rendered["failures"] = ["ok", 123]

        summary = build_recovery_session_host_verdict_summary(rendered)

        self.assertIs(summary.ok, False)
        self.assertEqual(summary.reason_code, "invalid_aggregation")
        self.assertIn("aggregation_failures_invalid", summary.failures)

    def test_summary_rejects_summary_not_dict(self) -> None:
        rendered = _success_rendered_aggregation()
        rendered["summary"] = "bad"

        summary = build_recovery_session_host_verdict_summary(rendered)

        self.assertIs(summary.ok, False)
        self.assertEqual(summary.reason_code, "invalid_aggregation")
        self.assertIn("aggregation_summary_invalid", summary.failures)

    def test_summary_rejects_missing_aggregator_summary_keys(self) -> None:
        rendered = _success_rendered_aggregation()
        del rendered["summary"]["factory"]

        summary = build_recovery_session_host_verdict_summary(rendered)

        self.assertIs(summary.ok, False)
        self.assertEqual(summary.reason_code, "invalid_aggregation")
        self.assertIn(
            "aggregation_summary_shape_mismatch", summary.failures
        )

    def test_summary_operator_safe_false_for_aggregation_failure(
        self,
    ) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [{"phase": "unknown"}]
        )
        rendered = render_recovery_session_host_verdict_aggregation(
            aggregation
        )

        summary = build_recovery_session_host_verdict_summary(rendered)

        self.assertIs(summary.ok, True)
        self.assertIs(summary.digest["aggregation_ok"], False)
        self.assertIs(summary.digest["operator_safe"], False)
        self.assertIs(summary.digest["has_payload_errors"], True)
        self.assertEqual(
            summary.digest["payload_error_reason_counts"],
            {"unknown_payload_shape": 1},
        )

    def test_summary_operator_safe_false_for_restore_surface(self) -> None:
        rendered = _success_rendered_aggregation()
        rendered["summary"]["restore_surface"][
            "restore_supported_true"
        ] = 1

        summary = build_recovery_session_host_verdict_summary(rendered)

        self.assertIs(summary.digest["operator_safe"], False)
        self.assertIs(summary.digest["has_restore_surface"], True)

    def test_summary_operator_safe_false_for_durable_writes(self) -> None:
        rendered = _success_rendered_aggregation()
        rendered["summary"]["durable_writes"]["durable_writes_true"] = 1

        summary = build_recovery_session_host_verdict_summary(rendered)

        self.assertIs(summary.digest["operator_safe"], False)
        self.assertIs(summary.digest["has_durable_writes"], True)

    def test_summary_operator_safe_false_for_readiness_or_smoke_failure(
        self,
    ) -> None:
        cases = (
            ("readiness", "readiness", "ready_false"),
            ("smoke", "smoke", "passed_false"),
        )
        for name, section, key in cases:
            with self.subTest(name=name):
                rendered = _success_rendered_aggregation()
                rendered["summary"][section][key] = 1

                summary = build_recovery_session_host_verdict_summary(
                    rendered
                )

                self.assertIs(summary.digest["operator_safe"], False)

    def test_summary_count_dicts_are_sorted(self) -> None:
        rendered = _success_rendered_aggregation()
        rendered["summary"]["payload_type_counts"] = {
            "z_payload": 1,
            "a_payload": 2,
        }
        rendered["summary"]["factory"]["reason_code_counts"] = {
            "z_reason": 1,
            "a_reason": 2,
        }
        rendered["summary"]["recovery"]["class_counts"] = {
            "z_class": 1,
            "a_class": 2,
        }
        rendered["summary"]["readiness"]["failure_counts"] = {
            "z_failure": 1,
            "a_failure": 2,
        }
        rendered["summary"]["smoke"]["failure_counts"] = {
            "z_failure": 1,
            "a_failure": 2,
        }
        rendered["summary"]["rejected_payloads"] = 3
        rendered["summary"]["payload_errors"] = [
            {"reason_code": "z_reason"},
            {"reason_code": "a_reason"},
            {"reason_code": "z_reason"},
        ]

        summary = build_recovery_session_host_verdict_summary(rendered)

        for key in (
            "payload_type_counts",
            "factory_failure_reason_counts",
            "recovery_class_counts",
            "readiness_failure_counts",
            "smoke_failure_counts",
            "payload_error_reason_counts",
        ):
            self.assertEqual(
                list(summary.digest[key]),
                sorted(summary.digest[key]),
            )

    def test_summary_does_not_mutate_input(self) -> None:
        rendered = _success_rendered_aggregation()
        original = copy.deepcopy(rendered)

        summary = build_recovery_session_host_verdict_summary(rendered)
        render_recovery_session_host_verdict_summary(summary)

        self.assertEqual(rendered, original)

    def test_summary_render_returns_defensive_digest(self) -> None:
        summary = _build_success_summary()
        rendered = render_recovery_session_host_verdict_summary(summary)
        rendered["digest"]["payload_type_counts"]["factory_check"] = 999
        rendered["digest"]["aggregation_failures"].append("mutated")

        fresh = render_recovery_session_host_verdict_summary(summary)

        self.assertEqual(
            fresh["digest"]["payload_type_counts"]["factory_check"], 1
        )
        self.assertEqual(fresh["digest"]["aggregation_failures"], [])

    def test_summary_render_does_not_call_build(self) -> None:
        summary = RecoverySessionHostVerdictSummary(
            ok=True,
            reason_code="ok",
            failures=(),
            digest={"operator_safe": True},
        )

        with mock.patch.object(
            summary_module,
            "build_recovery_session_host_verdict_summary",
            side_effect=AssertionError("build called"),
        ):
            rendered = render_recovery_session_host_verdict_summary(summary)

        self.assertEqual(rendered["reason_code"], "ok")
        self.assertEqual(rendered["digest"], {"operator_safe": True})

    def test_summary_output_json_safe_and_no_runtime_repr(self) -> None:
        rendered = render_recovery_session_host_verdict_summary(
            _build_success_summary()
        )

        self.assertEqual(json.loads(json.dumps(rendered)), rendered)
        for value in _recursive_values(rendered):
            self.assertNotIsInstance(value, (set, frozenset, tuple))
            if not isinstance(value, str):
                continue
            for marker in (
                "object at 0x",
                "sqlite3.Connection",
                "RecoverySessionHost",
                "<kernel.",
                "<sqlite3.",
            ):
                self.assertNotIn(marker, value)

    def test_summary_module_has_no_runtime_dependencies(self) -> None:
        forbidden_names = {
            "sqlite3",
            "recovery_session_host_cli",
            "recovery_session_host_verdict_aggregator",
            "recovery_cli",
            "RecoverySessionHost",
            "RecoveryGate",
            "SignablePathOrchestrator",
            "KernelUnitOfWork",
            "build_parser",
            "main",
            "try_build_recovery_session_host_from_sqlite",
            "aggregate_recovery_session_host_operator_verdicts",
        }

        self.assertTrue(forbidden_names.isdisjoint(summary_module.__dict__))

    def test_summary_source_has_no_runtime_call_strings(self) -> None:
        source = inspect.getsource(summary_module)
        forbidden_markers = (
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
            "recovery_session_host_cli",
        )

        for marker in forbidden_markers:
            self.assertNotIn(marker, source)

    def test_summary_has_no_restore_public_function(self) -> None:
        public_function_names = {
            name
            for name, value in summary_module.__dict__.items()
            if (
                not name.startswith("_")
                and inspect.isfunction(value)
                and value.__module__ == summary_module.__name__
            )
        }

        for name in public_function_names:
            self.assertNotIn("restore", name)


if __name__ == "__main__":
    unittest.main()
