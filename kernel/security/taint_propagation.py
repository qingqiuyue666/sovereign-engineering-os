"""Pure taint propagation rules for V12."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .security_classification import CLASSIFICATION_ORDER, highest_classification, normalize_classification

__all__ = [
    "TAINT_LABELS",
    "TaintDecision",
    "derive_artifact_taint",
    "validate_taint_transition",
]

TAINT_LABELS = CLASSIFICATION_ORDER
_RANK = {label: index for index, label in enumerate(TAINT_LABELS)}


@dataclass(frozen=True)
class TaintDecision:
    accepted: bool
    resulting_taint: str
    failures: tuple[str, ...]


def derive_artifact_taint(inputs: Iterable[Mapping[str, object] | str]) -> str:
    labels: list[object] = []
    for item in inputs:
        if isinstance(item, Mapping):
            labels.append(item.get("classification"))
        else:
            labels.append(item)
    return highest_classification(labels)


def validate_taint_transition(
    *,
    current_taint: object,
    requested_taint: object,
    declassification_receipt: Mapping[str, object] | None = None,
) -> TaintDecision:
    current = normalize_classification(current_taint)
    requested = normalize_classification(requested_taint)
    failures: list[str] = []
    if current is None:
        failures.append("current_taint_unknown")
        current = "CROWN_JEWEL"
    if requested is None:
        failures.append("requested_taint_unknown")
        requested = "CROWN_JEWEL"
    if _RANK[requested] < _RANK[current]:
        if not _valid_declassification_receipt(declassification_receipt, current, requested):
            failures.append("declassification_receipt_required")
            requested = current
    return TaintDecision(
        accepted=not failures,
        resulting_taint=requested,
        failures=tuple(sorted(set(failures))),
    )


def _valid_declassification_receipt(receipt: Mapping[str, object] | None, source: str, target: str) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    return (
        receipt.get("receipt_type") == "declassification_receipt_v1"
        and receipt.get("source_taint") == source
        and receipt.get("target_taint") == target
        and isinstance(receipt.get("approved_by"), str)
        and bool(receipt.get("approved_by"))
    )
