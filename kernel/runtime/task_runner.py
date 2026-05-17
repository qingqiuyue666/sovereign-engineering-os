"""Task runner facade for dry-run execution only."""

from __future__ import annotations

from typing import Mapping

from .dry_run_executor import DryRunExecutionResult, execute_dry_run

__all__ = ["run_task_dry_run"]


def run_task_dry_run(task_manifest: Mapping[str, object]) -> DryRunExecutionResult:
    return execute_dry_run(task_manifest)
