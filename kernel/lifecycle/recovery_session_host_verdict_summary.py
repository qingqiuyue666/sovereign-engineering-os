"""Read-only summary for rendered RecoverySessionHost verdict aggregation."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping


_AGGREGATION_KEYS = {"ok", "reason_code", "failures", "summary"}
_REQUIRED_SUMMARY_KEYS = {
    "total_payloads",
    "accepted_payloads",
    "rejected_payloads",
    "payload_type_counts",
    "factory",
    "recovery",
    "readiness",
    "smoke",
    "restore_surface",
    "durable_writes",
    "payload_errors",
}


@dataclass(frozen=True)
class RecoverySessionHostVerdictSummary:
    ok: bool
    reason_code: str
    failures: tuple[str, ...]
    digest: dict[str, object]


def build_recovery_session_host_verdict_summary(
    rendered_aggregation: Mapping[str, object],
) -> RecoverySessionHostVerdictSummary:
    if not isinstance(rendered_aggregation, Mapping):
        return _invalid_summary(("aggregation_not_mapping",))

    if set(rendered_aggregation) != _AGGREGATION_KEYS:
        return _invalid_summary(("aggregation_shape_mismatch",))

    aggregation_ok = rendered_aggregation["ok"]
    aggregation_reason_code = rendered_aggregation["reason_code"]
    aggregation_failures = rendered_aggregation["failures"]
    aggregation_summary = rendered_aggregation["summary"]

    if not isinstance(aggregation_ok, bool) or not isinstance(
        aggregation_reason_code, str
    ):
        return _invalid_summary(("aggregation_shape_mismatch",))

    if not _is_string_list(aggregation_failures):
        return _invalid_summary(("aggregation_failures_invalid",))

    if not isinstance(aggregation_summary, dict):
        return _invalid_summary(("aggregation_summary_invalid",))

    if not _REQUIRED_SUMMARY_KEYS.issubset(set(aggregation_summary)):
        return _invalid_summary(("aggregation_summary_shape_mismatch",))

    digest = _build_digest(
        aggregation_ok=aggregation_ok,
        aggregation_reason_code=aggregation_reason_code,
        aggregation_failures=aggregation_failures,
        aggregation_summary=aggregation_summary,
    )
    if digest is None:
        return _invalid_summary(("aggregation_summary_shape_mismatch",))

    return RecoverySessionHostVerdictSummary(
        ok=True,
        reason_code="ok",
        failures=(),
        digest=digest,
    )


def render_recovery_session_host_verdict_summary(
    summary: RecoverySessionHostVerdictSummary,
) -> dict[str, object]:
    return {
        "ok": summary.ok,
        "reason_code": summary.reason_code,
        "failures": list(summary.failures),
        "digest": deepcopy(summary.digest),
    }


def _invalid_summary(
    failures: tuple[str, ...],
) -> RecoverySessionHostVerdictSummary:
    return RecoverySessionHostVerdictSummary(
        ok=False,
        reason_code="invalid_aggregation",
        failures=failures,
        digest={
            "aggregation_ok": False,
            "aggregation_reason_code": "invalid_aggregation",
            "aggregation_failures": list(failures),
            "operator_safe": False,
        },
    )


def _build_digest(
    *,
    aggregation_ok: bool,
    aggregation_reason_code: str,
    aggregation_failures: list[object],
    aggregation_summary: dict[str, object],
) -> dict[str, object] | None:
    total_payloads = _int_value(aggregation_summary, "total_payloads")
    accepted_payloads = _int_value(aggregation_summary, "accepted_payloads")
    rejected_payloads = _int_value(aggregation_summary, "rejected_payloads")
    if (
        total_payloads is None
        or accepted_payloads is None
        or rejected_payloads is None
    ):
        return None

    payload_type_counts = _sorted_count_dict(
        aggregation_summary["payload_type_counts"]
    )
    factory = _dict_value(aggregation_summary, "factory")
    recovery = _dict_value(aggregation_summary, "recovery")
    readiness = _dict_value(aggregation_summary, "readiness")
    smoke = _dict_value(aggregation_summary, "smoke")
    restore_surface = _dict_value(aggregation_summary, "restore_surface")
    durable_writes = _dict_value(aggregation_summary, "durable_writes")
    if (
        payload_type_counts is None
        or factory is None
        or recovery is None
        or readiness is None
        or smoke is None
        or restore_surface is None
        or durable_writes is None
    ):
        return None

    factory_failed = _int_value(factory, "failed")
    readiness_ready_false = _int_value(readiness, "ready_false")
    smoke_passed_false = _int_value(smoke, "passed_false")
    restore_supported_true = _int_value(
        restore_surface, "restore_supported_true"
    )
    restore_command_present = _int_value(
        restore_surface, "restore_command_present"
    )
    durable_writes_true = _int_value(durable_writes, "durable_writes_true")
    factory_failure_reason_counts = _sorted_count_dict(
        factory.get("reason_code_counts")
    )
    recovery_class_counts = _sorted_count_dict(recovery.get("class_counts"))
    readiness_failure_counts = _sorted_count_dict(
        readiness.get("failure_counts")
    )
    smoke_failure_counts = _sorted_count_dict(smoke.get("failure_counts"))
    payload_error_reason_counts = _payload_error_reason_counts(
        aggregation_summary["payload_errors"]
    )
    if (
        factory_failed is None
        or readiness_ready_false is None
        or smoke_passed_false is None
        or restore_supported_true is None
        or restore_command_present is None
        or durable_writes_true is None
        or factory_failure_reason_counts is None
        or recovery_class_counts is None
        or readiness_failure_counts is None
        or smoke_failure_counts is None
        or payload_error_reason_counts is None
    ):
        return None

    has_restore_surface = (
        restore_supported_true > 0 or restore_command_present > 0
    )
    has_durable_writes = durable_writes_true > 0
    has_payload_errors = (
        rejected_payloads > 0 or len(payload_error_reason_counts) > 0
    )
    operator_safe = (
        aggregation_ok is True
        and rejected_payloads == 0
        and restore_supported_true == 0
        and restore_command_present == 0
        and durable_writes_true == 0
        and readiness_ready_false == 0
        and smoke_passed_false == 0
    )

    return {
        "aggregation_ok": aggregation_ok,
        "aggregation_reason_code": aggregation_reason_code,
        "aggregation_failures": list(aggregation_failures),
        "total_payloads": total_payloads,
        "accepted_payloads": accepted_payloads,
        "rejected_payloads": rejected_payloads,
        "payload_type_counts": payload_type_counts,
        "factory_failed": factory_failed,
        "factory_failure_reason_counts": factory_failure_reason_counts,
        "recovery_class_counts": recovery_class_counts,
        "readiness_ready_false": readiness_ready_false,
        "readiness_failure_counts": readiness_failure_counts,
        "smoke_passed_false": smoke_passed_false,
        "smoke_failure_counts": smoke_failure_counts,
        "restore_supported_true": restore_supported_true,
        "restore_command_present": restore_command_present,
        "durable_writes_true": durable_writes_true,
        "payload_error_reason_counts": payload_error_reason_counts,
        "has_restore_surface": has_restore_surface,
        "has_durable_writes": has_durable_writes,
        "has_payload_errors": has_payload_errors,
        "operator_safe": operator_safe,
    }


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def _dict_value(
    source: dict[str, object], key: str
) -> dict[str, object] | None:
    value = source.get(key)
    if not isinstance(value, dict):
        return None
    return value


def _int_value(source: dict[str, object], key: str) -> int | None:
    value = source.get(key)
    if type(value) is not int:
        return None
    return value


def _sorted_count_dict(value: object) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None

    counts: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or type(count) is not int:
            return None
        counts[key] = count
    return {key: counts[key] for key in sorted(counts)}


def _payload_error_reason_counts(value: object) -> dict[str, int] | None:
    if not isinstance(value, list):
        return None

    counts: dict[str, int] = {}
    for item in value:
        if not isinstance(item, dict):
            return None
        reason_code = item.get("reason_code")
        if not isinstance(reason_code, str):
            return None
        counts[reason_code] = counts.get(reason_code, 0) + 1
    return {key: counts[key] for key in sorted(counts)}
