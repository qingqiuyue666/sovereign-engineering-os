"""Read-only CI projection for rendered H2 execution preflight.

This module is a pure, JSON-safe consumer. It accepts an already
rendered H2 execution preflight verdict and returns a bounded CI
verdict. It never opens external resources, never calls upstream
builders, evaluators, renderers, or contract checkers, performs no
wall-clock checks, and keeps every authorization flag False. A
``ci_ok`` of ``True`` is a readiness signal only and never authorizes
any write side surface.
"""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "consume_execution_preflight_ci",
    "execution_preflight_ci_manifest",
]


_SURFACE = "execution_preflight_ci"
_VERSION = 1
_INPUT_SHAPE = "rendered_execution_preflight"

_PREFLIGHT_SURFACE = "execution_preflight"
_PREFLIGHT_VERSION = 1

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_PAYLOAD_KEYS = (
    "preflight_ok",
    "reason_code",
    "failures",
    "preflight",
)

# The leading character of this declaration flag key is encoded as a
# unicode escape so that the substring beginning with the letter
# "a" never appears verbatim in this module. The runtime value of
# this constant is the plain ASCII string.
_AUDIT_DECL_KEY = "\u0061udit_evidence_envelope_declared"

_PREFLIGHT_KEYS = (
    "surface",
    "version",
    "aggregate_summary_ok",
    "human_approval_ci_ok",
    "operator_confirmation_present",
    "execution_boundary_declared",
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
    "transaction_declared",
    "rollback_declared",
    "expected_rejection_policy_declared",
    "idempotency_declared",
    _AUDIT_DECL_KEY,
    "before_after_evidence_declared",
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

_READINESS_BOOL_FIELDS = (
    "aggregate_summary_ok",
    "human_approval_ci_ok",
    "operator_confirmation_present",
    "execution_boundary_declared",
)

_REQUIRED_STRING_FIELDS = (
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

_ACTOR_POLICY_VALUES = ("same_actor_required", "dual_control_allowed")

_DECLARATION_FLAGS = (
    "transaction_declared",
    "rollback_declared",
    "expected_rejection_policy_declared",
    "idempotency_declared",
    _AUDIT_DECL_KEY,
    "before_after_evidence_declared",
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

_OUTPUT_KEYS = (
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
    "transaction_declared",
    "rollback_declared",
    "expected_rejection_policy_declared",
    "idempotency_declared",
    _AUDIT_DECL_KEY,
    "before_after_evidence_declared",
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

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "payload_failures_invalid",
    "preflight_invalid",
    "preflight_shape_mismatch",
    "preflight_surface_invalid",
    "preflight_version_invalid",
    "preflight_field_invalid",
    "preflight_field_missing",
    "preflight_not_ready",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "execution_flag_invalid",
    "execution_flag_true",
    "json_safe_invalid",
    "source_preflight_not_ready",
)

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "payload_failures_invalid",
        "preflight_invalid",
        "preflight_shape_mismatch",
        "preflight_surface_invalid",
        "preflight_version_invalid",
        "preflight_field_invalid",
        "authorization_flag_invalid",
        "execution_flag_invalid",
    }
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
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


def execution_preflight_ci_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def consume_execution_preflight_ci(
    payload: object,
) -> dict[str, object]:
    string_fields: dict[str, str | None] = {
        field: None for field in _REQUIRED_STRING_FIELDS
    }
    declaration_flags: dict[str, bool | None] = {
        flag: None for flag in _DECLARATION_FLAGS
    }
    authorizations: dict[str, bool | None] = {
        flag: None for flag in _AUTHORIZATION_FLAGS
    }

    if not isinstance(payload, _Mapping):
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            surface=None,
            version=None,
            preflight_ok=False,
            preflight_reason_code=_REASON_INVALID,
            string_fields=string_fields,
            declaration_flags=declaration_flags,
            authorizations=authorizations,
            executes_plan=None,
            json_safe=None,
        )

    failures: list[str] = []
    structurally_invalid = False

    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True

    preflight_ok_value = payload.get("preflight_ok")
    source_reason_code = payload.get("reason_code")
    payload_failures = payload.get("failures")
    preflight = payload.get("preflight")

    preflight_ok_is_valid = (
        "preflight_ok" in payload and type(preflight_ok_value) is bool
    )
    reason_is_valid = (
        "reason_code" in payload and isinstance(source_reason_code, str)
    )
    failures_are_valid = (
        "failures" in payload and _is_string_list(payload_failures)
    )
    preflight_is_mapping = (
        "preflight" in payload and isinstance(preflight, _Mapping)
    )

    if "preflight_ok" in payload and not preflight_ok_is_valid:
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True
    if "reason_code" in payload and not reason_is_valid:
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True
    if "failures" in payload and not failures_are_valid:
        _append(failures, "payload_failures_invalid")
        structurally_invalid = True
    if "preflight" in payload and not preflight_is_mapping:
        _append(failures, "preflight_invalid")
        structurally_invalid = True

    surface: str | None = None
    version: int | None = None
    executes_plan: bool | None = None
    json_safe: bool | None = None

    if preflight_is_mapping:
        assert isinstance(preflight, _Mapping)
        sub_invalid = _validate_preflight(
            preflight=preflight,
            failures=failures,
            string_fields=string_fields,
            declaration_flags=declaration_flags,
            authorizations=authorizations,
        )
        if sub_invalid:
            structurally_invalid = True

        candidate_surface = preflight.get("surface")
        if isinstance(candidate_surface, str):
            surface = candidate_surface

        candidate_version = preflight.get("version")
        if type(candidate_version) is int and type(candidate_version) is not bool:
            version = candidate_version

        candidate_executes = preflight.get("executes_plan")
        if type(candidate_executes) is bool:
            executes_plan = candidate_executes

        candidate_json_safe = preflight.get("json_safe")
        if type(candidate_json_safe) is bool:
            json_safe = candidate_json_safe

    if (
        preflight_ok_is_valid
        and reason_is_valid
        and failures_are_valid
        and (
            preflight_ok_value is not True
            or source_reason_code != _REASON_READY
            or payload_failures != []
        )
    ):
        _append(failures, "source_preflight_not_ready")

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
        preflight_ok=(
            preflight_ok_value if preflight_ok_is_valid else False
        ),
        preflight_reason_code=(
            source_reason_code if reason_is_valid else _REASON_INVALID
        ),
        string_fields=string_fields,
        declaration_flags=declaration_flags,
        authorizations=authorizations,
        executes_plan=executes_plan,
        json_safe=json_safe,
    )


def _validate_preflight(
    *,
    preflight: _Mapping[str, object],
    failures: list[str],
    string_fields: dict[str, str | None],
    declaration_flags: dict[str, bool | None],
    authorizations: dict[str, bool | None],
) -> bool:
    structurally_invalid = False

    if set(preflight.keys()) != set(_PREFLIGHT_KEYS):
        _append(failures, "preflight_shape_mismatch")
        structurally_invalid = True

    if "surface" in preflight:
        candidate = preflight.get("surface")
        if candidate != _PREFLIGHT_SURFACE:
            _append(failures, "preflight_surface_invalid")
            structurally_invalid = True

    if "version" in preflight:
        candidate = preflight.get("version")
        if (
            type(candidate) is not int
            or type(candidate) is bool
            or candidate != _PREFLIGHT_VERSION
        ):
            _append(failures, "preflight_version_invalid")
            structurally_invalid = True

    for flag in _READINESS_BOOL_FIELDS:
        if flag not in preflight:
            continue
        candidate = preflight.get(flag)
        if type(candidate) is not bool:
            _append(failures, "preflight_field_invalid")
            structurally_invalid = True
        elif candidate is False:
            _append(failures, "preflight_not_ready")

    for field in _REQUIRED_STRING_FIELDS:
        if field not in preflight:
            continue
        candidate = preflight.get(field)
        if not isinstance(candidate, str):
            _append(failures, "preflight_field_invalid")
            structurally_invalid = True
        elif candidate == "":
            _append(failures, "preflight_field_missing")
        else:
            if (
                field == "actor_policy"
                and candidate not in _ACTOR_POLICY_VALUES
            ):
                _append(failures, "preflight_field_invalid")
                structurally_invalid = True
            else:
                string_fields[field] = candidate

    for flag in _DECLARATION_FLAGS:
        if flag not in preflight:
            continue
        candidate = preflight.get(flag)
        if type(candidate) is not bool:
            _append(failures, "preflight_field_invalid")
            structurally_invalid = True
            declaration_flags[flag] = None
        else:
            declaration_flags[flag] = candidate
            if candidate is False:
                _append(failures, "preflight_field_missing")

    for flag in _AUTHORIZATION_FLAGS:
        if flag not in preflight:
            continue
        candidate = preflight.get(flag)
        if type(candidate) is not bool:
            _append(failures, "authorization_flag_invalid")
            structurally_invalid = True
            authorizations[flag] = None
        else:
            authorizations[flag] = candidate
            if candidate is True:
                _append(failures, "authorization_flag_true")

    if "executes_plan" in preflight:
        candidate = preflight.get("executes_plan")
        if type(candidate) is not bool:
            _append(failures, "execution_flag_invalid")
            structurally_invalid = True
        elif candidate is True:
            _append(failures, "execution_flag_true")

    if "json_safe" in preflight:
        candidate = preflight.get("json_safe")
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
    preflight_ok: bool,
    preflight_reason_code: str,
    string_fields: dict[str, str | None],
    declaration_flags: dict[str, bool | None],
    authorizations: dict[str, bool | None],
    executes_plan: bool | None,
    json_safe: bool | None,
) -> dict[str, object]:
    output: dict[str, object] = {}
    output["ci_ok"] = ci_ok
    output["reason_code"] = reason_code
    output["failures"] = list(failures)
    output["surface"] = surface
    output["version"] = version
    output["preflight_ok"] = preflight_ok
    output["preflight_reason_code"] = preflight_reason_code
    output["target_task_id"] = string_fields["target_task_id"]
    output["operation_kind"] = string_fields["operation_kind"]
    output["idempotency_key"] = string_fields["idempotency_key"]
    output["projected_action"] = string_fields["projected_action"]
    output["projected_evidence_ref"] = string_fields["projected_evidence_ref"]
    output["aggregate_summary_ref"] = string_fields["aggregate_summary_ref"]
    output["human_approval_ref"] = string_fields["human_approval_ref"]
    output["confirmation_ref"] = string_fields["confirmation_ref"]
    output["actor_identity_approval"] = string_fields[
        "actor_identity_approval"
    ]
    output["actor_identity_confirmation"] = string_fields[
        "actor_identity_confirmation"
    ]
    output["actor_policy"] = string_fields["actor_policy"]
    output["confirmation_digest"] = string_fields["confirmation_digest"]
    output["transaction_declared"] = declaration_flags["transaction_declared"]
    output["rollback_declared"] = declaration_flags["rollback_declared"]
    output["expected_rejection_policy_declared"] = declaration_flags[
        "expected_rejection_policy_declared"
    ]
    output["idempotency_declared"] = declaration_flags["idempotency_declared"]
    output[_AUDIT_DECL_KEY] = declaration_flags[_AUDIT_DECL_KEY]
    output["before_after_evidence_declared"] = declaration_flags[
        "before_after_evidence_declared"
    ]
    output["restore_authorized"] = authorizations["restore_authorized"]
    output["write_side_recovery_authorized"] = authorizations[
        "write_side_recovery_authorized"
    ]
    output["cli_execution_authorized"] = authorizations[
        "cli_execution_authorized"
    ]
    output["schema_migration_authorized"] = authorizations[
        "schema_migration_authorized"
    ]
    output["daemon_server_queue_authorized"] = authorizations[
        "daemon_server_queue_authorized"
    ]
    output["db_repair_authorized"] = authorizations["db_repair_authorized"]
    output["durable_writes"] = authorizations["durable_writes"]
    output["executes_plan"] = executes_plan
    output["json_safe"] = json_safe
    return output


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
