"""Read-only contract check over rendered approval/review envelopes.

This module accepts only an already-rendered approval/review readiness
envelope payload and emits a bounded structural and consistency verdict.
It does not call upstream builders, data stores, operator commands, or
approval/review mutation paths.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass


_SURFACE = "approval_review_readiness_contract"
_VERSION = 1
_INPUT_SHAPE = "rendered_approval_review_readiness_envelope"
_ENVELOPE_SURFACE = "approval_review_readiness"
_ENVELOPE_VERSION = 1

_REASON_CODE_INVALID = "invalid_approval_review_envelope"
_REASON_CODE_NOT_READY = "not_ready"
_REASON_CODE_READY = "ready"
_REASON_CODES: tuple[str, ...] = (
    _REASON_CODE_INVALID,
    _REASON_CODE_NOT_READY,
    _REASON_CODE_READY,
)

_UPSTREAM_REASON_CODE_INVALID = "invalid_approval_review"
_UPSTREAM_REASON_CODE_NOT_READY = "not_ready"
_UPSTREAM_REASON_CODE_READY = "ready"

_FAILURE_PAYLOAD_NOT_MAPPING = "payload_not_mapping"
_FAILURE_PAYLOAD_SHAPE_MISMATCH = "payload_shape_mismatch"
_FAILURE_PAYLOAD_FAILURES_INVALID = "payload_failures_invalid"
_FAILURE_ENVELOPE_INVALID = "envelope_invalid"
_FAILURE_ENVELOPE_SHAPE_MISMATCH = "envelope_shape_mismatch"
_FAILURE_ENVELOPE_COUNTER_INVALID = "envelope_counter_invalid"
_FAILURE_ENVELOPE_BOOL_INVALID = "envelope_bool_invalid"
_FAILURE_ENVELOPE_LIST_INVALID = "envelope_list_invalid"
_FAILURE_ENVELOPE_MAPPING_INVALID = "envelope_mapping_invalid"
_FAILURE_STATUS_INCONSISTENT = "status_inconsistent"
_FAILURE_SAFETY_INCONSISTENT = "safety_inconsistent"
_FAILURE_OPERATOR_NOT_SAFE = "operator_not_safe"

_FAILURE_VALUES: tuple[str, ...] = (
    _FAILURE_PAYLOAD_NOT_MAPPING,
    _FAILURE_PAYLOAD_SHAPE_MISMATCH,
    _FAILURE_PAYLOAD_FAILURES_INVALID,
    _FAILURE_ENVELOPE_INVALID,
    _FAILURE_ENVELOPE_SHAPE_MISMATCH,
    _FAILURE_ENVELOPE_COUNTER_INVALID,
    _FAILURE_ENVELOPE_BOOL_INVALID,
    _FAILURE_ENVELOPE_LIST_INVALID,
    _FAILURE_ENVELOPE_MAPPING_INVALID,
    _FAILURE_STATUS_INCONSISTENT,
    _FAILURE_SAFETY_INCONSISTENT,
    _FAILURE_OPERATOR_NOT_SAFE,
)

_STRUCTURAL_FAILURES: frozenset[str] = frozenset(
    {
        _FAILURE_PAYLOAD_NOT_MAPPING,
        _FAILURE_PAYLOAD_SHAPE_MISMATCH,
        _FAILURE_PAYLOAD_FAILURES_INVALID,
        _FAILURE_ENVELOPE_INVALID,
        _FAILURE_ENVELOPE_SHAPE_MISMATCH,
        _FAILURE_ENVELOPE_COUNTER_INVALID,
        _FAILURE_ENVELOPE_BOOL_INVALID,
        _FAILURE_ENVELOPE_LIST_INVALID,
        _FAILURE_ENVELOPE_MAPPING_INVALID,
        _FAILURE_STATUS_INCONSISTENT,
        _FAILURE_SAFETY_INCONSISTENT,
    }
)

_TOP_LEVEL_KEYS = {"ready", "reason_code", "failures", "envelope"}
_REQUIRED_ENVELOPE_KEYS = {
    "surface",
    "version",
    "item_count",
    "unique_task_count",
    "task_ids",
    "record_type_counts",
    "approval_state_counts",
    "review_state_counts",
    "revision_id_count",
    "seal_id_count",
    "missing_review_state_count",
    "missing_revision_or_seal_count",
    "operator_safe",
    "restore_supported",
    "durable_writes",
    "cli_command_count",
    "runtime_dependency_count",
    "json_safe",
}
_COUNTER_FIELDS = (
    "version",
    "item_count",
    "unique_task_count",
    "revision_id_count",
    "seal_id_count",
    "missing_review_state_count",
    "missing_revision_or_seal_count",
    "cli_command_count",
    "runtime_dependency_count",
)
_BOOL_FIELDS = (
    "operator_safe",
    "restore_supported",
    "durable_writes",
    "json_safe",
)
_LIST_FIELDS = ("task_ids",)
_MAPPING_FIELDS = (
    "record_type_counts",
    "approval_state_counts",
    "review_state_counts",
)


@dataclass(frozen=True)
class ApprovalReviewReadinessContractCheck:
    """Frozen verdict over a rendered approval/review readiness envelope."""

    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    contract: dict[str, object]


def _build_manifest() -> dict[str, object]:
    return {
        "surface": _SURFACE,
        "version": _VERSION,
        "input_shape": _INPUT_SHAPE,
        "restore_supported": False,
        "durable_writes": False,
        "cli_commands": [],
        "runtime_dependencies": [],
        "json_safe": True,
        "reason_codes": list(_REASON_CODES),
        "failure_values": list(_FAILURE_VALUES),
    }


_MANIFEST = _build_manifest()


def approval_review_readiness_contract_manifest() -> dict[str, object]:
    """Return a defensive JSON-safe manifest for this contract surface."""

    return deepcopy(_MANIFEST)


def check_approval_review_readiness_contract(
    rendered_envelope: object,
) -> ApprovalReviewReadinessContractCheck:
    """Validate a rendered approval/review envelope without upstream calls."""

    contract = approval_review_readiness_contract_manifest()
    failures = _validate_rendered_envelope(rendered_envelope)

    structural_failures = [
        failure for failure in failures if failure in _STRUCTURAL_FAILURES
    ]
    if structural_failures:
        return ApprovalReviewReadinessContractCheck(
            ready=False,
            reason_code=_REASON_CODE_INVALID,
            failures=tuple(structural_failures),
            contract=contract,
        )

    if _envelope_operator_safe(rendered_envelope):
        return ApprovalReviewReadinessContractCheck(
            ready=True,
            reason_code=_REASON_CODE_READY,
            failures=(),
            contract=contract,
        )

    return ApprovalReviewReadinessContractCheck(
        ready=False,
        reason_code=_REASON_CODE_NOT_READY,
        failures=(_FAILURE_OPERATOR_NOT_SAFE,),
        contract=contract,
    )


def render_approval_review_readiness_contract_check(
    check: ApprovalReviewReadinessContractCheck,
) -> dict[str, object]:
    """Render a contract check to a defensive JSON-safe payload."""

    return {
        "ready": bool(check.ready),
        "reason_code": str(check.reason_code),
        "failures": list(check.failures),
        "contract": deepcopy(check.contract),
    }


def _validate_rendered_envelope(rendered_envelope: object) -> list[str]:
    failure_set: set[str] = set()

    if not isinstance(rendered_envelope, Mapping):
        return [_FAILURE_PAYLOAD_NOT_MAPPING]

    top_level_shape_valid = set(rendered_envelope.keys()) == _TOP_LEVEL_KEYS
    ready = rendered_envelope.get("ready")
    reason_code = rendered_envelope.get("reason_code")
    payload_failures = rendered_envelope.get("failures")
    envelope = rendered_envelope.get("envelope")

    ready_valid = type(ready) is bool
    reason_code_valid = isinstance(reason_code, str)
    if not top_level_shape_valid or not ready_valid or not reason_code_valid:
        failure_set.add(_FAILURE_PAYLOAD_SHAPE_MISMATCH)

    payload_failures_valid = _is_string_list(payload_failures)
    if not payload_failures_valid:
        failure_set.add(_FAILURE_PAYLOAD_FAILURES_INVALID)

    if type(envelope) is not dict:
        failure_set.add(_FAILURE_ENVELOPE_INVALID)
        return _ordered_failures(failure_set)

    if not _REQUIRED_ENVELOPE_KEYS.issubset(set(envelope.keys())):
        failure_set.add(_FAILURE_ENVELOPE_SHAPE_MISMATCH)
        return _ordered_failures(failure_set)

    counter_valid = _has_valid_counter_fields(envelope)
    bool_valid = _has_valid_bool_fields(envelope)
    list_valid = _has_valid_list_fields(envelope)
    mapping_valid = _has_valid_mapping_fields(envelope)

    if not counter_valid:
        failure_set.add(_FAILURE_ENVELOPE_COUNTER_INVALID)
    if not bool_valid:
        failure_set.add(_FAILURE_ENVELOPE_BOOL_INVALID)
    if not list_valid:
        failure_set.add(_FAILURE_ENVELOPE_LIST_INVALID)
    if not mapping_valid:
        failure_set.add(_FAILURE_ENVELOPE_MAPPING_INVALID)

    if counter_valid and bool_valid and not _envelope_constants_valid(envelope):
        failure_set.add(_FAILURE_SAFETY_INCONSISTENT)

    if counter_valid and list_valid and not _task_counts_are_consistent(envelope):
        failure_set.add(_FAILURE_SAFETY_INCONSISTENT)

    if (
        payload_failures_valid
        and counter_valid
        and mapping_valid
        and not _record_counts_are_consistent(envelope, payload_failures)
    ):
        failure_set.add(_FAILURE_SAFETY_INCONSISTENT)

    if (
        payload_failures_valid
        and counter_valid
        and bool_valid
        and list_valid
        and not _operator_safe_is_consistent(envelope, payload_failures)
    ):
        failure_set.add(_FAILURE_SAFETY_INCONSISTENT)

    if (
        ready_valid
        and reason_code_valid
        and payload_failures_valid
        and counter_valid
        and bool_valid
        and list_valid
        and not _status_is_consistent(
            ready=ready,
            reason_code=reason_code,
            payload_failures=payload_failures,
            envelope=envelope,
        )
    ):
        failure_set.add(_FAILURE_STATUS_INCONSISTENT)

    if (
        counter_valid
        and bool_valid
        and envelope.get("operator_safe") is False
        and _FAILURE_STATUS_INCONSISTENT not in failure_set
        and _FAILURE_SAFETY_INCONSISTENT not in failure_set
    ):
        failure_set.add(_FAILURE_OPERATOR_NOT_SAFE)

    return _ordered_failures(failure_set)


def _envelope_constants_valid(envelope: Mapping[str, object]) -> bool:
    return (
        envelope.get("surface") == _ENVELOPE_SURFACE
        and envelope.get("version") == _ENVELOPE_VERSION
        and envelope.get("restore_supported") is False
        and envelope.get("durable_writes") is False
        and envelope.get("cli_command_count") == 0
        and envelope.get("runtime_dependency_count") == 0
        and envelope.get("json_safe") is True
    )


def _has_valid_counter_fields(envelope: Mapping[str, object]) -> bool:
    return all(
        _is_non_negative_int(envelope.get(field)) for field in _COUNTER_FIELDS
    )


def _has_valid_bool_fields(envelope: Mapping[str, object]) -> bool:
    return all(type(envelope.get(field)) is bool for field in _BOOL_FIELDS)


def _has_valid_list_fields(envelope: Mapping[str, object]) -> bool:
    return all(_is_string_list(envelope.get(field)) for field in _LIST_FIELDS)


def _has_valid_mapping_fields(envelope: Mapping[str, object]) -> bool:
    return all(
        _is_string_int_mapping(envelope.get(field))
        for field in _MAPPING_FIELDS
    )


def _task_counts_are_consistent(envelope: Mapping[str, object]) -> bool:
    return envelope["unique_task_count"] == len(envelope["task_ids"])


def _record_counts_are_consistent(
    envelope: Mapping[str, object],
    payload_failures: object,
) -> bool:
    item_count = envelope["item_count"]
    counts_are_bounded = (
        _mapping_sum(envelope["record_type_counts"]) <= item_count
        and _mapping_sum(envelope["approval_state_counts"]) <= item_count
        and _mapping_sum(envelope["review_state_counts"]) <= item_count
        and envelope["revision_id_count"] <= item_count
        and envelope["seal_id_count"] <= item_count
        and envelope["missing_review_state_count"] <= item_count
        and envelope["missing_revision_or_seal_count"] <= item_count
    )
    if not counts_are_bounded:
        return False
    if payload_failures != []:
        return True
    return (
        _mapping_sum(envelope["record_type_counts"]) == item_count
        and _mapping_sum(envelope["review_state_counts"]) == item_count
        and envelope["revision_id_count"] + envelope["seal_id_count"] >= item_count
    )


def _operator_safe_is_consistent(
    envelope: Mapping[str, object],
    payload_failures: object,
) -> bool:
    expected_safe = (
        payload_failures == []
        and envelope["item_count"] > 0
        and envelope["unique_task_count"] == 1
        and envelope["missing_review_state_count"] == 0
        and envelope["missing_revision_or_seal_count"] == 0
    )
    return envelope["operator_safe"] is expected_safe


def _status_is_consistent(
    *,
    ready: object,
    reason_code: object,
    payload_failures: object,
    envelope: Mapping[str, object],
) -> bool:
    if ready is True:
        return (
            reason_code == _UPSTREAM_REASON_CODE_READY
            and payload_failures == []
            and envelope["operator_safe"] is True
            and envelope["item_count"] > 0
            and envelope["unique_task_count"] == 1
            and envelope["missing_review_state_count"] == 0
            and envelope["missing_revision_or_seal_count"] == 0
        )

    if reason_code == _UPSTREAM_REASON_CODE_INVALID:
        return payload_failures != [] and envelope["operator_safe"] is False

    if reason_code == _UPSTREAM_REASON_CODE_NOT_READY:
        return payload_failures != [] and envelope["operator_safe"] is False

    return False


def _envelope_operator_safe(rendered_envelope: object) -> bool:
    if not isinstance(rendered_envelope, Mapping):
        return False
    envelope = rendered_envelope.get("envelope")
    if type(envelope) is not dict:
        return False
    return envelope.get("operator_safe") is True


def _is_non_negative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _is_string_list(value: object) -> bool:
    return type(value) is list and all(isinstance(item, str) for item in value)


def _is_string_int_mapping(value: object) -> bool:
    return type(value) is dict and all(
        isinstance(key, str) and _is_non_negative_int(count)
        for key, count in value.items()
    )


def _mapping_sum(value: object) -> int:
    if type(value) is not dict:
        return 0
    return sum(value.values())


def _ordered_failures(failures: set[str]) -> list[str]:
    return [failure for failure in _FAILURE_VALUES if failure in failures]


__all__ = [
    "ApprovalReviewReadinessContractCheck",
    "approval_review_readiness_contract_manifest",
    "check_approval_review_readiness_contract",
    "render_approval_review_readiness_contract_check",
]
