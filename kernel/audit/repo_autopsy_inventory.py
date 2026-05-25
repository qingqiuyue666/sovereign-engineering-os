"""Static repository autopsy inventory records.

This module classifies supplied records only. It does not scan the repository,
delete files, move files, archive files, launch tools, call providers, or
perform execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping

__all__ = [
    "AUTOPSY_CATEGORIES",
    "SCORE_VALUES",
    "RepoAutopsyRecord",
    "RepoAutopsyValidationResult",
    "record_content_hash",
    "validate_repo_autopsy_record",
]

AUTOPSY_CATEGORIES = frozenset(
    {
        "CORE_RUNTIME",
        "EVIDENCE_SPINE",
        "RISK_BOUNDARY",
        "APPROVAL_BOUNDARY",
        "DRY_RUN_SUPPORT",
        "GOVERNANCE_POLICY",
        "TEST_INFRASTRUCTURE",
        "DOCS_EXPLANATORY",
        "USE_CASE_LINKED",
        "CANDIDATE_ASSET",
        "PRUNE_CANDIDATE",
        "ARCHIVE_CANDIDATE",
        "UNKNOWN",
    }
)

SCORE_VALUES = frozenset({"NONE", "LOW", "MEDIUM", "HIGH"})


@dataclass(frozen=True)
class RepoAutopsyRecord:
    record_id: str
    path: str
    module_name: str
    category: str
    execution_value: str
    evidence_value: str
    risk_reduction_value: str
    use_case_ids: tuple[str, ...]
    runtime_pressure: str
    test_pressure: str
    external_pressure: str
    prune_candidate: bool
    archive_candidate: bool
    keep_reason: str
    prune_reason: str
    owner_layer: str
    last_reviewed_at: str
    content_hash: str = ""
    archive_reason: str = ""
    reviewer_marked_conflict: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["use_case_ids"] = list(self.use_case_ids)
        return data


@dataclass(frozen=True)
class RepoAutopsyValidationResult:
    accepted: bool
    failures: tuple[str, ...]
    review_required: bool


def record_content_hash(record: RepoAutopsyRecord | Mapping[str, object]) -> str:
    data = _record_map(record)
    material = {
        key: value
        for key, value in data.items()
        if key not in {"content_hash", "last_reviewed_at"}
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_repo_autopsy_record(record: RepoAutopsyRecord | Mapping[str, object]) -> RepoAutopsyValidationResult:
    data = _record_map(record)
    failures: list[str] = []

    for field in (
        "record_id",
        "path",
        "module_name",
        "category",
        "execution_value",
        "evidence_value",
        "risk_reduction_value",
        "runtime_pressure",
        "test_pressure",
        "external_pressure",
        "owner_layer",
        "last_reviewed_at",
    ):
        if not isinstance(data.get(field), str) or not data.get(field):
            failures.append(f"{field}_required")

    category = data.get("category")
    if category not in AUTOPSY_CATEGORIES:
        failures.append("category_invalid")

    for field in (
        "execution_value",
        "evidence_value",
        "risk_reduction_value",
        "runtime_pressure",
        "test_pressure",
        "external_pressure",
    ):
        if data.get(field) not in SCORE_VALUES:
            failures.append(f"{field}_invalid")

    use_case_ids = data.get("use_case_ids")
    if not isinstance(use_case_ids, list) or not all(isinstance(item, str) and item for item in use_case_ids):
        failures.append("use_case_ids_must_be_string_list")

    for field in ("prune_candidate", "archive_candidate"):
        if not isinstance(data.get(field), bool):
            failures.append(f"{field}_must_be_bool")

    if category == "CORE_RUNTIME" and data.get("execution_value") == "NONE":
        failures.append("core_runtime_requires_execution_value")
    if category == "EVIDENCE_SPINE" and data.get("evidence_value") == "NONE":
        failures.append("evidence_spine_requires_evidence_value")
    if category == "RISK_BOUNDARY" and data.get("risk_reduction_value") == "NONE":
        failures.append("risk_boundary_requires_risk_reduction_value")
    if category == "CORE_RUNTIME" and data.get("prune_candidate") is True and data.get("reviewer_marked_conflict") is not True:
        failures.append("core_runtime_prune_conflict_requires_reviewer_marked_conflict")
    if (category == "ARCHIVE_CANDIDATE" or data.get("archive_candidate") is True) and not (
        data.get("prune_reason") or data.get("archive_reason")
    ):
        failures.append("archive_candidate_requires_reason")

    content_hash = data.get("content_hash")
    if content_hash and content_hash != record_content_hash(data):
        failures.append("content_hash_mismatch")

    review_required = data.get("use_case_ids") == [] and data.get("runtime_pressure") == "NONE"
    return RepoAutopsyValidationResult(
        accepted=not failures,
        failures=tuple(sorted(set(failures))),
        review_required=review_required,
    )


def _record_map(record: RepoAutopsyRecord | Mapping[str, object]) -> dict[str, object]:
    if isinstance(record, RepoAutopsyRecord):
        return record.as_dict()
    if not isinstance(record, Mapping):
        raise TypeError("record must be a RepoAutopsyRecord or mapping")
    return dict(record)
