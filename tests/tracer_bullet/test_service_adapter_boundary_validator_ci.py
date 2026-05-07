"""Tracer bullets for the service adapter boundary validator CI consumer."""

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

import kernel.lifecycle.service_adapter_boundary_validator_ci as ci_module
from kernel.lifecycle.service_adapter_boundary_validator_ci import (
    consume_service_adapter_boundary_validator_ci,
    service_adapter_boundary_validator_ci_manifest,
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
    "source_append_runtime_authority_service_boundary_read_only_stack_tag": (
        "append-runtime-authority-service-boundary-read-only-stack-v1"
    ),
    "source_append_runtime_authority_service_boundary_read_only_stack_commit": (
        "bda430a6a8d1e1dbede2adb9594baa1ab5cf2039"
    ),
    "source_service_adapter_boundary_spec_only_tag": (
        "service-adapter-boundary-spec-only-v1"
    ),
    "source_service_adapter_boundary_spec_only_commit": (
        "d03a3e258dae6f12a14f12e4bbc12d21e78e8d5d"
    ),
}

VALIDATOR_BINDING_VALUES = {
    "source_service_adapter_boundary_validator_tag": (
        "service-adapter-boundary-validator-v1"
    ),
    "source_service_adapter_boundary_validator_commit": (
        "124359832c8e83412a54ff740073640cc92082e1"
    ),
}

SERVICE_IDENTITIES = [
    "evidence_service",
    "approval_service",
    "review_service",
    "revision_seal_service",
    "audit_service_future_adapter",
]

KNOWN_FORBIDDEN_METHODS = [
    "EvidenceService.close_evidence",
    "ApprovalService.evaluate_barrier",
    "ApprovalService.reverify_for_seal",
    "ReviewService.render_review",
    "RevisionSealService.seal_revision",
]

REQUIRED_DECLARATIONS = (
    "service_adapter_implementation_forbidden",
    "service_calls_forbidden",
    "evidence_service_call_forbidden",
    "approval_service_call_forbidden",
    "review_service_call_forbidden",
    "revision_seal_service_call_forbidden",
    "audit_service_call_forbidden",
    "unnamed_service_forbidden",
    "dynamic_service_resolution_forbidden",
    "wildcard_service_authority_forbidden",
    "class_level_service_authority_forbidden",
    "module_level_service_authority_forbidden",
    "service_method_allowlist_required",
    "exact_service_identity_required",
    "exact_service_class_name_required",
    "exact_service_method_name_required",
    "service_result_contract_required",
    "service_result_json_safe_required",
    "service_result_bounded_required",
    "service_result_deterministic_required",
    "service_result_no_runtime_handles_required",
    "service_result_no_raw_repr_required",
    "service_object_leakage_forbidden",
    "db_handle_leakage_forbidden",
    "repository_uow_handle_leakage_forbidden",
    "exception_object_leakage_forbidden",
    "filesystem_network_handle_leakage_forbidden",
    "raw_service_result_passthrough_forbidden",
    "implicit_append_success_forbidden",
    "implicit_audit_emission_forbidden",
    "service_transaction_ownership_forbidden_by_default",
    "kernel_owned_transaction_required_for_future_runtime",
    "uncontrolled_nested_transaction_forbidden",
    "in_transaction_service_call_requires_separate_authority",
    "out_of_band_service_call_policy_required",
    "commit_after_required_bookkeeping_only",
    "post_mutation_service_failure_incident_class",
    "service_idempotency_binding_required",
    "service_replay_classification_required",
    "same_key_same_binding_safe_replay_only",
    "same_key_different_binding_fail_closed",
    "ambiguous_replay_incident_class",
    "evidence_audit_ref_fabrication_forbidden",
    "undeclared_ref_forbidden",
    "missing_ref_fail_closed",
    "mismatched_ref_fail_closed",
    "evidence_audit_refs_source_bound_required",
    "evidence_audit_refs_operation_bound_required",
    "evidence_audit_refs_json_safe_required",
    "adapter_output_cannot_imply_append_success_without_authority",
    "adapter_output_cannot_imply_audit_emission_without_authority",
    "adapter_output_cannot_create_refs_without_authority",
    "forbidden_service_call_fail_closed",
    "method_not_allowlisted_fail_closed",
    "malformed_service_result_fail_closed",
    "idempotency_mismatch_fail_closed",
    "transaction_violation_incident_class",
    "rollback_failure_incident_class",
    "partial_success_forbidden",
    "silent_success_forbidden",
    "future_validator_required",
    "future_ci_required",
)

AUTHORIZATION_FLAGS = (
    "service_adapter_runtime_authorized",
    "evidence_service_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "audit_service_authorized",
    "service_method_call_authorized",
    "service_side_effect_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "append_runtime_authorized",
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

CI_FAILURE_ORDER = [
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "validator_surface_invalid",
    "validator_version_invalid",
    "validator_checkpoint_mismatch",
    "validator_readiness_invalid",
    "validator_reason_code_invalid",
    "validator_failures_invalid",
    "validator_failure_unknown",
    "source_ref_mismatch",
    "service_identity_invalid",
    "forbidden_service_method_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
]

VALIDATOR_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "boundary_surface_invalid",
    "boundary_version_invalid",
    "source_ref_mismatch",
    "service_identity_invalid",
    "forbidden_service_method_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
)

EXPECTED_MANIFEST = {
    "surface": "service_adapter_boundary_validator_ci",
    "version": 1,
    "input_shape": (
        "already_rendered_service_adapter_boundary_validator_output_v1"
    ),
    "depends_on": {
        "service_adapter_boundary_validator": (
            "service-adapter-boundary-validator-v1"
        ),
        "service_adapter_boundary_spec_only": (
            "service-adapter-boundary-spec-only-v1"
        ),
        "append_runtime_authority_service_boundary_read_only_stack": (
            "append-runtime-authority-service-boundary-read-only-stack-v1"
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
    "ci_ok_authorizes_service_calls": False,
    "ci_ok_authorizes_runtime": False,
    "ci_ok_authorizes_write": False,
    "service_adapter_runtime_authorized": False,
    "evidence_service_authorized": False,
    "approval_service_authorized": False,
    "review_service_authorized": False,
    "revision_seal_service_authorized": False,
    "audit_service_authorized": False,
    "service_method_call_authorized": False,
    "service_side_effect_authorized": False,
    "evidence_append_authorized": False,
    "audit_append_authorized": False,
    "append_runtime_authorized": False,
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
    "boundary",
]

EXPECTED_BOUNDARY_OUTPUT_KEYS = (
    ["surface", "version"]
    + list(SOURCE_BINDING_VALUES.keys())
    + list(VALIDATOR_BINDING_VALUES.keys())
    + ["service_identities", "known_forbidden_service_methods"]
    + list(REQUIRED_DECLARATIONS)
    + list(AUTHORIZATION_FLAGS)
    + ["json_safe"]
)

REPR_MARKERS = (
    "ServiceAdapterBoundary(",
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
    "close_evidence",
    "evaluate_barrier",
    "reverify_for_seal",
    "render_review",
    "seal_revision",
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
    "validate_repository_uow_allowlist(",
    "consume_repository_uow_allowlist_validator_ci(",
    "validate_evidence_audit_append_contract(",
    "consume_evidence_audit_append_contract_validator_ci(",
    "validate_append_runtime_authority_service_boundary(",
    "consume_append_runtime_authority_service_boundary_validator_ci(",
    "service_adapter_boundary_validator_manifest",
    "validate_service_adapter_boundary(",
    "begin_transaction",
    "commit(",
    "rollback(",
    "reserve_idempotency",
    "service_adapter_runtime",
    "call_service",
    "service_method_call",
)

ALLOWED_SOURCE_FIELD_STRINGS = (
    "service_adapter_boundary_validator_ci",
    "service_adapter_boundary_validator_ci_manifest",
    "consume_service_adapter_boundary_validator_ci",
    "service-adapter-boundary-validator-v1",
    "service-adapter-boundary-spec-only-v1",
    "service_adapter_runtime_authorized",
    "evidence_service_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "audit_service_authorized",
    "service_method_call_authorized",
    "service_side_effect_authorized",
)


def _boundary(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "service_adapter_boundary_validator",
        "version": 1,
    }
    for name, value in SOURCE_BINDING_VALUES.items():
        base[name] = value
    for name, value in VALIDATOR_BINDING_VALUES.items():
        base[name] = value
    base["service_identities"] = list(SERVICE_IDENTITIES)
    base["known_forbidden_service_methods"] = list(KNOWN_FORBIDDEN_METHODS)
    for name in REQUIRED_DECLARATIONS:
        base[name] = True
    for name in AUTHORIZATION_FLAGS:
        base[name] = False
    base["json_safe"] = True
    base.update(overrides)
    return base


def _payload(**overrides: object) -> dict[str, object]:
    boundary = overrides.pop("boundary", None)
    if boundary is None:
        boundary = _boundary()
    payload: dict[str, object] = {
        "service_adapter_ready": True,
        "reason_code": "ready",
        "failures": [],
        "boundary": boundary,
    }
    payload.update(overrides)
    return payload


def _expected_happy_output() -> dict[str, object]:
    boundary: dict[str, object] = {
        "surface": "service_adapter_boundary_validator_ci",
        "version": 1,
    }
    for name, value in SOURCE_BINDING_VALUES.items():
        boundary[name] = value
    for name, value in VALIDATOR_BINDING_VALUES.items():
        boundary[name] = value
    boundary["service_identities"] = list(SERVICE_IDENTITIES)
    boundary["known_forbidden_service_methods"] = list(
        KNOWN_FORBIDDEN_METHODS
    )
    for name in REQUIRED_DECLARATIONS:
        boundary[name] = True
    for name in AUTHORIZATION_FLAGS:
        boundary[name] = False
    boundary["json_safe"] = True
    return {
        "ci_ok": True,
        "reason_code": "ready",
        "failures": [],
        "boundary": boundary,
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
    source = inspect.getsource(ci_module)
    for allowed in ALLOWED_SOURCE_FIELD_STRINGS:
        source = source.replace(allowed, "")
    return source


def _assert_rejected_with(
    payload: object,
    failure: str,
) -> dict[str, object]:
    result = consume_service_adapter_boundary_validator_ci(payload)
    if result["ci_ok"] is not False:
        raise AssertionError("CI payload unexpectedly ready")
    if result["reason_code"] != "invalid_ci_payload":
        raise AssertionError(f"unexpected reason: {result['reason_code']}")
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_happy_ready_path(self) -> None:
        self.assertEqual(
            consume_service_adapter_boundary_validator_ci(_payload()),
            _expected_happy_output(),
        )

    def test_exact_input_shape(self) -> None:
        result = consume_service_adapter_boundary_validator_ci(_payload())
        self.assertEqual(list(_payload().keys()), [
            "service_adapter_ready",
            "reason_code",
            "failures",
            "boundary",
        ])
        self.assertTrue(result["ci_ok"])

    def test_exact_output_shape(self) -> None:
        result = consume_service_adapter_boundary_validator_ci(_payload())
        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertEqual(
            list(result["boundary"].keys()),
            EXPECTED_BOUNDARY_OUTPUT_KEYS,
        )

    def test_happy_not_ready_path(self) -> None:
        result = consume_service_adapter_boundary_validator_ci(
            _payload(
                service_adapter_ready=False,
                reason_code="not_ready",
                failures=[
                    "authorization_flag_true",
                    "required_declaration_false",
                ],
            )
        )
        self.assertEqual(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(
            result["failures"],
            [
                "required_declaration_false",
                "authorization_flag_true",
            ],
        )


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_payload(self) -> None:
        result = _assert_rejected_with([], "payload_not_mapping")
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key(self) -> None:
        payload = _payload()
        payload.pop("reason_code")
        _assert_rejected_with(payload, "payload_shape_mismatch")

    def test_extra_top_level_key(self) -> None:
        _assert_rejected_with(
            _payload(extra="unexpected"),
            "payload_shape_mismatch",
        )

    def test_service_adapter_ready_non_bool(self) -> None:
        _assert_rejected_with(
            _payload(service_adapter_ready="true"),
            "validator_readiness_invalid",
        )

    def test_service_adapter_ready_bool_as_int(self) -> None:
        _assert_rejected_with(
            _payload(service_adapter_ready=1),
            "validator_readiness_invalid",
        )

    def test_reason_code_invalid(self) -> None:
        _assert_rejected_with(
            _payload(reason_code="invalid"),
            "validator_reason_code_invalid",
        )

    def test_failures_non_list_or_non_string(self) -> None:
        _assert_rejected_with(
            _payload(failures="required_declaration_false"),
            "validator_failures_invalid",
        )
        _assert_rejected_with(
            _payload(failures=[1]),
            "validator_failures_invalid",
        )


class BoundaryStructureTests(unittest.TestCase):
    def test_boundary_non_mapping(self) -> None:
        _assert_rejected_with(
            _payload(boundary=[]),
            "boundary_not_mapping",
        )

    def test_boundary_missing_key(self) -> None:
        boundary = _boundary()
        boundary.pop("json_safe")
        _assert_rejected_with(
            _payload(boundary=boundary),
            "boundary_shape_mismatch",
        )

    def test_boundary_extra_key(self) -> None:
        _assert_rejected_with(
            _payload(boundary=_boundary(extra="unexpected")),
            "boundary_shape_mismatch",
        )

    def test_wrong_validator_surface(self) -> None:
        _assert_rejected_with(
            _payload(boundary=_boundary(surface="ServiceAdapterBoundaryV1")),
            "validator_surface_invalid",
        )

    def test_wrong_validator_version(self) -> None:
        _assert_rejected_with(
            _payload(boundary=_boundary(version=2)),
            "validator_version_invalid",
        )

    def test_bool_as_int_version(self) -> None:
        _assert_rejected_with(
            _payload(boundary=_boundary(version=True)),
            "validator_version_invalid",
        )

    def test_validator_checkpoint_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                boundary=_boundary(
                    source_service_adapter_boundary_validator_commit="bad"
                )
            ),
            "validator_checkpoint_mismatch",
        )


class BindingTests(unittest.TestCase):
    def test_source_mismatch(self) -> None:
        _assert_rejected_with(
            _payload(
                boundary=_boundary(
                    source_repository_uow_allowlist_read_only_stack_commit=(
                        "bec2d04eab1922594bcef59f4efe0fe4849"
                    )
                )
            ),
            "source_ref_mismatch",
        )

    def test_invalid_service_identities(self) -> None:
        _assert_rejected_with(
            _payload(boundary=_boundary(service_identities=[])),
            "service_identity_invalid",
        )

    def test_invalid_known_forbidden_methods(self) -> None:
        _assert_rejected_with(
            _payload(boundary=_boundary(known_forbidden_service_methods=[])),
            "forbidden_service_method_invalid",
        )


class ValidatorReadinessTests(unittest.TestCase):
    def test_ready_with_non_ready_reason(self) -> None:
        _assert_rejected_with(
            _payload(reason_code="not_ready"),
            "validator_readiness_invalid",
        )

    def test_ready_with_failures(self) -> None:
        _assert_rejected_with(
            _payload(failures=["required_declaration_false"]),
            "validator_readiness_invalid",
        )

    def test_not_ready_with_ready_reason(self) -> None:
        _assert_rejected_with(
            _payload(
                service_adapter_ready=False,
                reason_code="ready",
                failures=["required_declaration_false"],
            ),
            "validator_readiness_invalid",
        )

    def test_not_ready_with_empty_failures(self) -> None:
        _assert_rejected_with(
            _payload(service_adapter_ready=False, reason_code="not_ready"),
            "validator_readiness_invalid",
        )

    def test_invalid_service_adapter_payload_reason_allowed_when_not_ready(
        self,
    ) -> None:
        result = consume_service_adapter_boundary_validator_ci(
            _payload(
                service_adapter_ready=False,
                reason_code="invalid_service_adapter_payload",
                failures=["payload_shape_mismatch"],
            )
        )
        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])

    def test_unknown_validator_failure(self) -> None:
        _assert_rejected_with(
            _payload(
                service_adapter_ready=False,
                reason_code="not_ready",
                failures=["unknown_failure"],
            ),
            "validator_failure_unknown",
        )

    def test_validator_failure_taxonomy_values_are_accepted(self) -> None:
        for failure in VALIDATOR_FAILURE_TAXONOMY:
            with self.subTest(failure=failure):
                result = consume_service_adapter_boundary_validator_ci(
                    _payload(
                        service_adapter_ready=False,
                        reason_code="not_ready",
                        failures=[failure],
                    )
                )
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertEqual(result["failures"], [failure])


class DeclarationTests(unittest.TestCase):
    def test_required_declaration_false(self) -> None:
        _assert_rejected_with(
            _payload(
                boundary=_boundary(
                    service_result_contract_required=False,
                )
            ),
            "required_declaration_false",
        )

    def test_required_declaration_non_bool(self) -> None:
        _assert_rejected_with(
            _payload(
                boundary=_boundary(
                    service_result_contract_required="true",
                )
            ),
            "required_declaration_invalid",
        )


class AuthorizationFlagTests(unittest.TestCase):
    def test_authority_flag_true(self) -> None:
        _assert_rejected_with(
            _payload(
                boundary=_boundary(
                    evidence_service_authorized=True,
                )
            ),
            "authorization_flag_true",
        )

    def test_authority_flag_non_bool(self) -> None:
        _assert_rejected_with(
            _payload(
                boundary=_boundary(
                    evidence_service_authorized="false",
                )
            ),
            "authorization_flag_invalid",
        )


class JsonSafeTests(unittest.TestCase):
    def test_json_safe_false(self) -> None:
        _assert_rejected_with(
            _payload(boundary=_boundary(json_safe=False)),
            "json_safe_invalid",
        )

    def test_json_safe_non_bool(self) -> None:
        _assert_rejected_with(
            _payload(boundary=_boundary(json_safe="true")),
            "json_safe_invalid",
        )


class BoundaryOutputTests(unittest.TestCase):
    def test_output_hard_false_authority_flags(self) -> None:
        result = consume_service_adapter_boundary_validator_ci(_payload())
        boundary = result["boundary"]
        for name in AUTHORIZATION_FLAGS:
            with self.subTest(name=name):
                self.assertIs(boundary[name], False)

    def test_ci_ok_grants_no_authority(self) -> None:
        result = consume_service_adapter_boundary_validator_ci(_payload())
        self.assertIs(result["ci_ok"], True)
        boundary = result["boundary"]
        for name in AUTHORIZATION_FLAGS:
            with self.subTest(name=name):
                self.assertIs(boundary[name], False)
        manifest = service_adapter_boundary_validator_ci_manifest()
        self.assertIs(manifest["ci_ok_authorizes_service_calls"], False)
        self.assertIs(manifest["ci_ok_authorizes_runtime"], False)
        self.assertIs(manifest["ci_ok_authorizes_write"], False)


class SafetyAndDeterminismTests(unittest.TestCase):
    def test_output_json_safe(self) -> None:
        result = consume_service_adapter_boundary_validator_ci(_payload())
        _assert_json_safe(result)
        _assert_no_runtime_repr(result)

    def test_input_not_mutated(self) -> None:
        payload = _payload()
        snapshot = copy.deepcopy(payload)
        consume_service_adapter_boundary_validator_ci(payload)
        self.assertEqual(payload, snapshot)

    def test_deterministic_failure_ordering(self) -> None:
        result = consume_service_adapter_boundary_validator_ci(
            _payload(
                service_adapter_ready=1,
                reason_code="bad",
                failures=["unknown"],
                boundary=_boundary(
                    surface="bad",
                    version=True,
                    source_service_adapter_boundary_validator_commit="bad",
                    source_read_only_governance_layer_commit="bad",
                    service_identities=[],
                    known_forbidden_service_methods=[],
                    service_result_contract_required=False,
                    evidence_service_authorized=True,
                    json_safe=False,
                ),
            )
        )
        self.assertEqual(
            result["failures"],
            [
                "validator_surface_invalid",
                "validator_version_invalid",
                "validator_checkpoint_mismatch",
                "validator_readiness_invalid",
                "validator_reason_code_invalid",
                "validator_failure_unknown",
                "source_ref_mismatch",
                "service_identity_invalid",
                "forbidden_service_method_invalid",
                "required_declaration_false",
                "authorization_flag_true",
                "json_safe_invalid",
            ],
        )

    def test_no_raw_validator_object_leakage(self) -> None:
        result = _assert_rejected_with(
            _payload(boundary=_boundary(service_identities=["wrong"])),
            "service_identity_invalid",
        )
        values = _recursive_values(result)
        self.assertNotIn("wrong", values)


class ManifestTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            service_adapter_boundary_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        first = service_adapter_boundary_validator_ci_manifest()
        first["mutated"] = "x"
        first["depends_on"]["mutated"] = "y"
        first["failure_values"].append("mutated")
        second = service_adapter_boundary_validator_ci_manifest()
        self.assertEqual(second, EXPECTED_MANIFEST)
        self.assertNotIn("mutated", second)
        self.assertNotIn("mutated", second["depends_on"])
        self.assertNotIn("mutated", second["failure_values"])

    def test_manifest_json_safe(self) -> None:
        _assert_json_safe(service_adapter_boundary_validator_ci_manifest())


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(ci_module.__all__),
            sorted(
                [
                    "service_adapter_boundary_validator_ci_manifest",
                    "consume_service_adapter_boundary_validator_ci",
                ]
            ),
        )

    def test_signatures(self) -> None:
        manifest_sig = inspect.signature(
            service_adapter_boundary_validator_ci_manifest
        )
        self.assertEqual(list(manifest_sig.parameters.keys()), [])
        consume_sig = inspect.signature(
            consume_service_adapter_boundary_validator_ci
        )
        self.assertEqual(list(consume_sig.parameters.keys()), ["payload"])


class SourceBoundaryTests(unittest.TestCase):
    def test_only_allowed_production_imports(self) -> None:
        source = inspect.getsource(ci_module)
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

    def test_no_validator_import_or_call(self) -> None:
        source = _scrubbed_source()
        for marker in (
            "service_adapter_boundary_validator_manifest",
            "validate_service_adapter_boundary(",
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
            "recovery_session_host",
            "argparse",
            "click",
            "sqlite3",
            "repositories",
            "unit_of_work",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_upstream_validator_checker_ci_import(self) -> None:
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
            "validate_repository_uow_allowlist(",
            "consume_repository_uow_allowlist_validator_ci(",
            "validate_evidence_audit_append_contract(",
            "consume_evidence_audit_append_contract_validator_ci(",
            "validate_append_runtime_authority_service_boundary(",
            "consume_append_runtime_authority_service_boundary_validator_ci(",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_evidence_audit_append_markers(self) -> None:
        source = _scrubbed_source()
        for marker in (
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
            "service_adapter_runtime",
            "call_service",
            "service_method_call",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_datetime_time_digest_or_runtime_introspection_markers(self) -> None:
        source = inspect.getsource(ci_module)
        for marker in (
            "datetime.now",
            "time.time",
            "time.monotonic",
            "hashlib",
            "hmac",
            "secrets",
            "sha256",
            "blake2",
            "getattr(",
            "callable(",
            "dir(",
            "hasattr(",
            "inspect.",
            "importlib",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
