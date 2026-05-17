"""Security classification helpers for V12 foundation surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

__all__ = [
    "CLASSIFICATION_ORDER",
    "ClassificationResult",
    "highest_classification",
    "normalize_classification",
    "validate_classification",
]

CLASSIFICATION_ORDER = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET", "CROWN_JEWEL")
_RANK = {label: index for index, label in enumerate(CLASSIFICATION_ORDER)}


@dataclass(frozen=True)
class ClassificationResult:
    accepted: bool
    classification: str | None
    failures: tuple[str, ...]


def normalize_classification(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized if normalized in _RANK else None


def validate_classification(value: object) -> ClassificationResult:
    normalized = normalize_classification(value)
    failures = () if normalized else ("classification_unknown",)
    return ClassificationResult(
        accepted=normalized is not None,
        classification=normalized,
        failures=failures,
    )


def highest_classification(values: Iterable[object]) -> str:
    highest = "PUBLIC"
    for value in values:
        normalized = normalize_classification(value)
        if normalized is None:
            return "CROWN_JEWEL"
        if _RANK[normalized] > _RANK[highest]:
            highest = normalized
    return highest
