"""Artifact provenance validation for digest-only V12 records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .security_classification import validate_classification

__all__ = ["ArtifactProvenanceResult", "validate_artifact_provenance"]

_REQUIRED = ("artifact_id", "artifact_type", "content_hash", "source_refs", "classification", "created_by_stage")


@dataclass(frozen=True)
class ArtifactProvenanceResult:
    accepted: bool
    failures: tuple[str, ...]


def validate_artifact_provenance(record: Mapping[str, object]) -> ArtifactProvenanceResult:
    if not isinstance(record, Mapping):
        return ArtifactProvenanceResult(False, ("provenance_must_be_mapping",))
    failures: list[str] = []
    for field in _REQUIRED:
        if field not in record:
            failures.append(f"{field}_required")
    for field in ("artifact_id", "artifact_type", "content_hash", "created_by_stage"):
        if field in record and (not isinstance(record.get(field), str) or not record.get(field)):
            failures.append(f"{field}_must_be_nonempty_string")
    if isinstance(record.get("content_hash"), str) and not str(record["content_hash"]).startswith("sha256:"):
        failures.append("content_hash_must_be_digest_ref")
    source_refs = record.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs or not all(isinstance(item, str) and item for item in source_refs):
        failures.append("source_refs_must_be_nonempty_string_list")
    classification = validate_classification(record.get("classification"))
    if not classification.accepted:
        failures.extend(classification.failures)
    if "raw_content" in record:
        failures.append("raw_content_forbidden")
    return ArtifactProvenanceResult(not failures, tuple(sorted(set(failures))))
