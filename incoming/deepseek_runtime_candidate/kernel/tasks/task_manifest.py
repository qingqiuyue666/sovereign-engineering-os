"""Task manifest validation."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["validate_task_manifest", "ManifestResult"]

REQUIRED_TOP_KEYS = {"task_id", "objective", "classification"}
ALLOWED_CLASSIFICATIONS = {"PUBLIC", "INTERNAL", "RESTRICTED"}


@dataclass
class ManifestResult:
    accepted: bool
    manifest: dict[str, object]
    failures: list[str] = field(default_factory=list)


def validate_task_manifest(payload: object) -> ManifestResult:
    failures: list[str] = []

    if not isinstance(payload, dict):
        return ManifestResult(accepted=False, manifest={}, failures=["payload_must_be_object"])

    manifest: dict[str, object] = payload  # type: ignore[assignment]

    missing = REQUIRED_TOP_KEYS - set(manifest.keys())
    if missing:
        failures.append(f"missing_required_keys:{','.join(sorted(missing))}")

    if isinstance(manifest.get("task_id"), str) and manifest.get("task_id"):
        tid = manifest["task_id"]
        if not isinstance(tid, str) or not tid.startswith("task-"):
            failures.append("task_id_must_start_with_task-")

    classification = manifest.get("classification")
    if classification not in ALLOWED_CLASSIFICATIONS:
        failures.append(f"invalid_classification:{classification}")

    if not isinstance(manifest.get("objective"), str) or not manifest.get("objective", "").strip():
        failures.append("objective_must_be_non_empty_string")

    return ManifestResult(
        accepted=len(failures) == 0,
        manifest=manifest,
        failures=failures,
    )
