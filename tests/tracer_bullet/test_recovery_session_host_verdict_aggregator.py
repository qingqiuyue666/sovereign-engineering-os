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


def _representative_mixed_payloads() -> list[dict[str, object]]:
    return [
        _factory_check_payload(_factory()),
        _factory_check_payload(
            _factory(ok=False, reason_code="missing_db_file")
        ),
        _evaluate_payload(_recovery("safe_to_resume")),
        _evaluate_payload(_recovery("unrecoverable")),
        _readiness_payload(),
        _smoke_payload(),
    ]


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

    def test_aggregator_summary_exact_top_level_shape(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            _representative_mixed_payloads()
        )

        self.assertEqual(
            set(aggregation.summary.keys()),
            {
                "total_payloads",
                "accepted_payloads",
                "rejected_payloads",
                "payload_type_counts",
                "factory",
                "recovery",
                "readiness",
                "smoke",
                "restore_surface",
                "durable_writes",
                "payload_errors",
            },
        )

    def test_aggregator_summary_nested_shapes_are_exact(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            _representative_mixed_payloads()
        )
        summary = aggregation.summary

        self.assertEqual(
            set(summary["payload_type_counts"].keys()),
            {
                "factory_check",
                "evaluate",
                "readiness",
                "smoke",
                "unknown",
            },
        )
        self.assertEqual(
            set(summary["factory"].keys()),
            {
                "ok",
                "failed",
                "reason_code_counts",
            },
        )
        self.assertEqual(
            set(summary["recovery"].keys()),
            {
                "present",
                "missing",
                "class_counts",
                "reason_counts",
                "restored_true",
                "restored_false",
            },
        )
        self.assertEqual(
            set(summary["readiness"].keys()),
            {
                "ready_true",
                "ready_false",
                "reason_code_counts",
                "failure_counts",
            },
        )
        self.assertEqual(
            set(summary["smoke"].keys()),
            {
                "passed_true",
                "passed_false",
                "reason_code_counts",
                "failure_counts",
            },
        )
        self.assertEqual(
            set(summary["restore_surface"].keys()),
            {
                "restore_supported_true",
                "restore_command_present",
            },
        )
        self.assertEqual(
            set(summary["durable_writes"].keys()),
            {
                "durable_writes_true",
            },
        )

    def test_aggregator_count_dict_keys_are_sorted(self) -> None:
        payloads = [
            _factory_check_payload(
                _factory(ok=False, reason_code=reason_code)
            )
            for reason_code in ("z_reason", "a_reason", "m_reason")
        ]
        payloads.extend(
            _evaluate_payload(
                _recovery(recovery_class, reason=f"{recovery_class}_reason")
            )
            for recovery_class in ("z_class", "a_class", "m_class")
        )
        payloads.extend(
            _readiness_payload(
                reason_code=reason_code,
                failures=[failure],
            )
            for reason_code, failure in (
                ("z_reason", "z_failure"),
                ("a_reason", "a_failure"),
                ("m_reason", "m_failure"),
            )
        )
        payloads.extend(
            _smoke_payload(
                reason_code=reason_code,
                failures=[failure],
            )
            for reason_code, failure in (
                ("z_reason", "z_failure"),
                ("a_reason", "a_failure"),
                ("m_reason", "m_failure"),
            )
        )

        aggregation = aggregate_recovery_session_host_operator_verdicts(
            payloads
        )
        summary = aggregation.summary

        count_dicts = (
            summary["factory"]["reason_code_counts"],
            summary["recovery"]["class_counts"],
            summary["recovery"]["reason_counts"],
            summary["readiness"]["reason_code_counts"],
            summary["readiness"]["failure_counts"],
            summary["smoke"]["reason_code_counts"],
            summary["smoke"]["failure_counts"],
        )
        for count_dict in count_dicts:
            self.assertEqual(list(count_dict), sorted(count_dict))

    def test_aggregator_rejection_payload_error_shape_is_exact(
        self,
    ) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            ["bad", {"x": 1}, {"command": "factory-check"}]
        )

        for error in aggregation.summary["payload_errors"]:
            self.assertEqual(set(error.keys()), {"index", "reason_code", "message"})
            self.assertIsInstance(error["index"], int)
            self.assertIsInstance(error["reason_code"], str)
            self.assertIsInstance(error["message"], str)
            self.assertNotEqual(error["message"], "")

    def test_aggregator_rejection_payload_error_order_matches_input_order(
        self,
    ) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [
                "bad",
                {"x": 1},
                {"command": "factory-check"},
                _evaluate_payload("bad"),
            ]
        )
        payload_errors = aggregation.summary["payload_errors"]

        self.assertEqual(
            [error["index"] for error in payload_errors],
            [0, 1, 2, 3],
        )
        self.assertEqual(
            [error["reason_code"] for error in payload_errors],
            [
                "payload_not_mapping",
                "unknown_payload_shape",
                "factory_missing_or_invalid",
                "recovery_invalid",
            ],
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

    def test_aggregator_accepts_factory_false_without_reason_code_but_counts_failed(
        self,
    ) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [
                _factory_check_payload(
                    {
                        "ok": False,
                    }
                )
            ]
        )

        self.assertIs(aggregation.ok, True)
        self.assertEqual(aggregation.summary["accepted_payloads"], 1)
        self.assertEqual(aggregation.summary["factory"]["failed"], 1)
        self.assertEqual(
            aggregation.summary["factory"]["reason_code_counts"],
            {},
        )

    def test_aggregator_rejects_factory_ok_non_bool(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [_factory_check_payload({"ok": "yes"})]
        )

        self.assertIs(aggregation.ok, False)
        self.assertEqual(
            aggregation.summary["payload_errors"][0]["reason_code"],
            "payload_shape_mismatch",
        )

    def test_aggregator_rejects_readiness_manifest_non_dict(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [_readiness_payload(manifest="bad")]
        )

        self.assertIs(aggregation.ok, False)
        self.assertEqual(
            aggregation.summary["payload_errors"][0]["reason_code"],
            "payload_shape_mismatch",
        )

    def test_aggregator_rejects_readiness_failures_non_string_entries(
        self,
    ) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [_readiness_payload(failures=["ok", 123])]
        )

        self.assertIs(aggregation.ok, False)
        self.assertEqual(
            aggregation.summary["payload_errors"][0]["reason_code"],
            "payload_shape_mismatch",
        )

    def test_aggregator_rejects_smoke_failures_non_string_entries(
        self,
    ) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [_smoke_payload(failures=["ok", 123])]
        )

        self.assertIs(aggregation.ok, False)
        self.assertEqual(
            aggregation.summary["payload_errors"][0]["reason_code"],
            "payload_shape_mismatch",
        )

    def test_aggregator_smoke_nested_manifest_absent_is_accepted(
        self,
    ) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [
                _smoke_payload(
                    payload={
                        "ready": True,
                        "reason_code": "ready",
                        "failures": [],
                    }
                )
            ]
        )

        self.assertIs(aggregation.ok, True)
        self.assertEqual(aggregation.summary["accepted_payloads"], 1)
        self.assertEqual(
            aggregation.summary["restore_surface"],
            {"restore_supported_true": 0, "restore_command_present": 0},
        )
        self.assertEqual(
            aggregation.summary["durable_writes"],
            {"durable_writes_true": 0},
        )

    def test_aggregator_restore_command_present_counts_once_per_manifest(
        self,
    ) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [
                _readiness_payload(
                    manifest={
                        "commands": ["restore", "restore-dry-run"],
                        "restore_supported": False,
                        "durable_writes": False,
                    }
                )
            ]
        )

        self.assertEqual(
            aggregation.summary["restore_surface"][
                "restore_command_present"
            ],
            1,
        )

    def test_aggregator_durable_and_restore_counts_across_readiness_and_smoke(
        self,
    ) -> None:
        manifest = {
            "commands": ["evaluate", "factory-check"],
            "restore_supported": True,
            "durable_writes": True,
        }
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [
                _readiness_payload(manifest=manifest),
                _smoke_payload(payload=_readiness_payload(manifest=manifest)),
            ]
        )

        self.assertEqual(
            aggregation.summary["restore_surface"]["restore_supported_true"],
            2,
        )
        self.assertEqual(
            aggregation.summary["durable_writes"]["durable_writes_true"],
            2,
        )

    def test_aggregator_render_exact_shape(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            _representative_mixed_payloads()
        )
        rendered = render_recovery_session_host_verdict_aggregation(
            aggregation
        )

        self.assertEqual(
            set(rendered.keys()),
            {"ok", "reason_code", "failures", "summary"},
        )
        self.assertIsInstance(rendered["failures"], list)
        self.assertIsInstance(rendered["summary"], dict)
        self.assertEqual(json.loads(json.dumps(rendered)), rendered)

    def test_aggregator_render_does_not_call_aggregate(self) -> None:
        aggregation = aggregator_module.RecoverySessionHostVerdictAggregation(
            ok=True,
            reason_code="ok",
            failures=(),
            summary={
                "payload_type_counts": {
                    "factory_check": 1,
                }
            },
        )

        with mock.patch.object(
            aggregator_module,
            "aggregate_recovery_session_host_operator_verdicts",
            side_effect=AssertionError("aggregate called"),
        ):
            rendered = render_recovery_session_host_verdict_aggregation(
                aggregation
            )

        self.assertEqual(rendered["reason_code"], "ok")
        self.assertEqual(
            rendered["summary"]["payload_type_counts"]["factory_check"],
            1,
        )

    def test_aggregator_module_does_not_import_runtime_dependencies(
        self,
    ) -> None:
        forbidden_names = {
            "sqlite3",
            "open_connection",
            "RecoverySessionHost",
            "RecoveryGate",
            "SignablePathOrchestrator",
            "KernelUnitOfWork",
            "build_parser",
            "main",
            "try_build_recovery_session_host_from_sqlite",
        }

        self.assertTrue(
            forbidden_names.isdisjoint(aggregator_module.__dict__)
        )

    def test_aggregator_source_has_no_runtime_call_strings(self) -> None:
        source = inspect.getsource(aggregator_module)
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
        )

        for marker in forbidden_markers:
            self.assertNotIn(marker, source)

    def test_aggregator_mixed_valid_and_invalid_payloads_counts_both(
        self,
    ) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            [
                _factory_check_payload(_factory()),
                {"x": 1},
                _evaluate_payload(_recovery("safe_to_resume")),
                "bad",
            ]
        )
        summary = aggregation.summary

        self.assertEqual(summary["total_payloads"], 4)
        self.assertEqual(summary["accepted_payloads"], 2)
        self.assertEqual(summary["rejected_payloads"], 2)
        self.assertIs(aggregation.ok, False)
        self.assertEqual(aggregation.reason_code, "invalid_payloads")
        self.assertEqual(summary["factory"]["ok"], 2)
        self.assertEqual(summary["recovery"]["present"], 1)

    def test_aggregator_summary_is_independent_between_calls(self) -> None:
        payloads = _representative_mixed_payloads()
        first = aggregate_recovery_session_host_operator_verdicts(payloads)
        second = aggregate_recovery_session_host_operator_verdicts(payloads)

        first.summary["payload_type_counts"]["factory_check"] = 999
        first.summary["factory"]["reason_code_counts"]["x"] = 999

        self.assertEqual(
            second.summary["payload_type_counts"]["factory_check"],
            2,
        )
        self.assertEqual(
            second.summary["factory"]["reason_code_counts"],
            {"missing_db_file": 1},
        )

        fresh = aggregate_recovery_session_host_operator_verdicts(payloads)
        self.assertEqual(
            fresh.summary["payload_type_counts"]["factory_check"],
            2,
        )
        self.assertEqual(
            fresh.summary["factory"]["reason_code_counts"],
            {"missing_db_file": 1},
        )

    def test_aggregator_handles_sequence_tuple_input(self) -> None:
        aggregation = aggregate_recovery_session_host_operator_verdicts(
            tuple(_representative_mixed_payloads())
        )

        self.assertIs(aggregation.ok, True)
        self.assertEqual(aggregation.summary["accepted_payloads"], 6)
        self.assertEqual(
            aggregation.summary["payload_type_counts"]["evaluate"],
            2,
        )

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
