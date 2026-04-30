"""Flat read-only CI projection for rendered write-side preconditions."""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "write_side_recovery_precondition_ci_manifest",
    "consume_write_side_recovery_precondition_ci",
]


_SURFACE = "write_side_recovery_precondition_ci"
_VERSION = 1
_INPUT_SHAPE = "rendered_write_side_recovery_precondition_check"
_CONTRACT_SURFACE = "write_side_recovery_precondition_check"

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_PAYLOAD_KEYS = ("ready", "reason_code", "failures", "preconditions")
_PRECONDITION_KEYS = (
    "surface",
    "version",
    "source_truth_ready",
    "governance_ready",
    "target_task_ready",
    "evidence_replay_ready",
    "approval_review_ready",
    "human_approval_ready",
    "dry_run_ready",
    "idempotency_ready",
    "evidence_snapshot_ready",
    "transaction_ready",
    "rollback_ready",
    "schema_migration_safe",
    "runtime_boundary_safe",
    "operator_confirmation_ready",
    "operator_safe",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "json_safe",
)
_READINESS_FLAGS = (
    "source_truth_ready",
    "governance_ready",
    "target_task_ready",
    "evidence_replay_ready",
    "approval_review_ready",
    "human_approval_ready",
    "dry_run_ready",
    "idempotency_ready",
    "evidence_snapshot_ready",
    "transaction_ready",
    "rollback_ready",
    "schema_migration_safe",
    "runtime_boundary_safe",
    "operator_confirmation_ready",
    "operator_safe",
)
_AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
)
_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "payload_failures_invalid",
    "preconditions_invalid",
    "preconditions_shape_mismatch",
    "preconditions_surface_invalid",
    "preconditions_version_invalid",
    "readiness_flag_invalid",
    "readiness_flag_not_ready",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
    "checker_not_ready",
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "restore_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "durable_writes": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [_REASON_INVALID, _REASON_NOT_READY, _REASON_READY],
    "failure_values": list(_FAILURE_ORDER),
}


def write_side_recovery_precondition_ci_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def consume_write_side_recovery_precondition_ci(
    payload: object,
) -> dict[str, object]:
    failures: list[str] = []
    structurally_invalid = False

    if not isinstance(payload, _Mapping):
        return _result(
            ci_ok=False,
            reason_code=_REASON_INVALID,
            failures=["payload_not_mapping"],
            surface=None,
            version=None,
            contract_ready=False,
            contract_reason_code=_REASON_INVALID,
            restore_authorized=None,
            write_side_recovery_authorized=None,
            cli_execution_authorized=None,
            schema_migration_authorized=None,
            daemon_server_queue_authorized=None,
            json_safe=None,
        )

    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        _append_failure(failures, "payload_shape_mismatch")
        structurally_invalid = True

    ready = payload.get("ready")
    contract_reason_code = payload.get("reason_code")
    payload_failures = payload.get("failures")
    preconditions = payload.get("preconditions")

    ready_is_valid = "ready" in payload and type(ready) is bool
    reason_is_valid = (
        "reason_code" in payload and isinstance(contract_reason_code, str)
    )
    failures_are_valid = (
        "failures" in payload and _is_string_list(payload_failures)
    )
    preconditions_are_valid = (
        "preconditions" in payload and isinstance(preconditions, _Mapping)
    )

    if "ready" in payload and not ready_is_valid:
        _append_failure(failures, "payload_shape_mismatch")
        structurally_invalid = True
    if "reason_code" in payload and not reason_is_valid:
        _append_failure(failures, "payload_shape_mismatch")
        structurally_invalid = True
    if "failures" in payload and not failures_are_valid:
        _append_failure(failures, "payload_failures_invalid")
        structurally_invalid = True
    if "preconditions" in payload and not preconditions_are_valid:
        _append_failure(failures, "preconditions_invalid")
        structurally_invalid = True

    surface = None
    version = None
    restore_authorized = None
    write_side_recovery_authorized = None
    cli_execution_authorized = None
    schema_migration_authorized = None
    daemon_server_queue_authorized = None
    json_safe = None

    if preconditions_are_valid:
        assert isinstance(preconditions, _Mapping)
        projected = _project_preconditions(preconditions)
        surface = projected["surface"]
        version = projected["version"]
        restore_authorized = projected["restore_authorized"]
        write_side_recovery_authorized = projected[
            "write_side_recovery_authorized"
        ]
        cli_execution_authorized = projected["cli_execution_authorized"]
        schema_migration_authorized = projected[
            "schema_migration_authorized"
        ]
        daemon_server_queue_authorized = projected[
            "daemon_server_queue_authorized"
        ]
        json_safe = projected["json_safe"]

        if set(preconditions.keys()) != set(_PRECONDITION_KEYS):
            _append_failure(failures, "preconditions_shape_mismatch")
            structurally_invalid = True

        if (
            "surface" in preconditions
            and preconditions.get("surface") != _CONTRACT_SURFACE
        ):
            _append_failure(failures, "preconditions_surface_invalid")
            structurally_invalid = True

        if (
            "version" in preconditions
            and (
                type(preconditions.get("version")) is not int
                or preconditions.get("version") != _VERSION
            )
        ):
            _append_failure(failures, "preconditions_version_invalid")
            structurally_invalid = True

        for flag in _READINESS_FLAGS:
            if flag not in preconditions:
                continue
            value = preconditions.get(flag)
            if type(value) is not bool:
                _append_failure(failures, "readiness_flag_invalid")
                structurally_invalid = True
            elif value is False:
                _append_failure(failures, "readiness_flag_not_ready")

        for flag in _AUTHORIZATION_FLAGS:
            if flag not in preconditions:
                continue
            value = preconditions.get(flag)
            if type(value) is not bool:
                _append_failure(failures, "authorization_flag_invalid")
                structurally_invalid = True
            elif value is True:
                _append_failure(failures, "authorization_flag_true")

        if "json_safe" in preconditions:
            value = preconditions.get("json_safe")
            if type(value) is not bool:
                _append_failure(failures, "json_safe_invalid")
                structurally_invalid = True
            elif value is False:
                _append_failure(failures, "json_safe_invalid")

    if (
        ready_is_valid
        and reason_is_valid
        and failures_are_valid
        and (
            ready is not True
            or contract_reason_code != _REASON_READY
            or payload_failures != []
        )
    ):
        _append_failure(failures, "checker_not_ready")

    ordered_failures = _ordered_failures(failures)
    ci_ok = not structurally_invalid and ordered_failures == []
    if ci_ok:
        reason_code = _REASON_READY
    elif structurally_invalid:
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _result(
        ci_ok=ci_ok,
        reason_code=reason_code,
        failures=ordered_failures,
        surface=surface,
        version=version,
        contract_ready=ready if ready_is_valid else False,
        contract_reason_code=(
            contract_reason_code if reason_is_valid else _REASON_INVALID
        ),
        restore_authorized=restore_authorized,
        write_side_recovery_authorized=write_side_recovery_authorized,
        cli_execution_authorized=cli_execution_authorized,
        schema_migration_authorized=schema_migration_authorized,
        daemon_server_queue_authorized=daemon_server_queue_authorized,
        json_safe=json_safe,
    )


def _project_preconditions(
    preconditions: _Mapping[str, object],
) -> dict[str, object]:
    return {
        "surface": (
            preconditions.get("surface")
            if isinstance(preconditions.get("surface"), str)
            else None
        ),
        "version": (
            preconditions.get("version")
            if type(preconditions.get("version")) is int
            else None
        ),
        "restore_authorized": _bool_or_none(
            preconditions.get("restore_authorized")
        ),
        "write_side_recovery_authorized": _bool_or_none(
            preconditions.get("write_side_recovery_authorized")
        ),
        "cli_execution_authorized": _bool_or_none(
            preconditions.get("cli_execution_authorized")
        ),
        "schema_migration_authorized": _bool_or_none(
            preconditions.get("schema_migration_authorized")
        ),
        "daemon_server_queue_authorized": _bool_or_none(
            preconditions.get("daemon_server_queue_authorized")
        ),
        "json_safe": _bool_or_none(preconditions.get("json_safe")),
    }


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    surface: str | None,
    version: int | None,
    contract_ready: bool,
    contract_reason_code: str,
    restore_authorized: bool | None,
    write_side_recovery_authorized: bool | None,
    cli_execution_authorized: bool | None,
    schema_migration_authorized: bool | None,
    daemon_server_queue_authorized: bool | None,
    json_safe: bool | None,
) -> dict[str, object]:
    return {
        "ci_ok": ci_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "surface": surface,
        "version": version,
        "contract_ready": contract_ready,
        "contract_reason_code": contract_reason_code,
        "restore_authorized": restore_authorized,
        "write_side_recovery_authorized": write_side_recovery_authorized,
        "cli_execution_authorized": cli_execution_authorized,
        "schema_migration_authorized": schema_migration_authorized,
        "daemon_server_queue_authorized": daemon_server_queue_authorized,
        "json_safe": json_safe,
    }


def _bool_or_none(value: object) -> bool | None:
    return value if type(value) is bool else None


def _append_failure(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
