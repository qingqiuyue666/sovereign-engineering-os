"""Read-only CI projection for rendered R1 restore dry-run readiness.

This module is a pure, JSON-safe consumer. It accepts an already
rendered restore dry-run readiness payload and returns a bounded CI
verdict. It never opens external resources, never calls upstream
builders, evaluators, renderers, or contract checkers, and keeps every
authorization flag False.
"""

from collections.abc import Mapping as _Mapping
from copy import deepcopy as _deepcopy


__all__ = [
    "restore_dry_run_readiness_ci_manifest",
    "consume_restore_dry_run_readiness_ci",
]


_SURFACE = "restore_dry_run_readiness_ci"
_VERSION = 1
_INPUT_SHAPE = "rendered_restore_dry_run_readiness"
_CONTRACT_SURFACE = "restore_dry_run_readiness"
_CONTRACT_VERSION = 1

_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_PAYLOAD_KEYS = ("ready", "reason_code", "failures", "readiness")

_READINESS_KEYS = (
    "surface",
    "version",
    "source_truth_ready",
    "governance_ci_ready",
    "precondition_ci_ready",
    "target_task_ready",
    "dry_run_ready",
    "idempotency_ready",
    "evidence_snapshot_ready",
    "human_approval_ready",
    "schema_migration_safe",
    "db_repair_safe",
    "runtime_boundary_safe",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
    "json_safe",
)

_READINESS_FLAGS = (
    "source_truth_ready",
    "governance_ci_ready",
    "precondition_ci_ready",
    "target_task_ready",
    "dry_run_ready",
    "idempotency_ready",
    "evidence_snapshot_ready",
    "human_approval_ready",
    "schema_migration_safe",
    "db_repair_safe",
    "runtime_boundary_safe",
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
    "payload_failures_invalid",
    "readiness_invalid",
    "readiness_shape_mismatch",
    "readiness_surface_invalid",
    "readiness_version_invalid",
    "readiness_flag_invalid",
    "readiness_flag_not_ready",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
    "source_readiness_not_ready",
)

_STRUCTURAL_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "payload_failures_invalid",
        "readiness_invalid",
        "readiness_shape_mismatch",
        "readiness_surface_invalid",
        "readiness_version_invalid",
        "readiness_flag_invalid",
        "authorization_flag_invalid",
    }
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "depends_on": {
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
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [_REASON_INVALID, _REASON_NOT_READY, _REASON_READY],
    "failure_values": list(_FAILURE_ORDER),
}


def restore_dry_run_readiness_ci_manifest() -> dict[str, object]:
    return _deepcopy(_MANIFEST)


def consume_restore_dry_run_readiness_ci(
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
            authorizations={flag: None for flag in _AUTHORIZATION_FLAGS},
            json_safe=None,
        )

    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True

    ready_value = payload.get("ready")
    contract_reason_code = payload.get("reason_code")
    payload_failures = payload.get("failures")
    readiness = payload.get("readiness")

    ready_is_valid = "ready" in payload and type(ready_value) is bool
    reason_is_valid = (
        "reason_code" in payload and isinstance(contract_reason_code, str)
    )
    failures_are_valid = (
        "failures" in payload and _is_string_list(payload_failures)
    )
    readiness_is_mapping = (
        "readiness" in payload and isinstance(readiness, _Mapping)
    )

    if "ready" in payload and not ready_is_valid:
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True
    if "reason_code" in payload and not reason_is_valid:
        _append(failures, "payload_shape_mismatch")
        structurally_invalid = True
    if "failures" in payload and not failures_are_valid:
        _append(failures, "payload_failures_invalid")
        structurally_invalid = True
    if "readiness" in payload and not readiness_is_mapping:
        _append(failures, "readiness_invalid")
        structurally_invalid = True

    surface: str | None = None
    version: int | None = None
    authorizations: dict[str, bool | None] = {
        flag: None for flag in _AUTHORIZATION_FLAGS
    }
    json_safe: bool | None = None

    if readiness_is_mapping:
        assert isinstance(readiness, _Mapping)
        projected = _project_readiness(readiness)
        surface = projected["surface"]
        version = projected["version"]
        for flag in _AUTHORIZATION_FLAGS:
            authorizations[flag] = projected[flag]
        json_safe = projected["json_safe"]

        if set(readiness.keys()) != set(_READINESS_KEYS):
            _append(failures, "readiness_shape_mismatch")
            structurally_invalid = True

        if (
            "surface" in readiness
            and readiness.get("surface") != _CONTRACT_SURFACE
        ):
            _append(failures, "readiness_surface_invalid")
            structurally_invalid = True

        if "version" in readiness:
            version_value = readiness.get("version")
            if (
                type(version_value) is not int
                or version_value != _CONTRACT_VERSION
            ):
                _append(failures, "readiness_version_invalid")
                structurally_invalid = True

        for flag in _READINESS_FLAGS:
            if flag not in readiness:
                continue
            value = readiness.get(flag)
            if type(value) is not bool:
                _append(failures, "readiness_flag_invalid")
                structurally_invalid = True
            elif value is False:
                _append(failures, "readiness_flag_not_ready")

        for flag in _AUTHORIZATION_FLAGS:
            if flag not in readiness:
                continue
            value = readiness.get(flag)
            if type(value) is not bool:
                _append(failures, "authorization_flag_invalid")
                structurally_invalid = True
            elif value is True:
                _append(failures, "authorization_flag_true")

        if "json_safe" in readiness:
            value = readiness.get("json_safe")
            if type(value) is not bool:
                _append(failures, "json_safe_invalid")
                structurally_invalid = True
            elif value is False:
                _append(failures, "json_safe_invalid")

    if (
        ready_is_valid
        and reason_is_valid
        and failures_are_valid
        and (
            ready_value is not True
            or contract_reason_code != _REASON_READY
            or payload_failures != []
        )
    ):
        _append(failures, "source_readiness_not_ready")

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
        contract_ready=ready_value if ready_is_valid else False,
        contract_reason_code=(
            contract_reason_code if reason_is_valid else _REASON_INVALID
        ),
        authorizations=authorizations,
        json_safe=json_safe,
    )


def _project_readiness(
    readiness: _Mapping[str, object],
) -> dict[str, object]:
    projected: dict[str, object] = {
        "surface": (
            readiness.get("surface")
            if isinstance(readiness.get("surface"), str)
            else None
        ),
        "version": (
            readiness.get("version")
            if type(readiness.get("version")) is int
            else None
        ),
        "json_safe": _bool_or_none(readiness.get("json_safe")),
    }
    for flag in _AUTHORIZATION_FLAGS:
        projected[flag] = _bool_or_none(readiness.get(flag))
    return projected


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    surface: str | None,
    version: int | None,
    contract_ready: bool,
    contract_reason_code: str,
    authorizations: dict[str, bool | None],
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
        "json_safe": json_safe,
    }


def _bool_or_none(value: object) -> bool | None:
    return value if type(value) is bool else None


def _append(failures: list[str], failure: str) -> None:
    if failure not in failures:
        failures.append(failure)


def _ordered_failures(failures: list[str]) -> list[str]:
    return [failure for failure in _FAILURE_ORDER if failure in failures]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )
