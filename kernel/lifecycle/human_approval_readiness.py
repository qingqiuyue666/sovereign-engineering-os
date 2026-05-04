"""Read-only Human Approval Readiness (H1).

Pure evaluator. Consumes already-rendered restore dry-run aggregate
summary output and an already-rendered human approval declaration, and
returns a bounded JSON-safe verdict whose meaning is strictly
"eligible for the next human/process review", never "allowed to
execute". Every authorization flag is held False; no upstream call,
no I/O, no DB, no service, no CLI, no wall-clock time, no mutation.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime


__all__ = [
    "HumanApprovalReadiness",
    "human_approval_readiness_manifest",
    "evaluate_human_approval_readiness",
    "render_human_approval_readiness",
]


_SURFACE = "human_approval_readiness"
_VERSION = 1
_INPUT_SHAPE = "already_rendered_human_approval_pair"

_REASON_READY = "ready"
_REASON_INVALID = "invalid_human_approval_payload"
_REASON_NOT_READY = "not_ready"

_AGGREGATE_SURFACE = "restore_dry_run_aggregate_summary"

_TOP_LEVEL_KEYS = ("aggregate_summary", "human_approval_declaration")

_AGGREGATE_TOP_KEYS = ("aggregate_ok", "reason_code", "failures", "summary")

_AGGREGATE_SUMMARY_REQUIRED_KEYS = (
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

_AGGREGATE_STRING_FIELDS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "determinism_hash",
)

_AGGREGATE_AUTHORIZATION_FIELDS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)

_DECLARATION_KEYS = (
    "approval_present",
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

_DECLARATION_STRING_FIELDS = (
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
)

_DECLARATION_AUTHORIZATION_FIELDS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)

_CROSS_FIELDS_FAILURE = {
    "target_task_id": "target_mismatch",
    "operation_kind": "operation_mismatch",
    "idempotency_key": "idempotency_mismatch",
    "projected_action": "projected_action_mismatch",
    "projected_evidence_ref": "projected_evidence_mismatch",
}

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "aggregate_summary_invalid",
    "aggregate_summary_not_ready",
    "aggregate_summary_authorization_hazard",
    "aggregate_summary_execution_hazard",
    "human_approval_invalid",
    "human_approval_missing",
    "approval_ref_invalid",
    "actor_identity_invalid",
    "approval_scope_invalid",
    "approval_reason_invalid",
    "created_at_invalid",
    "expires_at_invalid",
    "freshness_seconds_invalid",
    "freshness_window_invalid",
    "target_mismatch",
    "operation_mismatch",
    "idempotency_mismatch",
    "projected_action_mismatch",
    "projected_evidence_mismatch",
    "summary_ref_invalid",
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
        "human_approval_invalid",
    }
)

_HUMAN_APPROVAL_DEFAULTS: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "aggregate_summary_ready": False,
    "approval_present": False,
    "approval_ref": None,
    "actor_identity": None,
    "approval_scope": None,
    "approval_reason": None,
    "created_at": None,
    "expires_at": None,
    "freshness_seconds": None,
    "target_task_id": None,
    "operation_kind": None,
    "idempotency_key": None,
    "projected_action": None,
    "projected_evidence_ref": None,
    "aggregate_summary_ref": None,
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

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "restore_dry_run_read_only_stack": "restore-dry-run-read-only-stack-v1",
        "restore_dry_run_aggregate_summary": "restore-dry-run-aggregate-summary-v1",
        "restore_dry_run_plan_ci": "restore-dry-run-plan-ci-v1",
        "restore_dry_run_plan_renderer": "restore-dry-run-plan-renderer-v1",
        "restore_dry_run_readiness_ci": "restore-dry-run-readiness-ci-v1",
        "restore_dry_run_readiness": "restore-dry-run-readiness-v1",
        "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": "write-side-precondition-checker-v1",
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
class HumanApprovalReadiness:
    human_approval_ready: bool
    reason_code: str
    failures: tuple[str, ...]
    human_approval: dict[str, object]


def human_approval_readiness_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def evaluate_human_approval_readiness(payload: object) -> HumanApprovalReadiness:
    failures: list[str] = []
    human_approval = deepcopy(_HUMAN_APPROVAL_DEFAULTS)

    if not isinstance(payload, Mapping):
        return _build(
            failures=["payload_not_mapping"],
            human_approval=human_approval,
        )

    if set(payload.keys()) != set(_TOP_LEVEL_KEYS):
        _append(failures, "payload_shape_mismatch")

    aggregate_values: dict[str, object] = {}
    if "aggregate_summary" in payload:
        aggregate_ready, aggregate_failures, aggregate_values = (
            _validate_aggregate_summary(payload.get("aggregate_summary"))
        )
        human_approval["aggregate_summary_ready"] = aggregate_ready
        _extend(failures, aggregate_failures)

    declaration_values: dict[str, object] = {}
    if "human_approval_declaration" in payload:
        declaration_failures, declaration_values = _validate_declaration(
            payload.get("human_approval_declaration")
        )
        _apply_declaration_values(human_approval, declaration_values)
        _extend(failures, declaration_failures)

    _check_cross_fields(
        aggregate_values=aggregate_values,
        declaration_values=declaration_values,
        failures=failures,
    )

    ordered = _ordered_failures(failures)

    if ordered == []:
        reason_code = _REASON_READY
        ready = True
    elif any(failure in _STRUCTURAL_FAILURES for failure in ordered):
        reason_code = _REASON_INVALID
        ready = False
    else:
        reason_code = _REASON_NOT_READY
        ready = False

    return HumanApprovalReadiness(
        human_approval_ready=ready,
        reason_code=reason_code,
        failures=tuple(ordered),
        human_approval=human_approval,
    )


def render_human_approval_readiness(
    readiness: HumanApprovalReadiness,
) -> dict[str, object]:
    return {
        "human_approval_ready": bool(readiness.human_approval_ready),
        "reason_code": str(readiness.reason_code),
        "failures": list(readiness.failures),
        "human_approval": deepcopy(readiness.human_approval),
    }


def _validate_aggregate_summary(
    candidate: object,
) -> tuple[bool, list[str], dict[str, object]]:
    failures: list[str] = []
    extracted: dict[str, object] = {}

    if not isinstance(candidate, Mapping):
        return False, ["aggregate_summary_invalid"], extracted

    if set(candidate.keys()) != set(_AGGREGATE_TOP_KEYS):
        _append(failures, "aggregate_summary_invalid")

    aggregate_ok = candidate.get("aggregate_ok")
    if "aggregate_ok" in candidate and type(aggregate_ok) is not bool:
        _append(failures, "aggregate_summary_invalid")
    elif aggregate_ok is False:
        _append(failures, "aggregate_summary_not_ready")

    reason_code = candidate.get("reason_code")
    if "reason_code" in candidate:
        if not isinstance(reason_code, str):
            _append(failures, "aggregate_summary_invalid")
        elif reason_code != _REASON_READY:
            _append(failures, "aggregate_summary_not_ready")

    failures_value = candidate.get("failures")
    if "failures" in candidate:
        if not _is_string_list(failures_value):
            _append(failures, "aggregate_summary_invalid")
        elif failures_value != []:
            _append(failures, "aggregate_summary_not_ready")

    summary = candidate.get("summary")
    if "summary" in candidate:
        if not isinstance(summary, Mapping):
            _append(failures, "aggregate_summary_invalid")
        else:
            _validate_aggregate_summary_body(summary, failures, extracted)

    ready = failures == []
    return ready, _ordered_failures(failures), extracted


def _validate_aggregate_summary_body(
    summary: Mapping[str, object],
    failures: list[str],
    extracted: dict[str, object],
) -> None:
    if set(summary.keys()) != set(_AGGREGATE_SUMMARY_REQUIRED_KEYS):
        _append(failures, "aggregate_summary_invalid")

    surface = summary.get("surface")
    if "surface" in summary and surface != _AGGREGATE_SURFACE:
        _append(failures, "aggregate_summary_invalid")

    version = summary.get("version")
    if "version" in summary and (
        type(version) is not int or version != _VERSION
    ):
        _append(failures, "aggregate_summary_invalid")

    for flag in ("readiness_ci_ok", "plan_ci_ok"):
        value = summary.get(flag)
        if flag in summary and type(value) is not bool:
            _append(failures, "aggregate_summary_invalid")
        elif value is False:
            _append(failures, "aggregate_summary_not_ready")

    for field in _AGGREGATE_STRING_FIELDS:
        value = summary.get(field)
        if field in summary:
            if value is None or isinstance(value, str):
                if isinstance(value, str) and value != "":
                    extracted[field] = value
                elif value == "" or value is None:
                    _append(failures, "aggregate_summary_not_ready")
            else:
                _append(failures, "aggregate_summary_invalid")

    for flag in ("transaction_required", "rollback_required"):
        value = summary.get(flag)
        if flag in summary and type(value) is not bool:
            _append(failures, "aggregate_summary_invalid")
        elif value is False:
            _append(failures, "aggregate_summary_not_ready")

    for flag in _AGGREGATE_AUTHORIZATION_FIELDS:
        value = summary.get(flag)
        if flag in summary and value is not False:
            _append(failures, "aggregate_summary_authorization_hazard")

    if "executes_plan" in summary and summary.get("executes_plan") is not False:
        _append(failures, "aggregate_summary_execution_hazard")

    json_safe = summary.get("json_safe")
    if "json_safe" in summary:
        if type(json_safe) is not bool or json_safe is not True:
            _append(failures, "aggregate_summary_invalid")


def _validate_declaration(
    candidate: object,
) -> tuple[list[str], dict[str, object]]:
    failures: list[str] = []
    extracted: dict[str, object] = {}

    if not isinstance(candidate, Mapping):
        return ["human_approval_invalid"], extracted

    if set(candidate.keys()) != set(_DECLARATION_KEYS):
        _append(failures, "human_approval_invalid")

    approval_present = candidate.get("approval_present")
    if "approval_present" in candidate and type(approval_present) is not bool:
        _append(failures, "human_approval_invalid")
    elif approval_present is False:
        _append(failures, "human_approval_missing")
    elif approval_present is True:
        extracted["approval_present"] = True

    _check_required_string(
        candidate, "approval_ref", "approval_ref_invalid", failures, extracted
    )
    _check_required_string(
        candidate,
        "actor_identity",
        "actor_identity_invalid",
        failures,
        extracted,
    )
    _check_required_string(
        candidate,
        "approval_scope",
        "approval_scope_invalid",
        failures,
        extracted,
    )
    _check_required_string(
        candidate,
        "approval_reason",
        "approval_reason_invalid",
        failures,
        extracted,
    )

    created_at_dt = _check_created_at(candidate, failures, extracted)
    expires_at_dt = _check_expires_at(candidate, failures, extracted)
    has_freshness_seconds = _check_freshness_seconds(
        candidate, failures, extracted
    )

    if (
        "expires_at" in candidate
        and "freshness_seconds" in candidate
        and candidate.get("expires_at") is None
        and candidate.get("freshness_seconds") is None
    ):
        _append(failures, "freshness_window_invalid")

    if (
        created_at_dt is not None
        and expires_at_dt is not None
        and not (expires_at_dt > created_at_dt)
    ):
        _append(failures, "freshness_window_invalid")

    for field in _DECLARATION_STRING_FIELDS:
        value = candidate.get(field)
        if isinstance(value, str) and value != "":
            extracted[field] = value
        elif field in candidate:
            _append(failures, "human_approval_invalid")

    summary_ref = candidate.get("aggregate_summary_ref")
    if "aggregate_summary_ref" in candidate:
        if isinstance(summary_ref, str) and summary_ref != "":
            extracted["aggregate_summary_ref"] = summary_ref
        else:
            _append(failures, "summary_ref_invalid")

    for flag in _DECLARATION_AUTHORIZATION_FIELDS:
        value = candidate.get(flag)
        if flag in candidate:
            if type(value) is not bool:
                _append(failures, "authorization_flag_invalid")
            elif value is True:
                _append(failures, "authorization_flag_true")

    if "executes_plan" in candidate:
        executes = candidate.get("executes_plan")
        if type(executes) is not bool:
            _append(failures, "execution_flag_invalid")
        elif executes is True:
            _append(failures, "execution_flag_true")

    if "json_safe" in candidate:
        json_safe = candidate.get("json_safe")
        if type(json_safe) is not bool or json_safe is not True:
            _append(failures, "json_safe_invalid")

    _ = has_freshness_seconds
    return _ordered_failures(failures), extracted


def _check_required_string(
    candidate: Mapping[str, object],
    field: str,
    failure: str,
    failures: list[str],
    extracted: dict[str, object],
) -> None:
    if field not in candidate:
        return
    value = candidate.get(field)
    if isinstance(value, str) and value != "":
        extracted[field] = value
    else:
        _append(failures, failure)


def _check_created_at(
    candidate: Mapping[str, object],
    failures: list[str],
    extracted: dict[str, object],
) -> datetime | None:
    if "created_at" not in candidate:
        return None
    value = candidate.get("created_at")
    if not isinstance(value, str) or value == "":
        _append(failures, "created_at_invalid")
        return None
    parsed = _parse_timestamp(value)
    if parsed is None:
        _append(failures, "created_at_invalid")
        return None
    extracted["created_at"] = value
    return parsed


def _check_expires_at(
    candidate: Mapping[str, object],
    failures: list[str],
    extracted: dict[str, object],
) -> datetime | None:
    if "expires_at" not in candidate:
        return None
    value = candidate.get("expires_at")
    if value is None:
        return None
    if not isinstance(value, str) or value == "":
        _append(failures, "expires_at_invalid")
        return None
    parsed = _parse_timestamp(value)
    if parsed is None:
        _append(failures, "expires_at_invalid")
        return None
    extracted["expires_at"] = value
    return parsed


def _check_freshness_seconds(
    candidate: Mapping[str, object],
    failures: list[str],
    extracted: dict[str, object],
) -> bool:
    if "freshness_seconds" not in candidate:
        return False
    value = candidate.get("freshness_seconds")
    if value is None:
        return False
    if type(value) is bool or type(value) is not int or value <= 0:
        _append(failures, "freshness_seconds_invalid")
        return False
    extracted["freshness_seconds"] = value
    return True


def _parse_timestamp(value: str) -> datetime | None:
    candidate = value
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _apply_declaration_values(
    human_approval: dict[str, object],
    declaration_values: Mapping[str, object],
) -> None:
    for key in (
        "approval_present",
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
    ):
        if key in declaration_values:
            human_approval[key] = declaration_values[key]


def _check_cross_fields(
    *,
    aggregate_values: Mapping[str, object],
    declaration_values: Mapping[str, object],
    failures: list[str],
) -> None:
    for field, failure in _CROSS_FIELDS_FAILURE.items():
        aggregate_value = aggregate_values.get(field)
        declaration_value = declaration_values.get(field)
        if (
            isinstance(aggregate_value, str)
            and aggregate_value != ""
            and isinstance(declaration_value, str)
            and declaration_value != ""
            and aggregate_value != declaration_value
        ):
            _append(failures, failure)


def _build(
    *,
    failures: list[str],
    human_approval: dict[str, object],
) -> HumanApprovalReadiness:
    ordered = _ordered_failures(failures)
    if ordered == []:
        reason_code = _REASON_READY
        ready = True
    elif any(failure in _STRUCTURAL_FAILURES for failure in ordered):
        reason_code = _REASON_INVALID
        ready = False
    else:
        reason_code = _REASON_NOT_READY
        ready = False
    return HumanApprovalReadiness(
        human_approval_ready=ready,
        reason_code=reason_code,
        failures=tuple(ordered),
        human_approval=human_approval,
    )


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _extend(failures: list[str], new_failures: list[str]) -> None:
    for failure in new_failures:
        _append(failures, failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
