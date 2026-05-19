"""Shared pure validation helpers for non-Houdini completion contracts."""

from __future__ import annotations

from typing import Mapping, Sequence
import json

from kernel.runtime._production_workbench_validation import (
    contains_required_terms,
    has_nonempty_violation,
    has_unsafe_status,
)

__all__ = [
    "all_required_gates_true",
    "contains_text",
    "json_text",
    "reject_text_markers",
    "require_bool",
    "require_bool_gate_map",
    "require_complete_has_no_status_violation",
    "require_complete_has_required_gates",
    "require_text_terms",
]


def require_bool(value: object, *, field: str) -> None:
    """Require an explicit boolean value."""

    if not isinstance(value, bool):
        raise ValueError(f"{field}_must_be_bool")


def require_bool_gate_map(
    value: object,
    *,
    field: str,
    required_gates: Sequence[str],
) -> dict[str, bool]:
    """Require a boolean gate map containing every required gate."""

    if not isinstance(value, dict):
        raise ValueError(f"{field}_must_be_dict")
    for gate in required_gates:
        if gate not in value:
            raise ValueError(f"{field}_missing_required_gate:{gate}")
    normalized: dict[str, bool] = {}
    for gate, state in value.items():
        if not isinstance(gate, str):
            raise ValueError(f"{field}_gate_name_must_be_string")
        if not isinstance(state, bool):
            raise ValueError(f"{field}_{gate}_must_be_bool")
        normalized[gate] = state
    return normalized


def all_required_gates_true(gates: Mapping[str, bool], required_gates: Sequence[str]) -> bool:
    """Return true only when every required gate is explicitly true."""

    return all(gates.get(gate) is True for gate in required_gates)


def require_complete_has_required_gates(
    decision: str,
    *,
    gates: Mapping[str, bool],
    required_gates: Sequence[str],
    complete_value: str = "complete",
) -> None:
    """Reject a complete decision unless all required gates are true."""

    if decision == complete_value and not all_required_gates_true(gates, required_gates):
        raise ValueError("incomplete_gate_blocks_complete")


def require_complete_has_no_status_violation(
    decision: str,
    *,
    status: object,
    complete_value: str = "complete",
    error: str = "status_violation_blocks_complete",
) -> None:
    """Reject completion when caller-provided status carries a violation signal."""

    if decision == complete_value and (has_nonempty_violation(status) or has_unsafe_status(status)):
        raise ValueError(error)


def require_text_terms(value: object, terms: Sequence[str], *, error: str) -> None:
    """Require all terms to appear somewhere in JSON-normalized material."""

    if not contains_required_terms(value, terms):
        raise ValueError(error)


def reject_text_markers(value: object, markers: Sequence[str], *, error: str) -> None:
    """Reject any marker found in JSON-normalized material."""

    text = json_text(value)
    for marker in markers:
        if marker.lower() in text:
            raise ValueError(error)


def contains_text(value: object, marker: str) -> bool:
    """Return whether a marker appears in JSON-normalized material."""

    return marker.lower() in json_text(value)


def json_text(value: object) -> str:
    """Render stable lower-case JSON text for phrase checks."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).lower()
