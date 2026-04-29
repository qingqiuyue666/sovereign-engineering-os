"""Read-only readiness envelope for rendered evidence/replay audit records.

Boundary:

The existing evidence spine is materialized through append-only
``audit_records`` rows. Evidence closure and replay-anchor admission are
already represented in those rows by ``task_id``, ``record_type``,
``artifact_refs``, optional stage payloads rendered to ``stage``, and
``created_at``.

This module does not open repositories, write rows, call restore, or
invoke CLI/runtime surfaces. It accepts only already-rendered dictionaries
and emits a bounded JSON-safe readiness envelope for operator review.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass


_SURFACE = "evidence_replay_readiness"
_VERSION = 1
_INPUT_SHAPE = (
    "rendered audit_records rows: task_id, record_type, artifact_refs, "
    "optional stage, created_at"
)

_REASON_CODE_INVALID = "invalid_evidence_replay"
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
        "artifact_ref_invalid",
        "stage_invalid",
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
    "artifact_ref_invalid",
    "stage_invalid",
    "created_at_invalid",
    "duplicate_artifact_ref",
    "missing_artifact_ref",
    "mixed_task_ids",
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


@dataclass(frozen=True)
class EvidenceReplayReadinessEnvelope:
    """Frozen verdict from the evidence/replay read-only envelope."""

    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    envelope: dict[str, object]


def evidence_replay_readiness_manifest() -> dict[str, object]:
    """Return a deep-copied JSON-safe manifest for this read-only surface."""

    return deepcopy(_MANIFEST)


def build_evidence_replay_readiness_envelope(
    items: object,
) -> EvidenceReplayReadinessEnvelope:
    """Build a readiness envelope from rendered audit/evidence records.

    ``items`` must be a non-empty sequence of mappings. The canonical
    artifact reference field is the existing audit-record ``artifact_refs``
    sequence; a singular ``artifact_ref`` is accepted only for callers
    that have already rendered a replay/evidence item down to one ref.
    """

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
    stage_counts: Counter[str] = Counter()
    artifact_refs: list[str] = []
    missing_artifact_ref_count = 0

    for item in item_sequence:
        if not isinstance(item, Mapping):
            failures.add("item_invalid_type")
            continue

        if not _has_minimum_shape(item):
            failures.add("item_shape_invalid")
            continue

        task_id = item.get("task_id")
        if _is_non_empty_str(task_id):
            task_ids.append(task_id)
        else:
            failures.add("task_id_invalid")

        record_type = item.get("record_type")
        if _is_non_empty_str(record_type):
            record_type_counts[str(record_type)] += 1
        else:
            failures.add("record_type_invalid")

        refs, missing_ref, refs_valid = _extract_artifact_refs(item)
        if not refs_valid:
            failures.add("artifact_ref_invalid")
        if missing_ref:
            missing_artifact_ref_count += 1
        artifact_refs.extend(refs)

        stage, stage_valid = _extract_stage(item)
        if not stage_valid:
            failures.add("stage_invalid")
        elif stage is not None:
            stage_counts[stage] += 1

        if not _created_at_valid(item):
            failures.add("created_at_invalid")

    unique_task_ids = sorted(set(task_ids))
    duplicate_refs = sorted(
        ref for ref, count in Counter(artifact_refs).items() if count > 1
    )

    if duplicate_refs:
        failures.add("duplicate_artifact_ref")
    if missing_artifact_ref_count:
        failures.add("missing_artifact_ref")
    if len(unique_task_ids) > 1:
        failures.add("mixed_task_ids")

    envelope.update(
        {
            "unique_task_count": len(unique_task_ids),
            "task_ids": unique_task_ids,
            "record_type_counts": dict(sorted(record_type_counts.items())),
            "stage_counts": dict(sorted(stage_counts.items())),
            "artifact_ref_count": len(artifact_refs),
            "missing_artifact_ref_count": missing_artifact_ref_count,
            "duplicate_artifact_refs": duplicate_refs,
        }
    )
    return _build_result(failures, envelope)


def render_evidence_replay_readiness_envelope(
    envelope: EvidenceReplayReadinessEnvelope,
) -> dict[str, object]:
    """Render an envelope verdict to a JSON-safe deep-copied dictionary."""

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
        "stage_counts": {},
        "artifact_ref_count": 0,
        "missing_artifact_ref_count": 0,
        "duplicate_artifact_refs": [],
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
) -> EvidenceReplayReadinessEnvelope:
    ordered_failures = tuple(
        failure for failure in _FAILURE_VALUES if failure in failures
    )
    has_structural_failure = any(
        failure in _STRUCTURAL_FAILURES for failure in ordered_failures
    )
    if has_structural_failure:
        reason_code = _REASON_CODE_INVALID
        ready = False
    elif ordered_failures:
        reason_code = _REASON_CODE_NOT_READY
        ready = False
    else:
        reason_code = _REASON_CODE_READY
        ready = True

    envelope["operator_safe"] = ready
    return EvidenceReplayReadinessEnvelope(
        ready=ready,
        reason_code=reason_code,
        failures=ordered_failures,
        envelope=envelope,
    )


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _is_non_empty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _has_minimum_shape(item: Mapping[str, object]) -> bool:
    has_artifact_ref = "artifact_refs" in item or "artifact_ref" in item
    return (
        "task_id" in item
        and "record_type" in item
        and has_artifact_ref
        and "created_at" in item
    )


def _extract_artifact_refs(
    item: Mapping[str, object],
) -> tuple[list[str], bool, bool]:
    if "artifact_refs" in item:
        refs = item.get("artifact_refs")
        if not _is_sequence(refs):
            return [], False, False
        rendered_refs: list[str] = []
        refs_valid = True
        for ref in refs:
            if _is_non_empty_str(ref):
                rendered_refs.append(str(ref))
            else:
                refs_valid = False
        return rendered_refs, not rendered_refs, refs_valid

    ref = item.get("artifact_ref")
    if ref is None:
        return [], True, True
    if _is_non_empty_str(ref):
        return [str(ref)], False, True
    return [], False, False


def _extract_stage(item: Mapping[str, object]) -> tuple[str | None, bool]:
    stage = item.get("stage")
    if stage is None:
        payload = item.get("payload")
        if isinstance(payload, Mapping):
            stage = payload.get("stage")
    if stage is None:
        return None, True
    if _is_non_empty_str(stage):
        return str(stage), True
    return None, False


def _created_at_valid(item: Mapping[str, object]) -> bool:
    if "created_at" not in item:
        return True
    created_at = item.get("created_at")
    return created_at is None or _is_non_empty_str(created_at)


__all__ = [
    "EvidenceReplayReadinessEnvelope",
    "build_evidence_replay_readiness_envelope",
    "evidence_replay_readiness_manifest",
    "render_evidence_replay_readiness_envelope",
]
