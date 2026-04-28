"""P0-31 read-only RecoverySessionHost verdict aggregation tests."""

from __future__ import annotations

import copy
import inspect
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from kernel.lifecycle import recovery_session_host_cli
from kernel.lifecycle import recovery_session_host_verdict_aggregator as aggregator_module
from kernel.lifecycle.recovery_session_host_cli import (
    current_recovery_session_host_cli_readiness_payload,
    current_recovery_session_host_cli_readiness_smoke,
    render_recovery_session_host_cli_readiness_smoke,
)
from kernel.lifecycle.recovery_session_host_verdict_aggregator import (
    aggregate_recovery_session_host_operator_verdicts,
    render_recovery_session_host_verdict_aggregation,
)


def _factory(
    *,
    ok: bool = True,
    reason_code: str = "ok",
    db_path: str = "operator.db",
) -> dict[str, object]:
    return {
        "ok": ok,
        "db_path": db_path,
        "reason_code": reason_code,
        "message": None if ok else "factory failed",
        "details": {} if ok else {"db_path": db_path},
        "host_present": ok,
        "host_closed": True if ok else None,
    }


def _factory_check_payload(factory: dict[str, object]) -> dict[str, object]:
    return {
        "command": "factory-check",
        "factory": factory,
    }


def _recovery(
    recovery_class: str,
    *,
    reason: str = "classified",
    restored: bool = False,
) -> dict[str, object]:
    return {
        "task_id": f"task-{recovery_class}",
        "recovery_class": recovery_class,
        "reason": reason,
        "restored": restored,
        "snapshot_present": recovery_class != "unrecoverable",
        "current_stage": "inference",
        "terminal_state": None,
        "artifact_count": 2,
        "intent_anchor_count": 1,
        "malformed_event_count": 0,
        "last_event_sequence": 7,
    }


def _evaluate_payload(recovery: object) -> dict[str, object]:
    return {
        "command": "evaluate",
        "factory": _factory(),
        "host_state": {"closed": True},
        "recovery": recovery,
    }


def _readiness_payload(
    *,
    ready: bool = True,
    reason_code: str = "ready",
    failures: object | None = None,
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
    failures: object | None = None,
    payload: object | None = None,
) -> dict[str, object]:
    return {
        "passed": passed,
        "reason_code": reason_code,
        "failures": [] if failures is None else failures,
        "payload": _readiness_payload() if payload is None else payload,
    }


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


class TestRecoverySessionHostVerdictAggregator(unittest.TestCase):
    def test_aggregator_accepts_empty_payloads(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts([])

        self.assertIs(aggregation.ok, True)
        self.assertEqual(aggregation.reason_code, "ok")
        self.assertEqual(aggregation.failures, ())

        summary = aggregation.summary
        self.assertEqual(summary["total_payloads"], 0)
        self.assertEqual(summary["accepted_payloads"], 0)
        self.assertEqual(summary["rejected_payloads"], 0)
        self.assertEqual(
            summary["payload_type_counts"],
            {
                "factory_check": 0,
                "evaluate": 0,
                "readiness": 0,
                "smoke": 0,
                "unknown": 0,
            },
        )
        self.assertEqual(
            summary["factory"],
            {"ok": 0, "failed": 0, "reason_code_counts": {}},
        )
        self.assertEqual(
            summary["recovery"],
            {
                "present": 0,
                "missing": 0,
                "class_counts": {},
                "reason_counts": {},
                "restored_true": 0,
                "restored_false": 0,
            },
        )
        self.assertEqual(
            summary["readiness"],
            {
                "ready_true": 0,
                "ready_false": 0,
                "reason_code_counts": {},
                "failure_counts": {},
            },
        )
        self.assertEqual(
            summary["smoke"],
            {
                "passed_true": 0,
                "passed_false": 0,
                "reason_code_counts": {},
                "failure_counts": {},
            },
        )
        self.assertEqual(
            summary["restore_surface"],
            {"restore_supported_true": 0, "restore_command_present": 0},
        )
        self.assertEqual(
            summary["durable_writes"], {"durable_writes_true": 0}
        )
        self.assertEqual(summary["payload_errors"], [])

        rendered = render_recovery_session_host_verdict_aggregation(
            aggregation
        )
        self._assert_json_safe_no_runtime_types(rendered)

    def test_aggregator_summarizes_factory_check_success_and_failure(
        self,
    ) -> None:
        payloads = [
            _factory_check_payload(_factory()),
            _factory_check_payload(
                _factory(ok=False, reason_code="missing_db_file")
            ),
        ]

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        summary = aggregation.summary

        self.assertIs(aggregation.ok, True)
        self.assertEqual(summary["total_payloads"], 2)
        self.assertEqual(
            summary["payload_type_counts"]["factory_check"], 2
        )
        self.assertEqual(summary["factory"]["ok"], 1)
        self.assertEqual(summary["factory"]["failed"], 1)
        self.assertEqual(
            summary["factory"]["reason_code_counts"],
            {"missing_db_file": 1},
        )

    def test_aggregator_summarizes_evaluate_recovery_classes(self) -> None:
        payloads = [
            _evaluate_payload(_recovery("safe_to_resume")),
            _evaluate_payload(_recovery("unrecoverable")),
            _evaluate_payload(_recovery("needs_manual_review")),
        ]

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        summary = aggregation.summary

        self.assertEqual(summary["payload_type_counts"]["evaluate"], 3)
        self.assertEqual(summary["recovery"]["present"], 3)
        self.assertEqual(
            summary["recovery"]["class_counts"],
            {
                "needs_manual_review": 1,
                "safe_to_resume": 1,
                "unrecoverable": 1,
            },
        )
        self.assertEqual(summary["recovery"]["restored_false"], 3)

    def test_aggregator_counts_missing_recovery(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [_evaluate_payload(None)]
        )

        self.assertIs(aggregation.ok, True)
        self.assertEqual(aggregation.summary["recovery"]["missing"], 1)
        self.assertEqual(aggregation.summary["accepted_payloads"], 1)

    def test_aggregator_summarizes_readiness_and_smoke(self) -> None:
        readiness_payload = current_recovery_session_host_cli_readiness_payload()
        smoke_payload = render_recovery_session_host_cli_readiness_smoke(
            current_recovery_session_host_cli_readiness_smoke()
        )

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [readiness_payload, smoke_payload]
        )
        summary = aggregation.summary

        self.assertIs(aggregation.ok, True)
        self.assertEqual(summary["payload_type_counts"]["readiness"], 1)
        self.assertEqual(summary["payload_type_counts"]["smoke"], 1)
        self.assertEqual(summary["readiness"]["ready_true"], 1)
        self.assertEqual(summary["smoke"]["passed_true"], 1)
        self.assertEqual(
            summary["restore_surface"],
            {"restore_supported_true": 0, "restore_command_present": 0},
        )
        self.assertEqual(
            summary["durable_writes"], {"durable_writes_true": 0}
        )

    def test_aggregator_detects_restore_surface_from_manifest(self) -> None:
        payloads = [
            _readiness_payload(
                manifest={
                    "commands": ["evaluate", "factory-check", "restore"],
                    "restore_supported": False,
                    "durable_writes": False,
                }
            ),
            _readiness_payload(
                manifest={
                    "commands": ["evaluate", "factory-check"],
                    "restore_supported": True,
                    "durable_writes": False,
                }
            ),
        ]

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        restore_surface = aggregation.summary["restore_surface"]

        self.assertIs(aggregation.ok, True)
        self.assertGreaterEqual(
            restore_surface["restore_command_present"], 1
        )
        self.assertGreaterEqual(
            restore_surface["restore_supported_true"], 1
        )

    def test_aggregator_detects_durable_writes_true(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [
                _readiness_payload(
                    manifest={
                        "commands": ["evaluate", "factory-check"],
                        "restore_supported": False,
                        "durable_writes": True,
                    }
                )
            ]
        )

        self.assertIs(aggregation.ok, True)
        self.assertEqual(
            aggregation.summary["durable_writes"]["durable_writes_true"], 1
        )

    def test_aggregator_rejects_non_mapping_payload(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            ["bad"]
        )

        self.assertIs(aggregation.ok, False)
        self.assertEqual(aggregation.reason_code, "invalid_payloads")
        self.assertIn("payload_not_mapping", aggregation.failures)
        self.assertEqual(aggregation.summary["rejected_payloads"], 1)
        self.assertEqual(
            aggregation.summary["payload_errors"][0]["reason_code"],
            "payload_not_mapping",
        )

    def test_aggregator_rejects_unknown_shape(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [{"x": 1}]
        )

        self.assertIs(aggregation.ok, False)
        self.assertIn("unknown_payload_shape", aggregation.failures)

    def test_aggregator_rejects_factory_missing(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [{"command": "factory-check"}]
        )

        self.assertIs(aggregation.ok, False)
        self.assertIn("factory_missing_or_invalid", aggregation.failures)

    def test_aggregator_rejects_invalid_recovery_object(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [_evaluate_payload("bad")]
        )

        self.assertIs(aggregation.ok, False)
        self.assertIn("recovery_invalid", aggregation.failures)

    def test_aggregator_rejects_invalid_failures_list(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [_readiness_payload(failures="bad")]
        )

        self.assertIs(aggregation.ok, False)
        self.assertIn("failures_invalid", aggregation.failures)

    def test_aggregator_rejects_invalid_smoke_payload(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [_smoke_payload(payload="bad")]
        )

        self.assertIs(aggregation.ok, False)
        self.assertIn("smoke_payload_invalid", aggregation.failures)

    def test_aggregator_multiple_failures_are_unique_and_ordered(
        self,
    ) -> None:
        payloads = [
            "bad",
            {"x": 1},
            {"command": "factory-check"},
            _evaluate_payload("bad"),
        ]

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )

        self.assertEqual(
            aggregation.failures,
            (
                "payload_not_mapping",
                "unknown_payload_shape",
                "factory_missing_or_invalid",
                "recovery_invalid",
            ),
        )

    def test_aggregator_does_not_mutate_inputs(self) -> None:
        payloads = [
            _factory_check_payload(
                _factory(ok=False, reason_code="missing_db_file")
            ),
            _readiness_payload(
                failures=["commands_mismatch"],
                manifest={
                    "commands": ["restore-dry-run"],
                    "restore_supported": True,
                    "durable_writes": False,
                },
            ),
        ]
        original = copy.deepcopy(payloads)

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        render_recovery_session_host_verdict_aggregation(aggregation)

        self.assertEqual(payloads, original)

    def test_aggregator_render_returns_defensive_summary(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [_factory_check_payload(_factory())]
        )

        rendered = render_recovery_session_host_verdict_aggregation(
            aggregation
        )
        rendered["summary"]["payload_type_counts"]["factory_check"] = 999

        fresh = render_recovery_session_host_verdict_aggregation(aggregation)
        self.assertEqual(
            fresh["summary"]["payload_type_counts"]["factory_check"], 1
        )
        self.assertEqual(
            aggregation.summary["payload_type_counts"]["factory_check"], 1
        )

    def test_aggregator_output_is_json_safe_and_no_runtime_repr(self) -> None:
        readiness_payload = current_recovery_session_host_cli_readiness_payload()
        smoke_payload = render_recovery_session_host_cli_readiness_smoke(
            current_recovery_session_host_cli_readiness_smoke()
        )
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [
                _factory_check_payload(_factory()),
                _evaluate_payload(_recovery("safe_to_resume")),
                readiness_payload,
                smoke_payload,
            ]
        )
        rendered = render_recovery_session_host_verdict_aggregation(
            aggregation
        )

        self._assert_json_safe_no_runtime_types(rendered)
        self._assert_no_runtime_repr_strings(rendered)

    def test_aggregator_is_pure_no_cli_db_stdio_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing.db"
            self.assertFalse(missing_path.exists())
            payloads = [
                _factory_check_payload(
                    _factory(db_path=str(missing_path))
                )
            ]
            stdout = io.StringIO()
            stderr = io.StringIO()

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
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                aggregation = (
                    aggregate_recovery_session_host_operator_verdicts(
                        payloads
                    )
                )
                render_recovery_session_host_verdict_aggregation(
                    aggregation
                )

            self.assertIs(aggregation.ok, True)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue(), "")
            self.assertFalse(missing_path.exists())

    def test_aggregator_does_not_import_or_call_restore(self) -> None:
        public_functions = [
            name
            for name, value in vars(aggregator_module).items()
            if (
                not name.startswith("_")
                and inspect.isfunction(value)
                and value.__module__ == aggregator_module.__name__
            )
        ]
        for name in public_functions:
            self.assertNotIn("restore", name)

        forbidden_markers = (
            "restore_task",
            "restore_if_allowed",
            "restore_task_from_snapshot",
        )
        for function in (
            aggregate_recovery_session_host_operator_verdicts,
            render_recovery_session_host_verdict_aggregation,
        ):
            source = inspect.getsource(function)
            for marker in forbidden_markers:
                self.assertNotIn(marker, source)

    def _assert_json_safe_no_runtime_types(self, payload: object) -> None:
        encoded = json.dumps(payload, sort_keys=True)
        decoded = json.loads(encoded)
        self.assertEqual(decoded, payload)

        for value in _recursive_values(payload):
            self.assertNotIsInstance(value, (set, frozenset, tuple))

    def _assert_no_runtime_repr_strings(self, payload: object) -> None:
        markers = (
            "object at 0x",
            "sqlite3.Connection",
            "RecoverySessionHost",
            "<kernel.",
            "<sqlite3.",
        )
        for value in _recursive_values(payload):
            if not isinstance(value, str):
                continue
            for marker in markers:
                self.assertNotIn(marker, value)
