"""Pure validator for rendered service call admission gate declarations."""

from collections.abc import Mapping
from copy import deepcopy


__all__ = [
    "service_call_admission_gate_validator_manifest",
    "validate_service_call_admission_gate",
]


_SURFACE = "service_call_admission_gate_validator"
_CONTRACT_NAME = "ServiceCallAdmissionGateV1"
_VERSION = 1

_REASON_READY = "ready"
_REASON_NOT_READY = "not_ready"
_REASON_INVALID = "invalid_service_call_admission_payload"

_INPUT_KEY = "service_call_admission_gate"
_INPUT_KEYS = (_INPUT_KEY,)

_GATE_KEYS = (
    "surface",
    "version",
    "source_refs",
    "service_identity",
    "service_class_name",
    "service_method_name",
    "operation_ref",
    "target_surface",
    "permitted_action_class",
    "forbidden_action_class",
    "runtime_authority_grant_object_ref",
    "authority_ref",
    "service_method_authority_ref",
    "service_call_execution_boundary_ref",
    "execution_authorization_ref",
    "human_approval_ref",
    "operator_confirmation_ref",
    "runtime_authority_checker_enforcer_stack_ref",
    "service_adapter_boundary_ref",
    "evidence_audit_append_boundary_ref",
    "repository_uow_allowlist_ref",
    "write_path_boundary_ref",
    "executor_precondition_ref",
    "idempotency_key_ref",
    "transaction_placement_ref",
    "evidence_pre_bookkeeping_ref",
    "audit_pre_bookkeeping_ref",
    "evidence_post_bookkeeping_ref",
    "audit_post_bookkeeping_ref",
    "expiry_ref",
    "revocation_ref",
    "revocation_status_ref",
    "admission_denial_policy",
    "incident_classification_policy",
    "false_authority_flags",
    "true_declarations",
    "json_safe",
)

_SOURCE_REFS = {
    "read-only-governance-layer-v1": (
        "4656e8f03404c6bb39e7976c6165e3d7dc0314fb"
    ),
    "write-side-precondition-checker-v1": (
        "fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6"
    ),
    "write-side-precondition-ci-v1": (
        "05c81541ad3d7deee20023843142f702937f6c3f"
    ),
    "write-side-recovery-spec-only-v1": (
        "ad560cc2dab135f2c1d56d948410ae47586d118e"
    ),
    "restore-dry-run-read-only-stack-v1": (
        "e7c78e3ff0c5dc05806c293f01ab32cd33c9518b"
    ),
    "preflight-read-only-stack-v1": (
        "662b6161253c35204b437e88809c5bab21908c6d"
    ),
    "execution-authorization-read-only-stack-v1": (
        "d586aeb60620010c900df7be1a88621ab2cb8dc1"
    ),
    "executor-precondition-read-only-stack-v1": (
        "cb3948eb843866dcc961b6a074038c13db64d017"
    ),
    "write-path-read-only-stack-v1": (
        "8ffd4679aca8f593415089748df35df42af8f015"
    ),
    "repository-uow-allowlist-read-only-stack-v1": (
        "bec2d04eab1922594dcbfbe35971f4efe0fe4849"
    ),
    "evidence-audit-append-read-only-stack-v1": (
        "62db8a586efa9375d2c77cf7c6335ccf5ef11279"
    ),
    "append-runtime-authority-service-boundary-read-only-stack-v1": (
        "bda430a6a8d1e1dbede2adb9594baa1ab5cf2039"
    ),
    "service-adapter-boundary-read-only-stack-v1": (
        "8698ea42c78cbe79231698be8839b9d2c246cfdf"
    ),
    "service-method-authority-read-only-stack-v1": (
        "db2f628cc79df0dc7b4f1306cbe24d880693188b"
    ),
    "service-call-execution-boundary-read-only-stack-v1": (
        "2a82b78665541d2e408113646ea11fbda4b62037"
    ),
    "runtime-authority-checker-enforcer-read-only-stack-v1": (
        "a749545998e94aceee52775d363f9b8bb43e26a4"
    ),
    "runtime-authority-grant-object-read-only-stack-v1": (
        "4acbddba3e0897d16bcfc74007ecd094817faa11"
    ),
    "service-call-admission-gate-spec-only-v1": (
        "47a86884718bdf215d2f1a7c706bf69de41ee7a9"
    ),
    "runtime-authority-checker-enforcer-boundary-spec-only-v1": (
        "9bd776b4178ce627e28eb430ea07d6b7a2a002ce"
    ),
    "runtime-authority-checker-enforcer-boundary-validator-v1": (
        "b2627216e5efb803ebe673dc38b3167db7a8e3db"
    ),
    "runtime-authority-checker-enforcer-boundary-validator-ci-v1": (
        "a749545998e94aceee52775d363f9b8bb43e26a4"
    ),
    "runtime-authority-grant-object-spec-only-v1": (
        "3910680b973a7bfb9fa89b2ab52a213d402fbdae"
    ),
    "runtime-authority-grant-object-validator-v1": (
        "ed31e3c92a7bd3d35e411dd4e559038023a2f8d9"
    ),
    "runtime-authority-grant-object-validator-ci-v1": (
        "4acbddba3e0897d16bcfc74007ecd094817faa11"
    ),
}

_BINDING_GROUPS = {
    "service_identity_binding": (
        "service_identity",
        "service_class_name",
        "service_method_name",
        "operation_ref",
        "target_surface",
        "permitted_action_class",
        "forbidden_action_class",
    ),
    "authority_input_binding": (
        "runtime_authority_grant_object_ref",
        "authority_ref",
        "service_method_authority_ref",
        "service_call_execution_boundary_ref",
        "execution_authorization_ref",
        "human_approval_ref",
        "operator_confirmation_ref",
    ),
    "read_only_stack_binding": (
        "runtime_authority_checker_enforcer_stack_ref",
        "service_adapter_boundary_ref",
        "evidence_audit_append_boundary_ref",
        "repository_uow_allowlist_ref",
        "write_path_boundary_ref",
        "executor_precondition_ref",
    ),
    "evidence_idempotency_transaction_binding": (
        "idempotency_key_ref",
        "transaction_placement_ref",
        "evidence_pre_bookkeeping_ref",
        "audit_pre_bookkeeping_ref",
        "evidence_post_bookkeeping_ref",
        "audit_post_bookkeeping_ref",
    ),
    "expiry_revocation_binding": (
        "expiry_ref",
        "revocation_ref",
        "revocation_status_ref",
    ),
    "denial_incident_policy": (
        "admission_denial_policy",
        "incident_classification_policy",
    ),
}

_FORBIDDEN_IMPLICIT_AUTHORITY_SOURCES = (
    "tag existence",
    "readiness",
    "validator success",
    "CI success",
    "approval",
    "execution authorization",
    "method authority",
    "service call boundary",
    "runtime authority grant object readiness",
    "runtime authority checker/enforcer readiness",
    "evidence/audit ref existence",
    "idempotency key existence",
    "transaction placement declaration",
    "service adapter boundary declaration",
)

_FORBIDDEN_IMPLICIT_AUTHORITY_DECLARATIONS = (
    "tag_existence_is_not_authority",
    "readiness_is_not_authority",
    "authorization_is_not_execution",
    "approval_is_not_authority",
    "execution_authorization_is_not_execution",
    "method_authority_is_not_runtime_authority",
    "service_call_boundary_is_not_runtime_authority",
    "runtime_authority_stack_readiness_is_not_runtime_authority",
    "runtime_authority_grant_object_readiness_is_not_runtime_authority",
    "service_call_admission_is_not_execution",
    "admission_decision_is_not_service_call",
    "implicit_admission_escalation_forbidden",
    "implicit_authority_escalation_forbidden",
)

_REQUIRED_FALSE_AUTHORITY_FLAGS = (
    "service_call_admission_runtime_authorized",
    "service_call_admission_gate_authorized",
    "service_call_admission_decision_authorized",
    "runtime_authority_grant_runtime_authorized",
    "runtime_authority_ref_runtime_authorized",
    "runtime_authority_checker_authorized",
    "runtime_authority_enforcer_authorized",
    "runtime_authority_runtime_authorized",
    "runtime_allowlist_authorized",
    "runtime_checker_authorized",
    "runtime_enforcer_authorized",
    "service_call_execution_authorized",
    "service_adapter_runtime_authorized",
    "service_adapter_implementation_authorized",
    "service_method_call_authorized",
    "service_side_effect_authorized",
    "evidence_service_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "audit_service_authorized",
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
    "executor_implementation_authorized",
    "executor_service_dispatch_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "filesystem_side_effects_authorized",
    "external_network_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
    "db_repair_authorized",
)

_REQUIRED_TRUE_DECLARATIONS = (
    "spec_only_non_executable",
    "service_call_admission_forbidden",
    "service_call_admission_runtime_forbidden",
    "service_call_admission_is_not_execution",
    "admission_decision_is_not_service_call",
    "readiness_is_not_authority",
    "authorization_is_not_execution",
    "approval_is_not_authority",
    "execution_authorization_is_not_execution",
    "method_authority_is_not_runtime_authority",
    "service_call_boundary_is_not_runtime_authority",
    "runtime_authority_stack_readiness_is_not_runtime_authority",
    "runtime_authority_grant_object_readiness_is_not_runtime_authority",
    "tag_existence_is_not_authority",
    "runtime_authority_grant_object_required",
    "authority_ref_required",
    "authority_ref_source_bound_required",
    "authority_ref_operation_bound_required",
    "authority_ref_target_bound_required",
    "authority_ref_revocation_checked_required",
    "authority_ref_expiry_checked_required",
    "service_method_authority_required",
    "service_call_execution_boundary_required",
    "execution_authorization_required",
    "human_approval_required",
    "operator_confirmation_required",
    "runtime_authority_checker_enforcer_stack_required",
    "service_adapter_boundary_required",
    "evidence_audit_append_boundary_required",
    "repository_uow_allowlist_required",
    "write_path_boundary_required",
    "executor_precondition_required",
    "exact_service_identity_required",
    "exact_service_class_name_required",
    "exact_service_method_name_required",
    "operation_bound_required",
    "target_surface_bound_required",
    "permitted_action_class_required",
    "forbidden_action_class_required",
    "idempotency_key_ref_required",
    "transaction_placement_ref_required",
    "evidence_pre_bookkeeping_ref_required",
    "audit_pre_bookkeeping_ref_required",
    "evidence_post_bookkeeping_ref_required",
    "audit_post_bookkeeping_ref_required",
    "denial_fail_closed_required",
    "missing_grant_fail_closed",
    "missing_authority_ref_fail_closed",
    "malformed_authority_ref_fail_closed",
    "mismatched_authority_ref_fail_closed",
    "expired_authority_fail_closed",
    "revoked_authority_fail_closed",
    "ambiguous_authority_incident_class",
    "admission_mismatch_incident_class",
    "silent_admission_success_forbidden",
    "implicit_admission_escalation_forbidden",
    "implicit_authority_escalation_forbidden",
    "service_calls_forbidden",
    "service_call_execution_forbidden",
    "service_adapter_implementation_forbidden",
    "db_repository_uow_writes_forbidden",
    "evidence_append_forbidden",
    "audit_append_forbidden",
    "transaction_runtime_forbidden",
    "idempotency_reservation_forbidden",
    "rollback_runtime_forbidden",
    "executor_dispatch_forbidden",
    "durable_writes_forbidden",
    "irreversible_actions_forbidden",
    "future_validator_required",
    "future_ci_required",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "gate_not_mapping",
    "gate_shape_mismatch",
    "gate_surface_invalid",
    "gate_version_invalid",
    "source_ref_mismatch",
    "admission_input_invalid",
    "binding_group_invalid",
    "required_binding_invalid",
    "required_binding_false",
    "forbidden_implicit_authority_invalid",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "required_declaration_invalid",
    "required_declaration_false",
    "json_safe_invalid",
)

_INVALID_PAYLOAD_FAILURES = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "gate_not_mapping",
    "gate_shape_mismatch",
)

_BINDING_FIELD_TO_GROUP = {
    field: group_name
    for group_name, fields in _BINDING_GROUPS.items()
    for field in fields
}

_BINDING_VALUE_KEYS = ("binding_group", "required")

_AUTHORITY_SUMMARY = {
    flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
}

_NON_AUTHORITY_SUMMARY = {
    "service_call_admission_gate_ready_proves": (
        "structural_declaration_validity_only"
    ),
    "service_call_admission_gate_ready_authorizes_service_call_admission_runtime": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_admission_decision_runtime": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_runtime_authority_grant_usage": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_authority_ref_runtime_usage": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_checker_enforcer_runtime": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_service_calls": False,
    "service_call_admission_gate_ready_authorizes_evidence_audit_append": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_db_repository_uow_writes": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_transaction_runtime": False,
    "service_call_admission_gate_ready_authorizes_idempotency_reservation": (
        False
    ),
    "service_call_admission_gate_ready_authorizes_rollback_runtime": False,
    "service_call_admission_gate_ready_authorizes_executor_dispatch": False,
    "service_call_admission_gate_ready_authorizes_durable_writes": False,
    "service_call_admission_gate_ready_authorizes_irreversible_actions": False,
}

_ADMISSION_INPUT_SUMMARY = {
    group_name: list(fields) for group_name, fields in _BINDING_GROUPS.items()
}
_ADMISSION_INPUT_SUMMARY["forbidden_implicit_authority_sources"] = list(
    _FORBIDDEN_IMPLICIT_AUTHORITY_SOURCES
)

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "contract_name": _CONTRACT_NAME,
    "expected_top_level_keys": list(_INPUT_KEYS),
    "expected_gate_keys": list(_GATE_KEYS),
    "expected_source_refs": deepcopy(_SOURCE_REFS),
    "expected_binding_groups": deepcopy(_ADMISSION_INPUT_SUMMARY),
    "expected_binding_value_keys": list(_BINDING_VALUE_KEYS),
    "required_false_authority_flags": list(
        _REQUIRED_FALSE_AUTHORITY_FLAGS
    ),
    "required_true_declarations": list(_REQUIRED_TRUE_DECLARATIONS),
    "forbidden_implicit_authority_declarations": list(
        _FORBIDDEN_IMPLICIT_AUTHORITY_DECLARATIONS
    ),
    "failure_taxonomy": list(_FAILURE_ORDER),
    "allowed_reason_codes": [
        _REASON_READY,
        _REASON_NOT_READY,
        _REASON_INVALID,
    ],
    "authority_summary": deepcopy(_AUTHORITY_SUMMARY),
    "non_authority_summary": deepcopy(_NON_AUTHORITY_SUMMARY),
    "public_api": list(__all__),
    "import_boundary": [
        "from collections.abc import Mapping",
        "from copy import deepcopy",
    ],
    "json_safe": True,
}

_MAX_DEPTH = 8
_MAX_MAPPING_ITEMS = 128
_MAX_SEQUENCE_ITEMS = 128
_MAX_STRING_LENGTH = 4096


def service_call_admission_gate_validator_manifest():
    """Return bounded metadata for the read-only admission gate validator."""

    return deepcopy(_MANIFEST)


def validate_service_call_admission_gate(payload):
    """Validate an already-rendered service call admission declaration."""

    failures = []

    if not isinstance(payload, Mapping):
        _append(failures, "payload_not_mapping")
        return _result(failures)

    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    gate = payload.get(_INPUT_KEY)
    if not isinstance(gate, Mapping):
        _append(failures, "gate_not_mapping")
        return _result(failures)

    if set(gate.keys()) != set(_GATE_KEYS):
        _append(failures, "gate_shape_mismatch")

    _validate_gate(gate, failures)
    return _result(failures)


def _validate_gate(gate, failures):
    if gate.get("surface") != _CONTRACT_NAME:
        _append(failures, "gate_surface_invalid")

    version = gate.get("version")
    if type(version) is not int or version != _VERSION:
        _append(failures, "gate_version_invalid")

    _validate_source_refs(gate.get("source_refs"), failures)
    _validate_admission_input(gate, failures)
    _validate_false_authority_flags(gate.get("false_authority_flags"), failures)
    _validate_true_declarations(gate.get("true_declarations"), failures)

    if type(gate.get("json_safe")) is not bool or gate.get("json_safe") is not True:
        _append(failures, "json_safe_invalid")


def _validate_source_refs(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "source_ref_mismatch")
        return

    if set(candidate.keys()) != set(_SOURCE_REFS.keys()):
        _append(failures, "source_ref_mismatch")
        return

    for name, expected in _SOURCE_REFS.items():
        value = candidate.get(name)
        if type(value) is not str or value != expected:
            _append(failures, "source_ref_mismatch")
            return


def _validate_admission_input(gate, failures):
    for field, expected_group in _BINDING_FIELD_TO_GROUP.items():
        candidate = gate.get(field)
        if not isinstance(candidate, Mapping):
            _append(failures, "admission_input_invalid")
            _append(failures, "required_binding_invalid")
            continue

        if set(candidate.keys()) != set(_BINDING_VALUE_KEYS):
            _append(failures, "binding_group_invalid")

        if not _is_json_safe(candidate, 0):
            _append(failures, "admission_input_invalid")

        if candidate.get("binding_group") != expected_group:
            _append(failures, "binding_group_invalid")

        required = candidate.get("required")
        if type(required) is not bool:
            _append(failures, "required_binding_invalid")
        elif required is False:
            _append(failures, "required_binding_false")


def _validate_false_authority_flags(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "authorization_flag_invalid")
        return

    if set(candidate.keys()) != set(_REQUIRED_FALSE_AUTHORITY_FLAGS):
        _append(failures, "authorization_flag_invalid")

    for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS:
        value = candidate.get(flag)
        if type(value) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif value is True:
            _append(failures, "authorization_flag_true")


def _validate_true_declarations(candidate, failures):
    if not isinstance(candidate, Mapping):
        _append(failures, "required_declaration_invalid")
        _append(failures, "forbidden_implicit_authority_invalid")
        return

    if set(candidate.keys()) != set(_REQUIRED_TRUE_DECLARATIONS):
        _append(failures, "required_declaration_invalid")

    for declaration in _REQUIRED_TRUE_DECLARATIONS:
        value = candidate.get(declaration)
        if type(value) is not bool:
            _append(failures, "required_declaration_invalid")
        elif value is False:
            _append(failures, "required_declaration_false")

    for declaration in _FORBIDDEN_IMPLICIT_AUTHORITY_DECLARATIONS:
        if candidate.get(declaration) is not True:
            _append(failures, "forbidden_implicit_authority_invalid")
            return


def _result(failures):
    ordered_failures = _ordered_failures(failures)
    ready = ordered_failures == []
    if ready:
        reason_code = _REASON_READY
    elif _has_invalid_payload_failure(ordered_failures):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return {
        "service_call_admission_gate_ready": ready,
        "reason_code": reason_code,
        "failures": ordered_failures,
        "gate": _gate_output(),
        "authority": deepcopy(_AUTHORITY_SUMMARY),
        "non_authority": deepcopy(_NON_AUTHORITY_SUMMARY),
        "json_safe": True,
    }


def _gate_output():
    return {
        "surface": _CONTRACT_NAME,
        "version": _VERSION,
        "source_refs": deepcopy(_SOURCE_REFS),
        "admission_input": deepcopy(_ADMISSION_INPUT_SUMMARY),
        "required_false_authority_flags": {
            flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
        },
        "required_true_declarations": {
            declaration: True for declaration in _REQUIRED_TRUE_DECLARATIONS
        },
        "json_safe": True,
    }


def _has_invalid_payload_failure(ordered_failures):
    for failure in ordered_failures:
        if failure in _INVALID_PAYLOAD_FAILURES:
            return True
    return False


def _is_json_safe(candidate, depth):
    if depth > _MAX_DEPTH:
        return False
    if candidate is None:
        return True
    if type(candidate) in (bool, int, float):
        return True
    if type(candidate) is str:
        return len(candidate) <= _MAX_STRING_LENGTH
    if isinstance(candidate, Mapping):
        if len(candidate) > _MAX_MAPPING_ITEMS:
            return False
        for key, value in candidate.items():
            if type(key) is not str:
                return False
            if len(key) > _MAX_STRING_LENGTH:
                return False
            if not _is_json_safe(value, depth + 1):
                return False
        return True
    if type(candidate) in (list, tuple):
        if len(candidate) > _MAX_SEQUENCE_ITEMS:
            return False
        for value in candidate:
            if not _is_json_safe(value, depth + 1):
                return False
        return True
    return False


def _append(failures, failure):
    if failure not in failures:
        failures[:] = failures + [failure]


def _ordered_failures(failures):
    return [failure for failure in _FAILURE_ORDER if failure in failures]
