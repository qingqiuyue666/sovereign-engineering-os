"""Read-only contract manifest for rendered RecoverySessionHost summaries."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping


_TOP_LEVEL_KEYS = ["digest", "failures", "ok", "reason_code"]
_DIGEST_KEYS = [
    "accepted_payloads",
    "aggregation_failures",
    "aggregation_ok",
    "aggregation_reason_code",
    "durable_writes_true",
    "factory_failed",
    "factory_failure_reason_counts",
    "has_durable_writes",
    "has_payload_errors",
    "has_restore_surface",
    "operator_safe",
    "payload_error_reason_counts",
    "payload_type_counts",
    "readiness_failure_counts",
    "readiness_ready_false",
    "recovery_class_counts",
    "rejected_payloads",
    "restore_command_present",
    "restore_supported_true",
    "smoke_failure_counts",
    "smoke_passed_false",
    "total_payloads",
]
_FAILURE_VALUES = [
    "aggregation_failures_invalid",
    "aggregation_not_mapping",
    "aggregation_shape_mismatch",
    "aggregation_summary_invalid",
    "aggregation_summary_shape_mismatch",
]
_REASON_CODES = ["invalid_aggregation", "ok"]
_OPERATOR_SAFE_REQUIRES = {
    "aggregation_ok": True,
    "rejected_payloads": 0,
    "restore_supported_true": 0,
    "restore_command_present": 0,
    "durable_writes_true": 0,
    "readiness_ready_false": 0,
    "smoke_passed_false": 0,
}
_MANIFEST = {
    "surface": "recovery_session_host_verdict_summary",
    "version": 1,
    "input_shape": "rendered_summary",
    "top_level_keys": _TOP_LEVEL_KEYS,
    "digest_keys": _DIGEST_KEYS,
    "failure_values": _FAILURE_VALUES,
    "reason_codes": _REASON_CODES,
    "operator_safe_requires": _OPERATOR_SAFE_REQUIRES,
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
}
_COUNTER_KEYS = [
    "total_payloads",
    "accepted_payloads",
    "rejected_payloads",
    "factory_failed",
    "readiness_ready_false",
    "smoke_passed_false",
    "restore_supported_true",
    "restore_command_present",
    "durable_writes_true",
]
_BOOL_KEYS = [
    "aggregation_ok",
    "has_restore_surface",
    "has_durable_writes",
    "has_payload_errors",
    "operator_safe",
]
_STRING_KEYS = ["aggregation_reason_code"]
_LIST_KEYS = ["aggregation_failures"]
_COUNT_DICT_KEYS = [
    "payload_type_counts",
    "factory_failure_reason_counts",
    "recovery_class_counts",
    "readiness_failure_counts",
    "smoke_failure_counts",
    "payload_error_reason_counts",
]


@dataclass(frozen=True)
class RecoverySessionHostVerdictSummaryContractCheck:
    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    manifest: dict[str, object]


def recovery_session_host_verdict_summary_contract_manifest() -> dict[
    str, object
]:
    return deepcopy(_MANIFEST)


def check_recovery_session_host_verdict_summary_contract(
    rendered_summary: Mapping[str, object],
) -> RecoverySessionHostVerdictSummaryContractCheck:
    manifest = recovery_session_host_verdict_summary_contract_manifest()
    failures: list[str] = []

    if not isinstance(rendered_summary, Mapping):
        failures.append("summary_not_mapping")
        return _contract_check(failures, manifest)

    top_level_shape_valid = set(rendered_summary) == set(_TOP_LEVEL_KEYS)
    if not top_level_shape_valid:
        failures.append("summary_shape_mismatch")

    ok = rendered_summary.get("ok")
    ok_valid = isinstance(ok, bool)
    if not ok_valid and "summary_shape_mismatch" not in failures:
        failures.append("summary_shape_mismatch")

    reason_code = rendered_summary.get("reason_code")
    reason_code_valid = (
        isinstance(reason_code, str) and reason_code in _REASON_CODES
    )
    if not reason_code_valid:
        failures.append("reason_code_invalid")

    summary_failures = rendered_summary.get("failures")
    failures_valid = _is_string_list(summary_failures)
    if not failures_valid:
        failures.append("failures_invalid")
    elif any(item not in _FAILURE_VALUES for item in summary_failures):
        failures.append("failure_value_unknown")

    digest = rendered_summary.get("digest")
    digest_valid = isinstance(digest, dict)
    if not digest_valid:
        failures.append("digest_invalid")
        return _contract_check(failures, manifest)

    digest_shape_valid = set(digest) == set(_DIGEST_KEYS)
    if not digest_shape_valid:
        failures.append("digest_shape_mismatch")

    if digest_shape_valid:
        if not _has_valid_counters(digest):
            failures.append("digest_counter_invalid")

        if not _has_valid_bool_fields(digest):
            failures.append("digest_bool_invalid")

        if not _has_valid_string_fields(digest):
            failures.append("digest_string_invalid")

        if not _has_valid_list_fields(digest):
            failures.append("digest_list_invalid")

        if not _has_valid_count_dict_fields(digest):
            failures.append("digest_count_dict_invalid")

        if not _operator_safe_is_consistent(digest):
            failures.append("operator_safe_inconsistent")

        if (
            _is_int_counter(digest["restore_supported_true"])
            and digest["restore_supported_true"] > 0
        ) or (
            _is_int_counter(digest["restore_command_present"])
            and digest["restore_command_present"] > 0
        ):
            failures.append("restore_surface_present")

        if (
            _is_int_counter(digest["durable_writes_true"])
            and digest["durable_writes_true"] > 0
        ):
            failures.append("durable_writes_present")

    if (
        ok_valid
        and reason_code_valid
        and failures_valid
        and not _summary_status_is_consistent(
            ok=ok,
            reason_code=reason_code,
            failures=summary_failures,
        )
    ):
        failures.append("summary_status_inconsistent")

    return _contract_check(failures, manifest)


def render_recovery_session_host_verdict_summary_contract_check(
    check: RecoverySessionHostVerdictSummaryContractCheck,
) -> dict[str, object]:
    return {
        "ready": check.ready,
        "reason_code": check.reason_code,
        "failures": list(check.failures),
        "manifest": deepcopy(check.manifest),
    }


def _contract_check(
    failures: list[str],
    manifest: dict[str, object],
) -> RecoverySessionHostVerdictSummaryContractCheck:
    if failures:
        return RecoverySessionHostVerdictSummaryContractCheck(
            ready=False,
            reason_code="not_ready",
            failures=tuple(failures),
            manifest=manifest,
        )
    return RecoverySessionHostVerdictSummaryContractCheck(
        ready=True,
        reason_code="ready",
        failures=(),
        manifest=manifest,
    )


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def _is_int_counter(value: object) -> bool:
    return type(value) is int


def _has_valid_counters(digest: dict[str, object]) -> bool:
    return all(_is_int_counter(digest[key]) for key in _COUNTER_KEYS)


def _has_valid_bool_fields(digest: dict[str, object]) -> bool:
    return all(isinstance(digest[key], bool) for key in _BOOL_KEYS)


def _has_valid_string_fields(digest: dict[str, object]) -> bool:
    return all(isinstance(digest[key], str) for key in _STRING_KEYS)


def _has_valid_list_fields(digest: dict[str, object]) -> bool:
    return all(_is_string_list(digest[key]) for key in _LIST_KEYS)


def _has_valid_count_dict_fields(digest: dict[str, object]) -> bool:
    return all(_is_sorted_count_dict(digest[key]) for key in _COUNT_DICT_KEYS)


def _is_sorted_count_dict(value: object) -> bool:
    if not isinstance(value, dict):
        return False

    if not all(isinstance(key, str) for key in value):
        return False

    keys = list(value)
    if keys != sorted(keys):
        return False

    return all(_is_int_counter(count) for count in value.values())


def _operator_safe_is_consistent(digest: dict[str, object]) -> bool:
    operator_safe = digest["operator_safe"]
    if not isinstance(operator_safe, bool):
        return False
    if operator_safe is not True:
        return True

    return all(
        digest[key] == expected
        for key, expected in _OPERATOR_SAFE_REQUIRES.items()
    )


def _summary_status_is_consistent(
    *,
    ok: object,
    reason_code: object,
    failures: object,
) -> bool:
    if ok is True:
        return reason_code == "ok" and failures == []
    return reason_code == "invalid_aggregation" and failures != []
