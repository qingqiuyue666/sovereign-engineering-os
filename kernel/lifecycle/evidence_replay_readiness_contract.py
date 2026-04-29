"""Read-only contract check over rendered P2-01 evidence/replay envelopes.

This module accepts only an already-rendered P2-01 evidence replay
readiness envelope payload and emits a bounded structural and consistency
verdict. It does not open data stores, invoke repositories, call CLI
code, or trigger recovery behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass


_SURFACE = "evidence_replay_readiness_contract"
_VERSION = 1
_INPUT_SHAPE = "rendered_evidence_replay_readiness_envelope"
_ENVELOPE_SURFACE = "evidence_replay_readiness"

_REASON_CODE_INVALID = "invalid_evidence_replay_envelope"
_REASON_CODE_NOT_READY = "not_ready"
_REASON_CODE_READY = "ready"
_REASON_CODES: tuple[str, ...] = (
    _REASON_CODE_INVALID,
    _REASON_CODE_NOT_READY,
    _REASON_CODE_READY,
)

_P2_01_REASON_CODE_INVALID = "invalid_evidence_replay"
_P2_01_REASON_CODE_NOT_READY = "not_ready"
_P2_01_REASON_CODE_READY = "ready"

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
    "stage_counts",
    "artifact_ref_count",
    "missing_artifact_ref_count",
    "duplicate_artifact_refs",
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
    "artifact_ref_count",
    "missing_artifact_ref_count",
    "cli_command_count",
    "runtime_dependency_count",
)
_BOOL_FIELDS = (
    "operator_safe",
    "restore_supported",
    "durable_writes",
    "json_safe",
)
_LIST_FIELDS = ("task_ids", "duplicate_artifact_refs")
_MAPPING_FIELDS = ("record_type_counts", "stage_counts")


@dataclass(frozen=True)
class EvidenceReplayReadinessContractCheck:
    """Frozen verdict over a rendered P2-01 evidence/replay envelope."""

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


def evidence_replay_readiness_contract_manifest() -> dict[str, object]:
    """Return a defensive JSON-safe manifest for the contract surface."""

    return deepcopy(_MANIFEST)


def check_evidence_replay_readiness_contract(
    rendered_envelope: object,
) -> EvidenceReplayReadinessContractCheck:
    """Validate a rendered P2-01 envelope without upstream calls."""

    contract = evidence_replay_readiness_contract_manifest()
    failures = _validate_rendered_envelope(rendered_envelope)

    structural_failures = [
        failure for failure in failures if failure in _STRUCTURAL_FAILURES
    ]
    if structural_failures:
        return EvidenceReplayReadinessContractCheck(
            ready=False,
            reason_code=_REASON_CODE_INVALID,
            failures=tuple(structural_failures),
            contract=contract,
        )

    if _envelope_operator_safe(rendered_envelope):
        return EvidenceReplayReadinessContractCheck(
            ready=True,
            reason_code=_REASON_CODE_READY,
            failures=(),
            contract=contract,
        )

    return EvidenceReplayReadinessContractCheck(
        ready=False,
        reason_code=_REASON_CODE_NOT_READY,
        failures=(_FAILURE_OPERATOR_NOT_SAFE,),
        contract=contract,
    )


def render_evidence_replay_readiness_contract_check(
    check: EvidenceReplayReadinessContractCheck,
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

    envelope_shape_valid = _REQUIRED_ENVELOPE_KEYS.issubset(set(envelope.keys()))
    if not envelope_shape_valid:
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

    if (
        counter_valid
        and bool_valid
        and not _envelope_constants_valid(envelope)
    ):
        failure_set.add(_FAILURE_SAFETY_INCONSISTENT)

    if (
        counter_valid
        and list_valid
        and envelope.get("unique_task_count")
        != len(envelope.get("task_ids"))
    ):
        failure_set.add(_FAILURE_SAFETY_INCONSISTENT)

    if (
        counter_valid
        and bool_valid
        and list_valid
        and not _operator_safe_is_consistent(envelope)
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
        and not envelope.get("operator_safe")
        and _FAILURE_STATUS_INCONSISTENT not in failure_set
        and _FAILURE_SAFETY_INCONSISTENT not in failure_set
    ):
        failure_set.add(_FAILURE_OPERATOR_NOT_SAFE)

    return _ordered_failures(failure_set)


def _envelope_constants_valid(envelope: Mapping[str, object]) -> bool:
    return (
        envelope.get("surface") == _ENVELOPE_SURFACE
        and type(envelope.get("version")) is int
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


def _operator_safe_is_consistent(envelope: Mapping[str, object]) -> bool:
    operator_safe = envelope["operator_safe"]
    item_count = envelope["item_count"]
    missing_count = envelope["missing_artifact_ref_count"]
    duplicate_refs = envelope["duplicate_artifact_refs"]

    expected_safe = (
        item_count > 0
        and missing_count == 0
        and duplicate_refs == []
    )
    return operator_safe is expected_safe


def _status_is_consistent(
    *,
    ready: object,
    reason_code: object,
    payload_failures: object,
    envelope: Mapping[str, object],
) -> bool:
    operator_safe = envelope["operator_safe"]
    item_count = envelope["item_count"]
    missing_count = envelope["missing_artifact_ref_count"]
    duplicate_refs = envelope["duplicate_artifact_refs"]

    if ready is True:
        return (
            reason_code == _P2_01_REASON_CODE_READY
            and payload_failures == []
            and operator_safe is True
            and item_count > 0
            and missing_count == 0
            and duplicate_refs == []
        )

    if reason_code == _P2_01_REASON_CODE_INVALID:
        return payload_failures != []

    if reason_code == _P2_01_REASON_CODE_NOT_READY:
        return operator_safe is False and payload_failures != []

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


def _ordered_failures(failures: set[str]) -> list[str]:
    return [failure for failure in _FAILURE_VALUES if failure in failures]


__all__ = [
    "EvidenceReplayReadinessContractCheck",
    "check_evidence_replay_readiness_contract",
    "evidence_replay_readiness_contract_manifest",
    "render_evidence_replay_readiness_contract_check",
]
