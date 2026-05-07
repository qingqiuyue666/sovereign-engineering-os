"""Tracer bullets for the append authority service boundary validator CI."""

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

import kernel.lifecycle.append_runtime_authority_service_boundary_validator_ci as ci_module
from kernel.lifecycle.append_runtime_authority_service_boundary_validator_ci import (
    append_runtime_authority_service_boundary_validator_ci_manifest,
    consume_append_runtime_authority_service_boundary_validator_ci,
)


SOURCE_BINDING_VALUES = {
    "source_read_only_governance_layer_tag": (
        "read-only-governance-layer-v1"
    ),
    "source_read_only_governance_layer_commit": (
        "4656e8f03404c6bb39e7976c6165e3d7dc0314fb"
    ),
    "source_write_side_precondition_checker_tag": (
        "write-side-precondition-checker-v1"
    ),
    "source_write_side_precondition_checker_commit": (
        "fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6"
    ),
    "source_write_side_precondition_ci_tag": (
        "write-side-precondition-ci-v1"
    ),
    "source_write_side_precondition_ci_commit": (
        "05c81541ad3d7deee20023843142f702937f6c3f"
    ),
    "source_write_side_recovery_spec_only_tag": (
        "write-side-recovery-spec-only-v1"
    ),
    "source_write_side_recovery_spec_only_commit": (
        "ad560cc2dab135f2c1d56d948410ae47586d118e"
    ),
    "source_restore_dry_run_read_only_stack_tag": (
        "restore-dry-run-read-only-stack-v1"
    ),
    "source_restore_dry_run_read_only_stack_commit": (
        "e7c78e3ff0c5dc05806c293f01ab32cd33c9518b"
    ),
    "source_preflight_read_only_stack_tag": (
        "preflight-read-only-stack-v1"
    ),
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
    "source_write_path_read_only_stack_tag": (
        "write-path-read-only-stack-v1"
    ),
    "source_write_path_read_only_stack_commit": (
        "8ffd4679aca8f593415089748df35df42af8f015"
    ),
    "source_repository_uow_allowlist_read_only_stack_tag": (
        "repository-uow-allowlist-read-only-stack-v1"
    ),
    "source_repository_uow_allowlist_read_only_stack_commit": (
        "bec2d04eab1922594dcbfbe35971f4efe0fe4849"
    ),
    "source_evidence_audit_append_read_only_stack_tag": (
        "evidence-audit-append-read-only-stack-v1"
    ),
    "source_evidence_audit_append_read_only_stack_commit": (
        "62db8a586efa9375d2c77cf7c6335ccf5ef11279"
    ),
    "source_append_runtime_authority_service_boundary_spec_only_tag": (
        "append-runtime-authority-service-boundary-spec-only-v1"
    ),
    "source_append_runtime_authority_service_boundary_spec_only_commit": (
        "5b48c6537702ee9d9dc52b39f28399166096754b"
    ),
}

VALIDATOR_BINDING_VALUES = {
    "source_append_runtime_authority_service_boundary_validator_tag": (
        "append-runtime-authority-service-boundary-validator-v1"
    ),
    "source_append_runtime_authority_service_boundary_validator_commit": (
        "19af3abba5be4ae44ff2aa58a883ee2c99da6cb0"
    ),
}

OPERATION_REFS = (
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "append_contract_ref",
    "append_idempotency_key",
    "human_approval_ref",
    "operator_confirmation_ref",
    "execution_authorization_validator_ci_ref",
    "executor_precondition_validator_ci_ref",
    "write_path_contract_validator_ci_ref",
    "repository_uow_allowlist_validator_ci_ref",
    "evidence_audit_append_contract_validator_ci_ref",
    "append_runtime_authority_contract_ref",
)

OPERATION_REF_VALUES = {name: f"{name}-value" for name in OPERATION_REFS}

RUNTIME_AUTHORITY_DECLARATIONS = (
    "append_authority_explicit_only",
    "evidence_append_authority_explicit_only",
    "audit_append_authority_explicit_only",
    "service_authority_explicit_only",
    "db_authority_explicit_only",
    "repository_uow_authority_explicit_only",
    "transaction_authority_explicit_only",
    "idempotency_reservation_authority_explicit_only",
    "rollback_authority_explicit_only",
    "executor_authority_explicit_only",
    "read_only_success_grants_no_runtime_authority",
    "authority_source_bound_required",
    "authority_operation_bound_required",
    "authority_narrow_required",
    "authority_revocable_required",
    "authority_fail_closed_required",
)

SERVICE_BOUNDARY_DECLARATIONS = (
    "evidence_service_append_forbidden",
    "approval_service_forbidden",
    "review_service_forbidden",
    "revision_seal_service_forbidden",
    "service_adapter_required_for_future_runtime",
    "service_method_allowlist_required",
    "service_result_contract_required",
    "service_transaction_ownership_forbidden_by_default",
    "evidence_audit_ref_fabrication_forbidden",
    "service_calls_forbidden_in_spec_only_package",
)

DB_REPOSITORY_UOW_BOUNDARY_DECLARATIONS = (
    "direct_sqlite_forbidden",
    "ad_hoc_sql_forbidden",
    "repository_uow_import_forbidden",
    "repository_uow_call_forbidden",
    "kernel_owned_uow_required_for_future_runtime",
    "repository_method_allowlist_required",
    "repository_result_contract_required",
    "evidence_bearing_result_required",
    "executor_transaction_ownership_forbidden",
    "uncontrolled_nested_transaction_forbidden",
)

IDEMPOTENCY_DECLARATIONS = (
    "idempotency_reservation_required_before_mutation_or_append",
    "append_idempotency_key_binding_required",
    "same_key_same_binding_safe_replay_only",
    "same_key_different_binding_fail_closed",
    "ambiguous_reservation_incident_class",
    "replay_classification_required",
    "idempotency_runtime_not_authorized",
)

TRANSACTION_DECLARATIONS = (
    "one_outer_kernel_owned_transaction_required",
    "append_mutation_order_required",
    "commit_after_required_bookkeeping_only",
    "rollback_on_unexpected_exception_required",
    "rollback_failure_incident_class",
    "out_of_band_append_requires_explicit_declaration",
    "transaction_runtime_not_authorized",
)

APPEND_PHASE_AUTHORITY_DECLARATIONS = (
    "before_evidence_append_authority_required",
    "mutation_intent_evidence_append_authority_required",
    "after_evidence_append_authority_required",
    "rejection_evidence_append_authority_required",
    "failure_evidence_append_authority_required",
    "rollback_evidence_append_authority_required",
    "audit_event_append_authority_required",
    "duplicate_replay_audit_append_authority_required",
    "ambiguous_replay_audit_append_authority_required",
    "incident_audit_append_authority_required",
    "per_phase_authorization_required",
)

FAILURE_INCIDENT_DECLARATIONS = (
    "expected_rejection_is_not_execution_failure",
    "unexpected_exception_requires_rollback",
    "append_failure_before_mutation_blocks_mutation",
    "append_failure_after_mutation_is_incident_class",
    "rollback_failure_is_incident_class",
    "duplicate_mismatched_idempotency_is_incident_class",
    "ambiguous_append_or_replay_is_incident_class",
    "partial_success_forbidden",
    "success_requires_all_required_append_bookkeeping",
    "silent_success_forbidden",
)

FUTURE_VALIDATOR_DECLARATIONS = (
    "future_validator_consumes_already_rendered_declaration_only",
    "future_validator_validates_source_bindings",
    "future_validator_validates_operation_bindings",
    "future_validator_validates_service_boundaries",
    "future_validator_validates_db_repository_uow_boundaries",
    "future_validator_validates_idempotency_declarations",
    "future_validator_validates_transaction_declarations",
    "future_validator_validates_rollback_failure_incident_declarations",
    "future_validator_validates_append_phase_authority_declarations",
    "future_validator_validates_false_authority_flags",
    "future_validator_validates_json_safety",
    "future_validator_calls_no_services",
    "future_validator_opens_no_db",
    "future_validator_imports_no_repository_uow",
    "future_validator_appends_no_evidence_audit",
    "future_validator_implements_no_runtime",
)

FUTURE_CI_DECLARATIONS = (
    "future_ci_consumes_already_rendered_validator_output_only",
    "future_ci_calls_no_validator",
    "future_ci_validates_bounded_shape",
    "future_ci_validates_false_authority_flags",
    "future_ci_validates_json_safety",
    "future_ci_calls_no_services",
    "future_ci_opens_no_db",
    "future_ci_imports_no_repository_uow",
    "future_ci_appends_no_evidence_audit",
    "future_ci_implements_no_runtime",
)

DECLARATION_GROUPS = (
    RUNTIME_AUTHORITY_DECLARATIONS,
    SERVICE_BOUNDARY_DECLARATIONS,
    DB_REPOSITORY_UOW_BOUNDARY_DECLARATIONS,
    IDEMPOTENCY_DECLARATIONS,
    TRANSACTION_DECLARATIONS,
    APPEND_PHASE_AUTHORITY_DECLARATIONS,
    FAILURE_INCIDENT_DECLARATIONS,
    FUTURE_VALIDATOR_DECLARATIONS,
    FUTURE_CI_DECLARATIONS,
)

REQUIRED_DECLARATIONS = tuple(
    field for group in DECLARATION_GROUPS for field in group
)

AUTHORIZATION_FLAGS = (
    "append_runtime_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "evidence_service_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "repository_uow_writes_authorized",
    "direct_db_writes_authorized",
    "raw_sqlite_authorized",
    "ad_hoc_sql_authorized",
    "transaction_runtime_authorized",
    "idempotency_reservation_authorized",
    "rollback_runtime_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
)

RUNTIME_FLAGS = (
    "appends_evidence",
    "appends_audit",
    "calls_evidence_service",
    "calls_services",
    "opens_db",
    "calls_repository",
    "calls_uow",
    "executes_plan",
    "opens_transaction",
    "reserves_idempotency",
    "performs_rollback",
    "performs_runtime_append",
)

VALIDATOR_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "authority_not_mapping",
    "authority_shape_mismatch",
    "authority_surface_invalid",
    "authority_version_invalid",
    "source_ref_mismatch",
    "operation_ref_invalid",
    "evidence_ref_set_invalid",
    "audit_ref_set_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "runtime_flag_invalid",
    "runtime_flag_true",
    "json_safe_invalid",
)

CI_FAILURE_ORDER = [
    "payload_not_mapping",
    "payload_shape_mismatch",
    "authority_not_mapping",
    "authority_shape_mismatch",
    "validator_surface_invalid",
    "validator_version_invalid",
    "validator_readiness_invalid",
    "validator_reason_code_invalid",
    "validator_failures_invalid",
    "validator_failure_unknown",
    "source_ref_mismatch",
    "operation_ref_invalid",
    "evidence_ref_set_invalid",
    "audit_ref_set_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "runtime_flag_invalid",
    "runtime_flag_true",
    "json_safe_invalid",
]

EXPECTED_MANIFEST = {
    "surface": "append_runtime_authority_service_boundary_validator_ci",
    "version": 1,
    "input_shape": (
        "already_rendered_append_runtime_authority_service_boundary_"
        "validator_output_v1"
    ),
    "depends_on": {
        "append_runtime_authority_service_boundary_validator": (
            "append-runtime-authority-service-boundary-validator-v1"
        ),
        "append_runtime_authority_service_boundary_spec_only": (
            "append-runtime-authority-service-boundary-spec-only-v1"
        ),
        "evidence_audit_append_read_only_stack": (
            "evidence-audit-append-read-only-stack-v1"
        ),
        "repository_uow_allowlist_read_only_stack": (
            "repository-uow-allowlist-read-only-stack-v1"
        ),
        "write_path_read_only_stack": "write-path-read-only-stack-v1",
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
    "ci_ok_authorizes_append": False,
    "ci_ok_authorizes_write": False,
    "append_runtime_authorized": False,
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "evidence_service_authorized": False,
    "approval_service_authorized": False,
    "review_service_authorized": False,
    "revision_seal_service_authorized": False,
    "repository_uow_writes_authorized": False,
    "direct_db_writes_authorized": False,
    "raw_sqlite_authorized": False,
    "ad_hoc_sql_authorized": False,
    "transaction_runtime_authorized": False,
    "idempotency_reservation_authorized": False,
    "rollback_runtime_authorized": False,
    "durable_writes_authorized": False,
    "irreversible_action_authorized": False,
    "executor_implementation_authorized": False,
    "restore_execution_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "db_repair_authorized": False,
    "appends_evidence": False,
    "appends_audit": False,
    "calls_evidence_service": False,
    "calls_services": False,
    "opens_db": False,
    "calls_repository": False,
    "calls_uow": False,
    "executes_plan": False,
    "opens_transaction": False,
    "reserves_idempotency": False,
    "performs_rollback": False,
    "performs_runtime_append": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        "invalid_ci_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": CI_FAILURE_ORDER,
}

EXPECTED_OUTPUT_KEYS = [
    "ci_ok",
    "reason_code",
    "failures",
    "authority",
]

EXPECTED_AUTHORITY_OUTPUT_KEYS = (
    ["surface", "version"]
    + list(SOURCE_BINDING_VALUES.keys())
    + list(VALIDATOR_BINDING_VALUES.keys())
    + list(OPERATION_REFS)
    + ["evidence_ref_set", "audit_ref_set"]
    + list(REQUIRED_DECLARATIONS)
    + list(AUTHORIZATION_FLAGS)
    + list(RUNTIME_FLAGS)
    + ["json_safe"]
)

REPR_MARKERS = (
    "AppendRuntimeAuthorityServiceBoundary(",
    " object at 0x",
    "<sqlite3.",
)

FORBIDDEN_SOURCE_MARKERS = (
    "datetime.now",
    "time.time",
    "time.monotonic",
    "hashlib",
    "hmac",
    "secrets",
    "sha256",
    "blake2",
    "open(",
    "Path(",
    "os.environ",
    "subprocess",
    "threading",
    "asyncio",
    "socket",
    "argparse",
    "click",
    "inspect.",
    "getattr(",
    "callable(",
    "dir(",
    "hasattr(",
    "importlib",
    "open_connection",
    "UnitOfWork",
    "KernelUnitOfWork",
    "approval_service.",
    "review_service.",
    "revision_seal_service.",
    "evidence_service.",
    "append_audit",
    "append_evidence",
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "recovery_session_host",
    "signable_path_orchestrator",
    "apply_migrations",
    "validate_write_path_contract",
    "write_path_contract_validator_manifest",
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
    "repository_uow_allowlist_validator_manifest(",
    "validate_repository_uow_allowlist(",
    "consume_repository_uow_allowlist_validator_ci(",
    "repository_uow_allowlist_validator_ci_manifest(",
    "EvidenceService",
    "validate_evidence_audit_append_contract(",
    "evidence_audit_append_contract_validator_manifest(",
    "consume_evidence_audit_append_contract_validator_ci(",
    "evidence_audit_append_contract_validator_ci_manifest(",
    "append_runtime_authority_service_boundary_validator_manifest(",
    "validate_append_runtime_authority_service_boundary(",
    "begin_transaction",
    "commit(",
    "rollback(",
    "reserve_idempotency",
    "append_runtime",
    "performs_runtime_append",
)

ALLOWED_SOURCE_FIELD_STRINGS = (
    "append_runtime_authority_service_boundary_validator_ci",
    "append_runtime_authority_service_boundary_validator_ci_manifest",
    "consume_append_runtime_authority_service_boundary_validator_ci",
    "append_runtime_authority_service_boundary_validator",
    "append_runtime_authority_service_boundary_spec_only",
    "append-runtime-authority-service-boundary-validator-v1",
    "append-runtime-authority-service-boundary-spec-only-v1",
    "evidence-audit-append-read-only-stack-v1",
    "repository-uow-allowlist-read-only-stack-v1",
    "write-path-read-only-stack-v1",
    "executor-precondition-read-only-stack-v1",
    "execution-authorization-read-only-stack-v1",
    "preflight-read-only-stack-v1",
    "restore-dry-run-read-only-stack-v1",
    "append_runtime_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "evidence_service_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "transaction_runtime_authorized",
    "idempotency_reservation_authorized",
    "rollback_runtime_authorized",
    "appends_evidence",
    "appends_audit",
    "opens_transaction",
    "reserves_idempotency",
    "performs_rollback",
    "performs_runtime_append",
    "append_runtime_authority_contract_ref",
)

DEFAULT_AUTHORITY = object()


def _authority(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "append_runtime_authority_service_boundary_validator",
        "version": 1,
    }
    base.update(SOURCE_BINDING_VALUES)
    base.update(VALIDATOR_BINDING_VALUES)
    base.update(OPERATION_REF_VALUES)
    base["evidence_ref_set"] = ["evidence-ref-1", "evidence-ref-2"]
    base["audit_ref_set"] = ["audit-ref-1", "audit-ref-2"]
    for field in REQUIRED_DECLARATIONS:
        base[field] = True
    for field in AUTHORIZATION_FLAGS:
        base[field] = False
    for field in RUNTIME_FLAGS:
        base[field] = False
    base["json_safe"] = True
    base.update(overrides)
    return base


def _payload(
    *,
    ready: bool = True,
    reason_code: str = "ready",
    failures: list[str] | None = None,
    authority: object = DEFAULT_AUTHORITY,
) -> dict[str, object]:
    if failures is None:
        failures = []
    if authority is DEFAULT_AUTHORITY:
        authority = _authority()
    return {
        "runtime_authority_ready": ready,
        "reason_code": reason_code,
        "failures": list(failures),
        "authority": authority,
    }


def _expected_authority() -> dict[str, object]:
    output: dict[str, object] = {
        "surface": "append_runtime_authority_service_boundary_validator_ci",
        "version": 1,
    }
    output.update(SOURCE_BINDING_VALUES)
    output.update(VALIDATOR_BINDING_VALUES)
    output.update(OPERATION_REF_VALUES)
    output["evidence_ref_set"] = ["evidence-ref-1", "evidence-ref-2"]
    output["audit_ref_set"] = ["audit-ref-1", "audit-ref-2"]
    for field in REQUIRED_DECLARATIONS:
        output[field] = True
    for field in AUTHORIZATION_FLAGS:
        output[field] = False
    for field in RUNTIME_FLAGS:
        output[field] = False
    output["json_safe"] = True
    return output


def _expected_result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
) -> dict[str, object]:
    return {
        "ci_ok": ci_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "authority": _expected_authority(),
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


def _assert_json_safe(payload: object) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    decoded = json.loads(encoded)
    if decoded != payload:
        raise AssertionError("payload did not round-trip through JSON")
    for value in _recursive_values(payload):
        if isinstance(value, (set, frozenset, tuple)):
            raise AssertionError("runtime collection leaked")


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


def _assert_rejected_with(
    payload: object,
    failure: str,
) -> dict[str, object]:
    result = consume_append_runtime_authority_service_boundary_validator_ci(
        payload
    )
    if result["ci_ok"] is not False:
        raise AssertionError("payload unexpectedly passed CI")
    if result["reason_code"] != "invalid_ci_payload":
        raise AssertionError(result["reason_code"])
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_happy_ready_path(self) -> None:
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            _payload()
        )

        self.assertEqual(
            result,
            _expected_result(ci_ok=True, reason_code="ready", failures=[]),
        )

    def test_happy_not_ready_path(self) -> None:
        source_failures = ["required_declaration_false"]
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            _payload(
                ready=False,
                reason_code="not_ready",
                failures=source_failures,
            )
        )

        self.assertEqual(
            result,
            _expected_result(
                ci_ok=False,
                reason_code="not_ready",
                failures=source_failures,
            ),
        )

    def test_invalid_authority_payload_not_ready_path(self) -> None:
        source_failures = ["authority_shape_mismatch"]
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            _payload(
                ready=False,
                reason_code="invalid_authority_payload",
                failures=source_failures,
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], source_failures)

    def test_exact_input_shape(self) -> None:
        self.assertEqual(
            list(_payload().keys()),
            [
                "runtime_authority_ready",
                "reason_code",
                "failures",
                "authority",
            ],
        )

    def test_exact_output_shape(self) -> None:
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            _payload()
        )
        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertEqual(
            list(result["authority"].keys()),
            EXPECTED_AUTHORITY_OUTPUT_KEYS,
        )

    def test_output_ci_surface_distinct_from_validator_surface(self) -> None:
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            _payload()
        )

        self.assertEqual(
            _payload()["authority"]["surface"],
            "append_runtime_authority_service_boundary_validator",
        )
        self.assertEqual(
            result["authority"]["surface"],
            "append_runtime_authority_service_boundary_validator_ci",
        )


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_payload(self) -> None:
        for candidate in (None, "x", 1, 1.0, [], (), object()):
            with self.subTest(candidate=type(candidate).__name__):
                result = (
                    consume_append_runtime_authority_service_boundary_validator_ci(
                        candidate
                    )
                )
                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["reason_code"], "invalid_ci_payload")
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_or_extra_top_level_key(self) -> None:
        _assert_rejected_with({}, "payload_shape_mismatch")
        payload = _payload()
        payload["extra"] = "x"
        _assert_rejected_with(payload, "payload_shape_mismatch")

    def test_runtime_authority_ready_non_bool(self) -> None:
        for candidate in ("true", 1, None):
            with self.subTest(candidate=candidate):
                payload = _payload()
                payload["runtime_authority_ready"] = candidate
                _assert_rejected_with(
                    payload,
                    "validator_readiness_invalid",
                )

    def test_ready_with_non_ready_reason(self) -> None:
        _assert_rejected_with(
            _payload(reason_code="not_ready"),
            "validator_readiness_invalid",
        )

    def test_ready_with_failures(self) -> None:
        _assert_rejected_with(
            _payload(failures=["operation_ref_invalid"]),
            "validator_readiness_invalid",
        )

    def test_not_ready_with_ready_reason(self) -> None:
        _assert_rejected_with(
            _payload(
                ready=False,
                reason_code="ready",
                failures=["operation_ref_invalid"],
            ),
            "validator_readiness_invalid",
        )

    def test_not_ready_with_empty_failures(self) -> None:
        _assert_rejected_with(
            _payload(ready=False, reason_code="not_ready"),
            "validator_readiness_invalid",
        )

    def test_invalid_reason_code(self) -> None:
        _assert_rejected_with(
            _payload(reason_code="unexpected"),
            "validator_reason_code_invalid",
        )

    def test_failures_non_list_or_non_string(self) -> None:
        payload = _payload()
        payload["failures"] = "operation_ref_invalid"
        _assert_rejected_with(payload, "validator_failures_invalid")

        payload = _payload()
        payload["failures"] = ["operation_ref_invalid", 1]
        _assert_rejected_with(payload, "validator_failures_invalid")

    def test_unknown_validator_failure_value(self) -> None:
        _assert_rejected_with(
            _payload(ready=False, reason_code="not_ready", failures=["x"]),
            "validator_failure_unknown",
        )

    def test_validator_failure_taxonomy_values_are_accepted(self) -> None:
        for failure in VALIDATOR_FAILURE_TAXONOMY:
            with self.subTest(failure=failure):
                result = (
                    consume_append_runtime_authority_service_boundary_validator_ci(
                        _payload(
                            ready=False,
                            reason_code="not_ready",
                            failures=[failure],
                        )
                    )
                )
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertEqual(result["failures"], [failure])


class AuthorityShapeTests(unittest.TestCase):
    def test_authority_non_mapping(self) -> None:
        for candidate in (None, "x", 1, 1.0, [], object()):
            with self.subTest(candidate=type(candidate).__name__):
                _assert_rejected_with(
                    _payload(authority=candidate),
                    "authority_not_mapping",
                )

    def test_authority_missing_or_extra_key(self) -> None:
        authority = _authority()
        del authority["json_safe"]
        _assert_rejected_with(
            _payload(authority=authority),
            "authority_shape_mismatch",
        )

        _assert_rejected_with(
            _payload(authority=_authority(extra="x")),
            "authority_shape_mismatch",
        )

    def test_wrong_input_validator_surface(self) -> None:
        _assert_rejected_with(
            _payload(authority=_authority(surface="OtherSurface")),
            "validator_surface_invalid",
        )

    def test_wrong_version(self) -> None:
        _assert_rejected_with(
            _payload(authority=_authority(version=2)),
            "validator_version_invalid",
        )

    def test_bool_as_int_version(self) -> None:
        _assert_rejected_with(
            _payload(authority=_authority(version=True)),
            "validator_version_invalid",
        )


class BindingTests(unittest.TestCase):
    def test_source_mismatch(self) -> None:
        for field in SOURCE_BINDING_VALUES:
            with self.subTest(field=field):
                _assert_rejected_with(
                    _payload(authority=_authority(**{field: "wrong"})),
                    "source_ref_mismatch",
                )

    def test_validator_checkpoint_binding_mismatch(self) -> None:
        for field in VALIDATOR_BINDING_VALUES:
            with self.subTest(field=field):
                _assert_rejected_with(
                    _payload(authority=_authority(**{field: "wrong"})),
                    "source_ref_mismatch",
                )

    def test_invalid_operation_refs(self) -> None:
        for field in OPERATION_REFS:
            for candidate in (None, "", 1, True, [], {}):
                with self.subTest(field=field, candidate=candidate):
                    _assert_rejected_with(
                        _payload(authority=_authority(**{field: candidate})),
                        "operation_ref_invalid",
                    )


class RefSetTests(unittest.TestCase):
    def test_invalid_evidence_ref_set(self) -> None:
        cases = (None, "x", {}, 1, True, [], [""], [1], [True], ["a", "a"])
        for candidate in cases:
            with self.subTest(candidate=candidate):
                _assert_rejected_with(
                    _payload(authority=_authority(evidence_ref_set=candidate)),
                    "evidence_ref_set_invalid",
                )

    def test_invalid_audit_ref_set(self) -> None:
        cases = (None, "x", {}, 1, True, [], [""], [1], [True], ["a", "a"])
        for candidate in cases:
            with self.subTest(candidate=candidate):
                _assert_rejected_with(
                    _payload(authority=_authority(audit_ref_set=candidate)),
                    "audit_ref_set_invalid",
                )


class DeclarationTests(unittest.TestCase):
    def test_required_declaration_false(self) -> None:
        for field in REQUIRED_DECLARATIONS:
            with self.subTest(field=field):
                _assert_rejected_with(
                    _payload(authority=_authority(**{field: False})),
                    "required_declaration_false",
                )

    def test_required_declaration_non_bool(self) -> None:
        for field in REQUIRED_DECLARATIONS:
            for candidate in (None, "true", 1, 0, [], {}):
                with self.subTest(field=field, candidate=candidate):
                    _assert_rejected_with(
                        _payload(authority=_authority(**{field: candidate})),
                        "required_declaration_invalid",
                    )


class FlagAndSafetyTests(unittest.TestCase):
    def test_authority_flag_true_or_non_bool(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            for candidate, failure in (
                (True, "authorization_flag_true"),
                ("false", "authorization_flag_invalid"),
            ):
                with self.subTest(flag=flag, candidate=candidate):
                    _assert_rejected_with(
                        _payload(authority=_authority(**{flag: candidate})),
                        failure,
                    )

    def test_runtime_flag_true_or_non_bool(self) -> None:
        for flag in RUNTIME_FLAGS:
            for candidate, failure in (
                (True, "runtime_flag_true"),
                ("false", "runtime_flag_invalid"),
            ):
                with self.subTest(flag=flag, candidate=candidate):
                    _assert_rejected_with(
                        _payload(authority=_authority(**{flag: candidate})),
                        failure,
                    )

    def test_json_safe_false_or_non_bool(self) -> None:
        for candidate in (False, "true"):
            with self.subTest(candidate=candidate):
                _assert_rejected_with(
                    _payload(authority=_authority(json_safe=candidate)),
                    "json_safe_invalid",
                )

    def test_output_hard_false_authority_flags(self) -> None:
        authority = _authority()
        for flag in AUTHORIZATION_FLAGS:
            authority[flag] = True
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            _payload(authority=authority)
        )

        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result["authority"][flag], False)

    def test_output_hard_false_runtime_flags(self) -> None:
        authority = _authority()
        for flag in RUNTIME_FLAGS:
            authority[flag] = True
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            _payload(authority=authority)
        )

        for flag in RUNTIME_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result["authority"][flag], False)

    def test_ci_ok_grants_no_runtime_or_write_authority(self) -> None:
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            _payload()
        )
        self.assertTrue(result["ci_ok"])
        for flag in AUTHORIZATION_FLAGS + RUNTIME_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result["authority"][flag], False)

    def test_output_json_safe_and_no_runtime_repr(self) -> None:
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            _payload()
        )

        _assert_json_safe(result)
        _assert_no_runtime_repr(result)

    def test_no_raw_undeclared_fields_or_handles_leak(self) -> None:
        payload = _payload()
        payload["db_handle"] = object()
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            payload
        )

        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertNotIn("db_handle", result)
        self.assertNotIn("db_handle", result["authority"])
        _assert_json_safe(result)

    def test_input_not_mutated(self) -> None:
        payload = _payload()
        before = copy.deepcopy(payload)

        consume_append_runtime_authority_service_boundary_validator_ci(payload)

        self.assertEqual(payload, before)

    def test_deterministic_failure_ordering(self) -> None:
        authority = _authority(
            surface="OtherSurface",
            version=True,
            append_authority_explicit_only=False,
            append_runtime_authorized=True,
            appends_evidence=True,
            json_safe=False,
            approved_task_id="",
            evidence_ref_set=[],
        )
        authority["source_preflight_read_only_stack_tag"] = "wrong-tag"
        result = consume_append_runtime_authority_service_boundary_validator_ci(
            _payload(
                ready="yes",
                reason_code="unexpected",
                failures=["x"],
                authority=authority,
            )
        )

        positions = [CI_FAILURE_ORDER.index(item) for item in result["failures"]]
        self.assertEqual(positions, sorted(positions))


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = append_runtime_authority_service_boundary_validator_ci_manifest()
        self.assertEqual(manifest, EXPECTED_MANIFEST)
        self.assertEqual(
            list(manifest.keys()),
            list(EXPECTED_MANIFEST.keys()),
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = append_runtime_authority_service_boundary_validator_ci_manifest()
        manifest["failure_values"].append("mutated")
        manifest["runtime_dependencies"].append("mutated")
        manifest["depends_on"]["x"] = "y"

        self.assertEqual(
            append_runtime_authority_service_boundary_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_json_safe(self) -> None:
        _assert_json_safe(
            append_runtime_authority_service_boundary_validator_ci_manifest()
        )

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            ci_module.__all__,
            [
                "append_runtime_authority_service_boundary_validator_ci_manifest",
                "consume_append_runtime_authority_service_boundary_validator_ci",
            ],
        )

    def test_function_signatures(self) -> None:
        self.assertEqual(
            str(
                inspect.signature(
                    append_runtime_authority_service_boundary_validator_ci_manifest
                )
            ),
            "() -> dict[str, object]",
        )
        self.assertEqual(
            str(
                inspect.signature(
                    consume_append_runtime_authority_service_boundary_validator_ci
                )
            ),
            "(payload: object) -> dict[str, object]",
        )


class SourceBoundaryTests(unittest.TestCase):
    def test_only_allowed_production_imports(self) -> None:
        source = inspect.getsource(ci_module)
        imports = [
            line
            for line in source.splitlines()
            if line.startswith("import ") or line.startswith("from ")
        ]

        self.assertEqual(
            imports,
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )

    def test_no_forbidden_source_markers(self) -> None:
        source = _scrubbed_source()

        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_validator_import_or_call(self) -> None:
        source = inspect.getsource(ci_module)
        for marker in (
            "append_runtime_authority_service_boundary_validator_manifest(",
            "validate_append_runtime_authority_service_boundary(",
            "from kernel.lifecycle.append_runtime_authority_service_boundary_validator",
            "import kernel.lifecycle.append_runtime_authority_service_boundary_validator",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_service_db_repository_uow_recovery_cli_import(self) -> None:
        source = _scrubbed_source()
        for marker in (
            "approval_service.",
            "review_service.",
            "revision_seal_service.",
            "evidence_service.",
            "UnitOfWork",
            "KernelUnitOfWork",
            "open_connection",
            "recovery_session_host",
            "argparse",
            "click",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_upstream_validator_checker_ci_import_or_call(self) -> None:
        source = _scrubbed_source()
        for marker in (
            "validate_write_path_contract",
            "write_path_contract_validator_manifest",
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
            "repository_uow_allowlist_validator_manifest(",
            "validate_repository_uow_allowlist(",
            "consume_repository_uow_allowlist_validator_ci(",
            "repository_uow_allowlist_validator_ci_manifest(",
            "validate_evidence_audit_append_contract(",
            "evidence_audit_append_contract_validator_manifest(",
            "consume_evidence_audit_append_contract_validator_ci(",
            "evidence_audit_append_contract_validator_ci_manifest(",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_evidence_audit_append_markers(self) -> None:
        source = _scrubbed_source()
        for marker in (
            "EvidenceService",
            "append_audit",
            "append_evidence",
            "evidence_service.",
            "approval_service.",
            "review_service.",
            "revision_seal_service.",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_transaction_idempotency_rollback_runtime_markers(self) -> None:
        source = _scrubbed_source()
        for marker in (
            "begin_transaction",
            "commit(",
            "rollback(",
            "reserve_idempotency",
            "append_runtime",
            "performs_runtime_append",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_datetime_time_digest_or_runtime_introspection_markers(self) -> None:
        source = _scrubbed_source()
        for marker in (
            "datetime.now",
            "time.time",
            "time.monotonic",
            "perf_counter",
            "wall_clock",
            "fromisoformat",
            "strptime",
            "isoformat",
            "tzinfo",
            "utcoffset",
            "hashlib",
            "hmac",
            "secrets",
            "sha1",
            "sha256",
            "sha512",
            "blake2",
            "md5",
            "digest",
            "getattr(",
            "setattr(",
            "callable(",
            "hasattr(",
            "dir(",
            "inspect.",
            "importlib",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
