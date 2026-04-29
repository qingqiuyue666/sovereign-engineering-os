"""Read-only readiness envelope for rendered approval/review records.

Boundary:

The existing governance path already materializes approval artifacts,
review artifacts, sealed revisions, and bridge/audit attestations. This
module consumes only dictionaries that callers have already rendered from
those surfaces into the narrow approval/review readiness shape:
``task_id``, ``record_type``, optional approval/review states, optional
revision/seal identifiers, optional actor identity, and ``created_at``.

It does not open stores, mutate approval or review state, execute seal
logic, or invoke operator surfaces.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass


_SURFACE = "approval_review_readiness"
_VERSION = 1
_INPUT_SHAPE = (
    "rendered approval_artifacts/review_artifacts/revisions rows: "
    "task_id, record_type, approval_state, review_state, revision_id, "
    "seal_id, actor_identity, created_at"
)

_REASON_CODE_INVALID = "invalid_approval_review"
_REASON_CODE_NOT_READY = "not_ready"
_REASON_CODE_READY = "ready"

_STRUCTURAL_FAILURES: frozenset[str] = frozenset(
    {
        "items_not_sequence",
        "items_empty",
        "item_invalid_type",
        "item_shape_invalid",
        "task_id_invalid",
        "record_type_invalid",
        "approval_state_invalid",
        "review_state_invalid",
        "revision_id_invalid",
        "seal_id_invalid",
        "actor_identity_invalid",
        "created_at_invalid",
    }
)

_FAILURE_VALUES: tuple[str, ...] = (
    "items_not_sequence",
    "items_empty",
    "item_invalid_type",
    "item_shape_invalid",
    "task_id_invalid",
    "record_type_invalid",
    "approval_state_invalid",
    "review_state_invalid",
    "revision_id_invalid",
    "seal_id_invalid",
    "actor_identity_invalid",
    "created_at_invalid",
    "missing_review_state",
    "missing_revision_or_seal",
    "mixed_task_ids",
    "conflicting_terminal_states",
)

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        _REASON_CODE_INVALID,
        _REASON_CODE_NOT_READY,
        _REASON_CODE_READY,
    ],
    "failure_values": list(_FAILURE_VALUES),
}

_REQUIRED_ITEM_KEYS: frozenset[str] = frozenset(
    {
        "task_id",
        "record_type",
        "approval_state",
        "review_state",
        "revision_id",
        "seal_id",
        "actor_identity",
        "created_at",
    }
)

_APPROVED_TERMINAL_VALUES: frozenset[str] = frozenset(
    {"approved", "accepted", "pass", "passed"}
)
_REJECTED_TERMINAL_VALUES: frozenset[str] = frozenset(
    {"rejected", "declined", "denied", "fail", "failed", "expired", "invalidated"}
)


@dataclass(frozen=True)
class ApprovalReviewReadinessEnvelope:
    """Frozen verdict for the approval/review read-only envelope."""

    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    envelope: dict[str, object]


def approval_review_readiness_manifest() -> dict[str, object]:
    """Return a defensive JSON-safe manifest for this read-only surface."""

    return deepcopy(_MANIFEST)


def build_approval_review_readiness_envelope(
    items: object,
) -> ApprovalReviewReadinessEnvelope:
    """Build readiness from rendered approval/review/revision-seal items."""

    failures: set[str] = set()
    envelope = _empty_envelope()

    if not _is_sequence(items):
        failures.add("items_not_sequence")
        return _build_result(failures, envelope)

    item_sequence = items
    envelope["item_count"] = len(item_sequence)
    if not item_sequence:
        failures.add("items_empty")
        return _build_result(failures, envelope)

    task_ids: list[str] = []
    record_type_counts: Counter[str] = Counter()
    approval_state_counts: Counter[str] = Counter()
    review_state_counts: Counter[str] = Counter()
    revision_id_count = 0
    seal_id_count = 0
    missing_review_state_count = 0
    missing_revision_or_seal_count = 0
    terminal_values: set[str] = set()

    for item in item_sequence:
        if not isinstance(item, Mapping):
            failures.add("item_invalid_type")
            continue

        if not _has_minimum_shape(item):
            failures.add("item_shape_invalid")
            continue

        task_id = item.get("task_id")
        if _is_non_empty_str(task_id):
            task_ids.append(str(task_id))
        else:
            failures.add("task_id_invalid")

        record_type = item.get("record_type")
        if _is_non_empty_str(record_type):
            record_type_counts[str(record_type)] += 1
        else:
            failures.add("record_type_invalid")

        approval_state = item.get("approval_state")
        if _optional_non_empty_str(approval_state):
            if approval_state is not None:
                rendered = str(approval_state)
                approval_state_counts[rendered] += 1
                terminal_values.add(rendered.strip().lower())
        else:
            failures.add("approval_state_invalid")

        review_state = item.get("review_state")
        if _optional_non_empty_str(review_state):
            if review_state is None:
                missing_review_state_count += 1
            else:
                rendered = str(review_state)
                review_state_counts[rendered] += 1
                terminal_values.add(rendered.strip().lower())
        else:
            failures.add("review_state_invalid")

        revision_id = item.get("revision_id")
        revision_id_valid = _optional_non_empty_str(revision_id)
        if revision_id_valid:
            if revision_id is not None:
                revision_id_count += 1
        else:
            failures.add("revision_id_invalid")

        seal_id = item.get("seal_id")
        seal_id_valid = _optional_non_empty_str(seal_id)
        if seal_id_valid:
            if seal_id is not None:
                seal_id_count += 1
        else:
            failures.add("seal_id_invalid")

        if revision_id_valid and seal_id_valid and revision_id is None and seal_id is None:
            missing_revision_or_seal_count += 1

        if not _optional_non_empty_str(item.get("actor_identity")):
            failures.add("actor_identity_invalid")

        if not _optional_non_empty_str(item.get("created_at")):
            failures.add("created_at_invalid")

    unique_task_ids = sorted(set(task_ids))
    if len(unique_task_ids) > 1:
        failures.add("mixed_task_ids")
    if missing_review_state_count:
        failures.add("missing_review_state")
    if missing_revision_or_seal_count:
        failures.add("missing_revision_or_seal")
    if _has_conflicting_terminal_states(terminal_values):
        failures.add("conflicting_terminal_states")

    envelope.update(
        {
            "unique_task_count": len(unique_task_ids),
            "task_ids": unique_task_ids,
            "record_type_counts": dict(sorted(record_type_counts.items())),
            "approval_state_counts": dict(sorted(approval_state_counts.items())),
            "review_state_counts": dict(sorted(review_state_counts.items())),
            "revision_id_count": revision_id_count,
            "seal_id_count": seal_id_count,
            "missing_review_state_count": missing_review_state_count,
            "missing_revision_or_seal_count": missing_revision_or_seal_count,
        }
    )
    return _build_result(failures, envelope)


def render_approval_review_readiness_envelope(
    envelope: ApprovalReviewReadinessEnvelope,
) -> dict[str, object]:
    """Render an envelope verdict to a defensive JSON-safe dictionary."""

    return {
        "ready": bool(envelope.ready),
        "reason_code": str(envelope.reason_code),
        "failures": list(envelope.failures),
        "envelope": deepcopy(envelope.envelope),
    }


def _empty_envelope() -> dict[str, object]:
    return {
        "surface": _SURFACE,
        "version": _VERSION,
        "item_count": 0,
        "unique_task_count": 0,
        "task_ids": [],
        "record_type_counts": {},
        "approval_state_counts": {},
        "review_state_counts": {},
        "revision_id_count": 0,
        "seal_id_count": 0,
        "missing_review_state_count": 0,
        "missing_revision_or_seal_count": 0,
        "operator_safe": False,
        "restore_supported": False,
        "durable_writes": False,
        "cli_command_count": 0,
        "runtime_dependency_count": 0,
        "json_safe": True,
    }


def _build_result(
    failures: set[str],
    envelope: dict[str, object],
) -> ApprovalReviewReadinessEnvelope:
    ordered_failures = tuple(
        failure for failure in _FAILURE_VALUES if failure in failures
    )
    has_structural_failure = any(
        failure in _STRUCTURAL_FAILURES for failure in ordered_failures
    )

    if has_structural_failure:
        ready = False
        reason_code = _REASON_CODE_INVALID
    elif ordered_failures:
        ready = False
        reason_code = _REASON_CODE_NOT_READY
    else:
        ready = True
        reason_code = _REASON_CODE_READY

    envelope["operator_safe"] = ready
    return ApprovalReviewReadinessEnvelope(
        ready=ready,
        reason_code=reason_code,
        failures=ordered_failures,
        envelope=envelope,
    )


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _has_minimum_shape(item: Mapping[str, object]) -> bool:
    return _REQUIRED_ITEM_KEYS.issubset(set(item.keys()))


def _is_non_empty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _optional_non_empty_str(value: object) -> bool:
    return value is None or _is_non_empty_str(value)


def _has_conflicting_terminal_states(values: set[str]) -> bool:
    has_approved = any(value in _APPROVED_TERMINAL_VALUES for value in values)
    has_rejected = any(value in _REJECTED_TERMINAL_VALUES for value in values)
    return has_approved and has_rejected


__all__ = [
    "ApprovalReviewReadinessEnvelope",
    "approval_review_readiness_manifest",
    "build_approval_review_readiness_envelope",
    "render_approval_review_readiness_envelope",
]
