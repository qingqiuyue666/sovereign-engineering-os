"""Read-only Execution Preflight (H2).

Pure evaluator. Consumes already-rendered payloads only and returns a
bounded JSON-safe verdict whose meaning is strictly "eligible for the
next human/process review boundary", never "allowed to execute". Every
authorization flag is held False; no upstream call, no I/O, no DB, no
service, no CLI, no wall-clock, no digest computation, no mutation.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass


__all__ = [
    "ExecutionPreflight",
    "execution_preflight_manifest",
    "evaluate_execution_preflight",
    "render_execution_preflight",
]


_SURFACE = "execution_preflight"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_execution_preflight_payloads"

_REASON_READY = "ready"
_REASON_INVALID = "invalid_preflight_payload"
_REASON_NOT_READY = "not_ready"


_TOP_LEVEL_KEYS = (
    "restore_dry_run_aggregate_summary",
    "human_approval_readiness_ci",
    "operator_confirmation_declaration",
    "execution_boundary_declaration",
)


_AGGREGATE_TOP_KEYS = ("aggregate_ok", "reason_code", "failures", "summary")
_AGGREGATE_SURFACE = "restore_dry_run_aggregate_summary"
_AGGREGATE_SUMMARY_KEYS = (
    "surface",
    "version",
    "readiness_ci_ok",
    "plan_ci_ok",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "determinism_hash",
    "transaction_required",
    "rollback_required",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
    "executes_plan",
    "json_safe",
)
_AGGREGATE_REQUIRED_STRINGS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
)


_H1_CI_INNER_SURFACE = "human_approval_readiness"
_H1_CI_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "human_approval_ready",
    "human_approval_reason_code",
    "approval_ref",
    "actor_identity",
    "approval_scope",
    "approval_reason",
    "created_at",
    "expires_at",
    "freshness_seconds",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
    "executes_plan",
    "json_safe",
)
_H1_CI_REQUIRED_STRINGS = (
    "approval_ref",
    "actor_identity",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
)


_OPERATOR_KEYS = (
    "confirmation_present",
    "confirmation_ref",
    "actor_identity",
    "actor_policy",
    "confirmation_scope",
    "confirmation_reason",
    "confirmed_at",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "human_approval_ref",
    "confirmation_digest",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
    "executes_plan",
    "json_safe",
)
_OPERATOR_GENERIC_REQUIRED_STRINGS = (
    "confirmation_ref",
    "confirmation_scope",
    "confirmation_reason",
    "confirmed_at",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "human_approval_ref",
)
_ACTOR_POLICY_VALUES = ("same_actor_required", "dual_control_allowed")


_BOUNDARY_KEYS = (
    "transaction_declared",
    "rollback_declared",
    "expected_rejection_policy_declared",
    "idempotency_declared",
    "audit_evidence_envelope_declared",
    "before_after_evidence_declared",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "human_approval_ref",
    "confirmation_digest",
    "schema_migration_required",
    "db_repair_required",
    "cli_execution_required",
    "daemon_server_queue_required",
    "runtime_calls_required",
    "durable_writes_requested",
    "restore_requested",
    "write_side_recovery_requested",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
    "executes_plan",
    "json_safe",
)
_BOUNDARY_DECLARATION_FLAGS = (
    "transaction_declared",
    "rollback_declared",
    "expected_rejection_policy_declared",
    "idempotency_declared",
    "audit_evidence_envelope_declared",
    "before_after_evidence_declared",
)
_BOUNDARY_DECLARATION_FAILURES = {
    "transaction_declared": "transaction_not_declared",
    "rollback_declared": "rollback_not_declared",
    "expected_rejection_policy_declared": (
        "expected_rejection_policy_not_declared"
    ),
    "idempotency_declared": "idempotency_not_declared",
    "audit_evidence_envelope_declared": "audit_evidence_envelope_not_declared",
    "before_after_evidence_declared": "before_after_evidence_not_declared",
}
_BOUNDARY_REQUEST_FLAGS = (
    "schema_migration_required",
    "db_repair_required",
    "cli_execution_required",
    "daemon_server_queue_required",
    "runtime_calls_required",
    "durable_writes_requested",
    "restore_requested",
    "write_side_recovery_requested",
)
_BOUNDARY_REQUIRED_STRINGS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "human_approval_ref",
)


_AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)


_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "aggregate_summary_invalid",
    "aggregate_summary_not_ready",
    "human_approval_ci_invalid",
    "human_approval_ci_not_ready",
    "operator_confirmation_invalid",
    "operator_confirmation_missing",
    "execution_boundary_invalid",
    "execution_boundary_missing",
    "target_task_id_mismatch",
    "operation_kind_mismatch",
    "idempotency_key_mismatch",
    "projected_action_mismatch",
    "projected_evidence_ref_mismatch",
    "aggregate_summary_ref_mismatch",
    "human_approval_ref_mismatch",
    "actor_policy_invalid",
    "actor_identity_mismatch",
    "actor_identity_missing",
    "confirmation_digest_invalid",
    "confirmation_digest_mismatch",
    "transaction_not_declared",
    "rollback_not_declared",
    "expected_rejection_policy_not_declared",
    "idempotency_not_declared",
    "audit_evidence_envelope_not_declared",
    "before_after_evidence_not_declared",
    "schema_migration_required",
    "db_repair_required",
    "cli_execution_required",
    "daemon_server_queue_required",
    "runtime_calls_required",
    "durable_writes_requested",
    "restore_requested",
    "write_side_recovery_requested",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "execution_flag_invalid",
    "execution_flag_true",
    "json_safe_invalid",
)


_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "aggregate_summary_invalid",
        "human_approval_ci_invalid",
        "operator_confirmation_invalid",
        "execution_boundary_invalid",
        "actor_policy_invalid",
        "confirmation_digest_invalid",
        "authorization_flag_invalid",
        "execution_flag_invalid",
        "json_safe_invalid",
    }
)


_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "human_approval_readiness_ci": "human-approval-readiness-ci-v1",
        "human_approval_readiness": "human-approval-readiness-v1",
        "restore_dry_run_read_only_stack": (
            "restore-dry-run-read-only-stack-v1"
        ),
        "restore_dry_run_aggregate_summary": (
            "restore-dry-run-aggregate-summary-v1"
        ),
        "restore_dry_run_plan_ci": "restore-dry-run-plan-ci-v1",
        "restore_dry_run_plan_renderer": "restore-dry-run-plan-renderer-v1",
        "restore_dry_run_readiness_ci": "restore-dry-run-readiness-ci-v1",
        "restore_dry_run_readiness": "restore-dry-run-readiness-v1",
        "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": (
            "write-side-precondition-checker-v1"
        ),
        "read_only_governance_layer": "read-only-governance-layer-v1",
    },
    "restore_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "db_repair_authorized": False,
    "durable_writes": False,
    "executes_plan": False,
    "runtime_dependencies": [],
    "json_safe": True,
}


@dataclass(frozen=True)
class ExecutionPreflight:
    preflight_ok: bool
    reason_code: str
    failures: tuple[str, ...]
    preflight: dict[str, object]


def execution_preflight_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def evaluate_execution_preflight(payload: object) -> ExecutionPreflight:
    failures: list[str] = []

    fields: dict[str, str | None] = {
        "target_task_id": None,
        "operation_kind": None,
        "idempotency_key": None,
        "projected_action": None,
        "projected_evidence_ref": None,
        "aggregate_summary_ref": None,
        "human_approval_ref": None,
        "confirmation_ref": None,
        "actor_identity_approval": None,
        "actor_identity_confirmation": None,
        "actor_policy": None,
        "confirmation_digest": None,
    }
    boundary_decls: dict[str, bool | None] = {
        "transaction_declared": None,
        "rollback_declared": None,
        "expected_rejection_policy_declared": None,
        "idempotency_declared": None,
        "audit_evidence_envelope_declared": None,
        "before_after_evidence_declared": None,
    }

    if not isinstance(payload, Mapping):
        _append(failures, "payload_not_mapping")
        return _build_result(
            failures=failures,
            structural=True,
            aggregate_ok=False,
            h1_ci_ok=False,
            confirmation_present=False,
            boundary_all_declared=False,
            fields=fields,
            boundary_decls=boundary_decls,
        )

    if set(payload.keys()) != set(_TOP_LEVEL_KEYS):
        _append(failures, "payload_shape_mismatch")

    aggregate_section = payload.get("restore_dry_run_aggregate_summary")
    h1_ci_section = payload.get("human_approval_readiness_ci")
    operator_section = payload.get("operator_confirmation_declaration")
    boundary_section = payload.get("execution_boundary_declaration")

    aggregate_state = _validate_aggregate(
        section=aggregate_section, failures=failures, fields=fields
    )
    h1_ci_state = _validate_h1_ci(
        section=h1_ci_section, failures=failures, fields=fields
    )
    operator_state = _validate_operator(
        section=operator_section, failures=failures, fields=fields
    )
    boundary_state = _validate_boundary(
        section=boundary_section,
        failures=failures,
        fields=fields,
        boundary_decls=boundary_decls,
    )

    _check_cross_fields(
        aggregate_values=aggregate_state["values"],
        h1_ci_values=h1_ci_state["values"],
        operator_values=operator_state["values"],
        boundary_values=boundary_state["values"],
        failures=failures,
    )

    _check_actor_policy(
        operator_actor=operator_state["values"].get("actor_identity"),
        h1_actor=h1_ci_state["values"].get("actor_identity"),
        actor_policy=operator_state["values"].get("actor_policy"),
        operator_policy_present=operator_state["policy_present"],
        failures=failures,
    )

    _check_confirmation_digest(
        operator_digest=operator_state["values"].get("confirmation_digest"),
        boundary_digest=boundary_state["values"].get("confirmation_digest"),
        operator_digest_provided=operator_state["digest_provided"],
        boundary_digest_provided=boundary_state["digest_provided"],
        failures=failures,
    )

    ordered = _ordered_failures(failures)
    structural = any(failure in _STRUCTURAL_FAILURES for failure in ordered)

    return _build_result(
        failures=ordered,
        structural=structural,
        aggregate_ok=aggregate_state["ok"],
        h1_ci_ok=h1_ci_state["ok"],
        confirmation_present=operator_state["confirmation_present"],
        boundary_all_declared=boundary_state["all_declared"],
        fields=fields,
        boundary_decls=boundary_decls,
    )


def render_execution_preflight(
    preflight: ExecutionPreflight,
) -> dict[str, object]:
    return {
        "preflight_ok": preflight.preflight_ok,
        "reason_code": preflight.reason_code,
        "failures": list(preflight.failures),
        "preflight": deepcopy(preflight.preflight),
    }


def _validate_aggregate(
    *,
    section: object,
    failures: list[str],
    fields: dict[str, str | None],
) -> dict[str, object]:
    values: dict[str, str | None] = {
        "target_task_id": None,
        "operation_kind": None,
        "idempotency_key": None,
        "projected_action": None,
        "projected_evidence_ref": None,
    }
    if not isinstance(section, Mapping):
        _append(failures, "aggregate_summary_invalid")
        return {"ok": False, "values": values}

    structurally_invalid = False
    if set(section.keys()) != set(_AGGREGATE_TOP_KEYS):
        _append(failures, "aggregate_summary_invalid")
        structurally_invalid = True

    aggregate_ok_value = section.get("aggregate_ok")
    reason_value = section.get("reason_code")
    failures_value = section.get("failures")
    summary_value = section.get("summary")

    if "aggregate_ok" in section and type(aggregate_ok_value) is not bool:
        _append(failures, "aggregate_summary_invalid")
        structurally_invalid = True
    elif aggregate_ok_value is False:
        _append(failures, "aggregate_summary_not_ready")

    if "reason_code" in section:
        if not isinstance(reason_value, str):
            _append(failures, "aggregate_summary_invalid")
            structurally_invalid = True
        elif reason_value != _REASON_READY:
            _append(failures, "aggregate_summary_not_ready")

    if "failures" in section:
        if not _is_string_list(failures_value):
            _append(failures, "aggregate_summary_invalid")
            structurally_invalid = True
        elif failures_value != []:
            _append(failures, "aggregate_summary_not_ready")

    if not isinstance(summary_value, Mapping):
        if "summary" in section:
            _append(failures, "aggregate_summary_invalid")
            structurally_invalid = True
        return {"ok": False, "values": values}

    if set(summary_value.keys()) != set(_AGGREGATE_SUMMARY_KEYS):
        _append(failures, "aggregate_summary_invalid")
        structurally_invalid = True

    candidate_surface = summary_value.get("surface")
    candidate_version = summary_value.get("version")
    if candidate_surface != _AGGREGATE_SURFACE:
        _append(failures, "aggregate_summary_invalid")
        structurally_invalid = True
    if (
        type(candidate_version) is not int
        or type(candidate_version) is bool
        or candidate_version != _VERSION
    ):
        _append(failures, "aggregate_summary_invalid")
        structurally_invalid = True

    readiness_ci_ok = summary_value.get("readiness_ci_ok")
    plan_ci_ok = summary_value.get("plan_ci_ok")
    if "readiness_ci_ok" in summary_value:
        if type(readiness_ci_ok) is not bool:
            _append(failures, "aggregate_summary_invalid")
            structurally_invalid = True
        elif readiness_ci_ok is False:
            _append(failures, "aggregate_summary_not_ready")
    if "plan_ci_ok" in summary_value:
        if type(plan_ci_ok) is not bool:
            _append(failures, "aggregate_summary_invalid")
            structurally_invalid = True
        elif plan_ci_ok is False:
            _append(failures, "aggregate_summary_not_ready")

    for field in _AGGREGATE_REQUIRED_STRINGS:
        if field not in summary_value:
            continue
        candidate = summary_value.get(field)
        if not isinstance(candidate, str):
            _append(failures, "aggregate_summary_invalid")
            structurally_invalid = True
        elif candidate == "":
            _append(failures, "aggregate_summary_not_ready")
        else:
            values[field] = candidate
            if fields.get(field) is None:
                fields[field] = candidate

    _validate_authorization_flags(
        section=summary_value, failures=failures
    )
    _validate_executes_plan(section=summary_value, failures=failures)
    _validate_json_safe(section=summary_value, failures=failures)

    section_ok = (
        not structurally_invalid
        and aggregate_ok_value is True
        and reason_value == _REASON_READY
        and failures_value == []
    )
    return {"ok": section_ok, "values": values}


def _validate_h1_ci(
    *,
    section: object,
    failures: list[str],
    fields: dict[str, str | None],
) -> dict[str, object]:
    values: dict[str, str | None] = {
        "target_task_id": None,
        "operation_kind": None,
        "idempotency_key": None,
        "projected_action": None,
        "projected_evidence_ref": None,
        "aggregate_summary_ref": None,
        "approval_ref": None,
        "actor_identity": None,
    }
    if not isinstance(section, Mapping):
        _append(failures, "human_approval_ci_invalid")
        return {"ok": False, "values": values}

    structurally_invalid = False
    if set(section.keys()) != set(_H1_CI_KEYS):
        _append(failures, "human_approval_ci_invalid")
        structurally_invalid = True

    ci_ok_value = section.get("ci_ok")
    reason_value = section.get("reason_code")
    failures_value = section.get("failures")
    surface_value = section.get("surface")
    version_value = section.get("version")
    ready_value = section.get("human_approval_ready")
    ready_reason_value = section.get("human_approval_reason_code")

    if "ci_ok" in section and type(ci_ok_value) is not bool:
        _append(failures, "human_approval_ci_invalid")
        structurally_invalid = True
    elif ci_ok_value is False:
        _append(failures, "human_approval_ci_not_ready")

    if "reason_code" in section:
        if not isinstance(reason_value, str):
            _append(failures, "human_approval_ci_invalid")
            structurally_invalid = True
        elif reason_value != _REASON_READY:
            _append(failures, "human_approval_ci_not_ready")

    if "failures" in section:
        if not _is_string_list(failures_value):
            _append(failures, "human_approval_ci_invalid")
            structurally_invalid = True
        elif failures_value != []:
            _append(failures, "human_approval_ci_not_ready")

    if "surface" in section and surface_value != _H1_CI_INNER_SURFACE:
        _append(failures, "human_approval_ci_invalid")
        structurally_invalid = True

    if "version" in section:
        if (
            type(version_value) is not int
            or type(version_value) is bool
            or version_value != _VERSION
        ):
            _append(failures, "human_approval_ci_invalid")
            structurally_invalid = True

    if "human_approval_ready" in section:
        if type(ready_value) is not bool:
            _append(failures, "human_approval_ci_invalid")
            structurally_invalid = True
        elif ready_value is False:
            _append(failures, "human_approval_ci_not_ready")

    if "human_approval_reason_code" in section:
        if not isinstance(ready_reason_value, str):
            _append(failures, "human_approval_ci_invalid")
            structurally_invalid = True
        elif ready_reason_value != _REASON_READY:
            _append(failures, "human_approval_ci_not_ready")

    for field in _H1_CI_REQUIRED_STRINGS:
        if field not in section:
            continue
        candidate = section.get(field)
        if not isinstance(candidate, str):
            _append(failures, "human_approval_ci_invalid")
            structurally_invalid = True
        elif candidate == "":
            _append(failures, "human_approval_ci_not_ready")
        else:
            values[field] = candidate
            if field == "approval_ref":
                if fields.get("human_approval_ref") is None:
                    fields["human_approval_ref"] = candidate
            elif field == "actor_identity":
                if fields.get("actor_identity_approval") is None:
                    fields["actor_identity_approval"] = candidate
            elif field in fields and fields.get(field) is None:
                fields[field] = candidate

    _validate_authorization_flags(section=section, failures=failures)
    _validate_executes_plan(section=section, failures=failures)
    _validate_json_safe(section=section, failures=failures)

    section_ok = (
        not structurally_invalid
        and ci_ok_value is True
        and reason_value == _REASON_READY
        and failures_value == []
        and ready_value is True
        and ready_reason_value == _REASON_READY
    )
    return {"ok": section_ok, "values": values}


def _validate_operator(
    *,
    section: object,
    failures: list[str],
    fields: dict[str, str | None],
) -> dict[str, object]:
    values: dict[str, str | None] = {
        "target_task_id": None,
        "operation_kind": None,
        "idempotency_key": None,
        "projected_action": None,
        "projected_evidence_ref": None,
        "aggregate_summary_ref": None,
        "human_approval_ref": None,
        "confirmation_ref": None,
        "actor_identity": None,
        "actor_policy": None,
        "confirmation_digest": None,
    }
    if not isinstance(section, Mapping):
        _append(failures, "operator_confirmation_invalid")
        return {
            "ok": False,
            "values": values,
            "confirmation_present": False,
            "policy_present": False,
            "digest_provided": False,
        }

    structurally_invalid = False
    if set(section.keys()) != set(_OPERATOR_KEYS):
        _append(failures, "operator_confirmation_invalid")
        structurally_invalid = True

    confirmation_present_value = section.get("confirmation_present")
    confirmation_present = False
    if "confirmation_present" in section:
        if type(confirmation_present_value) is not bool:
            _append(failures, "operator_confirmation_invalid")
            structurally_invalid = True
        elif confirmation_present_value is False:
            _append(failures, "operator_confirmation_missing")
        else:
            confirmation_present = True

    actor_policy_value = section.get("actor_policy")
    policy_present = False
    if "actor_policy" in section:
        if (
            not isinstance(actor_policy_value, str)
            or actor_policy_value not in _ACTOR_POLICY_VALUES
        ):
            _append(failures, "actor_policy_invalid")
            structurally_invalid = True
        else:
            values["actor_policy"] = actor_policy_value
            policy_present = True
            if fields.get("actor_policy") is None:
                fields["actor_policy"] = actor_policy_value

    actor_identity_value = section.get("actor_identity")
    if "actor_identity" in section:
        if not isinstance(actor_identity_value, str):
            _append(failures, "actor_identity_missing")
        elif actor_identity_value == "":
            _append(failures, "actor_identity_missing")
        else:
            values["actor_identity"] = actor_identity_value
            if fields.get("actor_identity_confirmation") is None:
                fields["actor_identity_confirmation"] = actor_identity_value

    confirmation_digest_value = section.get("confirmation_digest")
    digest_provided = False
    if "confirmation_digest" in section:
        if (
            not isinstance(confirmation_digest_value, str)
            or confirmation_digest_value == ""
        ):
            _append(failures, "confirmation_digest_invalid")
        else:
            values["confirmation_digest"] = confirmation_digest_value
            digest_provided = True
            if fields.get("confirmation_digest") is None:
                fields["confirmation_digest"] = confirmation_digest_value

    for field in _OPERATOR_GENERIC_REQUIRED_STRINGS:
        if field not in section:
            continue
        candidate = section.get(field)
        if not isinstance(candidate, str) or candidate == "":
            _append(failures, "operator_confirmation_invalid")
            structurally_invalid = True
        else:
            values[field] = candidate
            if field == "confirmation_ref":
                if fields.get("confirmation_ref") is None:
                    fields["confirmation_ref"] = candidate
            elif field in fields and fields.get(field) is None:
                fields[field] = candidate

    _validate_authorization_flags(section=section, failures=failures)
    _validate_executes_plan(section=section, failures=failures)
    _validate_json_safe(section=section, failures=failures)

    section_ok = (
        not structurally_invalid
        and confirmation_present is True
        and policy_present is True
        and digest_provided is True
        and isinstance(values.get("actor_identity"), str)
        and values.get("actor_identity") != ""
    )
    return {
        "ok": section_ok,
        "values": values,
        "confirmation_present": confirmation_present,
        "policy_present": policy_present,
        "digest_provided": digest_provided,
    }


def _validate_boundary(
    *,
    section: object,
    failures: list[str],
    fields: dict[str, str | None],
    boundary_decls: dict[str, bool | None],
) -> dict[str, object]:
    values: dict[str, str | None] = {
        "target_task_id": None,
        "operation_kind": None,
        "idempotency_key": None,
        "projected_action": None,
        "projected_evidence_ref": None,
        "aggregate_summary_ref": None,
        "human_approval_ref": None,
        "confirmation_digest": None,
    }
    if not isinstance(section, Mapping):
        _append(failures, "execution_boundary_invalid")
        return {
            "ok": False,
            "values": values,
            "all_declared": False,
            "digest_provided": False,
        }

    structurally_invalid = False
    if set(section.keys()) != set(_BOUNDARY_KEYS):
        _append(failures, "execution_boundary_invalid")
        structurally_invalid = True

    all_declared = True
    for flag in _BOUNDARY_DECLARATION_FLAGS:
        if flag not in section:
            all_declared = False
            continue
        candidate = section.get(flag)
        if type(candidate) is not bool:
            _append(failures, "execution_boundary_invalid")
            structurally_invalid = True
            all_declared = False
        else:
            boundary_decls[flag] = candidate
            if candidate is False:
                _append(failures, _BOUNDARY_DECLARATION_FAILURES[flag])
                all_declared = False

    for flag in _BOUNDARY_REQUEST_FLAGS:
        if flag not in section:
            continue
        candidate = section.get(flag)
        if type(candidate) is not bool:
            _append(failures, "execution_boundary_invalid")
            structurally_invalid = True
        elif candidate is True:
            _append(failures, flag)

    digest_value = section.get("confirmation_digest")
    digest_provided = False
    if "confirmation_digest" in section:
        if not isinstance(digest_value, str) or digest_value == "":
            _append(failures, "confirmation_digest_invalid")
        else:
            values["confirmation_digest"] = digest_value
            digest_provided = True
            if fields.get("confirmation_digest") is None:
                fields["confirmation_digest"] = digest_value

    for field in _BOUNDARY_REQUIRED_STRINGS:
        if field not in section:
            continue
        candidate = section.get(field)
        if not isinstance(candidate, str) or candidate == "":
            _append(failures, "execution_boundary_invalid")
            structurally_invalid = True
        else:
            values[field] = candidate
            if field in fields and fields.get(field) is None:
                fields[field] = candidate

    _validate_authorization_flags(section=section, failures=failures)
    _validate_executes_plan(section=section, failures=failures)
    _validate_json_safe(section=section, failures=failures)

    section_all_declared = all_declared and not structurally_invalid
    return {
        "ok": not structurally_invalid,
        "values": values,
        "all_declared": section_all_declared,
        "digest_provided": digest_provided,
    }


def _validate_authorization_flags(
    *,
    section: Mapping[str, object],
    failures: list[str],
) -> None:
    for flag in _AUTHORIZATION_FLAGS:
        if flag not in section:
            continue
        candidate = section.get(flag)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")


def _validate_executes_plan(
    *,
    section: Mapping[str, object],
    failures: list[str],
) -> None:
    if "executes_plan" not in section:
        return
    candidate = section.get("executes_plan")
    if type(candidate) is not bool:
        _append(failures, "execution_flag_invalid")
    elif candidate is True:
        _append(failures, "execution_flag_true")


def _validate_json_safe(
    *,
    section: Mapping[str, object],
    failures: list[str],
) -> None:
    if "json_safe" not in section:
        return
    candidate = section.get("json_safe")
    if type(candidate) is not bool:
        _append(failures, "json_safe_invalid")
    elif candidate is False:
        _append(failures, "json_safe_invalid")


def _check_cross_fields(
    *,
    aggregate_values: dict[str, str | None],
    h1_ci_values: dict[str, str | None],
    operator_values: dict[str, str | None],
    boundary_values: dict[str, str | None],
    failures: list[str],
) -> None:
    plain_fields = {
        "target_task_id": "target_task_id_mismatch",
        "operation_kind": "operation_kind_mismatch",
        "idempotency_key": "idempotency_key_mismatch",
        "projected_action": "projected_action_mismatch",
        "projected_evidence_ref": "projected_evidence_ref_mismatch",
    }
    for field, mismatch_code in plain_fields.items():
        candidates = [
            aggregate_values.get(field),
            h1_ci_values.get(field),
            operator_values.get(field),
            boundary_values.get(field),
        ]
        _emit_if_distinct(candidates, mismatch_code, failures)

    aggregate_ref_candidates = [
        h1_ci_values.get("aggregate_summary_ref"),
        operator_values.get("aggregate_summary_ref"),
        boundary_values.get("aggregate_summary_ref"),
    ]
    _emit_if_distinct(
        aggregate_ref_candidates, "aggregate_summary_ref_mismatch", failures
    )

    human_approval_candidates = [
        h1_ci_values.get("approval_ref"),
        operator_values.get("human_approval_ref"),
        boundary_values.get("human_approval_ref"),
    ]
    _emit_if_distinct(
        human_approval_candidates, "human_approval_ref_mismatch", failures
    )


def _emit_if_distinct(
    candidates: list[object],
    failure_code: str,
    failures: list[str],
) -> None:
    distinct = {
        candidate
        for candidate in candidates
        if isinstance(candidate, str) and candidate != ""
    }
    if len(distinct) > 1:
        _append(failures, failure_code)


def _check_actor_policy(
    *,
    operator_actor: object,
    h1_actor: object,
    actor_policy: object,
    operator_policy_present: bool,
    failures: list[str],
) -> None:
    if not operator_policy_present:
        return
    operator_actor_str = (
        operator_actor
        if isinstance(operator_actor, str) and operator_actor != ""
        else None
    )
    h1_actor_str = (
        h1_actor if isinstance(h1_actor, str) and h1_actor != "" else None
    )
    if actor_policy == "same_actor_required":
        if operator_actor_str is None or h1_actor_str is None:
            _append(failures, "actor_identity_missing")
            return
        if operator_actor_str != h1_actor_str:
            _append(failures, "actor_identity_mismatch")
    elif actor_policy == "dual_control_allowed":
        if operator_actor_str is None or h1_actor_str is None:
            _append(failures, "actor_identity_missing")


def _check_confirmation_digest(
    *,
    operator_digest: object,
    boundary_digest: object,
    operator_digest_provided: bool,
    boundary_digest_provided: bool,
    failures: list[str],
) -> None:
    if not (operator_digest_provided and boundary_digest_provided):
        return
    if isinstance(operator_digest, str) and isinstance(boundary_digest, str):
        if operator_digest != boundary_digest:
            _append(failures, "confirmation_digest_mismatch")


def _build_result(
    *,
    failures: list[str],
    structural: bool,
    aggregate_ok: bool,
    h1_ci_ok: bool,
    confirmation_present: bool,
    boundary_all_declared: bool,
    fields: dict[str, str | None],
    boundary_decls: dict[str, bool | None],
) -> ExecutionPreflight:
    ordered_failures = _ordered_failures(failures)
    has_structural = structural or any(
        failure in _STRUCTURAL_FAILURES for failure in ordered_failures
    )
    preflight_ok = ordered_failures == []
    if preflight_ok:
        reason_code = _REASON_READY
    elif has_structural:
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    preflight = {
        "surface": _SURFACE,
        "version": _VERSION,
        "aggregate_summary_ok": aggregate_ok,
        "human_approval_ci_ok": h1_ci_ok,
        "operator_confirmation_present": confirmation_present,
        "execution_boundary_declared": boundary_all_declared,
        "target_task_id": fields["target_task_id"],
        "operation_kind": fields["operation_kind"],
        "idempotency_key": fields["idempotency_key"],
        "projected_action": fields["projected_action"],
        "projected_evidence_ref": fields["projected_evidence_ref"],
        "aggregate_summary_ref": fields["aggregate_summary_ref"],
        "human_approval_ref": fields["human_approval_ref"],
        "confirmation_ref": fields["confirmation_ref"],
        "actor_identity_approval": fields["actor_identity_approval"],
        "actor_identity_confirmation": fields["actor_identity_confirmation"],
        "actor_policy": fields["actor_policy"],
        "confirmation_digest": fields["confirmation_digest"],
        "transaction_declared": boundary_decls["transaction_declared"],
        "rollback_declared": boundary_decls["rollback_declared"],
        "expected_rejection_policy_declared": boundary_decls[
            "expected_rejection_policy_declared"
        ],
        "idempotency_declared": boundary_decls["idempotency_declared"],
        "audit_evidence_envelope_declared": boundary_decls[
            "audit_evidence_envelope_declared"
        ],
        "before_after_evidence_declared": boundary_decls[
            "before_after_evidence_declared"
        ],
        "restore_authorized": False,
        "write_side_recovery_authorized": False,
        "cli_execution_authorized": False,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "db_repair_authorized": False,
        "durable_writes": False,
        "executes_plan": False,
        "json_safe": True,
    }

    return ExecutionPreflight(
        preflight_ok=preflight_ok,
        reason_code=reason_code,
        failures=tuple(ordered_failures),
        preflight=preflight,
    )


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
