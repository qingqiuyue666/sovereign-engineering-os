"""Dry-run planning helper."""

from __future__ import annotations

def dry_run_plan(adapter: str, job: dict[str, object]) -> dict[str, object]:
    return {
        "adapter": adapter,
        "job_id": job.get("id", "JOB_DRY_RUN"),
        "dry_run": True,
        "execute_performed": False,
        "budget_required_before_execution": True,
    }
