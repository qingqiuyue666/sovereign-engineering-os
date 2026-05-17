"""Task manifest validation and deterministic task-id assignment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import copy
import hashlib

from kernel.security.security_classification import normalize_classification

from .run_id import canonical_json

__all__ = ["TaskManifestResult", "normalize_task_manifest", "validate_task_manifest"]

_REQUIRED = ("objective", "requested_capabilities", "classification", "policy_version", "code_version", "input_digest")


@dataclass(frozen=True)
class TaskManifestResult:
    accepted: bool
    manifest: dict[str, object]
    failures: tuple[str, ...]


def normalize_task_manifest(manifest: Mapping[str, object]) -> dict[str, object]:
    normalized = copy.deepcopy(dict(manifest))
    if not normalized.get("task_id"):
        payload = {key: value for key, value in normalized.items() if key != "task_id"}
        normalized["task_id"] = "task_" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()[:24]
    return normalized


def validate_task_manifest(manifest: Mapping[str, object]) -> TaskManifestResult:
    if not isinstance(manifest, Mapping):
        return TaskManifestResult(False, {}, ("task_manifest_must_be_mapping",))
    normalized = normalize_task_manifest(manifest)
    failures: list[str] = []
    for field in _REQUIRED:
        if field not in normalized:
            failures.append(f"{field}_required")
    for field in ("task_id", "objective", "policy_version", "code_version", "input_digest"):
        if field in normalized and (not isinstance(normalized.get(field), str) or not normalized.get(field)):
            failures.append(f"{field}_must_be_nonempty_string")
    caps = normalized.get("requested_capabilities")
    if not isinstance(caps, list) or not caps or not all(isinstance(item, str) and item for item in caps):
        failures.append("requested_capabilities_required")
        cap_values: list[str] = []
    else:
        cap_values = [str(item) for item in caps]
    classification = normalize_classification(normalized.get("classification"))
    if classification is None:
        failures.append("classification_required")
    provider_bound = bool(normalized.get("provider_bound")) or any("provider" in cap.lower() for cap in cap_values)
    if provider_bound and classification in {"SECRET", "CROWN_JEWEL"}:
        failures.append("provider_bound_sensitive_task_forbidden")
    if "raw_prompt" in normalized:
        failures.append("raw_prompt_forbidden")
    return TaskManifestResult(
        accepted=not failures,
        manifest=normalized,
        failures=tuple(sorted(set(failures))),
    )
