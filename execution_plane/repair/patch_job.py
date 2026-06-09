"""PatchRepairJob model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


PATCH_REPAIR_JOB_SCHEMA_VERSION = "seos.patch_repair_job.v1"


@dataclass(frozen=True)
class PatchRepairJob:
    repair_id: str
    source_failure_bundle: str
    failure_code: str
    target_files: tuple[str, ...]
    reproduction_command: str
    test_commands: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    mode: str
    auto_apply: bool
    max_iterations: int
    status: str
    classification: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PATCH_REPAIR_JOB_SCHEMA_VERSION,
            "repair_id": self.repair_id,
            "source_failure_bundle": self.source_failure_bundle,
            "failure_code": self.failure_code,
            "target_files": list(self.target_files),
            "reproduction_command": self.reproduction_command,
            "test_commands": list(self.test_commands),
            "allowed_tools": list(self.allowed_tools),
            "mode": self.mode,
            "auto_apply": self.auto_apply,
            "max_iterations": self.max_iterations,
            "status": self.status,
            "classification": dict(self.classification),
        }
