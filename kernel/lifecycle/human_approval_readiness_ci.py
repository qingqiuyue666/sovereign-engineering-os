"""Read-only CI projection for rendered H1 human approval readiness.

This module is a pure, JSON-safe consumer. It accepts an already
rendered H1 human approval readiness verdict and returns a bounded CI
verdict. It never opens external resources, never calls upstream
builders, evaluators, renderers, or contract checkers, performs no
wall-clock checks, and keeps every authorization flag False.
"""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "consume_human_approval_readiness_ci",
    "human_approval_readiness_ci_manifest",
]


_SURFACE = "human_approval_readiness_ci"
_VERSION = 1
_INPUT_SHAPE = "rendered_human_approval_readiness"

_HUMAN_APPROVAL_SURFACE = "human_approval_readiness"
_HUMAN_APPROVAL_VERSION = 1

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_PAYLOAD_KEYS = (
    "human_approval_ready",
    "reason_code",
    "failures",
    "human_approval",
)

_HUMAN_APPROVAL_KEYS = (
    "surface",
    "version",
    "aggregate_summary_ready",
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

_REQUIRED_STRING_FIELDS = (
    "approval_ref",
    "actor_identity",
    "approval_scope",
    "approval_reason",
    "created_at",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
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

_OPTIONAL_STRING_OUTPUTS = (
    "approval_ref",
    "actor_identity",
    "approval_scope",
    "approval_reason",
    "created_at",
    "expires_at",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
)

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "payload_failures_invalid",
    "human_approval_invalid",
    "human_approval_shape_mismatch",
    "human_approval_surface_invalid",
    "human_approval_version_invalid",
    "human_approval_field_invalid",
    "human_approval_field_missing",
    "human_approval_not_ready",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "execution_flag_invalid",
    "execution_flag_true",
    "json_safe_invalid",
    "source_human_approval_not_ready",
)

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "payload_failures_invalid",
        "human_approval_invalid",
        "human_approval_shape_mismatch",
        "human_approval_surface_invalid",
        "human_approval_version_invalid",
        "human_approval_field_invalid",
        "authorization_flag_invalid",
        "execution_flag_invalid",
    }
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
        "human_approval_readiness": "human-approval-readiness-v1",
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
    "reason_codes": [_REASON_INVALID, _REASON_NOT_READY, _REASON_READY],
    "failure_values": list(_FAILURE_ORDER),
}


def human_approval_readiness_ci_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def consume_human_approval_readiness_ci(
    payload: object,
) -> dict[str, object]:
    if not isinstance(payload, _Mapping):
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            surface=None,
            version=None,
            source_ready=False,
            source_reason_code=_REASON_INVALID,
            string_fields={field: None for field in _OPTIONAL_STRING_OUTPUTS},
            freshness_seconds=None,
            authorizations={flag: None for flag in _AUTHORIZATION_FLAGS},
            executes_plan=None,
            json_safe=None,
        )

    failures: list[str] = []
    structurally_invalid = False

    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True

    ready_value = payload.get("human_approval_ready")
    source_reason_code = payload.get("reason_code")
    payload_failures = payload.get("failures")
    human_approval = payload.get("human_approval")

    ready_is_valid = (
        "human_approval_ready" in payload and type(ready_value) is bool
    )
    reason_is_valid = (
        "reason_code" in payload and isinstance(source_reason_code, str)
    )
    failures_are_valid = (
        "failures" in payload and _is_string_list(payload_failures)
    )
    human_approval_is_mapping = (
        "human_approval" in payload and isinstance(human_approval, _Mapping)
    )

    if "human_approval_ready" in payload and not ready_is_valid:
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True
    if "reason_code" in payload and not reason_is_valid:
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True
    if "failures" in payload and not failures_are_valid:
        _append(failures, "payload_failures_invalid")
        structurally_invalid = True
    if "human_approval" in payload and not human_approval_is_mapping:
        _append(failures, "human_approval_invalid")
        structurally_invalid = True

    surface: str | None = None
    version: int | None = None
    string_fields: dict[str, str | None] = {
        field: None for field in _OPTIONAL_STRING_OUTPUTS
    }
    freshness_seconds: int | None = None
    authorizations: dict[str, bool | None] = {
        flag: None for flag in _AUTHORIZATION_FLAGS
    }
    executes_plan: bool | None = None
    json_safe: bool | None = None

    if human_approval_is_mapping:
        assert isinstance(human_approval, _Mapping)
        sub_invalid = _validate_human_approval(
            human_approval=human_approval,
            failures=failures,
            string_fields=string_fields,
            authorizations=authorizations,
        )
        if sub_invalid:
            structurally_invalid = True

        candidate_surface = human_approval.get("surface")
        if isinstance(candidate_surface, str):
            surface = candidate_surface

        candidate_version = human_approval.get("version")
        if type(candidate_version) is int:
            version = candidate_version

        candidate_freshness = human_approval.get("freshness_seconds")
        if (
            type(candidate_freshness) is int
            and type(candidate_freshness) is not bool
            and candidate_freshness > 0
        ):
            freshness_seconds = candidate_freshness

        candidate_executes = human_approval.get("executes_plan")
        if type(candidate_executes) is bool:
            executes_plan = candidate_executes

        candidate_json_safe = human_approval.get("json_safe")
        if type(candidate_json_safe) is bool:
            json_safe = candidate_json_safe

    if (
        ready_is_valid
        and reason_is_valid
        and failures_are_valid
        and (
            ready_value is not True
            or source_reason_code != _REASON_READY
            or payload_failures != []
        )
    ):
        _append(failures, "source_human_approval_not_ready")

    ordered_failures = _ordered_failures(failures)
    has_structural = structurally_invalid or any(
        failure in _STRUCTURAL_FAILURES for failure in ordered_failures
    )
    ci_ok = not has_structural and ordered_failures == []
    if ci_ok:
        reason_code = _REASON_READY
    elif has_structural:
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        ci_ok=ci_ok,
        reason_code=reason_code,
        failures=ordered_failures,
        surface=surface,
        version=version,
        source_ready=ready_value if ready_is_valid else False,
        source_reason_code=(
            source_reason_code if reason_is_valid else _REASON_INVALID
        ),
        string_fields=string_fields,
        freshness_seconds=freshness_seconds,
        authorizations=authorizations,
        executes_plan=executes_plan,
        json_safe=json_safe,
    )


def _validate_human_approval(
    *,
    human_approval: _Mapping[str, object],
    failures: list[str],
    string_fields: dict[str, str | None],
    authorizations: dict[str, bool | None],
) -> bool:
    structurally_invalid = False

    if set(human_approval.keys()) != set(_HUMAN_APPROVAL_KEYS):
        _append(failures, "human_approval_shape_mismatch")
        structurally_invalid = True

    if "surface" in human_approval:
        candidate = human_approval.get("surface")
        if candidate != _HUMAN_APPROVAL_SURFACE:
            _append(failures, "human_approval_surface_invalid")
            structurally_invalid = True

    if "version" in human_approval:
        candidate = human_approval.get("version")
        if (
            type(candidate) is not int
            or type(candidate) is bool
            or candidate != _HUMAN_APPROVAL_VERSION
        ):
            _append(failures, "human_approval_version_invalid")
            structurally_invalid = True

    if "aggregate_summary_ready" in human_approval:
        candidate = human_approval.get("aggregate_summary_ready")
        if type(candidate) is not bool:
            _append(failures, "human_approval_field_invalid")
            structurally_invalid = True
        elif candidate is False:
            _append(failures, "human_approval_not_ready")

    if "approval_present" in human_approval:
        candidate = human_approval.get("approval_present")
        if type(candidate) is not bool:
            _append(failures, "human_approval_field_invalid")
            structurally_invalid = True
        elif candidate is False:
            _append(failures, "human_approval_not_ready")

    for field in _REQUIRED_STRING_FIELDS:
        if field not in human_approval:
            continue
        candidate = human_approval.get(field)
        if not isinstance(candidate, str):
            _append(failures, "human_approval_field_invalid")
            structurally_invalid = True
        elif candidate == "":
            _append(failures, "human_approval_field_missing")
        else:
            string_fields[field] = candidate

    expires_present = False
    if "expires_at" in human_approval:
        candidate = human_approval.get("expires_at")
        if candidate is None:
            pass
        elif not isinstance(candidate, str):
            _append(failures, "human_approval_field_invalid")
            structurally_invalid = True
        elif candidate == "":
            _append(failures, "human_approval_field_missing")
        else:
            string_fields["expires_at"] = candidate
            expires_present = True

    freshness_present = False
    if "freshness_seconds" in human_approval:
        candidate = human_approval.get("freshness_seconds")
        if candidate is None:
            pass
        elif (
            type(candidate) is bool
            or type(candidate) is not int
            or candidate <= 0
        ):
            _append(failures, "human_approval_field_invalid")
            structurally_invalid = True
        else:
            freshness_present = True

    if (
        "expires_at" in human_approval
        and "freshness_seconds" in human_approval
        and not expires_present
        and not freshness_present
        and human_approval.get("expires_at") is None
        and human_approval.get("freshness_seconds") is None
    ):
        _append(failures, "human_approval_field_missing")

    for flag in _AUTHORIZATION_FLAGS:
        if flag not in human_approval:
            continue
        candidate = human_approval.get(flag)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
            structurally_invalid = True
            authorizations[flag] = None
        else:
            authorizations[flag] = candidate
            if candidate is True:
                _append(failures, "authorization_flag_true")

    if "executes_plan" in human_approval:
        candidate = human_approval.get("executes_plan")
        if type(candidate) is not bool:
            _append(failures, "execution_flag_invalid")
            structurally_invalid = True
        elif candidate is True:
            _append(failures, "execution_flag_true")

    if "json_safe" in human_approval:
        candidate = human_approval.get("json_safe")
        if type(candidate) is not bool:
            _append(failures, "json_safe_invalid")
            structurally_invalid = True
        elif candidate is False:
            _append(failures, "json_safe_invalid")

    return structurally_invalid


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    surface: str | None,
    version: int | None,
    source_ready: bool,
    source_reason_code: str,
    string_fields: dict[str, str | None],
    freshness_seconds: int | None,
    authorizations: dict[str, bool | None],
    executes_plan: bool | None,
    json_safe: bool | None,
) -> dict[str, object]:
    return {
        "ci_ok": ci_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "surface": surface,
        "version": version,
        "human_approval_ready": source_ready,
        "human_approval_reason_code": source_reason_code,
        "approval_ref": string_fields["approval_ref"],
        "actor_identity": string_fields["actor_identity"],
        "approval_scope": string_fields["approval_scope"],
        "approval_reason": string_fields["approval_reason"],
        "created_at": string_fields["created_at"],
        "expires_at": string_fields["expires_at"],
        "freshness_seconds": freshness_seconds,
        "target_task_id": string_fields["target_task_id"],
        "operation_kind": string_fields["operation_kind"],
        "idempotency_key": string_fields["idempotency_key"],
        "projected_action": string_fields["projected_action"],
        "projected_evidence_ref": string_fields["projected_evidence_ref"],
        "aggregate_summary_ref": string_fields["aggregate_summary_ref"],
        "restore_authorized": authorizations["restore_authorized"],
        "write_side_recovery_authorized": authorizations[
            "write_side_recovery_authorized"
        ],
        "cli_execution_authorized": authorizations[
            "cli_execution_authorized"
        ],
        "schema_migration_authorized": authorizations[
            "schema_migration_authorized"
        ],
        "daemon_server_queue_authorized": authorizations[
            "daemon_server_queue_authorized"
        ],
        "db_repair_authorized": authorizations["db_repair_authorized"],
        "durable_writes": authorizations["durable_writes"],
        "executes_plan": executes_plan,
        "json_safe": json_safe,
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
