"""Read-only CI consumer for rendered runtime authority boundary validation."""

from collections.abc import Mapping
from copy import deepcopy

__all__ = [
    "runtime_authority_checker_enforcer_boundary_validator_ci_manifest",
    "consume_runtime_authority_checker_enforcer_boundary_validator_ci",
]

_SURFACE = "runtime_authority_checker_enforcer_boundary_validator_ci"
_VERSION = 1
_VALIDATOR_BOUNDARY_SURFACE = "RuntimeAuthorityCheckerEnforcerBoundaryV1"
_VALIDATOR_BOUNDARY_VERSION = 1
_VALIDATOR_CHECKPOINT_TAG = "runtime-authority-checker-enforcer-boundary-validator-v1"
_VALIDATOR_CHECKPOINT_COMMIT = "b2627216e5efb803ebe673dc38b3167db7a8e3db"

_READY = "ready"
_NOT_READY = "not_ready"
_INVALID_CI_PAYLOAD = "invalid_ci_payload"
_INVALID_RUNTIME_AUTHORITY_PAYLOAD = "invalid_runtime_authority_payload"

_PAYLOAD_KEYS = (
    "runtime_authority_boundary_ready",
    "reason_code",
    "failures",
    "boundary",
    "authority",
    "validator_checkpoint_tag",
    "validator_checkpoint_commit",
)

_OUTPUT_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "validator_checkpoint",
    "boundary",
    "authority",
)

_BOUNDARY_KEYS = (
    "surface",
    "version",
    "source_refs",
    "readiness_signals",
    "authority_input_model",
    "authority_grant_ref_model",
    "checker_boundary",
    "enforcer_boundary",
    "checker_enforcer_separation",
    "revocation_expiry_model",
    "denial_fail_closed_behavior",
    "incident_classification",
    "required_false_authority_flags",
    "required_true_declarations",
    "json_safe",
)

_SOURCE_REFS = {
    "read-only-governance-layer-v1": "4656e8f03404c6bb39e7976c6165e3d7dc0314fb",
    "write-side-precondition-checker-v1": "fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6",
    "write-side-precondition-ci-v1": "05c81541ad3d7deee20023843142f702937f6c3f",
    "write-side-recovery-spec-only-v1": "ad560cc2dab135f2c1d56d948410ae47586d118e",
    "restore-dry-run-read-only-stack-v1": "e7c78e3ff0c5dc05806c293f01ab32cd33c9518b",
    "preflight-read-only-stack-v1": "662b6161253c35204b437e88809c5bab21908c6d",
    "execution-authorization-read-only-stack-v1": "d586aeb60620010c900df7be1a88621ab2cb8dc1",
    "executor-precondition-read-only-stack-v1": "cb3948eb843866dcc961b6a074038c13db64d017",
    "write-path-read-only-stack-v1": "8ffd4679aca8f593415089748df35df42af8f015",
    "repository-uow-allowlist-read-only-stack-v1": "bec2d04eab1922594dcbfbe35971f4efe0fe4849",
    "evidence-audit-append-read-only-stack-v1": "62db8a586efa9375d2c77cf7c6335ccf5ef11279",
    "append-runtime-authority-service-boundary-read-only-stack-v1": "bda430a6a8d1e1dbede2adb9594baa1ab5cf2039",
    "service-adapter-boundary-read-only-stack-v1": "8698ea42c78cbe79231698be8839b9d2c246cfdf",
    "service-method-authority-read-only-stack-v1": "db2f628cc79df0dc7b4f1306cbe24d880693188b",
    "service-call-execution-boundary-read-only-stack-v1": "2a82b78665541d2e408113646ea11fbda4b62037",
    "runtime-authority-checker-enforcer-boundary-spec-only-v1": "9bd776b4178ce627e28eb430ea07d6b7a2a002ce",
}

_READINESS_SIGNAL_FLAGS = (
    "service_adapter_ready",
    "method_authority_ready",
    "service_call_execution_boundary_ready",
    "runtime_authority_ready",
    "ci_ok",
    "preflight_readiness",
    "execution_authorization_readiness",
    "executor_precondition_readiness",
    "write_path_readiness",
    "repository_uow_allowlist_readiness",
    "evidence_audit_append_readiness",
    "restore_dry_run_readiness",
)

_BOUNDARY_MODEL_GROUPS = {
    "authority_input_model": (
        "source_bound",
        "operation_bound",
        "revocable",
        "expiring",
        "fail_closed",
        "json_safe",
        "authority_grant_ref_required",
        "readiness_inputs_only",
    ),
    "authority_grant_ref_model": (
        "explicit_grant_object_required",
        "explicit_authority_ref_required",
        "source_refs_required",
        "operation_refs_required",
        "target_surface_required",
        "permitted_action_class_required",
        "forbidden_action_class_required",
        "issuer_required",
        "expiry_required",
        "revocation_required",
        "operator_confirmation_ref_required",
        "human_approval_ref_required",
        "idempotency_key_ref_required",
        "evidence_audit_refs_required",
        "fail_closed_required",
    ),
    "checker_boundary": (
        "future_only",
        "forbidden_now",
        "already_rendered_declarations_only",
        "bounded_json_safe_decision_only",
        "no_service_calls",
        "no_db",
        "no_append",
        "no_mutation",
        "no_idempotency_reservation",
        "no_transaction",
        "no_rollback",
        "no_executor_dispatch",
        "no_durable_writes",
    ),
    "enforcer_boundary": (
        "future_only",
        "forbidden_now",
        "checker_output_only",
        "denial_fail_closed_only",
        "no_service_calls",
        "no_db",
        "no_append",
        "no_mutation",
        "no_idempotency_reservation",
        "no_transaction",
        "no_rollback",
        "no_executor_dispatch",
        "no_durable_writes",
    ),
    "checker_enforcer_separation": (
        "checker_separate_from_enforcer",
        "checker_separate_from_execution",
        "enforcer_separate_from_execution",
        "append_separate_from_checker",
        "db_write_separate_from_checker",
        "executor_dispatch_separate_from_checker",
        "no_combined_checker_enforcer_executor_service_call",
    ),
    "revocation_expiry_model": (
        "missing_authority_fail_closed",
        "malformed_authority_fail_closed",
        "expired_authority_fail_closed",
        "revoked_authority_fail_closed",
        "mismatched_authority_fail_closed",
        "ambiguous_authority_incident_class",
        "unverifiable_authority_fail_closed",
    ),
    "denial_fail_closed_behavior": (
        "default_denial",
        "no_silent_success",
        "no_partial_success",
        "no_implicit_authority_escalation",
        "no_readiness_to_runtime_promotion",
        "post_denial_execution_incident_class",
        "runtime_write_without_authority_incident_class",
        "service_call_without_authority_incident_class",
    ),
    "incident_classification": (
        "ambiguous_authority_incident_class",
        "checker_enforcer_disagreement_incident_class",
        "revoked_authority_use_attempt_incident_class",
        "expired_authority_use_attempt_fail_closed",
        "malformed_authority_fail_closed",
        "post_denial_execution_attempt_incident_class",
        "runtime_write_without_authority_incident_class",
        "service_call_without_authority_incident_class",
    ),
}

_GROUP_FAILURES = {
    "authority_input_model": "authority_input_model_invalid",
    "authority_grant_ref_model": "authority_grant_ref_model_invalid",
    "checker_boundary": "checker_boundary_invalid",
    "enforcer_boundary": "enforcer_boundary_invalid",
    "checker_enforcer_separation": "checker_enforcer_separation_invalid",
    "revocation_expiry_model": "revocation_expiry_model_invalid",
    "denial_fail_closed_behavior": "denial_fail_closed_behavior_invalid",
    "incident_classification": "incident_classification_invalid",
}

_REQUIRED_FALSE_AUTHORITY_FLAGS = (
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
    "runtime_authority_checker_forbidden",
    "runtime_authority_enforcer_forbidden",
    "runtime_authority_runtime_forbidden",
    "readiness_is_not_authority",
    "authorization_is_not_execution",
    "authority_source_bound_required",
    "authority_operation_bound_required",
    "authority_revocable_required",
    "authority_expiry_required",
    "authority_fail_closed_required",
    "authority_grant_object_required_for_future_runtime",
    "authority_grant_schema_required_for_future_runtime",
    "authority_ref_required",
    "authority_ref_source_bound_required",
    "authority_ref_operation_bound_required",
    "authority_ref_revocation_checked_required",
    "authority_ref_expiry_checked_required",
    "checker_enforcer_separation_required",
    "checker_output_json_safe_required",
    "checker_output_bounded_required",
    "enforcer_input_json_safe_required",
    "enforcer_denial_fail_closed_required",
    "missing_authority_fail_closed",
    "malformed_authority_fail_closed",
    "mismatched_authority_fail_closed",
    "expired_authority_fail_closed",
    "revoked_authority_fail_closed",
    "ambiguous_authority_incident_class",
    "silent_authority_success_forbidden",
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

_AUTHORITY_SUMMARY_FLAGS = (
    "runtime_authority_checker_authorized",
    "runtime_authority_enforcer_authorized",
    "runtime_authority_runtime_authorized",
    "service_call_execution_authorized",
    "service_adapter_runtime_authorized",
    "service_method_call_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "repository_uow_writes_authorized",
    "transaction_runtime_authorized",
    "idempotency_reservation_authorized",
    "rollback_runtime_authorized",
    "executor_service_dispatch_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
)

_VALIDATOR_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "boundary_surface_invalid",
    "boundary_version_invalid",
    "source_ref_mismatch",
    "readiness_signal_invalid",
    "authority_input_model_invalid",
    "authority_grant_ref_model_invalid",
    "checker_boundary_invalid",
    "enforcer_boundary_invalid",
    "checker_enforcer_separation_invalid",
    "revocation_expiry_model_invalid",
    "denial_fail_closed_behavior_invalid",
    "incident_classification_invalid",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "required_declaration_invalid",
    "required_declaration_false",
    "json_safe_invalid",
)

_CI_FAILURE_TAXONOMY = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "checkpoint_tag_invalid",
    "checkpoint_commit_invalid",
    "readiness_reason_failure_mismatch",
    "validator_failure_unknown",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
    "boundary_surface_invalid",
    "boundary_version_invalid",
    "source_ref_mismatch",
    "readiness_signal_invalid",
    "authority_input_model_invalid",
    "authority_grant_ref_model_invalid",
    "checker_boundary_invalid",
    "enforcer_boundary_invalid",
    "checker_enforcer_separation_invalid",
    "revocation_expiry_model_invalid",
    "denial_fail_closed_behavior_invalid",
    "incident_classification_invalid",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "required_declaration_invalid",
    "required_declaration_false",
    "authority_summary_invalid",
    "authority_summary_true",
    "json_safe_invalid",
)

_INVALID_CI_FAILURES = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "checkpoint_tag_invalid",
    "checkpoint_commit_invalid",
    "readiness_reason_failure_mismatch",
    "validator_failure_unknown",
    "boundary_not_mapping",
    "boundary_shape_mismatch",
)

_EXPECTED_VALIDATOR_CHECKPOINT = {
    "tag": _VALIDATOR_CHECKPOINT_TAG,
    "commit": _VALIDATOR_CHECKPOINT_COMMIT,
}

_EXPECTED_READINESS_SIGNALS = {
    signal: False for signal in _READINESS_SIGNAL_FLAGS
}

_EXPECTED_BOUNDARY_MODEL_GROUPS = {
    group: {field: True for field in fields}
    for group, fields in _BOUNDARY_MODEL_GROUPS.items()
}

_EXPECTED_FALSE_AUTHORITY_FLAGS = {
    flag: False for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS
}

_EXPECTED_TRUE_DECLARATIONS = {
    declaration: True for declaration in _REQUIRED_TRUE_DECLARATIONS
}

_EXPECTED_AUTHORITY_SUMMARY = {
    flag: False for flag in _AUTHORITY_SUMMARY_FLAGS
}

_EXPECTED_BOUNDARY = {
    "surface": _VALIDATOR_BOUNDARY_SURFACE,
    "version": _VALIDATOR_BOUNDARY_VERSION,
    "source_refs": _SOURCE_REFS,
    "readiness_signals": _EXPECTED_READINESS_SIGNALS,
    **_EXPECTED_BOUNDARY_MODEL_GROUPS,
    "required_false_authority_flags": _EXPECTED_FALSE_AUTHORITY_FLAGS,
    "required_true_declarations": _EXPECTED_TRUE_DECLARATIONS,
    "json_safe": True,
}

_NON_AUTHORITY_STATEMENT = {
    "ci_ok_proves": "structural_validity_for_read_only_stack_consolidation_only",
    "runtime_authorized": False,
    "checker_runtime_authorized": False,
    "enforcer_runtime_authorized": False,
    "service_calls_authorized": False,
    "db_repository_uow_authorized": False,
    "evidence_audit_append_authorized": False,
    "transaction_runtime_authorized": False,
    "idempotency_reservation_authorized": False,
    "rollback_runtime_authorized": False,
    "executor_dispatch_authorized": False,
    "durable_writes_authorized": False,
    "irreversible_actions_authorized": False,
}

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "expected_top_level_keys": _PAYLOAD_KEYS,
    "expected_boundary_keys": _BOUNDARY_KEYS,
    "expected_validator_checkpoint": _EXPECTED_VALIDATOR_CHECKPOINT,
    "expected_source_refs": _SOURCE_REFS,
    "expected_readiness_signals": _EXPECTED_READINESS_SIGNALS,
    "expected_boundary_model_groups": _EXPECTED_BOUNDARY_MODEL_GROUPS,
    "expected_false_authority_flags": _EXPECTED_FALSE_AUTHORITY_FLAGS,
    "expected_true_declarations": _EXPECTED_TRUE_DECLARATIONS,
    "expected_authority_summary": _EXPECTED_AUTHORITY_SUMMARY,
    "validator_failure_taxonomy": _VALIDATOR_FAILURE_TAXONOMY,
    "ci_failure_taxonomy": _CI_FAILURE_TAXONOMY,
    "reason_codes": (_READY, _NOT_READY, _INVALID_CI_PAYLOAD),
    "non_authority_statement": _NON_AUTHORITY_STATEMENT,
    "json_safe": True,
}


def runtime_authority_checker_enforcer_boundary_validator_ci_manifest():
    """Return bounded metadata for the read-only validator CI consumer."""

    return deepcopy(_MANIFEST)


def consume_runtime_authority_checker_enforcer_boundary_validator_ci(payload):
    """Consume already-rendered validator output without invoking runtime code."""

    if not isinstance(payload, Mapping):
        return _result(
            ci_ok=False,
            reason_code=_INVALID_CI_PAYLOAD,
            failures=("payload_not_mapping",),
        )

    failures = []
    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        _append_failure(failures, "payload_shape_mismatch")

    _validate_checkpoint(payload, failures)
    validator_failures = _validate_readiness_reason_failure(payload, failures)

    boundary = payload.get("boundary")
    if "boundary" in payload:
        if not isinstance(boundary, Mapping):
            _append_failure(failures, "boundary_not_mapping")
        else:
            _validate_boundary(boundary, failures)

    if "authority" in payload:
        _validate_authority_summary(payload.get("authority"), failures)

    ordered_failures = _ordered_failures(failures, _CI_FAILURE_TAXONOMY)
    if ordered_failures:
        if _has_invalid_ci_failure(ordered_failures):
            return _result(False, _INVALID_CI_PAYLOAD, ordered_failures)
        return _result(False, _NOT_READY, ordered_failures)

    if payload.get("runtime_authority_boundary_ready") is True:
        return _result(True, _READY, ())

    return _result(False, _NOT_READY, validator_failures)


def _validate_checkpoint(payload, failures):
    if payload.get("validator_checkpoint_tag") != _VALIDATOR_CHECKPOINT_TAG:
        _append_failure(failures, "checkpoint_tag_invalid")
    if payload.get("validator_checkpoint_commit") != _VALIDATOR_CHECKPOINT_COMMIT:
        _append_failure(failures, "checkpoint_commit_invalid")


def _validate_readiness_reason_failure(payload, failures):
    ready = payload.get("runtime_authority_boundary_ready")
    reason = payload.get("reason_code")
    source_failures = payload.get("failures")
    validator_failures = ()

    ready_is_bool = isinstance(ready, bool)
    reason_valid = reason in (
        _READY,
        _NOT_READY,
        _INVALID_RUNTIME_AUTHORITY_PAYLOAD,
    )
    source_failures_valid = _is_string_list(source_failures)

    if source_failures_valid:
        validator_failures = _ordered_failures(
            source_failures,
            _VALIDATOR_FAILURE_TAXONOMY,
        )
        if len(validator_failures) != len(tuple(dict.fromkeys(source_failures))):
            _append_failure(failures, "validator_failure_unknown")

    if ready_is_bool and reason_valid and source_failures_valid:
        if ready is True:
            if reason != _READY or source_failures != []:
                _append_failure(failures, "readiness_reason_failure_mismatch")
        else:
            if (
                reason not in (_NOT_READY, _INVALID_RUNTIME_AUTHORITY_PAYLOAD)
                or source_failures == []
            ):
                _append_failure(failures, "readiness_reason_failure_mismatch")
    elif (
        "runtime_authority_boundary_ready" in payload
        and "reason_code" in payload
        and "failures" in payload
    ):
        _append_failure(failures, "readiness_reason_failure_mismatch")

    return validator_failures


def _validate_boundary(boundary, failures):
    if set(boundary.keys()) != set(_BOUNDARY_KEYS):
        _append_failure(failures, "boundary_shape_mismatch")

    if boundary.get("surface") != _VALIDATOR_BOUNDARY_SURFACE:
        _append_failure(failures, "boundary_surface_invalid")

    version = boundary.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        _append_failure(failures, "boundary_version_invalid")

    if boundary.get("source_refs") != _SOURCE_REFS:
        _append_failure(failures, "source_ref_mismatch")

    if boundary.get("readiness_signals") != _EXPECTED_READINESS_SIGNALS:
        _append_failure(failures, "readiness_signal_invalid")

    for group, expected in _EXPECTED_BOUNDARY_MODEL_GROUPS.items():
        if boundary.get(group) != expected:
            _append_failure(failures, _GROUP_FAILURES[group])

    _validate_false_authority_flags(
        boundary.get("required_false_authority_flags"),
        failures,
    )
    _validate_true_declarations(
        boundary.get("required_true_declarations"),
        failures,
    )

    if boundary.get("json_safe") is not True:
        _append_failure(failures, "json_safe_invalid")


def _validate_false_authority_flags(authority_flags, failures):
    if authority_flags != _EXPECTED_FALSE_AUTHORITY_FLAGS:
        _append_failure(failures, "authorization_flag_invalid")
    if isinstance(authority_flags, Mapping):
        for flag in _REQUIRED_FALSE_AUTHORITY_FLAGS:
            if authority_flags.get(flag) is True:
                _append_failure(failures, "authorization_flag_true")
                break


def _validate_true_declarations(declarations, failures):
    if declarations != _EXPECTED_TRUE_DECLARATIONS:
        _append_failure(failures, "required_declaration_invalid")
    if isinstance(declarations, Mapping):
        for declaration in _REQUIRED_TRUE_DECLARATIONS:
            if declarations.get(declaration) is False:
                _append_failure(failures, "required_declaration_false")
                break


def _validate_authority_summary(authority, failures):
    if authority != _EXPECTED_AUTHORITY_SUMMARY:
        _append_failure(failures, "authority_summary_invalid")
    if isinstance(authority, Mapping):
        for flag in _AUTHORITY_SUMMARY_FLAGS:
            if authority.get(flag) is True:
                _append_failure(failures, "authority_summary_true")
                break


def _is_string_list(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _append_failure(failures, failure):
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures, taxonomy):
    present = tuple(dict.fromkeys(failures))
    return tuple(failure for failure in taxonomy if failure in present)


def _has_invalid_ci_failure(failures):
    return any(failure in _INVALID_CI_FAILURES for failure in failures)


def _result(ci_ok, reason_code, failures):
    result = {
        "ci_ok": ci_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "validator_checkpoint": deepcopy(_EXPECTED_VALIDATOR_CHECKPOINT),
        "boundary": deepcopy(_EXPECTED_BOUNDARY),
        "authority": deepcopy(_EXPECTED_AUTHORITY_SUMMARY),
    }
    return {key: result[key] for key in _OUTPUT_KEYS}
