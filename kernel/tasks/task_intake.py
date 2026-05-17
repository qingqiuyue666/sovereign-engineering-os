"""Read-only task intake facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .task_manifest import TaskManifestResult, validate_task_manifest

__all__ = ["TaskIntakeResult", "intake_task"]


@dataclass(frozen=True)
class TaskIntakeResult:
    accepted: bool
    task_manifest: dict[str, object]
    failures: tuple[str, ...]


def intake_task(manifest: Mapping[str, object]) -> TaskIntakeResult:
    result: TaskManifestResult = validate_task_manifest(manifest)
    return TaskIntakeResult(result.accepted, result.manifest, result.failures)
