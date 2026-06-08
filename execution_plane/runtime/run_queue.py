"""In-memory run queue for controlled execution jobs."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from execution_plane.permits.builder import stable_id
from execution_plane.runner.result_envelope import utc_now


@dataclass(frozen=True)
class RunJob:
    job_id: str
    adapter: str
    action: str
    permit: Mapping[str, Any]
    payload: Mapping[str, Any]
    status: str = "QUEUED"


class InMemoryRunQueue:
    def __init__(self) -> None:
        self._pending: deque[RunJob] = deque()
        self._jobs: dict[str, RunJob] = {}

    def enqueue(self, permit: Mapping[str, Any], payload: Mapping[str, Any] | None = None) -> RunJob:
        adapter = str(permit.get("allowed_adapter", ""))
        action = str(permit.get("allowed_action", ""))
        job_id = stable_id("JOB", permit.get("permit_id", ""), adapter, action, utc_now())
        job = RunJob(job_id=job_id, adapter=adapter, action=action, permit=dict(permit), payload=dict(payload or {}))
        self._pending.append(job)
        self._jobs[job_id] = job
        return job

    def pop_next(self) -> RunJob | None:
        if not self._pending:
            return None
        job = self._pending.popleft()
        running = _replace_status(job, "RUNNING")
        self._jobs[job.job_id] = running
        return running

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.status in {"SUCCEEDED", "FAILED", "CANCELED"}:
            return False
        self._jobs[job_id] = _replace_status(job, "CANCELED")
        self._pending = deque(item for item in self._pending if item.job_id != job_id)
        return True

    def mark(self, job_id: str, status: str) -> None:
        job = self._jobs[job_id]
        self._jobs[job_id] = _replace_status(job, status)

    def list_jobs(self) -> list[dict[str, Any]]:
        return [
            {
                "job_id": job.job_id,
                "adapter": job.adapter,
                "action": job.action,
                "status": job.status,
            }
            for job in self._jobs.values()
        ]

    def inspect(self, job_id: str) -> dict[str, Any]:
        job = self._jobs[job_id]
        return {
            "job_id": job.job_id,
            "adapter": job.adapter,
            "action": job.action,
            "status": job.status,
            "permit_id": job.permit.get("permit_id"),
        }


def _replace_status(job: RunJob, status: str) -> RunJob:
    return RunJob(
        job_id=job.job_id,
        adapter=job.adapter,
        action=job.action,
        permit=job.permit,
        payload=job.payload,
        status=status,
    )
