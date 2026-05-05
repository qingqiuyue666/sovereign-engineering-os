"""Tracer-bullet tests for the write path contract validator."""

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

from kernel.lifecycle import write_path_contract_validator as validator_module
from kernel.lifecycle.write_path_contract_validator import (
    validate_write_path_contract,
    write_path_contract_validator_manifest,
)


_DIRECT_EXECUTOR_LOCAL_STORE_FORBIDDEN_KEY = (
    "direct_executor_" "sql" "ite_forbidden"
)
_DIRECT_LOCAL_STORE_FORBIDDEN_KEY = "direct_" "sql" "ite_forbidden"
_RUN_DEPS_KEY = "run" "tim" "e_dependencies"


SOURCE_BINDING_VALUES = {
    "source_restore_dry_run_read_only_stack_tag": (
        "restore-dry-run-read-only-stack-v1"
    ),
    "source_restore_dry_run_read_only_stack_commit": (
        "e7c78e3ff0c5dc05806c293f01ab32cd33c9518b"
    ),
    "source_preflight_read_only_stack_tag": "preflight-read-only-stack-v1",
    "source_preflight_read_only_stack_commit": (
        "662b6161253c35204b437e88809c5bab21908c6d"
    ),
    "source_execution_authorization_read_only_stack_tag": (
        "execution-authorization-read-only-stack-v1"
    ),
    "source_execution_authorization_read_only_stack_commit": (
        "d586aeb60620010c900df7be1a88621ab2cb8dc1"
    ),
    "source_executor_precondition_read_only_stack_tag": (
        "executor-precondition-read-only-stack-v1"
    ),
    "source_executor_precondition_read_only_stack_commit": (
        "cb3948eb843866dcc961b6a074038c13db64d017"
    ),
}

SOURCE_BINDING_FAILURES = {
    "source_restore_dry_run_read_only_stack_tag": (
        "source_restore_dry_run_stack_tag_mismatch"
    ),
    "source_restore_dry_run_read_only_stack_commit": (
        "source_restore_dry_run_stack_commit_mismatch"
    ),
    "source_preflight_read_only_stack_tag": (
        "source_preflight_stack_tag_mismatch"
    ),
    "source_preflight_read_only_stack_commit": (
        "source_preflight_stack_commit_mismatch"
    ),
    "source_execution_authorization_read_only_stack_tag": (
        "source_execution_authorization_stack_tag_mismatch"
    ),
    "source_execution_authorization_read_only_stack_commit": (
        "source_execution_authorization_stack_commit_mismatch"
    ),
    "source_executor_precondition_read_only_stack_tag": (
        "source_executor_precondition_stack_tag_mismatch"
    ),
    "source_executor_precondition_read_only_stack_commit": (
        "source_executor_precondition_stack_commit_mismatch"
    ),
}


REQUIRED_REF_FIELDS = (
    "execution_authorization_validator_ci_ref",
    "executor_precondition_validator_ci_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "projected_evidence_ref",
    "target_artifact_id",
    "target_task_id",
    "before_evidence_ref",
)

REQUIRED_OPERATION_FIELDS = (
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
)

REQUIRED_TRUE_FLAGS = (
    "after_evidence_required",
    "outer_transaction_required",
    "kernel_owned_transaction_required",
    "uncontrolled_nested_transactions_forbidden",
    _DIRECT_EXECUTOR_LOCAL_STORE_FORBIDDEN_KEY,
    "partial_mutation_outside_transaction_forbidden",
    "idempotency_reservation_required",
    "idempotency_reservation_before_mutation_required",
    "before_evidence_before_mutation_required",
    "mutation_intent_evidence_before_mutation_required",
    "repository_uow_only_mutation_required",
    "after_evidence_after_mutation_required",
    "deterministic_evidence_audit_order_required",
    "expected_rejection_no_target_mutation_required",
    "unexpected_failure_rollback_required",
    "rollback_failure_incident_required",
    "no_silent_partial_success_required",
    "no_ambiguous_success_required",
    _DIRECT_LOCAL_STORE_FORBIDDEN_KEY,
    "ad_hoc_sql_forbidden",
    "filesystem_side_channel_forbidden",
    "repository_uow_allowlist_required",
    "one_uow_boundary_per_attempt_required",
    "service_side_effects_forbidden",
)

AUTHORIZATION_FLAGS = (
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "repository_uow_writes_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
)


FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "contract_not_mapping",
    "contract_shape_mismatch",
    "contract_surface_invalid",
    "contract_version_invalid",
    "source_restore_dry_run_stack_tag_mismatch",
    "source_restore_dry_run_stack_commit_mismatch",
    "source_preflight_stack_tag_mismatch",
    "source_preflight_stack_commit_mismatch",
    "source_execution_authorization_stack_tag_mismatch",
    "source_execution_authorization_stack_commit_mismatch",
    "source_executor_precondition_stack_tag_mismatch",
    "source_executor_precondition_stack_commit_mismatch",
    "required_ref_invalid",
    "required_operation_field_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "fail_closed_not_declared",
    "json_safe_invalid",
)


EXPECTED_MANIFEST = {
    "surface": "write_path_contract_validator",
    "version": 1,
    "input_shape": "already_rendered_write_path_contract",
    "depends_on": {
        "write_path_transaction_evidence_idempotency_spec_only": (
            "write-path-transaction-evidence-idempotency-spec-only-v1"
        ),
        "executor_precondition_read_only_stack": (
            "executor-precondition-read-only-stack-v1"
        ),
        "execution_authorization_read_only_stack": (
            "execution-authorization-read-only-stack-v1"
        ),
        "preflight_read_only_stack": "preflight-read-only-stack-v1",
        "restore_dry_run_read_only_stack": (
            "restore-dry-run-read-only-stack-v1"
        ),
        "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": (
            "write-side-precondition-checker-v1"
        ),
        "read_only_governance_layer": "read-only-governance-layer-v1",
    },
    "executor_implementation_authorized": False,
    "restore_execution_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "db_repair_authorized": False,
    "repository_uow_writes_authorized": False,
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "durable_writes_authorized": False,
    "irreversible_action_authorized": False,
    "executes_plan": False,
    "opens_db": False,
    "appends_evidence": False,
    _RUN_DEPS_KEY: [],
    "json_safe": True,
    "reason_codes": [
        "invalid_contract_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": list(FAILURE_ORDER),
}


REPR_MARKERS = (
    "WritePathContract(",
    " object at 0x",
    "<sqlite3.",
)


FORBIDDEN_SOURCE_MARKERS = (
    "datetime",
    "time",
    "sqlite",
    "open_connection",
    "Repository",
    "UnitOfWork",
    "KernelUnitOfWork",
    "approval_service",
    "review_service",
    "revision_seal_service",
    "evidence_service",
    "append_audit",
    "append_evidence",
    "subprocess",
    "os.environ",
    "argparse",
    "click",
    "socket",
    "queue",
    "threading",
    "asyncio",
    "datetime.now",
    "time.time",
    "time.monotonic",
    "hashlib",
    "hmac",
    "secrets",
    "sha256",
    "blake2",
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "recovery_session_host",
    "signable_path_orchestrator",
    "apply_migrations",
    "open(",
    "Path(",
    "audit",
    "evidence append",
    "validate_executor_precondition",
    "executor_precondition_validator_manifest",
    "consume_executor_precondition_validator_ci",
    "executor_precondition_validator_ci_manifest",
    "consume_execution_authorization_validator_ci",
    "execution_authorization_validator_ci_manifest",
    "validate_execution_authorization",
    "execution_authorization_validator_manifest",
    "summarize_preflight_readiness",
    "preflight_aggregate_summary_manifest",
    "consume_execution_preflight_ci",
    "execution_preflight_ci_manifest",
    "validate_execution_preflight",
    "execution_preflight_manifest",
    "validate_human_approval_readiness",
    "human_approval_readiness_ci_manifest",
    "summarize_restore_dry_run_readiness",
    "restore_dry_run_aggregate_summary_manifest",
    "governance_readiness_aggregator",
)


ALLOWED_SOURCE_FIELD_STRINGS = (
    "write_path_contract_validator",
    "WritePathTransactionEvidenceIdempotencyV1",
    "write-path-transaction-evidence-idempotency-spec-only-v1",
    "executor-precondition-read-only-stack-v1",
    "execution-authorization-read-only-stack-v1",
    "preflight-read-only-stack-v1",
    "restore-dry-run-read-only-stack-v1",
    "write-side-recovery-spec-only-v1",
    "write_side_precondition_ci",
    "write_side_precondition_checker",
    "projected_evidence_ref",
    "before_evidence_ref",
    "mutation_intent_evidence_before_mutation_required",
    "deterministic_evidence_audit_order_required",
    "evidence_append_authorized",
    "audit_append_authorized",
    "daemon_server_queue_authorized",
)


def _contract(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "WritePathTransactionEvidenceIdempotencyV1",
        "version": 1,
    }
    for name, value in SOURCE_BINDING_VALUES.items():
        base[name] = value
    for index, ref in enumerate(REQUIRED_REF_FIELDS):
        base[ref] = f"ref/{index}/value"
    for index, field in enumerate(REQUIRED_OPERATION_FIELDS):
        base[field] = f"op-{index}-value"
    for flag in REQUIRED_TRUE_FLAGS:
        base[flag] = True
    for flag in AUTHORIZATION_FLAGS:
        base[flag] = False
    base["fail_closed_declared"] = True
    base["json_safe"] = True
    base.update(overrides)
    return base


def _payload(**overrides: object) -> dict[str, object]:
    contract = overrides.pop("contract", None)
    if contract is None:
        contract = _contract()
    payload: dict[str, object] = {"write_path_contract": contract}
    payload.update(overrides)
    return payload


def _expected_happy_output() -> dict[str, object]:
    contract: dict[str, object] = {
        "surface": "write_path_contract_validator",
        "version": 1,
    }
    for name, value in SOURCE_BINDING_VALUES.items():
        contract[name] = value
    for index, ref in enumerate(REQUIRED_REF_FIELDS):
        contract[ref] = f"ref/{index}/value"
    for index, field in enumerate(REQUIRED_OPERATION_FIELDS):
        contract[field] = f"op-{index}-value"
    for flag in REQUIRED_TRUE_FLAGS:
        contract[flag] = True
    for flag in AUTHORIZATION_FLAGS:
        contract[flag] = False
    contract["fail_closed_declared"] = True
    contract["json_safe"] = True
    contract["executes_plan"] = False
    contract["opens_db"] = False
    contract["appends_evidence"] = False
    return {
        "write_path_contract_ready": True,
        "reason_code": "ready",
        "failures": [],
        "contract": contract,
    }


def _recursive_values(payload: object) -> list[object]:
    values: list[object] = [payload]
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
    source = inspect.getsource(validator_module)
    for allowed in ALLOWED_SOURCE_FIELD_STRINGS:
        source = source.replace(allowed, "")
    return source


def _assert_rejected_with(
    payload: object,
    failure: str,
) -> dict[str, object]:
    result = validate_write_path_contract(payload)
    if result["write_path_contract_ready"] is not False:
        raise AssertionError("contract unexpectedly ready")
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        result = validate_write_path_contract(_payload())
        self.assertEqual(result, _expected_happy_output())

    def test_ready_does_not_authorize_executor_restore_writes(self) -> None:
        result = validate_write_path_contract(_payload())
        contract = result["contract"]

        self.assertTrue(result["write_path_contract_ready"])
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(contract[flag], False)
        self.assertIs(contract["executes_plan"], False)
        self.assertIs(contract["opens_db"], False)
        self.assertIs(contract["appends_evidence"], False)

    def test_output_shape_exact(self) -> None:
        result = validate_write_path_contract(_payload())
        self.assertEqual(
            list(result.keys()),
            [
                "write_path_contract_ready",
                "reason_code",
                "failures",
                "contract",
            ],
        )
        contract_keys = list(result["contract"].keys())
        expected_contract_keys = list(_expected_happy_output()["contract"].keys())
        self.assertEqual(contract_keys, expected_contract_keys)


class TopLevelInputTests(unittest.TestCase):
    def test_non_mapping_rejected(self) -> None:
        for candidate in (None, "x", 1, 1.0, [], (), object()):
            with self.subTest(candidate=type(candidate).__name__):
                result = validate_write_path_contract(candidate)
                self.assertFalse(result["write_path_contract_ready"])
                self.assertEqual(result["reason_code"], "invalid_contract_payload")
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key_rejected(self) -> None:
        _assert_rejected_with({}, "payload_shape_mismatch")

    def test_unknown_top_level_key_rejected(self) -> None:
        payload = _payload()
        payload["unexpected"] = "x"
        _assert_rejected_with(payload, "payload_shape_mismatch")


class ContractStructureTests(unittest.TestCase):
    def test_contract_non_mapping_rejected(self) -> None:
        for candidate in (None, "x", 1, [], 1.0):
            with self.subTest(candidate=type(candidate).__name__):
                _assert_rejected_with(
                    {"write_path_contract": candidate},
                    "contract_not_mapping",
                )

    def test_contract_missing_key_rejected(self) -> None:
        contract = _contract()
        del contract["surface"]
        _assert_rejected_with(
            _payload(contract=contract),
            "contract_shape_mismatch",
        )

    def test_contract_unknown_key_rejected(self) -> None:
        contract = _contract()
        contract["unexpected"] = "x"
        _assert_rejected_with(
            _payload(contract=contract),
            "contract_shape_mismatch",
        )

    def test_wrong_contract_surface_rejected(self) -> None:
        contract = _contract(surface="OtherSurface")
        _assert_rejected_with(
            _payload(contract=contract),
            "contract_surface_invalid",
        )

    def test_wrong_version_rejected(self) -> None:
        contract = _contract(version=2)
        _assert_rejected_with(
            _payload(contract=contract),
            "contract_version_invalid",
        )

    def test_bool_as_int_version_rejected(self) -> None:
        contract = _contract(version=True)
        _assert_rejected_with(
            _payload(contract=contract),
            "contract_version_invalid",
        )


class SourceBindingTests(unittest.TestCase):
    def _assert_tag_mismatch(self, field: str) -> None:
        contract = _contract()
        contract[field] = "wrong-tag"
        result = _assert_rejected_with(
            _payload(contract=contract),
            SOURCE_BINDING_FAILURES[field],
        )
        self.assertNotIn("contract_shape_mismatch", result["failures"])

    def test_source_restore_stack_tag_mismatch(self) -> None:
        self._assert_tag_mismatch(
            "source_restore_dry_run_read_only_stack_tag",
        )

    def test_source_restore_stack_commit_mismatch(self) -> None:
        self._assert_tag_mismatch(
            "source_restore_dry_run_read_only_stack_commit",
        )

    def test_source_preflight_stack_tag_mismatch(self) -> None:
        self._assert_tag_mismatch("source_preflight_read_only_stack_tag")

    def test_source_preflight_stack_commit_mismatch(self) -> None:
        self._assert_tag_mismatch("source_preflight_read_only_stack_commit")

    def test_source_execution_authorization_stack_tag_mismatch(self) -> None:
        self._assert_tag_mismatch(
            "source_execution_authorization_read_only_stack_tag",
        )

    def test_source_execution_authorization_stack_commit_mismatch(self) -> None:
        self._assert_tag_mismatch(
            "source_execution_authorization_read_only_stack_commit",
        )

    def test_source_executor_precondition_stack_tag_mismatch(self) -> None:
        self._assert_tag_mismatch(
            "source_executor_precondition_read_only_stack_tag",
        )

    def test_source_executor_precondition_stack_commit_mismatch(self) -> None:
        self._assert_tag_mismatch(
            "source_executor_precondition_read_only_stack_commit",
        )


class RequiredRefTests(unittest.TestCase):
    def test_each_required_ref_invalid_rejected(self) -> None:
        for field in REQUIRED_REF_FIELDS:
            for bad in (None, "", 1, [], {}, True, 1.0):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract()
                    contract[field] = bad
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "required_ref_invalid",
                    )


class RequiredOperationTests(unittest.TestCase):
    def test_each_required_operation_field_invalid_rejected(self) -> None:
        for field in REQUIRED_OPERATION_FIELDS:
            for bad in (None, "", 1, [], {}, True, 1.0):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract()
                    contract[field] = bad
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "required_operation_field_invalid",
                    )


class RequiredDeclarationTests(unittest.TestCase):
    def test_each_required_declaration_non_bool_rejected(self) -> None:
        for flag in REQUIRED_TRUE_FLAGS:
            for bad in (None, "true", 1, 0, [], {}):
                with self.subTest(flag=flag, bad=type(bad).__name__):
                    contract = _contract()
                    contract[flag] = bad
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "required_declaration_invalid",
                    )

    def test_each_required_declaration_false_rejected(self) -> None:
        for flag in REQUIRED_TRUE_FLAGS:
            with self.subTest(flag=flag):
                contract = _contract()
                contract[flag] = False
                _assert_rejected_with(
                    _payload(contract=contract),
                    "required_declaration_false",
                )


class AuthorizationFlagTests(unittest.TestCase):
    def test_each_authorization_flag_non_bool_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            for bad in (None, "false", 1, 0, [], {}):
                with self.subTest(flag=flag, bad=type(bad).__name__):
                    contract = _contract()
                    contract[flag] = bad
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "authorization_flag_invalid",
                    )

    def test_each_authorization_flag_true_rejected(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                contract = _contract()
                contract[flag] = True
                _assert_rejected_with(
                    _payload(contract=contract),
                    "authorization_flag_true",
                )


class FailClosedTests(unittest.TestCase):
    def test_fail_closed_declared_false_rejected(self) -> None:
        contract = _contract(fail_closed_declared=False)
        _assert_rejected_with(
            _payload(contract=contract),
            "fail_closed_not_declared",
        )

    def test_fail_closed_declared_non_bool_rejected(self) -> None:
        for bad in (None, "true", 1, 0, [], {}):
            with self.subTest(bad=type(bad).__name__):
                contract = _contract(fail_closed_declared=bad)
                _assert_rejected_with(
                    _payload(contract=contract),
                    "fail_closed_not_declared",
                )


class JsonSafeTests(unittest.TestCase):
    def test_json_safe_false_rejected(self) -> None:
        contract = _contract(json_safe=False)
        _assert_rejected_with(
            _payload(contract=contract),
            "json_safe_invalid",
        )

    def test_json_safe_non_bool_rejected(self) -> None:
        for bad in (None, "true", 1, 0, [], {}):
            with self.subTest(bad=type(bad).__name__):
                contract = _contract(json_safe=bad)
                _assert_rejected_with(
                    _payload(contract=contract),
                    "json_safe_invalid",
                )


class FailureOrderingTests(unittest.TestCase):
    def test_combined_failures_deterministic_order(self) -> None:
        contract = _contract(
            surface="OtherSurface",
            version=2,
            fail_closed_declared=False,
            json_safe=False,
        )
        contract["source_preflight_read_only_stack_tag"] = "wrong-tag"
        contract["execution_authorization_validator_ci_ref"] = ""
        contract["approved_task_id"] = ""
        contract["after_evidence_required"] = False
        contract["executor_implementation_authorized"] = True
        result = validate_write_path_contract(_payload(contract=contract))
        self.assertFalse(result["write_path_contract_ready"])
        positions = [FAILURE_ORDER.index(item) for item in result["failures"]]
        self.assertEqual(positions, sorted(positions))


class ManifestTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = write_path_contract_validator_manifest()
        self.assertEqual(manifest, EXPECTED_MANIFEST)

    def test_manifest_defensive_copy(self) -> None:
        first = write_path_contract_validator_manifest()
        first["mutated"] = "x"
        first["depends_on"]["mutated"] = "y"
        first["failure_values"].append("mutated")
        second = write_path_contract_validator_manifest()
        self.assertEqual(second, EXPECTED_MANIFEST)
        self.assertNotIn("mutated", second)
        self.assertNotIn("mutated", second["depends_on"])


class JsonSafetyTests(unittest.TestCase):
    def test_output_json_safe(self) -> None:
        result = validate_write_path_contract(_payload())
        _assert_json_safe(result)

    def test_no_runtime_repr_leakage(self) -> None:
        result = validate_write_path_contract(_payload())
        _assert_no_runtime_repr(result)

    def test_manifest_json_safe(self) -> None:
        manifest = write_path_contract_validator_manifest()
        _assert_json_safe(manifest)


class InputImmutabilityTests(unittest.TestCase):
    def test_input_not_mutated(self) -> None:
        payload = _payload()
        snapshot = copy.deepcopy(payload)
        validate_write_path_contract(payload)
        self.assertEqual(payload, snapshot)


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(validator_module.__all__),
            sorted(
                [
                    "write_path_contract_validator_manifest",
                    "validate_write_path_contract",
                ]
            ),
        )

    def test_signatures(self) -> None:
        manifest_sig = inspect.signature(write_path_contract_validator_manifest)
        self.assertEqual(list(manifest_sig.parameters.keys()), [])
        validate_sig = inspect.signature(validate_write_path_contract)
        self.assertEqual(list(validate_sig.parameters.keys()), ["payload"])


class SourceBoundaryTests(unittest.TestCase):
    def test_source_boundary(self) -> None:
        source = _scrubbed_source()
        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_datetime_or_time_import(self) -> None:
        source = inspect.getsource(validator_module)
        self.assertNotIn("import datetime", source)
        self.assertNotIn("from datetime", source)
        self.assertNotIn("import time", source)
        self.assertNotIn("from time", source)

    def test_no_hidden_wall_clock_dependency(self) -> None:
        source = inspect.getsource(validator_module)
        for marker in (
            "datetime.now",
            "time.time",
            "time.monotonic",
            "perf_counter",
            "wall_clock",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_timestamp_parsing(self) -> None:
        source = inspect.getsource(validator_module)
        for marker in (
            "fromisoformat",
            "strptime",
            "isoformat",
            "tzinfo",
            "utcoffset",
            "timezone",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_digest_computation(self) -> None:
        source = inspect.getsource(validator_module)
        for marker in (
            "hashlib",
            "hmac",
            "secrets",
            "sha1",
            "sha256",
            "sha512",
            "blake2",
            "md5",
            "digest",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_upstream_service_db_cli_or_recovery_imports(self) -> None:
        source = _scrubbed_source()
        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
