"""Tracer-bullet tests for the evidence/audit append contract validator CI."""

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

import kernel.lifecycle.evidence_audit_append_contract_validator_ci as ci_module
from kernel.lifecycle.evidence_audit_append_contract_validator_ci import (
    consume_evidence_audit_append_contract_validator_ci,
    evidence_audit_append_contract_validator_ci_manifest,
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

CI_FAILURE_ORDER = [
    "payload_not_mapping",
    "payload_shape_mismatch",
    "append_contract_ready_invalid",
    "append_contract_reason_code_invalid",
    "append_contract_failures_invalid",
    "append_contract_failure_unknown",
    "readiness_reason_mismatch",
    "contract_not_mapping",
    "contract_shape_mismatch",
    "validator_surface_invalid",
    "validator_version_invalid",
    "source_ref_mismatch",
    "operation_ref_invalid",
    "evidence_ref_set_invalid",
    "audit_ref_set_invalid",
    "append_phase_declaration_invalid",
    "evidence_category_invalid",
    "audit_category_invalid",
    "deterministic_append_order_invalid",
    "idempotency_binding_invalid",
    "failure_policy_invalid",
    "boundary_declaration_invalid",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "runtime_flag_invalid",
    "runtime_flag_true",
    "json_safe_invalid",
]

EXPECTED_MANIFEST = {
    "surface": "evidence_audit_append_contract_validator_ci",
    "version": 1,
    "input_shape": (
        "already_rendered_evidence_audit_append_contract_validator_output"
    ),
    "depends_on": {
        "evidence_audit_append_contract_validator": (
            "evidence-audit-append-contract-validator-v1"
        ),
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
    "append_contract",
]

EXPECTED_APPEND_CONTRACT_OUTPUT_KEYS = (
    [
        "surface",
        "version",
        "append_contract_ready",
        "append_contract_reason_code",
        "append_contract_failures",
    ]
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
    + ["json_safe"]
)

EXPECTED_CONTRACT_KEYS = (
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
    " object at 0x",
    "<sqlite3.",
    "EvidenceAuditAppendContract(",
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
)


def _contract(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "evidence_audit_append_contract_validator",
        "version": 1,
    }
    base.update(SOURCE_BINDING_VALUES)
    for field in OPERATION_REFS:
        base[field] = f"{field}-value"
    base["evidence_ref_set"] = ["evidence-ref-1", "evidence-ref-2"]
    base["audit_ref_set"] = ["audit-ref-1", "audit-ref-2"]
    for field in APPEND_PHASE_DECLARATIONS:
        base[field] = True
    for field in EVIDENCE_CATEGORY_DECLARATIONS:
        base[field] = True
    for field in AUDIT_CATEGORY_DECLARATIONS:
        base[field] = True
    base["deterministic_append_order"] = list(DETERMINISTIC_APPEND_ORDER)
    for field in FAILURE_POLICY_DECLARATIONS:
        base[field] = True
    for field in IDEMPOTENCY_DECLARATIONS:
        base[field] = True
    for field in BOUNDARY_DECLARATIONS:
        base[field] = True
    for field in AUTHORIZATION_FLAGS:
        base[field] = False
    for field in RUNTIME_FLAGS:
        base[field] = False
    base["json_safe"] = True
    base["append_contract_ready"] = True
    base.update(overrides)
    return base


def _payload(
    *,
    ready: bool = True,
    reason_code: str = "ready",
    failures: list[str] | None = None,
    contract: object | None = None,
) -> dict[str, object]:
    if failures is None:
        failures = []
    if contract is None:
        contract = _contract(append_contract_ready=ready)
    return {
        "append_contract_ready": ready,
        "reason_code": reason_code,
        "failures": list(failures),
        "contract": contract,
    }


def _expected_append_contract(
    *,
    ready: bool,
    reason_code: str,
    failures: list[str],
) -> dict[str, object]:
    output: dict[str, object] = {
        "surface": "evidence_audit_append_contract_validator_ci",
        "version": 1,
        "append_contract_ready": ready,
        "append_contract_reason_code": reason_code,
        "append_contract_failures": list(failures),
    }
    output.update(SOURCE_BINDING_VALUES)
    for field in OPERATION_REFS:
        output[field] = f"{field}-value"
    output["evidence_ref_set"] = ["evidence-ref-1", "evidence-ref-2"]
    output["audit_ref_set"] = ["audit-ref-1", "audit-ref-2"]
    for field in APPEND_PHASE_DECLARATIONS:
        output[field] = True
    for field in EVIDENCE_CATEGORY_DECLARATIONS:
        output[field] = True
    for field in AUDIT_CATEGORY_DECLARATIONS:
        output[field] = True
    output["deterministic_append_order"] = list(DETERMINISTIC_APPEND_ORDER)
    for field in FAILURE_POLICY_DECLARATIONS:
        output[field] = True
    for field in IDEMPOTENCY_DECLARATIONS:
        output[field] = True
    for field in BOUNDARY_DECLARATIONS:
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
    source_ready: bool,
    source_reason_code: str,
    source_failures: list[str],
) -> dict[str, object]:
    return {
        "ci_ok": ci_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "append_contract": _expected_append_contract(
            ready=source_ready,
            reason_code=source_reason_code,
            failures=source_failures,
        ),
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


def _assert_rejected_with(
    payload: object,
    failure: str,
) -> dict[str, object]:
    result = consume_evidence_audit_append_contract_validator_ci(payload)
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
        result = consume_evidence_audit_append_contract_validator_ci(
            _payload()
        )

        self.assertEqual(
            result,
            _expected_result(
                ci_ok=True,
                reason_code="ready",
                failures=[],
                source_ready=True,
                source_reason_code="ready",
                source_failures=[],
            ),
        )

    def test_happy_not_ready_path(self) -> None:
        source_failures = ["operation_ref_invalid"]
        result = consume_evidence_audit_append_contract_validator_ci(
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
                source_ready=False,
                source_reason_code="not_ready",
                source_failures=source_failures,
            ),
        )

    def test_exact_input_shape(self) -> None:
        self.assertEqual(
            list(_payload().keys()),
            ["append_contract_ready", "reason_code", "failures", "contract"],
        )

    def test_exact_output_shape(self) -> None:
        result = consume_evidence_audit_append_contract_validator_ci(
            _payload()
        )
        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertEqual(
            list(result["append_contract"].keys()),
            EXPECTED_APPEND_CONTRACT_OUTPUT_KEYS,
        )

    def test_output_ci_surface_distinct_from_input_validator_surface(self) -> None:
        result = consume_evidence_audit_append_contract_validator_ci(
            _payload()
        )

        self.assertEqual(
            _payload()["contract"]["surface"],
            "evidence_audit_append_contract_validator",
        )
        self.assertEqual(
            result["append_contract"]["surface"],
            "evidence_audit_append_contract_validator_ci",
        )


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_payload(self) -> None:
        for candidate in (None, "x", 1, 1.0, [], (), object()):
            with self.subTest(candidate=type(candidate).__name__):
                result = consume_evidence_audit_append_contract_validator_ci(
                    candidate
                )
                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["reason_code"], "invalid_ci_payload")
                self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_missing_or_extra_top_level_key(self) -> None:
        _assert_rejected_with({}, "payload_shape_mismatch")
        payload = _payload()
        payload["extra"] = "x"
        _assert_rejected_with(payload, "payload_shape_mismatch")

    def test_append_contract_ready_invalid(self) -> None:
        for candidate in ("true", 1, None):
            with self.subTest(candidate=candidate):
                payload = _payload()
                payload["append_contract_ready"] = candidate
                _assert_rejected_with(
                    payload,
                    "append_contract_ready_invalid",
                )

    def test_ready_with_non_ready_reason(self) -> None:
        _assert_rejected_with(
            _payload(reason_code="not_ready"),
            "readiness_reason_mismatch",
        )

    def test_ready_with_failures(self) -> None:
        _assert_rejected_with(
            _payload(failures=["operation_ref_invalid"]),
            "readiness_reason_mismatch",
        )

    def test_not_ready_with_ready_reason(self) -> None:
        _assert_rejected_with(
            _payload(
                ready=False,
                reason_code="ready",
                failures=["operation_ref_invalid"],
            ),
            "readiness_reason_mismatch",
        )

    def test_not_ready_with_empty_failures(self) -> None:
        _assert_rejected_with(
            _payload(ready=False, reason_code="not_ready"),
            "readiness_reason_mismatch",
        )

    def test_invalid_reason_code(self) -> None:
        _assert_rejected_with(
            _payload(reason_code="unexpected"),
            "append_contract_reason_code_invalid",
        )

    def test_failures_non_list_or_non_string(self) -> None:
        payload = _payload()
        payload["failures"] = "operation_ref_invalid"
        _assert_rejected_with(payload, "append_contract_failures_invalid")

        payload = _payload()
        payload["failures"] = ["operation_ref_invalid", 1]
        _assert_rejected_with(payload, "append_contract_failures_invalid")

    def test_unknown_validator_failure(self) -> None:
        _assert_rejected_with(
            _payload(ready=False, reason_code="not_ready", failures=["x"]),
            "append_contract_failure_unknown",
        )


class ContractShapeTests(unittest.TestCase):
    def test_contract_non_mapping(self) -> None:
        _assert_rejected_with(
            _payload(contract=[]),
            "contract_not_mapping",
        )

    def test_contract_missing_or_extra_key(self) -> None:
        contract = _contract()
        del contract["json_safe"]
        _assert_rejected_with(
            _payload(contract=contract),
            "contract_shape_mismatch",
        )

        contract = _contract(extra="x")
        _assert_rejected_with(
            _payload(contract=contract),
            "contract_shape_mismatch",
        )

    def test_wrong_validator_surface(self) -> None:
        _assert_rejected_with(
            _payload(contract=_contract(surface="other")),
            "validator_surface_invalid",
        )

    def test_wrong_validator_version(self) -> None:
        _assert_rejected_with(
            _payload(contract=_contract(version=2)),
            "validator_version_invalid",
        )

    def test_bool_as_int_validator_version(self) -> None:
        _assert_rejected_with(
            _payload(contract=_contract(version=True)),
            "validator_version_invalid",
        )

    def test_nested_ready_must_match_top_level_ready(self) -> None:
        _assert_rejected_with(
            _payload(contract=_contract(append_contract_ready=False)),
            "readiness_reason_mismatch",
        )


class SourceBindingTests(unittest.TestCase):
    def test_every_source_mismatch(self) -> None:
        for field in SOURCE_BINDING_VALUES:
            with self.subTest(field=field):
                _assert_rejected_with(
                    _payload(contract=_contract(**{field: "wrong"})),
                    "source_ref_mismatch",
                )


class OperationAndRefSetTests(unittest.TestCase):
    def test_invalid_operation_refs(self) -> None:
        for field in OPERATION_REFS:
            with self.subTest(field=field):
                _assert_rejected_with(
                    _payload(contract=_contract(**{field: ""})),
                    "operation_ref_invalid",
                )

    def test_invalid_evidence_ref_set(self) -> None:
        for candidate in ([], ["x", "x"], ["x", ""], ["x", True], "x"):
            with self.subTest(candidate=candidate):
                _assert_rejected_with(
                    _payload(contract=_contract(evidence_ref_set=candidate)),
                    "evidence_ref_set_invalid",
                )

    def test_invalid_audit_ref_set(self) -> None:
        for candidate in ([], ["x", "x"], ["x", ""], ["x", True], "x"):
            with self.subTest(candidate=candidate):
                _assert_rejected_with(
                    _payload(contract=_contract(audit_ref_set=candidate)),
                    "audit_ref_set_invalid",
                )


class DeclarationTests(unittest.TestCase):
    def test_append_phase_declaration_invalid(self) -> None:
        for candidate in (False, "true"):
            with self.subTest(candidate=candidate):
                _assert_rejected_with(
                    _payload(
                        contract=_contract(
                            before_evidence_required=candidate
                        )
                    ),
                    "append_phase_declaration_invalid",
                )

    def test_evidence_category_declaration_invalid(self) -> None:
        _assert_rejected_with(
            _payload(contract=_contract(before_evidence_declared=False)),
            "evidence_category_invalid",
        )

    def test_audit_category_declaration_invalid(self) -> None:
        _assert_rejected_with(
            _payload(contract=_contract(write_attempt_audit_declared=False)),
            "audit_category_invalid",
        )

    def test_deterministic_append_order_invalid(self) -> None:
        order = list(DETERMINISTIC_APPEND_ORDER)
        order[-1] = "wrong"
        _assert_rejected_with(
            _payload(contract=_contract(deterministic_append_order=order)),
            "deterministic_append_order_invalid",
        )

    def test_idempotency_declaration_invalid(self) -> None:
        _assert_rejected_with(
            _payload(
                contract=_contract(
                    append_idempotency_key_binding_required=False
                )
            ),
            "idempotency_binding_invalid",
        )

    def test_failure_policy_declaration_invalid(self) -> None:
        _assert_rejected_with(
            _payload(
                contract=_contract(
                    expected_rejection_policy_declared=False
                )
            ),
            "failure_policy_invalid",
        )

    def test_boundary_declaration_invalid(self) -> None:
        _assert_rejected_with(
            _payload(contract=_contract(db_open_forbidden=False)),
            "boundary_declaration_invalid",
        )


class FlagAndSafetyTests(unittest.TestCase):
    def test_authorization_flag_true_or_non_bool(self) -> None:
        for flag in AUTHORIZATION_FLAGS:
            for candidate, failure in (
                (True, "authorization_flag_true"),
                ("false", "authorization_flag_invalid"),
            ):
                with self.subTest(flag=flag, candidate=candidate):
                    _assert_rejected_with(
                        _payload(contract=_contract(**{flag: candidate})),
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
                        _payload(contract=_contract(**{flag: candidate})),
                        failure,
                    )

    def test_json_safe_false_or_non_bool(self) -> None:
        for candidate in (False, "true"):
            with self.subTest(candidate=candidate):
                _assert_rejected_with(
                    _payload(contract=_contract(json_safe=candidate)),
                    "json_safe_invalid",
                )

    def test_output_hard_false_authority_and_runtime_flags(self) -> None:
        result = consume_evidence_audit_append_contract_validator_ci(
            _payload()
        )
        contract = result["append_contract"]

        for flag in AUTHORIZATION_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(contract[flag], False)
        for flag in RUNTIME_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(contract[flag], False)

    def test_output_json_safe_and_no_runtime_repr(self) -> None:
        result = consume_evidence_audit_append_contract_validator_ci(
            _payload()
        )

        _assert_json_safe(result)
        _assert_no_runtime_repr(result)

    def test_no_raw_undeclared_fields_or_handles_leak(self) -> None:
        payload = _payload()
        payload["db_handle"] = object()
        result = consume_evidence_audit_append_contract_validator_ci(payload)

        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertNotIn("db_handle", result)
        self.assertNotIn("db_handle", result["append_contract"])
        _assert_json_safe(result)

    def test_input_not_mutated(self) -> None:
        payload = _payload()
        before = copy.deepcopy(payload)

        consume_evidence_audit_append_contract_validator_ci(payload)

        self.assertEqual(payload, before)


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            evidence_audit_append_contract_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = evidence_audit_append_contract_validator_ci_manifest()
        manifest["failure_values"].append("mutated")
        manifest["depends_on"]["x"] = "y"

        self.assertEqual(
            evidence_audit_append_contract_validator_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            ci_module.__all__,
            [
                "evidence_audit_append_contract_validator_ci_manifest",
                "consume_evidence_audit_append_contract_validator_ci",
            ],
        )
        public = [
            name for name in dir(ci_module) if not name.startswith("_")
        ]
        self.assertEqual(set(public), set(ci_module.__all__))

    def test_function_signatures(self) -> None:
        self.assertEqual(
            str(
                inspect.signature(
                    evidence_audit_append_contract_validator_ci_manifest
                )
            ),
            "() -> dict[str, object]",
        )
        self.assertEqual(
            str(
                inspect.signature(
                    consume_evidence_audit_append_contract_validator_ci
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
                "from collections.abc import Mapping as _Mapping",
                "from copy import deepcopy as _deepcopy",
            ],
        )

    def test_no_forbidden_source_markers(self) -> None:
        source = inspect.getsource(ci_module)

        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_public_source_contains_no_append_or_service_calls(self) -> None:
        source = inspect.getsource(
            consume_evidence_audit_append_contract_validator_ci
        )

        for marker in (
            "validate_evidence_audit_append_contract(",
            "evidence_audit_append_contract_validator_manifest(",
            "EvidenceService",
            "open_connection",
            "append_evidence",
            "append_audit",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
