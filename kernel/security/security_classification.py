"""Security classification helpers for V12 leak prevention."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

_LEVELS = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET", "CROWN_JEWEL")
_ALLOWED_SINKS = {
    "PUBLIC": {"git_commit", "ai_context", "provider_request", "run_report", "exported_artifact", "ledger_record", "failure_bundle", "telegram_message"},
    "INTERNAL": {"git_commit", "ai_context", "run_report", "exported_artifact", "ledger_record", "failure_bundle"},
    "CONFIDENTIAL": {"run_report", "ledger_record", "failure_bundle"},
    "SECRET": set(),
    "CROWN_JEWEL": set(),
}


@dataclass(frozen=True)
class ClassificationResult:
    accepted: bool
    classification: str
    failures: tuple[str, ...]


def classify_record(record: Mapping[str, Any]) -> ClassificationResult:
    failures: list[str] = []
    if not isinstance(record, Mapping):
        return ClassificationResult(False, "UNKNOWN", ("record_must_be_mapping",))
    level = record.get("classification", "INTERNAL")
    if level not in _LEVELS:
        failures.append("classification_invalid")
        level = "UNKNOWN"
    if record.get("contains_secret_material") is True and level not in {"SECRET", "CROWN_JEWEL"}:
        failures.append("secret_material_requires_secret_classification")
    if record.get("contains_crown_jewel_material") is True and level != "CROWN_JEWEL":
        failures.append("crown_jewel_material_requires_crown_jewel_classification")
    return ClassificationResult(not failures, level, tuple(sorted(set(failures))))


def is_sink_allowed(classification: str, sink: str) -> bool:
    return sink in _ALLOWED_SINKS.get(classification, set())
