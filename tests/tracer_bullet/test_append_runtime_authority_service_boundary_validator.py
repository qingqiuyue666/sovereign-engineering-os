"""Tracer bullets for the append authority service boundary validator."""

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

import kernel.lifecycle.append_runtime_authority_service_boundary_validator as validator_module
from kernel.lifecycle.append_runtime_authority_service_boundary_validator import (
    append_runtime_authority_service_boundary_validator_manifest,
    validate_append_runtime_authority_service_boundary,
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
    name for group in DECLARATION_GROUPS for name in group
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

FAILURE_ORDER = [
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
]

EXPECTED_MANIFEST = {
    "surface": "append_runtime_authority_service_boundary_validator",
    "version": 1,
    "input_shape": (
        "already_rendered_append_runtime_authority_service_boundary_v1"
    ),
    "depends_on": {
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
    "runtime_authority_ready_authorizes_append": False,
    "runtime_authority_ready_authorizes_write": False,
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
        "invalid_authority_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": FAILURE_ORDER,
}

EXPECTED_OUTPUT_KEYS = [
    "runtime_authority_ready",
    "reason_code",
    "failures",
    "authority",
]

EXPECTED_AUTHORITY_OUTPUT_KEYS = (
    ["surface", "version"]
    + list(SOURCE_BINDING_VALUES.keys())
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
    "begin_transaction",
    "commit(",
    "rollback(",
    "reserve_idempotency",
    "append_runtime",
    "performs_runtime_append",
)

ALLOWED_SOURCE_FIELD_STRINGS = (
    "append_runtime_authority_service_boundary_validator",
    "append_runtime_authority_service_boundary_validator_manifest",
    "validate_append_runtime_authority_service_boundary",
    "AppendRuntimeAuthorityServiceBoundaryV1",
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
)


def _authority(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "AppendRuntimeAuthorityServiceBoundaryV1",
        "version": 1,
    }
    for name, value in SOURCE_BINDING_VALUES.items():
        base[name] = value
    for name, value in OPERATION_REF_VALUES.items():
        base[name] = value
    base["evidence_ref_set"] = ["evidence-ref-1", "evidence-ref-2"]
    base["audit_ref_set"] = ["audit-ref-1", "audit-ref-2"]
    for name in REQUIRED_DECLARATIONS:
        base[name] = True
    for name in AUTHORIZATION_FLAGS:
        base[name] = False
    for name in RUNTIME_FLAGS:
        base[name] = False
    base["json_safe"] = True
    base.update(overrides)
    return base


def _payload(**overrides: object) -> dict[str, object]:
    authority = overrides.pop("authority", None)
    if authority is None:
        authority = _authority()
    payload: dict[str, object] = {
        "append_runtime_authority_service_boundary": authority
    }
    payload.update(overrides)
    return payload


def _expected_happy_output() -> dict[str, object]:
    authority: dict[str, object] = {
        "surface": "append_runtime_authority_service_boundary_validator",
        "version": 1,
    }
    for name, value in SOURCE_BINDING_VALUES.items():
        authority[name] = value
    for name, value in OPERATION_REF_VALUES.items():
        authority[name] = value
    authority["evidence_ref_set"] = ["evidence-ref-1", "evidence-ref-2"]
    authority["audit_ref_set"] = ["audit-ref-1", "audit-ref-2"]
    for name in REQUIRED_DECLARATIONS:
        authority[name] = True
    for name in AUTHORIZATION_FLAGS:
        authority[name] = False
    for name in RUNTIME_FLAGS:
        authority[name] = False
    authority["json_safe"] = True
    return {
        "runtime_authority_ready": True,
        "reason_code": "ready",
        "failures": [],
        "authority": authority,
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
    result = validate_append_runtime_authority_service_boundary(payload)
    if result["runtime_authority_ready"] is not False:
        raise AssertionError("authority unexpectedly ready")
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_happy_ready_path(self) -> None:
        result = validate_append_runtime_authority_service_boundary(_payload())
        self.assertEqual(result, _expected_happy_output())

    def test_exact_input_shape(self) -> None:
        payload = _payload()
        self.assertEqual(
            list(payload.keys()),
            ["append_runtime_authority_service_boundary"],
        )

    def test_exact_output_shape(self) -> None:
        result = validate_append_runtime_authority_service_boundary(_payload())
        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertEqual(
            list(result["authority"].keys()),
            EXPECTED_AUTHORITY_OUTPUT_KEYS,
        )


class TopLevelInputTests(unittest.TestCase):
    def test_non_mapping_payload(self) -> None:
        for candidate in (None, "x", 1, 1.0, [], (), object()):
            with self.subTest(candidate=type(candidate).__name__):
                result = validate_append_runtime_authority_service_boundary(
                    candidate
                )
                self.assertFalse(result["runtime_authority_ready"])
                self.assertEqual(
                    result["reason_code"], "invalid_authority_payload"
                )
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key(self) -> None:
        _assert_rejected_with({}, "payload_shape_mismatch")

    def test_extra_top_level_key(self) -> None:
        payload = _payload(extra="x")
        _assert_rejected_with(payload, "payload_shape_mismatch")


class AuthorityStructureTests(unittest.TestCase):
    def test_authority_non_mapping(self) -> None:
        for candidate in (None, "x", 1, 1.0, [], object()):
            with self.subTest(candidate=type(candidate).__name__):
                _assert_rejected_with(
                    {
                        "append_runtime_authority_service_boundary": (
                            candidate
                        )
                    },
                    "authority_not_mapping",
                )

    def test_authority_missing_key(self) -> None:
        authority = _authority()
        del authority["surface"]
        _assert_rejected_with(
            _payload(authority=authority),
            "authority_shape_mismatch",
        )

    def test_authority_extra_key(self) -> None:
        authority = _authority(unexpected="x")
        _assert_rejected_with(
            _payload(authority=authority),
            "authority_shape_mismatch",
        )

    def test_wrong_surface(self) -> None:
        _assert_rejected_with(
            _payload(authority=_authority(surface="OtherSurface")),
            "authority_surface_invalid",
        )

    def test_wrong_version(self) -> None:
        _assert_rejected_with(
            _payload(authority=_authority(version=2)),
            "authority_version_invalid",
        )

    def test_bool_as_int_version(self) -> None:
        _assert_rejected_with(
            _payload(authority=_authority(version=True)),
            "authority_version_invalid",
        )


class BindingTests(unittest.TestCase):
    def test_source_mismatch(self) -> None:
        for field in SOURCE_BINDING_VALUES:
            with self.subTest(field=field):
                authority = _authority()
                authority[field] = "wrong-ref"
                result = _assert_rejected_with(
                    _payload(authority=authority),
                    "source_ref_mismatch",
                )
                self.assertEqual(
                    result["reason_code"], "invalid_authority_payload"
                )

    def test_invalid_operation_refs(self) -> None:
        for field in OPERATION_REFS:
            for bad in (None, "", 1, True, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    result = _assert_rejected_with(
                        _payload(authority=_authority(**{field: bad})),
                        "operation_ref_invalid",
                    )
                    self.assertEqual(
                        result["reason_code"], "invalid_authority_payload"
                    )


class RefSetTests(unittest.TestCase):
    def test_invalid_evidence_ref_set(self) -> None:
        cases = (None, "x", {}, 1, True, [], [""], [1], [True], ["a", "a"])
        for value in cases:
            with self.subTest(value=value):
                _assert_rejected_with(
                    _payload(authority=_authority(evidence_ref_set=value)),
                    "evidence_ref_set_invalid",
                )

    def test_invalid_audit_ref_set(self) -> None:
        cases = (None, "x", {}, 1, True, [], [""], [1], [True], ["a", "a"])
        for value in cases:
            with self.subTest(value=value):
                _assert_rejected_with(
                    _payload(authority=_authority(audit_ref_set=value)),
                    "audit_ref_set_invalid",
                )


class DeclarationTests(unittest.TestCase):
    def test_required_declaration_false(self) -> None:
        for field in REQUIRED_DECLARATIONS:
            with self.subTest(field=field):
                result = _assert_rejected_with(
                    _payload(authority=_authority(**{field: False})),
                    "required_declaration_false",
                )
                self.assertEqual(result["reason_code"], "not_ready")

    def test_required_declaration_non_bool(self) -> None:
        for field in REQUIRED_DECLARATIONS:
            for bad in (None, "true", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    result = _assert_rejected_with(
                        _payload(authority=_authority(**{field: bad})),
                        "required_declaration_invalid",
                    )
                    self.assertEqual(result["reason_code"], "not_ready")


class AuthorizationFlagTests(unittest.TestCase):
    def test_authority_flag_true(self) -> None:
        for field in AUTHORIZATION_FLAGS:
            with self.subTest(field=field):
                result = _assert_rejected_with(
                    _payload(authority=_authority(**{field: True})),
                    "authorization_flag_true",
                )
                self.assertEqual(result["reason_code"], "not_ready")

    def test_authority_flag_non_bool(self) -> None:
        for field in AUTHORIZATION_FLAGS:
            for bad in (None, "false", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    result = _assert_rejected_with(
                        _payload(authority=_authority(**{field: bad})),
                        "authorization_flag_invalid",
                    )
                    self.assertEqual(result["reason_code"], "not_ready")


class RuntimeFlagTests(unittest.TestCase):
    def test_runtime_flag_true(self) -> None:
        for field in RUNTIME_FLAGS:
            with self.subTest(field=field):
                result = _assert_rejected_with(
                    _payload(authority=_authority(**{field: True})),
                    "runtime_flag_true",
                )
                self.assertEqual(result["reason_code"], "not_ready")

    def test_runtime_flag_non_bool(self) -> None:
        for field in RUNTIME_FLAGS:
            for bad in (None, "false", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    result = _assert_rejected_with(
                        _payload(authority=_authority(**{field: bad})),
                        "runtime_flag_invalid",
                    )
                    self.assertEqual(result["reason_code"], "not_ready")


class JsonSafeTests(unittest.TestCase):
    def test_json_safe_false(self) -> None:
        result = _assert_rejected_with(
            _payload(authority=_authority(json_safe=False)),
            "json_safe_invalid",
        )
        self.assertEqual(result["reason_code"], "invalid_authority_payload")

    def test_json_safe_non_bool(self) -> None:
        for bad in (None, "true", 1, 0, [], {}):
            with self.subTest(bad=type(bad).__name__):
                result = _assert_rejected_with(
                    _payload(authority=_authority(json_safe=bad)),
                    "json_safe_invalid",
                )
                self.assertEqual(
                    result["reason_code"], "invalid_authority_payload"
                )


class BoundaryOutputTests(unittest.TestCase):
    def test_output_hard_false_authority_flags(self) -> None:
        authority = _authority()
        for flag in AUTHORIZATION_FLAGS:
            authority[flag] = True
        result = validate_append_runtime_authority_service_boundary(
            _payload(authority=authority)
        )
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result["authority"][flag], False)

    def test_output_hard_false_runtime_flags(self) -> None:
        authority = _authority()
        for flag in RUNTIME_FLAGS:
            authority[flag] = True
        result = validate_append_runtime_authority_service_boundary(
            _payload(authority=authority)
        )
        for flag in RUNTIME_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result["authority"][flag], False)

    def test_runtime_authority_ready_grants_no_runtime_or_write(self) -> None:
        result = validate_append_runtime_authority_service_boundary(_payload())
        self.assertTrue(result["runtime_authority_ready"])
        for flag in AUTHORIZATION_FLAGS + RUNTIME_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result["authority"][flag], False)


class SafetyAndDeterminismTests(unittest.TestCase):
    def test_output_json_safe(self) -> None:
        result = validate_append_runtime_authority_service_boundary(_payload())
        _assert_json_safe(result)
        _assert_no_runtime_repr(result)

    def test_input_not_mutated(self) -> None:
        payload = _payload()
        snapshot = copy.deepcopy(payload)
        validate_append_runtime_authority_service_boundary(payload)
        self.assertEqual(payload, snapshot)

    def test_deterministic_failure_ordering(self) -> None:
        authority = _authority(
            surface="OtherSurface",
            version=True,
            append_authority_explicit_only=False,
            append_runtime_authorized=True,
            appends_evidence=True,
            json_safe=False,
        )
        authority["approved_task_id"] = ""
        authority["source_preflight_read_only_stack_tag"] = "wrong-tag"
        result = validate_append_runtime_authority_service_boundary(
            _payload(authority=authority)
        )
        positions = [FAILURE_ORDER.index(item) for item in result["failures"]]
        self.assertEqual(positions, sorted(positions))


class ManifestTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            append_runtime_authority_service_boundary_validator_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        first = append_runtime_authority_service_boundary_validator_manifest()
        first["mutated"] = "x"
        first["depends_on"]["mutated"] = "y"
        first["failure_values"].append("mutated")
        second = append_runtime_authority_service_boundary_validator_manifest()
        self.assertEqual(second, EXPECTED_MANIFEST)
        self.assertNotIn("mutated", second)
        self.assertNotIn("mutated", second["depends_on"])
        self.assertNotIn("mutated", second["failure_values"])

    def test_manifest_json_safe(self) -> None:
        _assert_json_safe(
            append_runtime_authority_service_boundary_validator_manifest()
        )


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(validator_module.__all__),
            sorted(
                [
                    (
                        "append_runtime_authority_service_boundary_"
                        "validator_manifest"
                    ),
                    "validate_append_runtime_authority_service_boundary",
                ]
            ),
        )

    def test_signatures(self) -> None:
        manifest_sig = inspect.signature(
            append_runtime_authority_service_boundary_validator_manifest
        )
        self.assertEqual(list(manifest_sig.parameters.keys()), [])
        validate_sig = inspect.signature(
            validate_append_runtime_authority_service_boundary
        )
        self.assertEqual(list(validate_sig.parameters.keys()), ["payload"])


class SourceBoundaryTests(unittest.TestCase):
    def test_only_allowed_production_imports(self) -> None:
        source = inspect.getsource(validator_module)
        import_lines = [
            line.strip()
            for line in source.splitlines()
            if line.startswith("from ") or line.startswith("import ")
        ]
        self.assertEqual(
            import_lines,
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )

    def test_source_boundary_forbids_runtime_coupling(self) -> None:
        source = _scrubbed_source()
        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

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

    def test_no_runtime_method_introspection(self) -> None:
        source = inspect.getsource(validator_module)
        for marker in (
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

    def test_no_service_db_repository_uow_recovery_cli_imports(self) -> None:
        source = _scrubbed_source()
        for marker in (
            "approval_service.",
            "review_service.",
            "revision_seal_service.",
            "evidence_service.",
            "UnitOfWork",
            "KernelUnitOfWork",
            "recovery_session_host",
            "argparse",
            "click",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_upstream_validator_checker_ci_imports(self) -> None:
        source = _scrubbed_source()
        for marker in (
            "validate_write_path_contract",
            "write_path_contract_validator_manifest",
            "validate_executor_precondition",
            "executor_precondition_validator_manifest",
            "consume_executor_precondition_validator_ci",
            "consume_execution_authorization_validator_ci",
            "validate_execution_authorization",
            "summarize_preflight_readiness",
            "summarize_restore_dry_run_readiness",
            "governance_readiness_aggregator",
            "validate_evidence_audit_append_contract(",
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
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
