"""Read-only aggregation for RecoverySessionHost operator payloads."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping, Sequence


FACTORY_CHECK_KEYS = frozenset({"command", "factory"})
EVALUATE_KEYS = frozenset(
    {"command", "factory", "host_state", "recovery"}
)
READINESS_KEYS = frozenset(
    {"ready", "reason_code", "failures", "manifest"}
)
SMOKE_KEYS = frozenset({"passed", "reason_code", "failures", "payload"})

PAYLOAD_TYPES = (
    "factory_check",
    "evaluate",
    "readiness",
    "smoke",
    "unknown",
)

RESTORE_COMMANDS = frozenset({"restore", "restore-dry-run"})

FAILURE_MESSAGES = {
    "payload_not_mapping": "payload must be a mapping",
    "unknown_payload_shape": "payload did not match a frozen operator shape",
    "payload_shape_mismatch": "payload keys or scalar values did not match",
    "factory_missing_or_invalid": "factory must be present as a dict",
    "recovery_invalid": "recovery must be a dict or None",
    "failures_invalid": "failures must be a list",
    "smoke_payload_invalid": "smoke payload must be a dict",
}


@dataclass(frozen=True)
class RecoverySessionHostVerdictAggregation:
    ok: bool
    reason_code: str
    failures: tuple[str, ...]
    summary: dict[str, object]


def aggregate_recovery_session_host_operator_verdicts(
    payloads: Sequence[Mapping[str, object]],
) -> RecoverySessionHostVerdictAggregation:
    payload_type_counts = {payload_type: 0 for payload_type in PAYLOAD_TYPES}
    factory_reason_counts: dict[str, int] = {}
    recovery_class_counts: dict[str, int] = {}
    recovery_reason_counts: dict[str, int] = {}
    readiness_reason_counts: dict[str, int] = {}
    readiness_failure_counts: dict[str, int] = {}
    smoke_reason_counts: dict[str, int] = {}
    smoke_failure_counts: dict[str, int] = {}
    payload_errors: list[dict[str, object]] = []
    failure_reasons: list[str] = []

    factory_ok = 0
    factory_failed = 0
    recovery_present = 0
    recovery_missing = 0
    recovery_restored_true = 0
    recovery_restored_false = 0
    readiness_ready_true = 0
    readiness_ready_false = 0
    smoke_passed_true = 0
    smoke_passed_false = 0
    restore_supported_true = 0
    restore_command_present = 0
    durable_writes_true = 0
    accepted_payloads = 0

    for index, payload in enumerate(payloads):
        if not isinstance(payload, Mapping):
            payload_type_counts["unknown"] += 1
            _record_rejection(
                index=index,
                reason_code="payload_not_mapping",
                failure_reasons=failure_reasons,
                payload_errors=payload_errors,
            )
            continue

        keys = frozenset(payload)
        command = payload.get("command")

        if command == "factory-check":
            payload_type_counts["factory_check"] += 1
            factory = payload.get("factory")
            if not isinstance(factory, dict):
                _record_rejection(
                    index=index,
                    reason_code="factory_missing_or_invalid",
                    failure_reasons=failure_reasons,
                    payload_errors=payload_errors,
                )
                continue
            if keys != FACTORY_CHECK_KEYS or not isinstance(
                factory.get("ok"), bool
            ):
                _record_rejection(
                    index=index,
                    reason_code="payload_shape_mismatch",
                    failure_reasons=failure_reasons,
                    payload_errors=payload_errors,
                )
                continue

            accepted_payloads += 1
            factory_ok, factory_failed = _aggregate_factory(
                factory=factory,
                factory_ok=factory_ok,
                factory_failed=factory_failed,
                reason_counts=factory_reason_counts,
            )
            continue

        if command == "evaluate":
            payload_type_counts["evaluate"] += 1
            factory = payload.get("factory")
            if not isinstance(factory, dict):
                _record_rejection(
                    index=index,
                    reason_code="factory_missing_or_invalid",
                    failure_reasons=failure_reasons,
                    payload_errors=payload_errors,
                )
                continue
            if keys != EVALUATE_KEYS or not isinstance(
                factory.get("ok"), bool
            ):
                _record_rejection(
                    index=index,
                    reason_code="payload_shape_mismatch",
                    failure_reasons=failure_reasons,
                    payload_errors=payload_errors,
                )
                continue

            recovery = payload.get("recovery")
            if recovery is not None and not isinstance(recovery, dict):
                _record_rejection(
                    index=index,
                    reason_code="recovery_invalid",
                    failure_reasons=failure_reasons,
                    payload_errors=payload_errors,
                )
                continue

            accepted_payloads += 1
            factory_ok, factory_failed = _aggregate_factory(
                factory=factory,
                factory_ok=factory_ok,
                factory_failed=factory_failed,
                reason_counts=factory_reason_counts,
            )
            if recovery is None:
                recovery_missing += 1
            else:
                recovery_present += 1
                recovery_restored_true, recovery_restored_false = (
                    _aggregate_recovery(
                        recovery=recovery,
                        class_counts=recovery_class_counts,
                        reason_counts=recovery_reason_counts,
                        restored_true=recovery_restored_true,
                        restored_false=recovery_restored_false,
                    )
                )
            continue

        if keys == READINESS_KEYS:
            payload_type_counts["readiness"] += 1
            failures = payload.get("failures")
            if not isinstance(failures, list):
                _record_rejection(
                    index=index,
                    reason_code="failures_invalid",
                    failure_reasons=failure_reasons,
                    payload_errors=payload_errors,
                )
                continue
            ready = payload.get("ready")
            reason_code = payload.get("reason_code")
            manifest = payload.get("manifest")
            if (
                not isinstance(ready, bool)
                or not isinstance(reason_code, str)
                or not isinstance(manifest, dict)
                or not _is_string_list(failures)
            ):
                _record_rejection(
                    index=index,
                    reason_code="payload_shape_mismatch",
                    failure_reasons=failure_reasons,
                    payload_errors=payload_errors,
                )
                continue

            accepted_payloads += 1
            if ready:
                readiness_ready_true += 1
            else:
                readiness_ready_false += 1
            _increment(readiness_reason_counts, reason_code)
            _aggregate_failure_strings(failures, readiness_failure_counts)
            restore_supported_true, restore_command_present, durable_writes_true = (
                _inspect_manifest(
                    manifest=manifest,
                    restore_supported_true=restore_supported_true,
                    restore_command_present=restore_command_present,
                    durable_writes_true=durable_writes_true,
                )
            )
            continue

        if keys == SMOKE_KEYS:
            payload_type_counts["smoke"] += 1
            failures = payload.get("failures")
            if not isinstance(failures, list):
                _record_rejection(
                    index=index,
                    reason_code="failures_invalid",
                    failure_reasons=failure_reasons,
                    payload_errors=payload_errors,
                )
                continue
            smoke_payload = payload.get("payload")
            if not isinstance(smoke_payload, dict):
                _record_rejection(
                    index=index,
                    reason_code="smoke_payload_invalid",
                    failure_reasons=failure_reasons,
                    payload_errors=payload_errors,
                )
                continue
            passed = payload.get("passed")
            reason_code = payload.get("reason_code")
            if (
                not isinstance(passed, bool)
                or not isinstance(reason_code, str)
                or not _is_string_list(failures)
            ):
                _record_rejection(
                    index=index,
                    reason_code="payload_shape_mismatch",
                    failure_reasons=failure_reasons,
                    payload_errors=payload_errors,
                )
                continue

            accepted_payloads += 1
            if passed:
                smoke_passed_true += 1
            else:
                smoke_passed_false += 1
            _increment(smoke_reason_counts, reason_code)
            _aggregate_failure_strings(failures, smoke_failure_counts)
            manifest = smoke_payload.get("manifest")
            if isinstance(manifest, dict):
                restore_supported_true, restore_command_present, durable_writes_true = (
                    _inspect_manifest(
                        manifest=manifest,
                        restore_supported_true=restore_supported_true,
                        restore_command_present=restore_command_present,
                        durable_writes_true=durable_writes_true,
                    )
                )
            continue

        payload_type_counts["unknown"] += 1
        _record_rejection(
            index=index,
            reason_code="unknown_payload_shape",
            failure_reasons=failure_reasons,
            payload_errors=payload_errors,
        )

    total_payloads = len(payloads)
    rejected_payloads = len(payload_errors)
    summary = {
        "total_payloads": total_payloads,
        "accepted_payloads": accepted_payloads,
        "rejected_payloads": rejected_payloads,
        "payload_type_counts": dict(payload_type_counts),
        "factory": {
            "ok": factory_ok,
            "failed": factory_failed,
            "reason_code_counts": _sorted_counts(factory_reason_counts),
        },
        "recovery": {
            "present": recovery_present,
            "missing": recovery_missing,
            "class_counts": _sorted_counts(recovery_class_counts),
            "reason_counts": _sorted_counts(recovery_reason_counts),
            "restored_true": recovery_restored_true,
            "restored_false": recovery_restored_false,
        },
        "readiness": {
            "ready_true": readiness_ready_true,
            "ready_false": readiness_ready_false,
            "reason_code_counts": _sorted_counts(readiness_reason_counts),
            "failure_counts": _sorted_counts(readiness_failure_counts),
        },
        "smoke": {
            "passed_true": smoke_passed_true,
            "passed_false": smoke_passed_false,
            "reason_code_counts": _sorted_counts(smoke_reason_counts),
            "failure_counts": _sorted_counts(smoke_failure_counts),
        },
        "restore_surface": {
            "restore_supported_true": restore_supported_true,
            "restore_command_present": restore_command_present,
        },
        "durable_writes": {
            "durable_writes_true": durable_writes_true,
        },
        "payload_errors": payload_errors,
    }

    if rejected_payloads:
        return RecoverySessionHostVerdictAggregation(
            ok=False,
            reason_code="invalid_payloads",
            failures=tuple(failure_reasons),
            summary=summary,
        )

    return RecoverySessionHostVerdictAggregation(
        ok=True,
        reason_code="ok",
        failures=(),
        summary=summary,
    )


def render_recovery_session_host_verdict_aggregation(
    aggregation: RecoverySessionHostVerdictAggregation,
) -> dict[str, object]:
    return {
        "ok": aggregation.ok,
        "reason_code": aggregation.reason_code,
        "failures": list(aggregation.failures),
        "summary": deepcopy(aggregation.summary),
    }


def _record_rejection(
    *,
    index: int,
    reason_code: str,
    failure_reasons: list[str],
    payload_errors: list[dict[str, object]],
) -> None:
    if reason_code not in failure_reasons:
        failure_reasons.append(reason_code)
    payload_errors.append(
        {
            "index": index,
            "reason_code": reason_code,
            "message": FAILURE_MESSAGES[reason_code],
        }
    )


def _aggregate_factory(
    *,
    factory: dict[str, object],
    factory_ok: int,
    factory_failed: int,
    reason_counts: dict[str, int],
) -> tuple[int, int]:
    if factory.get("ok") is True:
        return factory_ok + 1, factory_failed

    reason_code = factory.get("reason_code")
    if isinstance(reason_code, str):
        _increment(reason_counts, reason_code)
    return factory_ok, factory_failed + 1


def _aggregate_recovery(
    *,
    recovery: dict[str, object],
    class_counts: dict[str, int],
    reason_counts: dict[str, int],
    restored_true: int,
    restored_false: int,
) -> tuple[int, int]:
    recovery_class = recovery.get("recovery_class")
    if isinstance(recovery_class, str):
        _increment(class_counts, recovery_class)

    reason = recovery.get("reason")
    if isinstance(reason, str):
        _increment(reason_counts, reason)

    restored = recovery.get("restored")
    if restored is True:
        restored_true += 1
    elif restored is False:
        restored_false += 1

    return restored_true, restored_false


def _inspect_manifest(
    *,
    manifest: dict[str, object],
    restore_supported_true: int,
    restore_command_present: int,
    durable_writes_true: int,
) -> tuple[int, int, int]:
    if manifest.get("restore_supported") is True:
        restore_supported_true += 1

    commands = manifest.get("commands")
    if isinstance(commands, list) and any(
        command in RESTORE_COMMANDS for command in commands
    ):
        restore_command_present += 1

    if manifest.get("durable_writes") is True:
        durable_writes_true += 1

    return (
        restore_supported_true,
        restore_command_present,
        durable_writes_true,
    )


def _aggregate_failure_strings(
    failures: list[object], failure_counts: dict[str, int]
) -> None:
    for failure in failures:
        if isinstance(failure, str):
            _increment(failure_counts, failure)


def _increment(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def _is_string_list(values: list[object]) -> bool:
    return all(isinstance(value, str) for value in values)


def _sorted_counts(counts: dict[str, int]) -> dict[str, int]:
    return {key: counts[key] for key in sorted(counts)}
