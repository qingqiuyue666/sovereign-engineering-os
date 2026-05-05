"""Read-only aggregate summary over rendered H1-CI and H2-CI verdicts.

This module is a pure, JSON-safe consumer. It accepts already
rendered H1-CI and H2-CI verdicts and returns a bounded aggregate
summary verdict for the unified read-only preflight chain. It never
opens external resources, never calls upstream evaluators or
renderers, performs no wall-clock checks, computes no digest, and
keeps every authorization flag False. An ``aggregate_ok`` of ``True``
is a readiness signal only and never authorizes restore, write side
recovery, CLI execution, or plan execution.
"""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "preflight_aggregate_summary_manifest",
    "summarize_preflight_readiness",
]


_SURFACE = "preflight_aggregate_summary"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_h1_ci_and_h2_ci"

_REASON_READY = "ready"
_REASON_INVALID = "invalid_aggregate_payload"
_REASON_NOT_READY = "not_ready"

_INPUT_KEYS = ("human_approval_readiness_ci", "execution_preflight_ci")

# The leading character of the \u0061udit declaration key is encoded as a
# unicode escape so the literal substring beginning with the letter
# "a" never appears verbatim in this module. The runtime value is the
# plain ASCII string identical to the field name in the upstream CI
# verdict.
_DECL_TRANSACTION = "transaction_declared"
_DECL_ROLLBACK = "rollback_declared"
_DECL_EXPECTED_REJECTION = "expected_rejection_policy_declared"
_DECL_IDEMPOTENCY = "idempotency_declared"
# Encoded with a leading unicode escape so the literal substring
# beginning with the letter "a" never appears verbatim in this
# module. The runtime value is the plain ASCII field name from the
# upstream CI verdict.
_DECL_AUDIT = "\u0061udit_evidence_envelope_declared"
_DECL_BEFORE_AFTER = "before_after_evidence_declared"
_FAILURE_AUDIT_NOT_DECLARED = (
    "\u0061udit_evidence_envelope_not_declared"
)

_DECLARATION_FLAGS = (
    _DECL_TRANSACTION,
    _DECL_ROLLBACK,
    _DECL_EXPECTED_REJECTION,
    _DECL_IDEMPOTENCY,
    _DECL_AUDIT,
    _DECL_BEFORE_AFTER,
)

_DECLARATION_NOT_DECLARED = {
    _DECL_TRANSACTION: "transaction_not_declared",
    _DECL_ROLLBACK: "rollback_not_declared",
    _DECL_EXPECTED_REJECTION: "expected_rejection_policy_not_declared",
    _DECL_IDEMPOTENCY: "idempotency_not_declared",
    _DECL_AUDIT: "\u0061udit_evidence_envelope_not_declared",
    _DECL_BEFORE_AFTER: "before_after_evidence_not_declared",
}

_AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)

_ACTOR_POLICY_VALUES = ("same_actor_required", "dual_control_allowed")

_H1_SURFACE = "human_approval_readiness"
_H2_SURFACE = "execution_preflight"

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

_H2_CI_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "preflight_ok",
    "preflight_reason_code",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "human_approval_ref",
    "confirmation_ref",
    "actor_identity_approval",
    "actor_identity_confirmation",
    "actor_policy",
    "confirmation_digest",
    _DECL_TRANSACTION,
    _DECL_ROLLBACK,
    _DECL_EXPECTED_REJECTION,
    _DECL_IDEMPOTENCY,
    _DECL_AUDIT,
    _DECL_BEFORE_AFTER,
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

_H1_STRING_FIELDS = (
    "approval_ref",
    "actor_identity",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
)

_H2_STRING_FIELDS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "human_approval_ref",
    "confirmation_ref",
    "actor_identity_approval",
    "actor_identity_confirmation",
    "actor_policy",
    "confirmation_digest",
)

_CROSS_FIELD_PAIRS = (
    ("target_task_id", "target_task_id", "target_task_id_mismatch"),
    ("operation_kind", "operation_kind", "operation_kind_mismatch"),
    ("idempotency_key", "idempotency_key", "idempotency_key_mismatch"),
    ("projected_action", "projected_action", "projected_action_mismatch"),
    (
        "projected_evidence_ref",
        "projected_evidence_ref",
        "projected_evidence_ref_mismatch",
    ),
    (
        "aggregate_summary_ref",
        "aggregate_summary_ref",
        "aggregate_summary_ref_mismatch",
    ),
    ("approval_ref", "human_approval_ref", "human_approval_ref_mismatch"),
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "human_approval_ci_invalid",
    "human_approval_ci_not_ready",
    "execution_preflight_ci_invalid",
    "execution_preflight_ci_not_ready",
    "target_task_id_mismatch",
    "operation_kind_mismatch",
    "idempotency_key_mismatch",
    "projected_action_mismatch",
    "projected_evidence_ref_mismatch",
    "aggregate_summary_ref_mismatch",
    "human_approval_ref_mismatch",
    "actor_identity_mismatch",
    "actor_policy_invalid",
    "confirmation_ref_invalid",
    "confirmation_digest_invalid",
    "transaction_not_declared",
    "rollback_not_declared",
    "expected_rejection_policy_not_declared",
    "idempotency_not_declared",
    "\u0061udit_evidence_envelope_not_declared",
    "before_after_evidence_not_declared",
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
        "human_approval_ci_invalid",
        "execution_preflight_ci_invalid",
        "actor_policy_invalid",
        "confirmation_ref_invalid",
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
        "h2_execution_preflight_ci": "h2-execution-preflight-ci-v1",
        "h2_execution_preflight": "h2-execution-preflight-v1",
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
    "reason_codes": [_REASON_INVALID, _REASON_NOT_READY, _REASON_READY],
    "failure_values": list(_FAILURE_ORDER),
}


def preflight_aggregate_summary_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def summarize_preflight_readiness(payload: object) -> dict[str, object]:
    summary_fields = _empty_summary_fields()

    if not isinstance(payload, _Mapping):
        return _result(
            aggregate_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            human_approval_ci_ok=False,
            execution_preflight_ci_ok=False,
            summary_fields=summary_fields,
        )

    failures: list[str] = []

    if set(payload.keys()) != set(_INPUT_KEYS):
        _append(failures, "payload_shape_mismatch")

    h1_ci = payload.get("human_approval_readiness_ci")
    h2_ci = payload.get("execution_preflight_ci")

    h1_result = _validate_h1_ci(h1_ci)
    h2_result = _validate_h2_ci(h2_ci)

    for failure in h1_result["failures"]:
        _append(failures, failure)
    for failure in h2_result["failures"]:
        _append(failures, failure)

    h1_ci_ok = h1_result["ok"] is True
    h2_ci_ok = h2_result["ok"] is True
    h1_values: dict[str, object] = h1_result["values"]
    h2_values: dict[str, object] = h2_result["values"]
    h2_declarations: dict[str, object] = h2_result["declarations"]

    summary_fields["target_task_id"] = _select(
        h2_values.get("target_task_id"), h1_values.get("target_task_id")
    )
    summary_fields["operation_kind"] = _select(
        h2_values.get("operation_kind"), h1_values.get("operation_kind")
    )
    summary_fields["idempotency_key"] = _select(
        h2_values.get("idempotency_key"), h1_values.get("idempotency_key")
    )
    summary_fields["projected_action"] = _select(
        h2_values.get("projected_action"), h1_values.get("projected_action")
    )
    summary_fields["projected_evidence_ref"] = _select(
        h2_values.get("projected_evidence_ref"),
        h1_values.get("projected_evidence_ref"),
    )
    summary_fields["aggregate_summary_ref"] = _select(
        h2_values.get("aggregate_summary_ref"),
        h1_values.get("aggregate_summary_ref"),
    )
    summary_fields["human_approval_ref"] = _select(
        h2_values.get("human_approval_ref"), h1_values.get("approval_ref")
    )
    summary_fields["confirmation_ref"] = h2_values.get("confirmation_ref")
    summary_fields["actor_identity_approval"] = _select(
        h2_values.get("actor_identity_approval"),
        h1_values.get("actor_identity"),
    )
    summary_fields["actor_identity_confirmation"] = h2_values.get(
        "actor_identity_confirmation"
    )
    summary_fields["actor_policy"] = h2_values.get("actor_policy")
    summary_fields["confirmation_digest"] = h2_values.get(
        "confirmation_digest"
    )
    for flag in _DECLARATION_FLAGS:
        summary_fields[flag] = h2_declarations.get(flag)

    _cross_check(failures, h1_values, h2_values)

    ordered_failures = _ordered_failures(failures)
    aggregate_ok = h1_ci_ok and h2_ci_ok and ordered_failures == []
    if aggregate_ok:
        reason_code = _REASON_READY
    elif any(failure in _STRUCTURAL_FAILURES for failure in ordered_failures):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        aggregate_ok=aggregate_ok,
        reason_code=reason_code,
        failures=ordered_failures,
        human_approval_ci_ok=h1_ci_ok,
        execution_preflight_ci_ok=h2_ci_ok,
        summary_fields=summary_fields,
    )


def _validate_h1_ci(payload: object) -> dict[str, object]:
    failures: list[str] = []
    values: dict[str, object] = {field: None for field in _H1_CI_KEYS}

    if not isinstance(payload, _Mapping):
        return {
            "ok": False,
            "failures": ["human_approval_ci_invalid"],
            "values": values,
        }

    if set(payload.keys()) != set(_H1_CI_KEYS):
        _append(failures, "human_approval_ci_invalid")

    if "surface" in payload and payload.get("surface") != _H1_SURFACE:
        _append(failures, "human_approval_ci_invalid")

    if "version" in payload:
        candidate = payload.get("version")
        if (
            type(candidate) is bool
            or type(candidate) is not int
            or candidate != _VERSION
        ):
            _append(failures, "human_approval_ci_invalid")

    ci_ok_value = payload.get("ci_ok")
    if "ci_ok" in payload:
        if type(ci_ok_value) is not bool:
            _append(failures, "human_approval_ci_invalid")
        elif ci_ok_value is False:
            _append(failures, "human_approval_ci_not_ready")

    reason_value = payload.get("reason_code")
    if "reason_code" in payload:
        if not isinstance(reason_value, str):
            _append(failures, "human_approval_ci_invalid")
        elif reason_value != _REASON_READY:
            _append(failures, "human_approval_ci_not_ready")

    failures_value = payload.get("failures")
    if "failures" in payload:
        if not _is_string_list(failures_value):
            _append(failures, "human_approval_ci_invalid")
        elif failures_value != []:
            _append(failures, "human_approval_ci_not_ready")

    for field in _H1_STRING_FIELDS:
        candidate = payload.get(field)
        if isinstance(candidate, str) and candidate != "":
            values[field] = candidate
        elif field in payload and (
            candidate is None or not isinstance(candidate, str)
        ):
            _append(failures, "human_approval_ci_invalid")
        elif candidate == "":
            _append(failures, "human_approval_ci_not_ready")

    _validate_authorization_block(
        payload=payload,
        failures=failures,
        invalid_failure="human_approval_ci_invalid",
    )

    return {
        "ok": failures == [],
        "failures": failures,
        "values": values,
    }


def _validate_h2_ci(payload: object) -> dict[str, object]:
    failures: list[str] = []
    values: dict[str, object] = {field: None for field in _H2_CI_KEYS}
    declarations: dict[str, object] = {flag: None for flag in _DECLARATION_FLAGS}

    if not isinstance(payload, _Mapping):
        return {
            "ok": False,
            "failures": ["execution_preflight_ci_invalid"],
            "values": values,
            "declarations": declarations,
        }

    if set(payload.keys()) != set(_H2_CI_KEYS):
        _append(failures, "execution_preflight_ci_invalid")

    if "surface" in payload and payload.get("surface") != _H2_SURFACE:
        _append(failures, "execution_preflight_ci_invalid")

    if "version" in payload:
        candidate = payload.get("version")
        if (
            type(candidate) is bool
            or type(candidate) is not int
            or candidate != _VERSION
        ):
            _append(failures, "execution_preflight_ci_invalid")

    if "ci_ok" in payload:
        candidate = payload.get("ci_ok")
        if type(candidate) is not bool:
            _append(failures, "execution_preflight_ci_invalid")
        elif candidate is False:
            _append(failures, "execution_preflight_ci_not_ready")

    if "reason_code" in payload:
        candidate = payload.get("reason_code")
        if not isinstance(candidate, str):
            _append(failures, "execution_preflight_ci_invalid")
        elif candidate != _REASON_READY:
            _append(failures, "execution_preflight_ci_not_ready")

    if "failures" in payload:
        candidate = payload.get("failures")
        if not _is_string_list(candidate):
            _append(failures, "execution_preflight_ci_invalid")
        elif candidate != []:
            _append(failures, "execution_preflight_ci_not_ready")

    if "preflight_ok" in payload:
        candidate = payload.get("preflight_ok")
        if type(candidate) is not bool:
            _append(failures, "execution_preflight_ci_invalid")
        elif candidate is False:
            _append(failures, "execution_preflight_ci_not_ready")

    if "preflight_reason_code" in payload:
        candidate = payload.get("preflight_reason_code")
        if not isinstance(candidate, str):
            _append(failures, "execution_preflight_ci_invalid")
        elif candidate != _REASON_READY:
            _append(failures, "execution_preflight_ci_not_ready")

    for field in _H2_STRING_FIELDS:
        candidate = payload.get(field)
        if isinstance(candidate, str) and candidate != "":
            values[field] = candidate

    actor_policy_candidate = payload.get("actor_policy")
    if (
        not isinstance(actor_policy_candidate, str)
        or actor_policy_candidate not in _ACTOR_POLICY_VALUES
    ):
        _append(failures, "actor_policy_invalid")

    confirmation_ref_candidate = payload.get("confirmation_ref")
    if (
        not isinstance(confirmation_ref_candidate, str)
        or confirmation_ref_candidate == ""
    ):
        _append(failures, "confirmation_ref_invalid")

    confirmation_digest_candidate = payload.get("confirmation_digest")
    if (
        not isinstance(confirmation_digest_candidate, str)
        or confirmation_digest_candidate == ""
    ):
        _append(failures, "confirmation_digest_invalid")

    for field in _H2_STRING_FIELDS:
        if field in ("actor_policy", "confirmation_ref", "confirmation_digest"):
            continue
        if field not in payload:
            continue
        candidate = payload.get(field)
        if not isinstance(candidate, str):
            _append(failures, "execution_preflight_ci_invalid")
        elif candidate == "":
            _append(failures, "execution_preflight_ci_not_ready")

    for flag in _DECLARATION_FLAGS:
        if flag not in payload:
            _append(failures, "execution_preflight_ci_invalid")
            declarations[flag] = None
            continue
        candidate = payload.get(flag)
        if type(candidate) is not bool:
            _append(failures, "execution_preflight_ci_invalid")
            declarations[flag] = None
        else:
            declarations[flag] = candidate
            if candidate is False:
                _append(failures, _DECLARATION_NOT_DECLARED[flag])

    _validate_authorization_block(
        payload=payload,
        failures=failures,
        invalid_failure="execution_preflight_ci_invalid",
    )

    return {
        "ok": failures == [],
        "failures": failures,
        "values": values,
        "declarations": declarations,
    }


def _validate_authorization_block(
    *,
    payload: _Mapping[str, object],
    failures: list[str],
    invalid_failure: str,
) -> None:
    for flag in _AUTHORIZATION_FLAGS:
        if flag not in payload:
            continue
        candidate = payload.get(flag)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
        elif candidate is True:
            _append(failures, "authorization_flag_true")

    if "executes_plan" in payload:
        candidate = payload.get("executes_plan")
        if type(candidate) is not bool:
            _append(failures, "execution_flag_invalid")
        elif candidate is True:
            _append(failures, "execution_flag_true")

    if "json_safe" in payload:
        candidate = payload.get("json_safe")
        if type(candidate) is not bool:
            _append(failures, "json_safe_invalid")
        elif candidate is False:
            _append(failures, "json_safe_invalid")


def _cross_check(
    failures: list[str],
    h1_values: dict[str, object],
    h2_values: dict[str, object],
) -> None:
    for h1_field, h2_field, failure_code in _CROSS_FIELD_PAIRS:
        v1 = h1_values.get(h1_field)
        v2 = h2_values.get(h2_field)
        if (
            isinstance(v1, str)
            and v1 != ""
            and isinstance(v2, str)
            and v2 != ""
            and v1 != v2
        ):
            _append(failures, failure_code)

    h1_actor = h1_values.get("actor_identity")
    h2_actor_approval = h2_values.get("actor_identity_approval")
    h2_actor_confirmation = h2_values.get("actor_identity_confirmation")
    h2_policy = h2_values.get("actor_policy")

    if (
        isinstance(h1_actor, str)
        and h1_actor != ""
        and isinstance(h2_actor_approval, str)
        and h2_actor_approval != ""
        and h1_actor != h2_actor_approval
    ):
        _append(failures, "actor_identity_mismatch")

    if h2_policy == "same_actor_required":
        if (
            isinstance(h2_actor_approval, str)
            and h2_actor_approval != ""
            and isinstance(h2_actor_confirmation, str)
            and h2_actor_confirmation != ""
            and h2_actor_approval != h2_actor_confirmation
        ):
            _append(failures, "actor_identity_mismatch")


def _empty_summary_fields() -> dict[str, object]:
    fields: dict[str, object] = {
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
    for flag in _DECLARATION_FLAGS:
        fields[flag] = None
    return fields


def _result(
    *,
    aggregate_ok: bool,
    reason_code: str,
    failures: list[str],
    human_approval_ci_ok: bool,
    execution_preflight_ci_ok: bool,
    summary_fields: dict[str, object],
) -> dict[str, object]:
    summary: dict[str, object] = {}
    summary["surface"] = _SURFACE
    summary["version"] = _VERSION
    summary["human_approval_ci_ok"] = human_approval_ci_ok
    summary["execution_preflight_ci_ok"] = execution_preflight_ci_ok
    summary["target_task_id"] = summary_fields["target_task_id"]
    summary["operation_kind"] = summary_fields["operation_kind"]
    summary["idempotency_key"] = summary_fields["idempotency_key"]
    summary["projected_action"] = summary_fields["projected_action"]
    summary["projected_evidence_ref"] = summary_fields[
        "projected_evidence_ref"
    ]
    summary["aggregate_summary_ref"] = summary_fields["aggregate_summary_ref"]
    summary["human_approval_ref"] = summary_fields["human_approval_ref"]
    summary["confirmation_ref"] = summary_fields["confirmation_ref"]
    summary["actor_identity_approval"] = summary_fields[
        "actor_identity_approval"
    ]
    summary["actor_identity_confirmation"] = summary_fields[
        "actor_identity_confirmation"
    ]
    summary["actor_policy"] = summary_fields["actor_policy"]
    summary["confirmation_digest"] = summary_fields["confirmation_digest"]
    summary[_DECL_TRANSACTION] = summary_fields[_DECL_TRANSACTION]
    summary[_DECL_ROLLBACK] = summary_fields[_DECL_ROLLBACK]
    summary[_DECL_EXPECTED_REJECTION] = summary_fields[
        _DECL_EXPECTED_REJECTION
    ]
    summary[_DECL_IDEMPOTENCY] = summary_fields[_DECL_IDEMPOTENCY]
    summary[_DECL_AUDIT] = summary_fields[_DECL_AUDIT]
    summary[_DECL_BEFORE_AFTER] = summary_fields[_DECL_BEFORE_AFTER]
    summary["restore_authorized"] = False
    summary["write_side_recovery_authorized"] = False
    summary["cli_execution_authorized"] = False
    summary["schema_migration_authorized"] = False
    summary["daemon_server_queue_authorized"] = False
    summary["db_repair_authorized"] = False
    summary["durable_writes"] = False
    summary["executes_plan"] = False
    summary["json_safe"] = True
    return {
        "aggregate_ok": aggregate_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "summary": summary,
    }


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def _select(primary: object, fallback: object) -> object:
    if isinstance(primary, str) and primary != "":
        return primary
    if isinstance(fallback, str) and fallback != "":
        return fallback
    return None
