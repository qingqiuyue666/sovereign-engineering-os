"""P0-45 rendered cross-phase verdict digest contract tests."""

import copy
import inspect
import json
import unittest
from unittest import mock

from kernel.lifecycle import (
    recovery_session_host_verdict_cross_phase_digest_contract as contract_module,
)
from kernel.lifecycle.recovery_session_host_verdict_cross_phase_digest_contract import (
    RecoverySessionHostVerdictCrossPhaseDigestContractCheck,
    check_recovery_session_host_verdict_cross_phase_digest_contract,
    recovery_session_host_verdict_cross_phase_digest_contract_manifest,
    render_recovery_session_host_verdict_cross_phase_digest_contract_check,
)


_MANIFEST_KEYS = {
    "surface",
    "version",
    "input_shape",
    "top_level_keys",
    "digest_keys",
    "failure_values",
    "reason_codes",
    "contract_ready_requires",
    "restore_supported",
    "durable_writes",
    "cli_commands",
    "runtime_dependencies",
    "json_safe",
}
_DIGEST_KEYS = [
    "after_manifest_version",
    "after_reason_code",
    "after_ready",
    "before_manifest_version",
    "before_reason_code",
    "before_ready",
    "cli_command_count",
    "comparison_change_count",
    "comparison_changed",
    "comparison_failure_count",
    "comparison_ok",
    "comparison_reason_code",
    "contract_failure_count",
    "contract_ready",
    "contract_reason_code",
    "cross_phase_ok",
    "durable_writes",
    "failures",
    "has_cli_commands",
    "has_contract_failure",
    "has_drift",
    "has_restore_or_durable_surface",
    "has_runtime_dependencies",
    "json_safe",
    "manifest_surface",
    "manifest_version",
    "operator_safe",
    "reason_code",
    "restore_supported",
    "runtime_dependency_count",
]
_RUNTIME_DEPENDENCY_NAMES = {
    "sqlite3",
    "recovery_session_host_cli",
    "recovery_session_host_verdict_aggregator",
    "recovery_session_host_verdict_summary",
    "recovery_session_host_verdict_summary_manifest",
    "recovery_session_host_verdict_summary_comparator",
    "recovery_session_host_verdict_cross_phase_digest",
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
    "compare_recovery_session_host_verdict_summary_checks",
    "build_recovery_session_host_verdict_cross_phase_digest",
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
    "build_recovery_session_host_verdict_cross_phase_digest",
    "recovery_session_host_cli",
}
_RUNTIME_REPR_STRINGS = {
    "object at 0x",
    "sqlite3.Connection",
    "RecoverySessionHost",
    "<kernel.",
    "<sqlite3.",
}


def _safe_rendered_digest() -> dict[str, object]:
    return {
        "ok": True,
        "reason_code": "ok",
        "failures": [],
        "digest": {
            "after_manifest_version": 1,
            "after_reason_code": "ready",
            "after_ready": True,
            "before_manifest_version": 1,
            "before_reason_code": "ready",
            "before_ready": True,
            "cli_command_count": 0,
            "comparison_change_count": 0,
            "comparison_changed": False,
            "comparison_failure_count": 0,
            "comparison_ok": True,
            "comparison_reason_code": "ok",
            "contract_failure_count": 0,
            "contract_ready": True,
            "contract_reason_code": "ready",
            "cross_phase_ok": True,
            "durable_writes": False,
            "failures": [],
            "has_cli_commands": False,
            "has_contract_failure": False,
            "has_drift": False,
            "has_restore_or_durable_surface": False,
            "has_runtime_dependencies": False,
            "json_safe": True,
            "manifest_surface": "recovery_session_host_verdict_summary",
            "manifest_version": 1,
            "operator_safe": True,
            "reason_code": "ok",
            "restore_supported": False,
            "runtime_dependency_count": 0,
        },
    }


def _invalid_rendered_digest(
    *,
    failures: list[str] | None = None,
    digest_failures: list[str] | None = None,
) -> dict[str, object]:
    payload = _safe_rendered_digest()
    payload["ok"] = False
    payload["reason_code"] = "invalid_cross_phase_digest"
    payload["failures"] = (
        ["check_not_mapping"] if failures is None else failures
    )
    digest = payload["digest"]
    assert isinstance(digest, dict)
    digest["cross_phase_ok"] = False
    digest["reason_code"] = "invalid_cross_phase_digest"
    digest["failures"] = (
        ["check_not_mapping"] if digest_failures is None else digest_failures
    )
    digest["operator_safe"] = False
    return payload


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


def _assert_json_round_trips(
    test_case: unittest.TestCase,
    payload: dict[str, object],
) -> None:
    test_case.assertEqual(json.loads(json.dumps(payload)), payload)


class TestRecoverySessionHostVerdictCrossPhaseDigestContract(
    unittest.TestCase
):
    def test_contract_manifest_shape_is_exact_and_json_safe(self) -> None:
        manifest = (
            recovery_session_host_verdict_cross_phase_digest_contract_manifest()
        )

        self.assertEqual(set(manifest), _MANIFEST_KEYS)
        _assert_json_round_trips(self, manifest)
        self.assertFalse(
            any(
                isinstance(value, (set, frozenset, tuple))
                for value in _recursive_values(manifest)
            )
        )
        self.assertEqual(
            manifest["surface"],
            "recovery_session_host_verdict_cross_phase_digest",
        )
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(
            manifest["input_shape"],
            "rendered_cross_phase_digest",
        )

    def test_contract_manifest_returns_defensive_copy(self) -> None:
        manifest1 = (
            recovery_session_host_verdict_cross_phase_digest_contract_manifest()
        )
        digest_keys = manifest1["digest_keys"]
        ready_requires = manifest1["contract_ready_requires"]
        self.assertIsInstance(digest_keys, list)
        self.assertIsInstance(ready_requires, dict)

        digest_keys.append("x")
        ready_requires["digest.operator_safe"] = False

        manifest2 = (
            recovery_session_host_verdict_cross_phase_digest_contract_manifest()
        )
        self.assertNotIn("x", manifest2["digest_keys"])
        self.assertIs(
            manifest2["contract_ready_requires"]["digest.operator_safe"],
            True,
        )

    def test_contract_accepts_safe_operator_ready_rendered_digest(self) -> None:
        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            _safe_rendered_digest()
        )

        self.assertIs(check.ready, True)
        self.assertEqual(check.reason_code, "ready")
        self.assertEqual(check.failures, ())
        rendered = (
            render_recovery_session_host_verdict_cross_phase_digest_contract_check(
                check
            )
        )
        _assert_json_round_trips(self, rendered)

    def test_contract_marks_structurally_valid_unsafe_digest_not_ready(
        self,
    ) -> None:
        rendered_digest = _safe_rendered_digest()
        digest = rendered_digest["digest"]
        assert isinstance(digest, dict)
        digest["operator_safe"] = False
        digest["has_drift"] = True
        digest["comparison_changed"] = True
        digest["comparison_change_count"] = 1

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIs(check.ready, False)
        self.assertEqual(check.reason_code, "not_ready")
        self.assertEqual(check.failures, ())

    def test_contract_rejects_non_mapping(self) -> None:
        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            "bad"
        )

        self.assertIn("payload_not_mapping", check.failures)

    def test_contract_rejects_top_level_shape_mismatch(self) -> None:
        rendered_digest = _safe_rendered_digest()
        rendered_digest["extra"] = True

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("payload_shape_mismatch", check.failures)

    def test_contract_rejects_invalid_reason_code(self) -> None:
        rendered_digest = _safe_rendered_digest()
        rendered_digest["reason_code"] = "weird"

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("reason_code_invalid", check.failures)

    def test_contract_rejects_invalid_failures(self) -> None:
        rendered_digest = _safe_rendered_digest()
        rendered_digest["failures"] = ["x", 1]

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("failures_invalid", check.failures)

    def test_contract_rejects_unknown_failure_value(self) -> None:
        rendered_digest = _invalid_rendered_digest(
            failures=["not_declared"],
            digest_failures=["check_not_mapping"],
        )

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("failure_value_unknown", check.failures)

    def test_contract_rejects_digest_invalid(self) -> None:
        rendered_digest = _safe_rendered_digest()
        rendered_digest["digest"] = "bad"

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("digest_invalid", check.failures)

    def test_contract_rejects_digest_shape_mismatch(self) -> None:
        rendered_digest = _safe_rendered_digest()
        digest = rendered_digest["digest"]
        assert isinstance(digest, dict)
        del digest["operator_safe"]

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("digest_shape_mismatch", check.failures)

    def test_contract_rejects_bool_fields_invalid(self) -> None:
        rendered_digest = _safe_rendered_digest()
        digest = rendered_digest["digest"]
        assert isinstance(digest, dict)
        digest["operator_safe"] = "yes"

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("digest_bool_invalid", check.failures)

    def test_contract_rejects_string_fields_invalid(self) -> None:
        rendered_digest = _safe_rendered_digest()
        digest = rendered_digest["digest"]
        assert isinstance(digest, dict)
        digest["reason_code"] = 123

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("digest_string_invalid", check.failures)

    def test_contract_rejects_list_fields_invalid(self) -> None:
        rendered_digest = _safe_rendered_digest()
        digest = rendered_digest["digest"]
        assert isinstance(digest, dict)
        digest["failures"] = ["x", 1]

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("digest_list_invalid", check.failures)

    def test_contract_rejects_counter_fields_invalid_and_bool(self) -> None:
        cases = [
            ("contract_failure_count", "1"),
            ("contract_failure_count", True),
            ("comparison_change_count", True),
        ]

        for field, value in cases:
            with self.subTest(field=field, value=value):
                rendered_digest = _safe_rendered_digest()
                digest = rendered_digest["digest"]
                assert isinstance(digest, dict)
                digest[field] = value

                check = (
                    check_recovery_session_host_verdict_cross_phase_digest_contract(
                        rendered_digest
                    )
                )

                self.assertIn("digest_counter_invalid", check.failures)

    def test_contract_rejects_optional_bool_fields_invalid(self) -> None:
        rendered_digest = _safe_rendered_digest()
        digest = rendered_digest["digest"]
        assert isinstance(digest, dict)
        digest["before_ready"] = "yes"

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("digest_optional_bool_invalid", check.failures)

    def test_contract_rejects_optional_string_fields_invalid(self) -> None:
        rendered_digest = _safe_rendered_digest()
        digest = rendered_digest["digest"]
        assert isinstance(digest, dict)
        digest["before_reason_code"] = 123

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("digest_optional_string_invalid", check.failures)

    def test_contract_rejects_optional_int_fields_invalid_and_bool(
        self,
    ) -> None:
        cases = [
            ("manifest_version", "1"),
            ("manifest_version", True),
            ("before_manifest_version", True),
        ]

        for field, value in cases:
            with self.subTest(field=field, value=value):
                rendered_digest = _safe_rendered_digest()
                digest = rendered_digest["digest"]
                assert isinstance(digest, dict)
                digest[field] = value

                check = (
                    check_recovery_session_host_verdict_cross_phase_digest_contract(
                        rendered_digest
                    )
                )

                self.assertIn("digest_optional_int_invalid", check.failures)

    def test_contract_rejects_operator_safe_inconsistent(self) -> None:
        rendered_digest = _safe_rendered_digest()
        digest = rendered_digest["digest"]
        assert isinstance(digest, dict)
        digest["operator_safe"] = True
        digest["has_drift"] = True
        digest["comparison_changed"] = True
        digest["comparison_change_count"] = 1

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertIn("operator_safe_inconsistent", check.failures)

    def test_contract_rejects_status_inconsistent(self) -> None:
        cases = [
            ("payload reason invalid", ("reason_code", "invalid_cross_phase_digest")),
            ("payload failures nonempty", ("failures", ["check_not_mapping"])),
            ("payload false reason ok", ("ok_false_reason", None)),
            ("payload false failures empty", ("ok_false_failures", None)),
            ("digest cross false", ("digest.cross_phase_ok", False)),
            (
                "digest reason invalid",
                ("digest.reason_code", "invalid_cross_phase_digest"),
            ),
            ("digest failures nonempty", ("digest.failures", ["check_not_mapping"])),
        ]

        for name, (field, value) in cases:
            with self.subTest(name=name):
                rendered_digest = _safe_rendered_digest()
                digest = rendered_digest["digest"]
                assert isinstance(digest, dict)
                if field == "ok_false_reason":
                    rendered_digest["ok"] = False
                    rendered_digest["reason_code"] = "ok"
                    rendered_digest["failures"] = ["check_not_mapping"]
                    digest["cross_phase_ok"] = False
                    digest["reason_code"] = "invalid_cross_phase_digest"
                    digest["failures"] = ["check_not_mapping"]
                    digest["operator_safe"] = False
                elif field == "ok_false_failures":
                    rendered_digest["ok"] = False
                    rendered_digest["reason_code"] = (
                        "invalid_cross_phase_digest"
                    )
                    rendered_digest["failures"] = []
                    digest["cross_phase_ok"] = False
                    digest["reason_code"] = "invalid_cross_phase_digest"
                    digest["failures"] = ["check_not_mapping"]
                    digest["operator_safe"] = False
                elif field.startswith("digest."):
                    digest[field.split(".", 1)[1]] = value
                else:
                    rendered_digest[field] = value

                check = (
                    check_recovery_session_host_verdict_cross_phase_digest_contract(
                        rendered_digest
                    )
                )

                self.assertIn("status_inconsistent", check.failures)

    def test_contract_rejects_hazard_flag_inconsistent(self) -> None:
        cases = [
            (
                "runtime dependency count",
                {
                    "runtime_dependency_count": 1,
                    "has_runtime_dependencies": False,
                },
            ),
            (
                "cli command count",
                {"cli_command_count": 1, "has_cli_commands": False},
            ),
            (
                "restore flag",
                {
                    "restore_supported": True,
                    "has_restore_or_durable_surface": False,
                },
            ),
            (
                "contract failure",
                {"contract_ready": False, "has_contract_failure": False},
            ),
            (
                "drift",
                {
                    "comparison_changed": True,
                    "comparison_change_count": 1,
                    "has_drift": False,
                },
            ),
        ]

        for name, updates in cases:
            with self.subTest(name=name):
                rendered_digest = _safe_rendered_digest()
                digest = rendered_digest["digest"]
                assert isinstance(digest, dict)
                digest["operator_safe"] = False
                digest.update(updates)

                check = (
                    check_recovery_session_host_verdict_cross_phase_digest_contract(
                        rendered_digest
                    )
                )

                self.assertIn("hazard_flag_inconsistent", check.failures)

    def test_contract_failure_order_is_deterministic(self) -> None:
        rendered_digest = _safe_rendered_digest()
        rendered_digest["extra"] = True
        rendered_digest["reason_code"] = "weird"
        rendered_digest["failures"] = ["ok", 123]
        digest = rendered_digest["digest"]
        assert isinstance(digest, dict)
        del digest["operator_safe"]

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertEqual(
            check.failures,
            (
                "payload_shape_mismatch",
                "reason_code_invalid",
                "failures_invalid",
                "digest_shape_mismatch",
            ),
        )

    def test_contract_does_not_mutate_input(self) -> None:
        rendered_digest = _safe_rendered_digest()
        original = copy.deepcopy(rendered_digest)

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )
        render_recovery_session_host_verdict_cross_phase_digest_contract_check(
            check
        )

        self.assertEqual(rendered_digest, original)

    def test_contract_renderer_exact_shape_and_defensive_contract(self) -> None:
        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            _safe_rendered_digest()
        )
        rendered = (
            render_recovery_session_host_verdict_cross_phase_digest_contract_check(
                check
            )
        )

        self.assertEqual(
            set(rendered),
            {"ready", "reason_code", "failures", "contract"},
        )
        rendered["contract"]["digest_keys"].append("x")
        rendered_again = (
            render_recovery_session_host_verdict_cross_phase_digest_contract_check(
                check
            )
        )

        self.assertNotIn("x", rendered_again["contract"]["digest_keys"])

    def test_contract_renderer_does_not_call_checker_or_manifest_builder(
        self,
    ) -> None:
        check = RecoverySessionHostVerdictCrossPhaseDigestContractCheck(
            ready=True,
            reason_code="ready",
            failures=(),
            contract={"surface": "manual", "digest_keys": []},
        )

        with mock.patch.object(
            contract_module,
            "check_recovery_session_host_verdict_cross_phase_digest_contract",
            side_effect=AssertionError("checker called"),
        ), mock.patch.object(
            contract_module,
            "recovery_session_host_verdict_cross_phase_digest_contract_manifest",
            side_effect=AssertionError("manifest builder called"),
        ):
            rendered = (
                render_recovery_session_host_verdict_cross_phase_digest_contract_check(
                    check
                )
            )

        self.assertEqual(rendered["contract"]["surface"], "manual")

    def test_contract_output_json_safe_and_no_runtime_repr(self) -> None:
        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            _safe_rendered_digest()
        )
        rendered = (
            render_recovery_session_host_verdict_cross_phase_digest_contract_check(
                check
            )
        )

        _assert_json_round_trips(self, rendered)
        values = _recursive_values(rendered)
        self.assertFalse(
            any(isinstance(value, (set, frozenset, tuple)) for value in values)
        )
        for value in values:
            if isinstance(value, str):
                self.assertFalse(
                    any(text in value for text in _RUNTIME_REPR_STRINGS)
                )

    def test_contract_module_has_no_runtime_dependencies(self) -> None:
        for name in _RUNTIME_DEPENDENCY_NAMES:
            with self.subTest(name=name):
                self.assertNotIn(name, contract_module.__dict__)

    def test_contract_source_has_no_runtime_call_strings(self) -> None:
        source = inspect.getsource(contract_module)

        for text in _RUNTIME_CALL_STRINGS:
            with self.subTest(text=text):
                self.assertNotIn(text, source)

    def test_contract_public_api_is_exact(self) -> None:
        public_api = {
            name
            for name, value in inspect.getmembers(contract_module)
            if not name.startswith("_")
            and getattr(value, "__module__", None) == contract_module.__name__
            and (inspect.isclass(value) or inspect.isfunction(value))
        }

        self.assertEqual(
            public_api,
            {
                "RecoverySessionHostVerdictCrossPhaseDigestContractCheck",
                "recovery_session_host_verdict_cross_phase_digest_contract_manifest",
                "check_recovery_session_host_verdict_cross_phase_digest_contract",
                "render_recovery_session_host_verdict_cross_phase_digest_contract_check",
            },
        )


if __name__ == "__main__":
    unittest.main()
