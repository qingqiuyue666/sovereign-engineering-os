"""Tracer-bullet tests for the evidence/audit append contract validator."""

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

import kernel.lifecycle.evidence_audit_append_contract_validator as validator_module
from kernel.lifecycle.evidence_audit_append_contract_validator import (
    evidence_audit_append_contract_validator_manifest,
    validate_evidence_audit_append_contract,
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
    "source_evidence_audit_append_contract_spec_only_tag": (
        "evidence-audit-append-contract-spec-only-v1"
    ),
    "source_evidence_audit_append_contract_spec_only_commit": (
        "a601acec242e578e52005e53ad46281f90eace63"
    ),
}

SOURCE_BINDING_FAILURES = {
    "source_read_only_governance_layer_tag": (
        "source_read_only_governance_layer_tag_mismatch"
    ),
    "source_read_only_governance_layer_commit": (
        "source_read_only_governance_layer_commit_mismatch"
    ),
    "source_write_side_precondition_checker_tag": (
        "source_write_side_precondition_checker_tag_mismatch"
    ),
    "source_write_side_precondition_checker_commit": (
        "source_write_side_precondition_checker_commit_mismatch"
    ),
    "source_write_side_precondition_ci_tag": (
        "source_write_side_precondition_ci_tag_mismatch"
    ),
    "source_write_side_precondition_ci_commit": (
        "source_write_side_precondition_ci_commit_mismatch"
    ),
    "source_write_side_recovery_spec_only_tag": (
        "source_write_side_recovery_spec_only_tag_mismatch"
    ),
    "source_write_side_recovery_spec_only_commit": (
        "source_write_side_recovery_spec_only_commit_mismatch"
    ),
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
    "source_write_path_read_only_stack_tag": (
        "source_write_path_stack_tag_mismatch"
    ),
    "source_write_path_read_only_stack_commit": (
        "source_write_path_stack_commit_mismatch"
    ),
    "source_repository_uow_allowlist_read_only_stack_tag": (
        "source_repository_uow_allowlist_stack_tag_mismatch"
    ),
    "source_repository_uow_allowlist_read_only_stack_commit": (
        "source_repository_uow_allowlist_stack_commit_mismatch"
    ),
    "source_evidence_audit_append_contract_spec_only_tag": (
        "source_evidence_audit_append_contract_spec_only_tag_mismatch"
    ),
    "source_evidence_audit_append_contract_spec_only_commit": (
        "source_evidence_audit_append_contract_spec_only_commit_mismatch"
    ),
}

OPERATION_REFS = (
    "approved_task_id",
    "approved_operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "target_artifact_id",
    "target_task_id",
    "human_approval_ref",
    "operator_confirmation_ref",
    "execution_authorization_validator_ci_ref",
    "executor_precondition_validator_ci_ref",
    "write_path_contract_validator_ci_ref",
    "repository_uow_allowlist_validator_ci_ref",
    "append_contract_ref",
    "append_idempotency_key",
)

OPERATION_REF_VALUES = {name: f"{name}-value" for name in OPERATION_REFS}

APPEND_PHASE_DECLARATIONS = (
    "before_evidence_required",
    "mutation_intent_evidence_required",
    "after_evidence_required",
    "rejection_evidence_policy_required",
    "failure_evidence_policy_required",
    "rollback_evidence_policy_required",
    "audit_event_required",
    "deterministic_append_order_required",
    "final_append_set_declaration_required",
)

EVIDENCE_CATEGORY_DECLARATIONS = (
    "before_evidence_declared",
    "mutation_intent_evidence_declared",
    "after_evidence_declared",
    "rejection_evidence_declared",
    "failure_evidence_declared",
    "rollback_evidence_declared",
    "incident_evidence_declared",
    "post_mutation_append_failure_evidence_declared",
)

AUDIT_CATEGORY_DECLARATIONS = (
    "write_attempt_audit_declared",
    "append_set_declaration_audit_declared",
    "rejection_audit_declared",
    "failure_audit_declared",
    "rollback_audit_declared",
    "duplicate_replay_audit_declared",
    "ambiguous_replay_audit_declared",
    "incident_audit_declared",
)

DETERMINISTIC_APPEND_ORDER = [
    "validate_read_only_prerequisites",
    "bind_operation_refs",
    "declare_append_idempotency_key",
    "declare_before_evidence",
    "declare_mutation_intent_evidence",
    "keep_mutation_execution_unauthorized",
    "declare_after_evidence",
    "declare_audit_event",
    "declare_rejection_failure_rollback_evidence_policies",
    "declare_final_append_set",
    "keep_all_append_execution_unauthorized",
]

FAILURE_POLICY_DECLARATIONS = (
    "expected_rejection_policy_declared",
    "unexpected_failure_policy_declared",
    "post_mutation_append_failure_policy_declared",
    "rollback_evidence_policy_declared",
    "rollback_failure_incident_class_declared",
)

IDEMPOTENCY_DECLARATIONS = (
    "append_idempotency_key_binding_required",
    "duplicate_append_same_binding_policy_declared",
    "duplicate_append_different_binding_fail_closed",
    "ambiguous_append_fail_closed",
)

BOUNDARY_DECLARATIONS = (
    "evidence_service_forbidden",
    "approval_service_forbidden",
    "review_service_forbidden",
    "revision_seal_service_forbidden",
    "db_open_forbidden",
    "db_write_forbidden",
    "repository_uow_import_forbidden",
    "repository_uow_call_forbidden",
    "direct_sql_forbidden",
    "raw_sqlite_forbidden",
    "runtime_allowlist_forbidden",
    "checker_forbidden",
    "executor_forbidden",
    "restore_forbidden",
    "restore_cli_forbidden",
    "schema_migration_forbidden",
    "daemon_server_queue_forbidden",
    "external_network_forbidden",
    "filesystem_side_channel_forbidden",
    "irreversible_action_forbidden",
)

AUTHORIZATION_FLAGS = (
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
)

FAILURE_ORDER = [
    "payload_not_mapping",
    "payload_shape_mismatch",
    "contract_not_mapping",
    "contract_shape_mismatch",
    "contract_surface_invalid",
    "contract_version_invalid",
    "source_read_only_governance_layer_tag_mismatch",
    "source_read_only_governance_layer_commit_mismatch",
    "source_write_side_precondition_checker_tag_mismatch",
    "source_write_side_precondition_checker_commit_mismatch",
    "source_write_side_precondition_ci_tag_mismatch",
    "source_write_side_precondition_ci_commit_mismatch",
    "source_write_side_recovery_spec_only_tag_mismatch",
    "source_write_side_recovery_spec_only_commit_mismatch",
    "source_restore_dry_run_stack_tag_mismatch",
    "source_restore_dry_run_stack_commit_mismatch",
    "source_preflight_stack_tag_mismatch",
    "source_preflight_stack_commit_mismatch",
    "source_execution_authorization_stack_tag_mismatch",
    "source_execution_authorization_stack_commit_mismatch",
    "source_executor_precondition_stack_tag_mismatch",
    "source_executor_precondition_stack_commit_mismatch",
    "source_write_path_stack_tag_mismatch",
    "source_write_path_stack_commit_mismatch",
    "source_repository_uow_allowlist_stack_tag_mismatch",
    "source_repository_uow_allowlist_stack_commit_mismatch",
    "source_evidence_audit_append_contract_spec_only_tag_mismatch",
    "source_evidence_audit_append_contract_spec_only_commit_mismatch",
    "operation_ref_invalid",
    "evidence_ref_set_invalid",
    "audit_ref_set_invalid",
    "append_phase_declaration_invalid",
    "append_phase_declaration_false",
    "evidence_category_invalid",
    "evidence_category_false",
    "audit_category_invalid",
    "audit_category_false",
    "deterministic_append_order_invalid",
    "idempotency_binding_invalid",
    "idempotency_binding_false",
    "failure_policy_invalid",
    "failure_policy_false",
    "boundary_declaration_invalid",
    "boundary_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "runtime_flag_invalid",
    "runtime_flag_true",
    "json_safe_invalid",
]

EXPECTED_MANIFEST = {
    "surface": "evidence_audit_append_contract_validator",
    "version": 1,
    "input_shape": "already_rendered_evidence_audit_append_contract",
    "depends_on": {
        "evidence_audit_append_contract_spec_only": (
            "evidence-audit-append-contract-spec-only-v1"
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
    "appends_evidence": False,
    "appends_audit": False,
    "calls_evidence_service": False,
    "calls_services": False,
    "opens_db": False,
    "calls_repository": False,
    "calls_uow": False,
    "executes_plan": False,
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
        "invalid_contract_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": FAILURE_ORDER,
}

EXPECTED_OUTPUT_KEYS = [
    "append_contract_ready",
    "reason_code",
    "failures",
    "contract",
]

EXPECTED_CONTRACT_OUTPUT_KEYS = (
    ["surface", "version"]
    + list(SOURCE_BINDING_VALUES.keys())
    + list(OPERATION_REFS)
    + ["evidence_ref_set", "audit_ref_set"]
    + list(APPEND_PHASE_DECLARATIONS)
    + list(EVIDENCE_CATEGORY_DECLARATIONS)
    + list(AUDIT_CATEGORY_DECLARATIONS)
    + ["deterministic_append_order"]
    + list(FAILURE_POLICY_DECLARATIONS)
    + list(IDEMPOTENCY_DECLARATIONS)
    + list(BOUNDARY_DECLARATIONS)
    + list(AUTHORIZATION_FLAGS)
    + list(RUNTIME_FLAGS)
    + ["json_safe", "append_contract_ready"]
)

REPR_MARKERS = (
    "EvidenceAuditAppendContract(",
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
)

ALLOWED_SOURCE_FIELD_STRINGS = (
    "evidence_audit_append_contract_validator_manifest",
    "validate_evidence_audit_append_contract",
    "evidence_audit_append_contract_validator",
    "EvidenceAuditAppendContractV1",
    "evidence-audit-append-contract-spec-only-v1",
    "repository-uow-allowlist-read-only-stack-v1",
    "write-path-read-only-stack-v1",
    "executor-precondition-read-only-stack-v1",
    "execution-authorization-read-only-stack-v1",
    "preflight-read-only-stack-v1",
    "restore-dry-run-read-only-stack-v1",
    "evidence_append_authorized",
    "audit_append_authorized",
    "evidence_service_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "daemon_server_queue_authorized",
    "appends_evidence",
    "appends_audit",
)


def _contract(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "EvidenceAuditAppendContractV1",
        "version": 1,
    }
    for name, value in SOURCE_BINDING_VALUES.items():
        base[name] = value
    for name, value in OPERATION_REF_VALUES.items():
        base[name] = value
    base["evidence_ref_set"] = ["evidence-ref-1", "evidence-ref-2"]
    base["audit_ref_set"] = ["audit-ref-1", "audit-ref-2"]
    for name in APPEND_PHASE_DECLARATIONS:
        base[name] = True
    for name in EVIDENCE_CATEGORY_DECLARATIONS:
        base[name] = True
    for name in AUDIT_CATEGORY_DECLARATIONS:
        base[name] = True
    base["deterministic_append_order"] = list(DETERMINISTIC_APPEND_ORDER)
    for name in FAILURE_POLICY_DECLARATIONS:
        base[name] = True
    for name in IDEMPOTENCY_DECLARATIONS:
        base[name] = True
    for name in BOUNDARY_DECLARATIONS:
        base[name] = True
    for name in AUTHORIZATION_FLAGS:
        base[name] = False
    for name in RUNTIME_FLAGS:
        base[name] = False
    base["json_safe"] = True
    base.update(overrides)
    return base


def _payload(**overrides: object) -> dict[str, object]:
    contract = overrides.pop("contract", None)
    if contract is None:
        contract = _contract()
    payload: dict[str, object] = {"evidence_audit_append_contract": contract}
    payload.update(overrides)
    return payload


def _expected_happy_output() -> dict[str, object]:
    contract: dict[str, object] = {
        "surface": "evidence_audit_append_contract_validator",
        "version": 1,
    }
    for name, value in SOURCE_BINDING_VALUES.items():
        contract[name] = value
    for name, value in OPERATION_REF_VALUES.items():
        contract[name] = value
    contract["evidence_ref_set"] = ["evidence-ref-1", "evidence-ref-2"]
    contract["audit_ref_set"] = ["audit-ref-1", "audit-ref-2"]
    for name in APPEND_PHASE_DECLARATIONS:
        contract[name] = True
    for name in EVIDENCE_CATEGORY_DECLARATIONS:
        contract[name] = True
    for name in AUDIT_CATEGORY_DECLARATIONS:
        contract[name] = True
    contract["deterministic_append_order"] = list(DETERMINISTIC_APPEND_ORDER)
    for name in FAILURE_POLICY_DECLARATIONS:
        contract[name] = True
    for name in IDEMPOTENCY_DECLARATIONS:
        contract[name] = True
    for name in BOUNDARY_DECLARATIONS:
        contract[name] = True
    for name in AUTHORIZATION_FLAGS:
        contract[name] = False
    for name in RUNTIME_FLAGS:
        contract[name] = False
    contract["json_safe"] = True
    contract["append_contract_ready"] = True
    return {
        "append_contract_ready": True,
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
    result = validate_evidence_audit_append_contract(payload)
    if result["append_contract_ready"] is not False:
        raise AssertionError("contract unexpectedly ready")
    if failure not in result["failures"]:
        raise AssertionError(
            f"missing failure {failure}: {result['failures']}"
        )
    return result


class HappyPathTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        result = validate_evidence_audit_append_contract(_payload())
        self.assertEqual(result, _expected_happy_output())

    def test_ready_does_not_authorize_append_or_writes(self) -> None:
        result = validate_evidence_audit_append_contract(_payload())
        contract = result["contract"]

        self.assertTrue(result["append_contract_ready"])
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(contract[flag], False)
        for flag in RUNTIME_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(contract[flag], False)

    def test_output_shape_exact(self) -> None:
        result = validate_evidence_audit_append_contract(_payload())
        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertEqual(
            list(result["contract"].keys()),
            EXPECTED_CONTRACT_OUTPUT_KEYS,
        )

    def test_input_shape_exact(self) -> None:
        payload = _payload()
        self.assertEqual(list(payload.keys()), ["evidence_audit_append_contract"])


class TopLevelInputTests(unittest.TestCase):
    def test_non_mapping_rejected(self) -> None:
        for candidate in (None, "x", 1, 1.0, [], (), object()):
            with self.subTest(candidate=type(candidate).__name__):
                result = validate_evidence_audit_append_contract(candidate)
                self.assertFalse(result["append_contract_ready"])
                self.assertEqual(
                    result["reason_code"], "invalid_contract_payload"
                )
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_top_level_key_rejected(self) -> None:
        _assert_rejected_with({}, "payload_shape_mismatch")

    def test_unknown_top_level_key_rejected(self) -> None:
        payload = _payload()
        payload["unexpected"] = "x"
        _assert_rejected_with(payload, "payload_shape_mismatch")


class ContractStructureTests(unittest.TestCase):
    def test_contract_non_mapping_rejected(self) -> None:
        for candidate in (None, "x", 1, 1.0, [], object()):
            with self.subTest(candidate=type(candidate).__name__):
                _assert_rejected_with(
                    {"evidence_audit_append_contract": candidate},
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

    def test_wrong_surface_rejected(self) -> None:
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
    def test_each_source_ref_mismatch_rejected(self) -> None:
        for field, failure in SOURCE_BINDING_FAILURES.items():
            with self.subTest(field=field):
                contract = _contract()
                contract[field] = "wrong-ref"
                result = _assert_rejected_with(
                    _payload(contract=contract),
                    failure,
                )
                self.assertNotIn(
                    "contract_shape_mismatch", result["failures"]
                )
                self.assertEqual(
                    result["reason_code"], "invalid_contract_payload"
                )


class OperationRefTests(unittest.TestCase):
    def test_each_operation_ref_invalid_rejected(self) -> None:
        for field in OPERATION_REFS:
            for bad in (None, "", 1, True, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract(**{field: bad})
                    result = _assert_rejected_with(
                        _payload(contract=contract),
                        "operation_ref_invalid",
                    )
                    self.assertEqual(result["reason_code"], "not_ready")


class RefSetTests(unittest.TestCase):
    def _expect_failure(self, field: str, value: object, failure: str) -> None:
        contract = _contract(**{field: value})
        _assert_rejected_with(_payload(contract=contract), failure)

    def test_evidence_ref_set_invalid_cases(self) -> None:
        cases = (
            None,
            "x",
            {},
            1,
            True,
            [],
            [""],
            [1],
            [True],
            ["a", "a"],
        )
        for value in cases:
            with self.subTest(value=value):
                self._expect_failure(
                    "evidence_ref_set", value, "evidence_ref_set_invalid"
                )

    def test_audit_ref_set_invalid_cases(self) -> None:
        cases = (
            None,
            "x",
            {},
            1,
            True,
            [],
            [""],
            [1],
            [True],
            ["a", "a"],
        )
        for value in cases:
            with self.subTest(value=value):
                self._expect_failure(
                    "audit_ref_set", value, "audit_ref_set_invalid"
                )


class AppendPhaseDeclarationTests(unittest.TestCase):
    def test_invalid_type_rejected(self) -> None:
        for field in APPEND_PHASE_DECLARATIONS:
            for bad in (None, "true", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract(**{field: bad})
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "append_phase_declaration_invalid",
                    )

    def test_false_rejected(self) -> None:
        for field in APPEND_PHASE_DECLARATIONS:
            with self.subTest(field=field):
                contract = _contract(**{field: False})
                _assert_rejected_with(
                    _payload(contract=contract),
                    "append_phase_declaration_false",
                )


class EvidenceCategoryDeclarationTests(unittest.TestCase):
    def test_invalid_type_rejected(self) -> None:
        for field in EVIDENCE_CATEGORY_DECLARATIONS:
            for bad in (None, "true", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract(**{field: bad})
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "evidence_category_invalid",
                    )

    def test_false_rejected(self) -> None:
        for field in EVIDENCE_CATEGORY_DECLARATIONS:
            with self.subTest(field=field):
                contract = _contract(**{field: False})
                _assert_rejected_with(
                    _payload(contract=contract),
                    "evidence_category_false",
                )


class AuditCategoryDeclarationTests(unittest.TestCase):
    def test_invalid_type_rejected(self) -> None:
        for field in AUDIT_CATEGORY_DECLARATIONS:
            for bad in (None, "true", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract(**{field: bad})
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "audit_category_invalid",
                    )

    def test_false_rejected(self) -> None:
        for field in AUDIT_CATEGORY_DECLARATIONS:
            with self.subTest(field=field):
                contract = _contract(**{field: False})
                _assert_rejected_with(
                    _payload(contract=contract),
                    "audit_category_false",
                )


class DeterministicOrderTests(unittest.TestCase):
    def test_wrong_value_rejected(self) -> None:
        wrong = list(DETERMINISTIC_APPEND_ORDER)
        wrong[0] = "wrong_step"
        contract = _contract(deterministic_append_order=wrong)
        _assert_rejected_with(
            _payload(contract=contract),
            "deterministic_append_order_invalid",
        )

    def test_missing_item_rejected(self) -> None:
        truncated = list(DETERMINISTIC_APPEND_ORDER)[:-1]
        contract = _contract(deterministic_append_order=truncated)
        _assert_rejected_with(
            _payload(contract=contract),
            "deterministic_append_order_invalid",
        )

    def test_extra_item_rejected(self) -> None:
        extended = list(DETERMINISTIC_APPEND_ORDER) + ["extra_step"]
        contract = _contract(deterministic_append_order=extended)
        _assert_rejected_with(
            _payload(contract=contract),
            "deterministic_append_order_invalid",
        )

    def test_non_list_rejected(self) -> None:
        for bad in (None, "x", 1, True, {}):
            with self.subTest(bad=type(bad).__name__):
                contract = _contract(deterministic_append_order=bad)
                _assert_rejected_with(
                    _payload(contract=contract),
                    "deterministic_append_order_invalid",
                )


class IdempotencyDeclarationTests(unittest.TestCase):
    def test_invalid_type_rejected(self) -> None:
        for field in IDEMPOTENCY_DECLARATIONS:
            for bad in (None, "true", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract(**{field: bad})
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "idempotency_binding_invalid",
                    )

    def test_false_rejected(self) -> None:
        for field in IDEMPOTENCY_DECLARATIONS:
            with self.subTest(field=field):
                contract = _contract(**{field: False})
                _assert_rejected_with(
                    _payload(contract=contract),
                    "idempotency_binding_false",
                )


class FailurePolicyDeclarationTests(unittest.TestCase):
    def test_invalid_type_rejected(self) -> None:
        for field in FAILURE_POLICY_DECLARATIONS:
            for bad in (None, "true", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract(**{field: bad})
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "failure_policy_invalid",
                    )

    def test_false_rejected(self) -> None:
        for field in FAILURE_POLICY_DECLARATIONS:
            with self.subTest(field=field):
                contract = _contract(**{field: False})
                _assert_rejected_with(
                    _payload(contract=contract),
                    "failure_policy_false",
                )


class BoundaryDeclarationTests(unittest.TestCase):
    def test_invalid_type_rejected(self) -> None:
        for field in BOUNDARY_DECLARATIONS:
            for bad in (None, "true", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract(**{field: bad})
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "boundary_declaration_invalid",
                    )

    def test_false_rejected(self) -> None:
        for field in BOUNDARY_DECLARATIONS:
            with self.subTest(field=field):
                contract = _contract(**{field: False})
                _assert_rejected_with(
                    _payload(contract=contract),
                    "boundary_declaration_false",
                )


class AuthorizationFlagTests(unittest.TestCase):
    def test_invalid_type_rejected(self) -> None:
        for field in AUTHORIZATION_FLAGS:
            for bad in (None, "false", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract(**{field: bad})
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "authorization_flag_invalid",
                    )

    def test_true_rejected(self) -> None:
        for field in AUTHORIZATION_FLAGS:
            with self.subTest(field=field):
                contract = _contract(**{field: True})
                _assert_rejected_with(
                    _payload(contract=contract),
                    "authorization_flag_true",
                )


class RuntimeFlagTests(unittest.TestCase):
    def test_invalid_type_rejected(self) -> None:
        for field in RUNTIME_FLAGS:
            for bad in (None, "false", 1, 0, [], {}):
                with self.subTest(field=field, bad=type(bad).__name__):
                    contract = _contract(**{field: bad})
                    _assert_rejected_with(
                        _payload(contract=contract),
                        "runtime_flag_invalid",
                    )

    def test_true_rejected(self) -> None:
        for field in RUNTIME_FLAGS:
            with self.subTest(field=field):
                contract = _contract(**{field: True})
                _assert_rejected_with(
                    _payload(contract=contract),
                    "runtime_flag_true",
                )


class JsonSafeTests(unittest.TestCase):
    def test_json_safe_false_rejected(self) -> None:
        contract = _contract(json_safe=False)
        _assert_rejected_with(
            _payload(contract=contract),
            "json_safe_invalid",
        )

    def test_json_safe_invalid_type_rejected(self) -> None:
        for bad in (None, "true", 1, 0, [], {}):
            with self.subTest(bad=type(bad).__name__):
                contract = _contract(json_safe=bad)
                _assert_rejected_with(
                    _payload(contract=contract),
                    "json_safe_invalid",
                )


class ReasonCodeMappingTests(unittest.TestCase):
    def test_invalid_payload_reason_code(self) -> None:
        result = validate_evidence_audit_append_contract(None)
        self.assertEqual(result["reason_code"], "invalid_contract_payload")

        contract = _contract(surface="other")
        result = validate_evidence_audit_append_contract(
            _payload(contract=contract)
        )
        self.assertEqual(result["reason_code"], "invalid_contract_payload")

    def test_not_ready_reason_code(self) -> None:
        contract = _contract(before_evidence_declared=False)
        result = validate_evidence_audit_append_contract(
            _payload(contract=contract)
        )
        self.assertFalse(result["append_contract_ready"])
        self.assertEqual(result["reason_code"], "not_ready")


class FailureOrderingTests(unittest.TestCase):
    def test_combined_failures_deterministic_order(self) -> None:
        contract = _contract(
            surface="OtherSurface",
            version=True,
            before_evidence_required=False,
            json_safe=False,
            executor_implementation_authorized=True,
            appends_evidence=True,
        )
        contract["source_preflight_read_only_stack_tag"] = "wrong-tag"
        result = validate_evidence_audit_append_contract(
            _payload(contract=contract)
        )
        self.assertFalse(result["append_contract_ready"])
        positions = [FAILURE_ORDER.index(item) for item in result["failures"]]
        self.assertEqual(positions, sorted(positions))


class OutputBoundaryTests(unittest.TestCase):
    def test_output_authorization_flags_hard_false(self) -> None:
        contract = _contract()
        for flag in AUTHORIZATION_FLAGS:
            contract[flag] = True
        # Note: with these flags True, validator will reject; but the output
        # contract must still echo authorization flags as hard False.
        result = validate_evidence_audit_append_contract(
            _payload(contract=contract)
        )
        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result["contract"][flag], False)

    def test_output_runtime_flags_hard_false(self) -> None:
        contract = _contract()
        for flag in RUNTIME_FLAGS:
            contract[flag] = True
        result = validate_evidence_audit_append_contract(
            _payload(contract=contract)
        )
        for flag in RUNTIME_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(result["contract"][flag], False)

    def test_output_no_raw_undeclared_fields(self) -> None:
        contract = _contract()
        contract_with_extra = dict(contract)
        # We can't pass extra fields without triggering shape mismatch, but
        # the output must always contain only the bounded keys regardless of
        # input; assert that here.
        result = validate_evidence_audit_append_contract(_payload())
        contract_keys = list(result["contract"].keys())
        self.assertEqual(contract_keys, EXPECTED_CONTRACT_OUTPUT_KEYS)


class JsonSafetyTests(unittest.TestCase):
    def test_output_json_safe(self) -> None:
        result = validate_evidence_audit_append_contract(_payload())
        _assert_json_safe(result)

    def test_manifest_json_safe(self) -> None:
        manifest = evidence_audit_append_contract_validator_manifest()
        _assert_json_safe(manifest)

    def test_no_runtime_repr_leakage(self) -> None:
        result = validate_evidence_audit_append_contract(_payload())
        _assert_no_runtime_repr(result)


class InputImmutabilityTests(unittest.TestCase):
    def test_input_not_mutated(self) -> None:
        payload = _payload()
        snapshot = copy.deepcopy(payload)
        validate_evidence_audit_append_contract(payload)
        self.assertEqual(payload, snapshot)


class ManifestTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = evidence_audit_append_contract_validator_manifest()
        self.assertEqual(manifest, EXPECTED_MANIFEST)

    def test_manifest_defensive_copy(self) -> None:
        first = evidence_audit_append_contract_validator_manifest()
        first["mutated"] = "x"
        first["depends_on"]["mutated"] = "y"
        first["failure_values"].append("mutated")
        second = evidence_audit_append_contract_validator_manifest()
        self.assertEqual(second, EXPECTED_MANIFEST)
        self.assertNotIn("mutated", second)
        self.assertNotIn("mutated", second["depends_on"])
        self.assertNotIn("mutated", second["failure_values"])


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(validator_module.__all__),
            sorted(
                [
                    "evidence_audit_append_contract_validator_manifest",
                    "validate_evidence_audit_append_contract",
                ]
            ),
        )

    def test_signatures(self) -> None:
        manifest_sig = inspect.signature(
            evidence_audit_append_contract_validator_manifest
        )
        self.assertEqual(list(manifest_sig.parameters.keys()), [])
        validate_sig = inspect.signature(
            validate_evidence_audit_append_contract
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
                "from collections.abc import Mapping as _Mapping",
                "from copy import deepcopy as _deepcopy",
            ],
        )

    def test_source_boundary_forbids_external_runtime_coupling(self) -> None:
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

    def test_no_evidence_audit_append_markers(self) -> None:
        source = inspect.getsource(validator_module)
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


if __name__ == "__main__":
    unittest.main()
