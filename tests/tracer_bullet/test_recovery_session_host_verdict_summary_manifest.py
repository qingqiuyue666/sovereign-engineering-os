"""P0-37 RecoverySessionHost verdict summary contract manifest tests."""

from __future__ import annotations

import copy
import inspect
import json
import unittest
from unittest import mock

from kernel.lifecycle import (
    recovery_session_host_verdict_summary_manifest as manifest_module,
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
    RecoverySessionHostVerdictSummaryContractCheck,
    check_recovery_session_host_verdict_summary_contract,
    recovery_session_host_verdict_summary_contract_manifest,
    render_recovery_session_host_verdict_summary_contract_check,
)


_MANIFEST_KEYS = {
    "surface",
    "version",
    "input_shape",
    "top_level_keys",
    "digest_keys",
    "failure_values",
    "reason_codes",
    "operator_safe_requires",
    "restore_supported",
    "durable_writes",
    "cli_commands",
    "runtime_dependencies",
    "json_safe",
}
_RUNTIME_DEPENDENCY_NAMES = {
    "sqlite3",
    "recovery_session_host_cli",
    "recovery_session_host_verdict_aggregator",
    "recovery_session_host_verdict_summary",
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
    "recovery_session_host_cli",
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


def _valid_rendered_summary() -> dict[str, object]:
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
    rendered_aggregation = render_recovery_session_host_verdict_aggregation(
        aggregation
    )
    summary = build_recovery_session_host_verdict_summary(
        rendered_aggregation
    )
    return render_recovery_session_host_verdict_summary(summary)


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


class TestRecoverySessionHostVerdictSummaryManifest(unittest.TestCase):
    def test_manifest_shape_is_exact_and_json_safe(self) -> None:
        manifest = recovery_session_host_verdict_summary_contract_manifest()

        self.assertEqual(set(manifest), _MANIFEST_KEYS)
        self.assertEqual(json.loads(json.dumps(manifest)), manifest)
        self.assertFalse(
            any(
                isinstance(value, (set, frozenset, tuple))
                for value in _recursive_values(manifest)
            )
        )
        self.assertEqual(
            manifest["surface"],
            "recovery_session_host_verdict_summary",
        )
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["input_shape"], "rendered_summary")

    def test_manifest_returns_defensive_copy(self) -> None:
        manifest1 = recovery_session_host_verdict_summary_contract_manifest()
        digest_keys = manifest1["digest_keys"]
        operator_safe_requires = manifest1["operator_safe_requires"]
        self.assertIsInstance(digest_keys, list)
        self.assertIsInstance(operator_safe_requires, dict)

        digest_keys.append("x")
        operator_safe_requires["rejected_payloads"] = 999

        manifest2 = recovery_session_host_verdict_summary_contract_manifest()
        self.assertNotIn("x", manifest2["digest_keys"])
        self.assertEqual(
            manifest2["operator_safe_requires"]["rejected_payloads"],
            0,
        )

    def test_checker_accepts_valid_rendered_summary(self) -> None:
        rendered_summary = _valid_rendered_summary()

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        rendered_check = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )

        self.assertIs(check.ready, True)
        self.assertEqual(check.reason_code, "ready")
        self.assertEqual(check.failures, ())
        self.assertEqual(json.loads(json.dumps(rendered_check)), rendered_check)

    def test_checker_rejects_non_mapping(self) -> None:
        check = check_recovery_session_host_verdict_summary_contract("bad")

        self.assertIn("summary_not_mapping", check.failures)

    def test_checker_rejects_top_level_shape_mismatch(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["extra"] = True

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("summary_shape_mismatch", check.failures)

    def test_checker_rejects_invalid_reason_code(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["reason_code"] = "weird"

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("reason_code_invalid", check.failures)

    def test_checker_rejects_failures_invalid(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["failures"] = ["ok", 123]

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("failures_invalid", check.failures)

    def test_checker_rejects_unknown_failure_value(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["ok"] = False
        rendered_summary["reason_code"] = "invalid_aggregation"
        rendered_summary["failures"] = ["not_declared"]

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("failure_value_unknown", check.failures)

    def test_checker_rejects_digest_invalid(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["digest"] = "bad"

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("digest_invalid", check.failures)

    def test_checker_rejects_digest_shape_mismatch(self) -> None:
        rendered_summary = _valid_rendered_summary()
        del rendered_summary["digest"]["operator_safe"]

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("digest_shape_mismatch", check.failures)

    def test_checker_rejects_counter_invalid_and_bool_counter(self) -> None:
        for value in ("1", True):
            with self.subTest(value=value):
                rendered_summary = _valid_rendered_summary()
                rendered_summary["digest"]["total_payloads"] = value

                check = check_recovery_session_host_verdict_summary_contract(
                    rendered_summary
                )

                self.assertIn("digest_counter_invalid", check.failures)

    def test_checker_rejects_bool_field_invalid(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["digest"]["operator_safe"] = "yes"

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("digest_bool_invalid", check.failures)

    def test_checker_rejects_string_field_invalid(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["digest"]["aggregation_reason_code"] = 123

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("digest_string_invalid", check.failures)

    def test_checker_rejects_list_field_invalid(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["digest"]["aggregation_failures"] = ["x", 1]

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("digest_list_invalid", check.failures)

    def test_checker_rejects_count_dict_invalid_or_unsorted(self) -> None:
        cases = (
            "bad",
            {"x": "1"},
            {1: 1},
            {"z": 1, "a": 2},
        )

        for value in cases:
            with self.subTest(value=value):
                rendered_summary = _valid_rendered_summary()
                rendered_summary["digest"]["payload_type_counts"] = value

                check = check_recovery_session_host_verdict_summary_contract(
                    rendered_summary
                )

                self.assertIn("digest_count_dict_invalid", check.failures)

    def test_checker_rejects_operator_safe_inconsistent(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["digest"]["operator_safe"] = True
        rendered_summary["digest"]["rejected_payloads"] = 1

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("operator_safe_inconsistent", check.failures)

    def test_checker_rejects_restore_surface_present(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["digest"]["restore_supported_true"] = 1

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("restore_surface_present", check.failures)

    def test_checker_rejects_durable_writes_present(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["digest"]["durable_writes_true"] = 1

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIn("durable_writes_present", check.failures)

    def test_checker_rejects_summary_status_inconsistent(self) -> None:
        cases = (
            {"ok": True, "reason_code": "invalid_aggregation"},
            {"ok": True, "failures": ["aggregation_not_mapping"]},
            {"ok": False, "reason_code": "ok"},
            {"ok": False, "reason_code": "invalid_aggregation"},
        )

        for updates in cases:
            with self.subTest(updates=updates):
                rendered_summary = _valid_rendered_summary()
                rendered_summary.update(updates)

                check = check_recovery_session_host_verdict_summary_contract(
                    rendered_summary
                )

                self.assertIn(
                    "summary_status_inconsistent",
                    check.failures,
                )

    def test_checker_failure_order_is_deterministic(self) -> None:
        rendered_summary = _valid_rendered_summary()
        rendered_summary["extra"] = True
        rendered_summary["reason_code"] = "weird"
        rendered_summary["failures"] = ["ok", 123]
        del rendered_summary["digest"]["operator_safe"]

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertEqual(
            check.failures,
            (
                "summary_shape_mismatch",
                "reason_code_invalid",
                "failures_invalid",
                "digest_shape_mismatch",
            ),
        )

    def test_checker_does_not_mutate_input(self) -> None:
        rendered_summary = _valid_rendered_summary()
        before = copy.deepcopy(rendered_summary)

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        render_recovery_session_host_verdict_summary_contract_check(check)

        self.assertEqual(rendered_summary, before)

    def test_check_renderer_exact_shape_and_defensive_manifest(self) -> None:
        check = check_recovery_session_host_verdict_summary_contract(
            _valid_rendered_summary()
        )
        rendered = render_recovery_session_host_verdict_summary_contract_check(
            check
        )

        self.assertEqual(
            set(rendered),
            {"ready", "reason_code", "failures", "manifest"},
        )
        rendered["manifest"]["digest_keys"].append("x")
        rendered_again = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )

        self.assertNotIn("x", rendered_again["manifest"]["digest_keys"])

    def test_check_renderer_does_not_call_checker_or_manifest_builder(
        self,
    ) -> None:
        check = RecoverySessionHostVerdictSummaryContractCheck(
            ready=True,
            reason_code="ready",
            failures=(),
            manifest={"surface": "manual", "digest_keys": []},
        )

        with mock.patch.object(
            manifest_module,
            "check_recovery_session_host_verdict_summary_contract",
            side_effect=AssertionError("checker called"),
        ), mock.patch.object(
            manifest_module,
            "recovery_session_host_verdict_summary_contract_manifest",
            side_effect=AssertionError("manifest builder called"),
        ):
            rendered = (
                render_recovery_session_host_verdict_summary_contract_check(
                    check
                )
            )

        self.assertEqual(rendered["manifest"]["surface"], "manual")

    def test_manifest_module_has_no_runtime_dependencies(self) -> None:
        for name in _RUNTIME_DEPENDENCY_NAMES:
            with self.subTest(name=name):
                self.assertNotIn(name, manifest_module.__dict__)

    def test_manifest_source_has_no_runtime_call_strings(self) -> None:
        source = inspect.getsource(manifest_module)

        for text in _RUNTIME_CALL_STRINGS:
            with self.subTest(text=text):
                self.assertNotIn(text, source)

    def test_manifest_public_api_is_exact(self) -> None:
        public_api = {
            name
            for name, value in inspect.getmembers(manifest_module)
            if not name.startswith("_")
            and getattr(value, "__module__", None) == manifest_module.__name__
            and (inspect.isclass(value) or inspect.isfunction(value))
        }

        self.assertEqual(
            public_api,
            {
                "RecoverySessionHostVerdictSummaryContractCheck",
                "recovery_session_host_verdict_summary_contract_manifest",
                "check_recovery_session_host_verdict_summary_contract",
                "render_recovery_session_host_verdict_summary_contract_check",
            },
        )
