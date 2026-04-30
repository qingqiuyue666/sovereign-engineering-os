"""Tracer-bullet tests for the write-side precondition CI projection."""

from __future__ import annotations

import copy
import inspect
import json
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle import write_side_recovery_precondition_ci as ci_module
from kernel.lifecycle.write_side_recovery_precondition_ci import (
    consume_write_side_recovery_precondition_ci,
    write_side_recovery_precondition_ci_manifest,
)


EXPECTED_MANIFEST = {
    "surface": "write_side_recovery_precondition_ci",
    "version": 1,
    "input_shape": "rendered_write_side_recovery_precondition_check",
    "restore_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "durable_writes": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": ["invalid_ci_payload", "not_ready", "ready"],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "payload_failures_invalid",
        "preconditions_invalid",
        "preconditions_shape_mismatch",
        "preconditions_surface_invalid",
        "preconditions_version_invalid",
        "readiness_flag_invalid",
        "readiness_flag_not_ready",
        "authorization_flag_invalid",
        "authorization_flag_true",
        "json_safe_invalid",
        "checker_not_ready",
    ],
}

EXPECTED_OUTPUT_KEYS = [
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "contract_ready",
    "contract_reason_code",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "json_safe",
]

READINESS_FLAGS = (
    "source_truth_ready",
    "governance_ready",
    "target_task_ready",
    "evidence_replay_ready",
    "approval_review_ready",
    "human_approval_ready",
    "dry_run_ready",
    "idempotency_ready",
    "evidence_snapshot_ready",
    "transaction_ready",
    "rollback_ready",
    "schema_migration_safe",
    "runtime_boundary_safe",
    "operator_confirmation_ready",
    "operator_safe",
)

AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
)

REPR_MARKERS = (
    "WriteSideRecoveryPreconditionCheck(",
    " object at 0x",
    "<sqlite3.",
)

FORBIDDEN_SOURCE_MARKERS = (
    "sqlite",
    "open_connection",
    "Repository",
    "UnitOfWork",
    "KernelUnitOfWork",
    "subprocess",
    "os.environ",
    "argparse",
    "click",
    "socket",
    "queue",
    "threading",
    "asyncio",
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "recovery_session_host",
    "signable_path_orchestrator",
    "apply_migrations",
    "open(",
    "Path(",
    "audit",
    "evidence",
    "check_write_side_recovery_preconditions",
    "render_write_side_recovery_precondition_check",
    "governance_readiness_aggregator",
    "approval_review_readiness",
    "evidence_replay_readiness",
    "task_lifecycle_journal_snapshot",
)

ALLOWED_SOURCE_FIELD_STRINGS = (
    "evidence_replay_ready",
    "evidence_snapshot_ready",
    "daemon_server_queue_authorized",
)


def _valid_preconditions(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "write_side_recovery_precondition_check",
        "version": 1,
        "source_truth_ready": True,
        "governance_ready": True,
        "target_task_ready": True,
        "evidence_replay_ready": True,
        "approval_review_ready": True,
        "human_approval_ready": True,
        "dry_run_ready": True,
        "idempotency_ready": True,
        "evidence_snapshot_ready": True,
        "transaction_ready": True,
        "rollback_ready": True,
        "schema_migration_safe": True,
        "runtime_boundary_safe": True,
        "operator_confirmation_ready": True,
        "operator_safe": True,
        "restore_authorized": False,
        "write_side_recovery_authorized": False,
        "cli_execution_authorized": False,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "json_safe": True,
    }
    base.update(overrides)
    return base


def _valid_payload(**overrides: object) -> dict[str, object]:
    preconditions = overrides.pop("preconditions", _valid_preconditions())
    base: dict[str, object] = {
        "ready": True,
        "reason_code": "ready",
        "failures": [],
        "preconditions": preconditions,
    }
    base.update(overrides)
    return base


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


def _assert_json_safe(payload: object) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    decoded = json.loads(encoded)
    if decoded != payload:
        raise AssertionError("payload did not round-trip through JSON")
    for value in _recursive_values(payload):
        if isinstance(value, (set, frozenset, tuple)):
            raise AssertionError(
                f"payload leaked runtime collection {type(value).__name__}"
            )


def _assert_no_runtime_repr(payload: object) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    for marker in REPR_MARKERS:
        if marker in encoded:
            raise AssertionError(f"runtime repr marker leaked: {marker}")


def _scrubbed_source() -> str:
    source = inspect.getsource(ci_module)
    for allowed in ALLOWED_SOURCE_FIELD_STRINGS:
        source = source.replace(allowed, "")
    return source


class HappyPathTests(unittest.TestCase):
    def test_valid_rendered_checker_output_returns_ci_ok_true(self) -> None:
        result = consume_write_side_recovery_precondition_ci(_valid_payload())

        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["surface"], "write_side_recovery_precondition_check"
        )
        self.assertEqual(result["version"], 1)
        self.assertIs(result["contract_ready"], True)
        self.assertEqual(result["contract_reason_code"], "ready")
        for flag in AUTHORIZATION_FLAGS:
            self.assertIs(result[flag], False, flag)
        self.assertIs(result["json_safe"], True)


class PayloadValidationTests(unittest.TestCase):
    def test_non_mapping_input_rejected(self) -> None:
        for payload in (None, 1, "x", [1, 2], (1, 2)):
            with self.subTest(payload=payload):
                result = consume_write_side_recovery_precondition_ci(payload)

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_top_level_missing_key_rejected(self) -> None:
        payload = _valid_payload()
        del payload["ready"]

        result = consume_write_side_recovery_precondition_ci(payload)

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])

    def test_top_level_unknown_key_rejected(self) -> None:
        payload = _valid_payload()
        payload["extra"] = True

        result = consume_write_side_recovery_precondition_ci(payload)

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])

    def test_ready_not_bool_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(ready=1)
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])
        self.assertIs(result["contract_ready"], False)

    def test_reason_code_not_str_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(reason_code=1)
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])
        self.assertEqual(result["contract_reason_code"], "invalid_ci_payload")

    def test_failures_not_list_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(failures=("x",))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_failures_invalid"])

    def test_failures_list_with_non_string_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(failures=["x", 1])
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_failures_invalid"])

    def test_preconditions_not_mapping_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(preconditions=[])
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["preconditions_invalid"])
        self.assertIsNone(result["surface"])
        self.assertIsNone(result["version"])


class PreconditionsValidationTests(unittest.TestCase):
    def test_missing_precondition_key_rejected(self) -> None:
        preconditions = _valid_preconditions()
        del preconditions["operator_safe"]

        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(preconditions=preconditions)
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["preconditions_shape_mismatch"])

    def test_unknown_precondition_key_rejected(self) -> None:
        preconditions = _valid_preconditions(extra=True)

        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(preconditions=preconditions)
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["preconditions_shape_mismatch"])

    def test_wrong_surface_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(
                preconditions=_valid_preconditions(surface="wrong")
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["preconditions_surface_invalid"])
        self.assertEqual(result["surface"], "wrong")

    def test_wrong_version_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(preconditions=_valid_preconditions(version=2))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["preconditions_version_invalid"])
        self.assertEqual(result["version"], 2)

    def test_bool_as_int_version_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(preconditions=_valid_preconditions(version=True))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["preconditions_version_invalid"])
        self.assertIsNone(result["version"])

    def test_readiness_flag_non_bool_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(
                preconditions=_valid_preconditions(source_truth_ready="yes")
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["readiness_flag_invalid"])

    def test_readiness_flag_false_returns_not_ready(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(
                preconditions=_valid_preconditions(governance_ready=False)
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["readiness_flag_not_ready"])

    def test_authorization_flag_non_bool_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(
                preconditions=_valid_preconditions(restore_authorized="no")
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["authorization_flag_invalid"])
        self.assertIsNone(result["restore_authorized"])

    def test_authorization_flag_true_returns_not_ready(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(
                preconditions=_valid_preconditions(
                    restore_authorized=True
                )
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["authorization_flag_true"])
        self.assertIs(result["restore_authorized"], True)

    def test_json_safe_false_returns_not_ready(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(preconditions=_valid_preconditions(json_safe=False))
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertIs(result["json_safe"], False)

    def test_json_safe_non_bool_rejected(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(preconditions=_valid_preconditions(json_safe="yes"))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertIsNone(result["json_safe"])


class CheckerReadinessSemanticsTests(unittest.TestCase):
    def test_ready_false_returns_not_ready_with_checker_not_ready(
        self,
    ) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(ready=False)
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["checker_not_ready"])
        self.assertIs(result["contract_ready"], False)

    def test_reason_code_not_ready_returns_not_ready(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(reason_code="not_ready")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["checker_not_ready"])
        self.assertEqual(result["contract_reason_code"], "not_ready")

    def test_failures_non_empty_returns_not_ready(self) -> None:
        result = consume_write_side_recovery_precondition_ci(
            _valid_payload(failures=["checker_detail"])
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["checker_not_ready"])

    def test_combined_failures_use_deterministic_order(self) -> None:
        preconditions = _valid_preconditions(
            surface="wrong",
            version=True,
            source_truth_ready="bad",
            governance_ready=False,
            restore_authorized="bad",
            write_side_recovery_authorized=True,
            json_safe=False,
        )
        payload = _valid_payload(
            ready=False,
            reason_code="not_ready",
            failures=["checker_detail"],
            preconditions=preconditions,
        )
        payload["extra"] = True

        result = consume_write_side_recovery_precondition_ci(payload)

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(
            result["failures"],
            [
                "payload_shape_mismatch",
                "preconditions_surface_invalid",
                "preconditions_version_invalid",
                "readiness_flag_invalid",
                "readiness_flag_not_ready",
                "authorization_flag_invalid",
                "authorization_flag_true",
                "json_safe_invalid",
                "checker_not_ready",
            ],
        )


class SafetyAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = write_side_recovery_precondition_ci_manifest()

        self.assertEqual(list(manifest.keys()), list(EXPECTED_MANIFEST.keys()))
        self.assertEqual(manifest, EXPECTED_MANIFEST)

    def test_manifest_defensive_copy(self) -> None:
        manifest = write_side_recovery_precondition_ci_manifest()
        manifest["surface"] = "tampered"
        manifest["failure_values"].append("injected")  # type: ignore[union-attr]

        self.assertEqual(
            write_side_recovery_precondition_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_output_json_safe(self) -> None:
        result = consume_write_side_recovery_precondition_ci(_valid_payload())

        _assert_json_safe(result)

    def test_no_runtime_repr_leakage(self) -> None:
        result = consume_write_side_recovery_precondition_ci(_valid_payload())

        _assert_no_runtime_repr(result)

    def test_input_not_mutated(self) -> None:
        payload = _valid_payload()
        snapshot = copy.deepcopy(payload)

        consume_write_side_recovery_precondition_ci(payload)

        self.assertEqual(payload, snapshot)

    def test_public_api_exact(self) -> None:
        public = sorted(
            name for name in dir(ci_module) if not name.startswith("_")
        )

        self.assertEqual(
            public,
            [
                "consume_write_side_recovery_precondition_ci",
                "write_side_recovery_precondition_ci_manifest",
            ],
        )
        self.assertEqual(
            sorted(ci_module.__all__),
            [
                "consume_write_side_recovery_precondition_ci",
                "write_side_recovery_precondition_ci_manifest",
            ],
        )

    def test_source_boundary_has_no_forbidden_symbols(self) -> None:
        source = _scrubbed_source()

        for marker in FORBIDDEN_SOURCE_MARKERS:
            self.assertNotIn(marker, source, marker)


if __name__ == "__main__":
    unittest.main()
