"""SQLite-backed durable job queue facade built on the v3 event log."""

from __future__ import annotations

import json
from typing import Any

from kernel.os_engine.database import OSDatabase, stable_content_hash, utc_now_iso, validate_no_secret_like
from kernel.os_engine.event_log import EventLog, EventLogError, JobEventRecord
from kernel.os_engine.event_types import JobEventType
from kernel.os_engine.job_projection import ProjectedJobState, project_all_jobs, project_job_state


class SQLiteJobQueueError(RuntimeError):
    """Raised when durable queue admission or transition fails."""


class SQLiteJobQueue:
    """Durable queue API where state is replayed from append-only job events."""

    def __init__(self, database: OSDatabase) -> None:
        self.database = database
        self.event_log = EventLog(database)

    def create_job(
        self,
        *,
        job_id: str,
        job_type: str,
        input_manifest: dict[str, Any] | None = None,
        output_dir: str = "",
        human_review_required: bool = False,
        dry_run: bool = False,
        source_git_commit: str = "",
        local_only: bool = True,
    ) -> JobEventRecord:
        manifest = dict(input_manifest or {})
        validate_no_secret_like(manifest)
        payload = {
            "created_at": utc_now_iso(),
            "dry_run": bool(dry_run),
            "human_review_required": bool(human_review_required),
            "input_manifest": manifest,
            "job_type": job_type,
            "local_only": bool(local_only),
            "output_dir": output_dir,
            "source_git_commit": source_git_commit,
        }
        return self.event_log.append_event(
            job_id=job_id,
            event_type=JobEventType.JOB_CREATED,
            payload=payload,
        )

    def admit_job(self, job_id: str, *, reason: str = "admitted by durable local queue") -> JobEventRecord:
        return self._append(job_id, JobEventType.JOB_ADMITTED, {"admitted": True}, reason=reason)

    def enqueue_job(self, job_id: str, *, reason: str = "queued for materialization") -> JobEventRecord:
        return self._append(job_id, JobEventType.JOB_QUEUED, {"queued": True}, reason=reason)

    def start_job(self, job_id: str, *, reason: str = "worker boundary started") -> JobEventRecord:
        return self._append(job_id, JobEventType.JOB_STARTED, {"started": True}, reason=reason)

    def select_worker(self, job_id: str, *, worker_name: str, reason: str = "worker selected") -> JobEventRecord:
        return self._append(
            job_id,
            JobEventType.WORKER_SELECTED,
            {"worker_name": worker_name},
            reason=reason,
        )

    def mark_subprocess_started(
        self,
        job_id: str,
        *,
        command_digest: str,
        reason: str = "subprocess started by worker boundary",
    ) -> JobEventRecord:
        return self._append(
            job_id,
            JobEventType.SUBPROCESS_STARTED,
            {"command_digest": command_digest},
            reason=reason,
        )

    def mark_artifact_discovered(
        self,
        job_id: str,
        *,
        artifact_id: str,
        artifact_type: str = "materialization_summary",
        reason: str = "artifact discovered",
    ) -> JobEventRecord:
        return self._append(
            job_id,
            JobEventType.ARTIFACT_DISCOVERED,
            {"artifact_id": artifact_id, "artifact_type": artifact_type},
            reason=reason,
        )

    def mark_artifact_validated(
        self,
        job_id: str,
        *,
        artifact_id: str,
        validation: dict[str, Any] | None = None,
        reason: str = "artifact validated",
    ) -> JobEventRecord:
        return self._append(
            job_id,
            JobEventType.ARTIFACT_VALIDATED,
            {"artifact_id": artifact_id, "validation": validation or {"passed": True}},
            reason=reason,
        )

    def request_human_review(self, job_id: str, *, artifact_id: str, reason: str) -> JobEventRecord:
        if not reason:
            raise SQLiteJobQueueError("human review request requires reason")
        return self._append(
            job_id,
            JobEventType.HUMAN_REVIEW_REQUESTED,
            {"artifact_id": artifact_id},
            reason=reason,
        )

    def approve_human_review(
        self,
        job_id: str,
        *,
        artifact_id: str,
        reviewer: str,
        reason: str = "approved by reviewer",
    ) -> JobEventRecord:
        if not reviewer:
            raise SQLiteJobQueueError("approval requires reviewer")
        return self._append(
            job_id,
            JobEventType.HUMAN_APPROVED,
            {"artifact_id": artifact_id, "reviewer": reviewer},
            reason=reason,
        )

    def reject_human_review(self, job_id: str, *, artifact_id: str, reviewer: str, reason: str) -> JobEventRecord:
        if not reviewer:
            raise SQLiteJobQueueError("rejection requires reviewer")
        if not reason:
            raise SQLiteJobQueueError("rejection requires reason")
        return self._append(
            job_id,
            JobEventType.HUMAN_REJECTED,
            {"artifact_id": artifact_id, "reviewer": reviewer},
            reason=reason,
        )

    def succeed_job(
        self,
        job_id: str,
        *,
        artifact_ids: list[str] | None = None,
        completion_evidence: dict[str, Any] | None = None,
        physical_proof: bool = False,
        reason: str = "materialization succeeded",
    ) -> JobEventRecord:
        if physical_proof and self._job_is_dry_run(job_id):
            raise SQLiteJobQueueError("dry_run jobs cannot produce physical proof claims")
        payload: dict[str, Any] = {"physical_proof": bool(physical_proof)}
        if artifact_ids:
            payload["artifact_ids"] = list(artifact_ids)
        if completion_evidence:
            payload["completion_evidence"] = completion_evidence
        if not (artifact_ids or completion_evidence):
            raise SQLiteJobQueueError("succeeded jobs require artifact or completion evidence")
        return self._append(job_id, JobEventType.JOB_SUCCEEDED, payload, reason=reason)

    def fail_job(self, job_id: str, *, reason: str) -> JobEventRecord:
        if not reason:
            raise SQLiteJobQueueError("failed jobs require reason")
        return self._append(job_id, JobEventType.JOB_FAILED, {"failed": True}, reason=reason)

    def quarantine_job(self, job_id: str, *, reason: str) -> JobEventRecord:
        if not reason:
            raise SQLiteJobQueueError("quarantined jobs require reason")
        return self._append(job_id, JobEventType.JOB_QUARANTINED, {"quarantined": True}, reason=reason)

    def cancel_job(self, job_id: str, *, reason: str) -> JobEventRecord:
        if not reason:
            raise SQLiteJobQueueError("cancelled jobs require reason")
        return self._append(job_id, JobEventType.JOB_CANCELLED, {"cancelled": True}, reason=reason)

    def get_job_state(self, job_id: str) -> ProjectedJobState:
        events = self.event_log.get_events(job_id)
        return project_job_state(events)

    def list_jobs(self) -> list[ProjectedJobState]:
        return list(self.replay_jobs().values())

    def replay_jobs(self) -> dict[str, ProjectedJobState]:
        return project_all_jobs(self.event_log.get_all_events())

    def deterministic_snapshot_hash(self) -> str:
        snapshot = {job_id: state.to_dict() for job_id, state in self.replay_jobs().items()}
        return stable_content_hash(snapshot)

    def _append(
        self,
        job_id: str,
        event_type: JobEventType,
        payload: dict[str, Any],
        *,
        reason: str | None,
    ) -> JobEventRecord:
        try:
            return self.event_log.append_event(job_id=job_id, event_type=event_type, payload=payload, reason=reason)
        except EventLogError as exc:
            raise SQLiteJobQueueError(str(exc)) from exc

    def _job_is_dry_run(self, job_id: str) -> bool:
        with self.database.connect() as connection:
            row = connection.execute("SELECT dry_run FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise SQLiteJobQueueError(f"job is not recorded: {job_id}")
        return bool(row["dry_run"])


def projected_jobs_to_json(states: list[ProjectedJobState]) -> str:
    payload = [state.to_dict() for state in sorted(states, key=lambda item: item.job_id)]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
