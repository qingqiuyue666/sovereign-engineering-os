"""Read-only contract check for rendered cross-phase verdict digests."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping


_TOP_LEVEL_KEYS = ["digest", "failures", "ok", "reason_code"]
_DIGEST_KEYS = [
    "after_manifest_version",
    "after_reason_code",
    "after_ready",
    "before_manifest_version",
    "before_reason_code",
    "before_ready",
    "cli_command_count",
    "comparison_change_count",
    "comparison_changed",
    "comparison_failure_count",
    "comparison_ok",
    "comparison_reason_code",
    "contract_failure_count",
    "contract_ready",
    "contract_reason_code",
    "cross_phase_ok",
    "durable_writes",
    "failures",
    "has_cli_commands",
    "has_contract_failure",
    "has_drift",
    "has_restore_or_durable_surface",
    "has_runtime_dependencies",
    "json_safe",
    "manifest_surface",
    "manifest_version",
    "operator_safe",
    "reason_code",
    "restore_supported",
    "runtime_dependency_count",
]
_FAILURE_VALUES = [
    "check_failures_invalid",
    "check_manifest_invalid",
    "check_manifest_shape_mismatch",
    "check_not_mapping",
    "check_shape_mismatch",
    "comparison_failures_invalid",
    "comparison_not_mapping",
    "comparison_report_invalid",
    "comparison_report_shape_mismatch",
    "comparison_shape_mismatch",
]
_REASON_CODES = ["invalid_cross_phase_digest", "ok"]
_CONTRACT_READY_REQUIRES = {
    "ok": True,
    "reason_code": "ok",
    "failures": [],
    "digest.cross_phase_ok": True,
    "digest.reason_code": "ok",
    "digest.failures": [],
    "digest.operator_safe": True,
}
_MANIFEST = {
    "surface": "recovery_session_host_verdict_cross_phase_digest",
    "version": 1,
    "input_shape": "rendered_cross_phase_digest",
    "top_level_keys": _TOP_LEVEL_KEYS,
    "digest_keys": _DIGEST_KEYS,
    "failure_values": _FAILURE_VALUES,
    "reason_codes": _REASON_CODES,
    "contract_ready_requires": _CONTRACT_READY_REQUIRES,
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
}
_BOOL_FIELDS = [
    "cross_phase_ok",
    "operator_safe",
    "contract_ready",
    "restore_supported",
    "durable_writes",
    "json_safe",
    "comparison_ok",
    "has_drift",
    "has_contract_failure",
    "has_runtime_dependencies",
    "has_cli_commands",
    "has_restore_or_durable_surface",
]
_STRING_FIELDS = [
    "reason_code",
    "contract_reason_code",
    "comparison_reason_code",
]
_LIST_FIELDS = ["failures"]
_COUNTER_FIELDS = [
    "contract_failure_count",
    "cli_command_count",
    "runtime_dependency_count",
    "comparison_failure_count",
    "comparison_change_count",
]
_OPTIONAL_BOOL_FIELDS = [
    "before_ready",
    "after_ready",
    "comparison_changed",
]
_OPTIONAL_STRING_FIELDS = [
    "manifest_surface",
    "before_reason_code",
    "after_reason_code",
]
_OPTIONAL_INT_FIELDS = [
    "manifest_version",
    "before_manifest_version",
    "after_manifest_version",
]


@dataclass(frozen=True)
class RecoverySessionHostVerdictCrossPhaseDigestContractCheck:
    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    contract: dict[str, object]


def recovery_session_host_verdict_cross_phase_digest_contract_manifest() -> (
    dict[str, object]
):
    return deepcopy(_MANIFEST)


def check_recovery_session_host_verdict_cross_phase_digest_contract(
    rendered_digest: Mapping[str, object],
) -> RecoverySessionHostVerdictCrossPhaseDigestContractCheck:
    contract = recovery_session_host_verdict_cross_phase_digest_contract_manifest()
    failures: list[str] = []

    if not isinstance(rendered_digest, Mapping):
        failures.append("payload_not_mapping")
        return _contract_check(failures, contract, operator_safe=False)

    top_level_shape_valid = set(rendered_digest) == set(_TOP_LEVEL_KEYS)
    ok = rendered_digest.get("ok")
    ok_valid = isinstance(ok, bool)
    if not top_level_shape_valid or not ok_valid:
        failures.append("payload_shape_mismatch")

    reason_code = rendered_digest.get("reason_code")
    reason_code_valid = (
        isinstance(reason_code, str) and reason_code in _REASON_CODES
    )
    if not reason_code_valid:
        failures.append("reason_code_invalid")

    payload_failures = rendered_digest.get("failures")
    payload_failures_valid = _is_string_list(payload_failures)
    if not payload_failures_valid:
        failures.append("failures_invalid")
    elif any(item not in _FAILURE_VALUES for item in payload_failures):
        failures.append("failure_value_unknown")

    digest = rendered_digest.get("digest")
    digest_valid = isinstance(digest, dict)
    if not digest_valid:
        failures.append("digest_invalid")
        return _contract_check(failures, contract, operator_safe=False)

    digest_shape_valid = set(digest) == set(_DIGEST_KEYS)
    if not digest_shape_valid:
        failures.append("digest_shape_mismatch")

    digest_bool_valid = False
    digest_string_valid = False
    digest_list_valid = False
    digest_counter_valid = False
    digest_optional_bool_valid = False
    digest_optional_string_valid = False
    digest_optional_int_valid = False

    if digest_shape_valid:
        digest_bool_valid = _has_valid_bool_fields(digest)
        if not digest_bool_valid:
            failures.append("digest_bool_invalid")

        digest_string_valid = _has_valid_string_fields(digest)
        if not digest_string_valid:
            failures.append("digest_string_invalid")

        digest_list_valid = _has_valid_list_fields(digest)
        if not digest_list_valid:
            failures.append("digest_list_invalid")

        digest_counter_valid = _has_valid_counter_fields(digest)
        if not digest_counter_valid:
            failures.append("digest_counter_invalid")

        digest_optional_bool_valid = _has_valid_optional_bool_fields(digest)
        if not digest_optional_bool_valid:
            failures.append("digest_optional_bool_invalid")

        digest_optional_string_valid = _has_valid_optional_string_fields(
            digest
        )
        if not digest_optional_string_valid:
            failures.append("digest_optional_string_invalid")

        digest_optional_int_valid = _has_valid_optional_int_fields(digest)
        if not digest_optional_int_valid:
            failures.append("digest_optional_int_invalid")

        if (
            digest_bool_valid
            and digest_counter_valid
            and not _operator_safe_is_consistent(digest)
        ):
            failures.append("operator_safe_inconsistent")

        if (
            ok_valid
            and reason_code_valid
            and payload_failures_valid
            and digest_bool_valid
            and digest_string_valid
            and digest_list_valid
            and not _status_is_consistent(
                ok=ok,
                reason_code=reason_code,
                failures=payload_failures,
                digest=digest,
            )
        ):
            failures.append("status_inconsistent")

        if (
            digest_bool_valid
            and digest_counter_valid
            and digest_optional_bool_valid
            and not _hazard_flags_are_consistent(digest)
        ):
            failures.append("hazard_flag_inconsistent")
        elif _has_typed_hazard_flag_inconsistency(digest):
            failures.append("hazard_flag_inconsistent")

    operator_safe = digest["operator_safe"] if digest_shape_valid else False
    return _contract_check(failures, contract, operator_safe=operator_safe)


def render_recovery_session_host_verdict_cross_phase_digest_contract_check(
    check: RecoverySessionHostVerdictCrossPhaseDigestContractCheck,
) -> dict[str, object]:
    return {
        "ready": check.ready,
        "reason_code": check.reason_code,
        "failures": list(check.failures),
        "contract": deepcopy(check.contract),
    }


def _contract_check(
    failures: list[str],
    contract: dict[str, object],
    *,
    operator_safe: object,
) -> RecoverySessionHostVerdictCrossPhaseDigestContractCheck:
    if failures:
        return RecoverySessionHostVerdictCrossPhaseDigestContractCheck(
            ready=False,
            reason_code="invalid_cross_phase_digest",
            failures=tuple(failures),
            contract=contract,
        )
    if operator_safe is True:
        return RecoverySessionHostVerdictCrossPhaseDigestContractCheck(
            ready=True,
            reason_code="ready",
            failures=(),
            contract=contract,
        )
    return RecoverySessionHostVerdictCrossPhaseDigestContractCheck(
        ready=False,
        reason_code="not_ready",
        failures=(),
        contract=contract,
    )


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def _is_int(value: object) -> bool:
    return type(value) is int


def _is_bool(value: object) -> bool:
    return isinstance(value, bool)


def _has_valid_bool_fields(digest: dict[str, object]) -> bool:
    return all(_is_bool(digest[key]) for key in _BOOL_FIELDS)


def _has_valid_string_fields(digest: dict[str, object]) -> bool:
    return all(isinstance(digest[key], str) for key in _STRING_FIELDS)


def _has_valid_list_fields(digest: dict[str, object]) -> bool:
    return all(_is_string_list(digest[key]) for key in _LIST_FIELDS)


def _has_valid_counter_fields(digest: dict[str, object]) -> bool:
    return all(_is_int(digest[key]) for key in _COUNTER_FIELDS)


def _has_valid_optional_bool_fields(digest: dict[str, object]) -> bool:
    return all(
        digest[key] is None or isinstance(digest[key], bool)
        for key in _OPTIONAL_BOOL_FIELDS
    )


def _has_valid_optional_string_fields(digest: dict[str, object]) -> bool:
    return all(
        digest[key] is None or isinstance(digest[key], str)
        for key in _OPTIONAL_STRING_FIELDS
    )


def _has_valid_optional_int_fields(digest: dict[str, object]) -> bool:
    return all(
        digest[key] is None or _is_int(digest[key])
        for key in _OPTIONAL_INT_FIELDS
    )


def _operator_safe_is_consistent(digest: dict[str, object]) -> bool:
    if digest["operator_safe"] is not True:
        return True

    return (
        digest["cross_phase_ok"] is True
        and digest["contract_ready"] is True
        and digest["contract_failure_count"] == 0
        and digest["comparison_ok"] is True
        and digest["comparison_failure_count"] == 0
        and digest["has_drift"] is False
        and digest["has_contract_failure"] is False
        and digest["has_runtime_dependencies"] is False
        and digest["has_cli_commands"] is False
        and digest["has_restore_or_durable_surface"] is False
        and digest["json_safe"] is True
    )


def _status_is_consistent(
    *,
    ok: object,
    reason_code: object,
    failures: object,
    digest: dict[str, object],
) -> bool:
    if ok is True:
        return (
            reason_code == "ok"
            and failures == []
            and digest["cross_phase_ok"] is True
            and digest["reason_code"] == "ok"
            and digest["failures"] == []
        )
    return (
        reason_code == "invalid_cross_phase_digest"
        and failures != []
        and digest["cross_phase_ok"] is False
        and digest["reason_code"] == "invalid_cross_phase_digest"
        and digest["failures"] != []
    )


def _hazard_flags_are_consistent(digest: dict[str, object]) -> bool:
    return (
        digest["has_runtime_dependencies"]
        == (digest["runtime_dependency_count"] > 0)
        and digest["has_cli_commands"] == (digest["cli_command_count"] > 0)
        and digest["has_restore_or_durable_surface"]
        == (digest["restore_supported"] or digest["durable_writes"])
        and digest["has_contract_failure"]
        == (
            digest["contract_ready"] is False
            or digest["contract_failure_count"] > 0
            or digest["comparison_ok"] is False
            or digest["comparison_failure_count"] > 0
        )
        and digest["has_drift"]
        == (
            digest["comparison_changed"] is True
            or digest["comparison_change_count"] > 0
        )
    )


def _has_typed_hazard_flag_inconsistency(
    digest: dict[str, object]
) -> bool:
    runtime_dependency_count = digest["runtime_dependency_count"]
    has_runtime_dependencies = digest["has_runtime_dependencies"]
    if _is_int(runtime_dependency_count) and _is_bool(
        has_runtime_dependencies
    ):
        if has_runtime_dependencies != (runtime_dependency_count > 0):
            return True

    cli_command_count = digest["cli_command_count"]
    has_cli_commands = digest["has_cli_commands"]
    if _is_int(cli_command_count) and _is_bool(has_cli_commands):
        if has_cli_commands != (cli_command_count > 0):
            return True

    restore_supported = digest["restore_supported"]
    durable_writes = digest["durable_writes"]
    has_restore_or_durable_surface = digest[
        "has_restore_or_durable_surface"
    ]
    if (
        _is_bool(restore_supported)
        and _is_bool(durable_writes)
        and _is_bool(has_restore_or_durable_surface)
    ):
        if has_restore_or_durable_surface != (
            restore_supported or durable_writes
        ):
            return True

    contract_ready = digest["contract_ready"]
    contract_failure_count = digest["contract_failure_count"]
    comparison_ok = digest["comparison_ok"]
    comparison_failure_count = digest["comparison_failure_count"]
    has_contract_failure = digest["has_contract_failure"]
    if (
        _is_bool(contract_ready)
        and _is_int(contract_failure_count)
        and _is_bool(comparison_ok)
        and _is_int(comparison_failure_count)
        and _is_bool(has_contract_failure)
    ):
        if has_contract_failure != (
            contract_ready is False
            or contract_failure_count > 0
            or comparison_ok is False
            or comparison_failure_count > 0
        ):
            return True

    comparison_changed = digest["comparison_changed"]
    comparison_change_count = digest["comparison_change_count"]
    has_drift = digest["has_drift"]
    if (
        (comparison_changed is None or _is_bool(comparison_changed))
        and _is_int(comparison_change_count)
        and _is_bool(has_drift)
    ):
        if has_drift != (
            comparison_changed is True or comparison_change_count > 0
        ):
            return True

    return False
