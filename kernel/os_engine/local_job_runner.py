"""Minimal local dispatch loop for admitted SQLite OS jobs."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from kernel.os_engine.builtin_workers import BuiltinWorkerContext
from kernel.os_engine.database import stable_content_hash, utc_now_iso, validate_no_secret_like
from kernel.os_engine.job_queue import Job, JobStatus
from kernel.os_engine.local_os_runtime import LocalOSRuntime
from kernel.os_engine.sqlite_artifact_store import ArtifactType, QuarantineStatus, ReviewStatus, SQLiteArtifactRecord
from kernel.os_engine.worker_registry import WorkerAdmissionError, WorkerRunResult


class LocalJobRunnerError(RuntimeError):
    """Raised when the local runner cannot dispatch a job safely."""


@dataclass(frozen=True, slots=True)
class LocalJobRunResult:
    job_id: str
    job_type: str
    worker_name: str | None
    final_status: str
    ran: bool
    artifact_ids: tuple[str, ...]
    failure_bundle_artifact_id: str | None
    dry_run: bool
    final_claim_allowed: bool
    reason: str
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))


class LocalJobRunner:
    def __init__(self, runtime: LocalOSRuntime) -> None:
        self.runtime = runtime

    def run_next(self, *, job_id: str | None = None) -> LocalJobRunResult:
        return asyncio.run(self.run_next_async(job_id=job_id))

    async def run_next_async(self, *, job_id: str | None = None) -> LocalJobRunResult:
        row = self._load_dispatchable_row(job_id=job_id)
        state = self.runtime.job_queue.get_job_state(str(row["job_id"]))
        if state.current_status in {"succeeded", "failed", "quarantined", "cancelled", "requires_human_review"}:
            return self._result_from_row(
                row=row,
                worker_name=state.worker_name,
                final_status=state.current_status,
                ran=False,
                artifact_ids=state.artifact_ids,
                failure_bundle_artifact_id=None,
                reason="terminal job was not rerun",
            )
        job = self._job_from_row(row)
        worker = None
        try:
            if not self.runtime.worker_registry.has_type(job.type):
                bundle = self._write_failure_bundle(job=job, worker_name=None, reason=f"unregistered worker: {job.type}")
                self.runtime.job_queue.fail_job(job.id, reason=f"unregistered worker: {job.type}")
                final = self.runtime.job_queue.get_job_state(job.id)
                return self._result(
                    job=job,
                    worker_name=None,
                    final_status=final.current_status,
                    ran=False,
                    artifact_ids=final.artifact_ids,
                    failure_bundle_artifact_id=bundle.artifact_id,
                    reason=f"unregistered worker: {job.type}",
                )
            worker = self.runtime.worker_registry.get(job.type)
            worker_name = str(getattr(worker, "name", job.type))
            self.runtime.job_queue.select_worker(job.id, worker_name=worker_name)
            if state.current_status == "admitted":
                self.runtime.job_queue.enqueue_job(job.id)
            self.runtime.job_queue.start_job(job.id)
            context = self._worker_context()
            result: WorkerRunResult | None = None
            try:
                await worker.preflight(job, context)  # type: ignore[arg-type]
                await worker.admit(job, context)  # type: ignore[arg-type]
                result = await worker.run(job, context)  # type: ignore[arg-type]
                await worker.validate_outputs(job, result, context)  # type: ignore[arg-type]
                artifact_records = self._record_result_artifacts(job=job, result=result)
                if bool(result.metadata.get("physical_proof")) and bool(row["dry_run"]):
                    raise LocalJobRunnerError("dry-run worker attempted a physical proof claim")
                if result.quarantined:
                    self._quarantine_artifacts(artifact_records, reason=str(result.metadata.get("quarantine_reason", "worker quarantined output")))
                    self.runtime.job_queue.quarantine_job(job.id, reason=str(result.metadata.get("quarantine_reason", "worker quarantined output")))
                elif bool(result.metadata.get("requires_human_review")):
                    artifact_id = artifact_records[0].artifact_id if artifact_records else "missing_artifact"
                    self._request_review(job_id=job.id, artifact_id=artifact_id, reason="worker requires human review before final claim")
                    self.runtime.job_queue.request_human_review(
                        job.id,
                        artifact_id=artifact_id,
                        reason="worker requires human review before final claim",
                    )
                elif result.succeeded:
                    self.runtime.job_queue.succeed_job(
                        job.id,
                        artifact_ids=[record.artifact_id for record in artifact_records],
                        completion_evidence={
                            "worker": worker_name,
                            "dry_run": bool(row["dry_run"]),
                            "metadata_hash": stable_content_hash(_json_safe_metadata(result.metadata)),
                        },
                        physical_proof=False,
                    )
                else:
                    bundle = self._write_failure_bundle(job=job, worker_name=worker_name, reason=result.stderr or "worker failed")
                    self._mark_failure_bundle_if_running(job.id, bundle.artifact_id)
                    self.runtime.job_queue.fail_job(job.id, reason=result.stderr or "worker failed")
                final = self.runtime.job_queue.get_job_state(job.id)
                return self._result(
                    job=job,
                    worker_name=worker_name,
                    final_status=final.current_status,
                    ran=True,
                    artifact_ids=final.artifact_ids,
                    failure_bundle_artifact_id=None,
                    reason="worker dispatched once",
                )
            finally:
                await worker.cleanup(job, result, context)  # type: ignore[arg-type]
        except Exception as exc:
            worker_name = str(getattr(worker, "name", job.type)) if worker is not None else None
            bundle = self._write_failure_bundle(job=job, worker_name=worker_name, reason=str(exc))
            self._mark_failure_bundle_if_running(job.id, bundle.artifact_id)
            current = self.runtime.job_queue.get_job_state(job.id)
            if current.current_status in {"admitted", "pending", "running"}:
                self.runtime.job_queue.quarantine_job(job.id, reason=str(exc) or "worker exception")
            final = self.runtime.job_queue.get_job_state(job.id)
            return self._result(
                job=job,
                worker_name=worker_name,
                final_status=final.current_status,
                ran=worker is not None,
                artifact_ids=final.artifact_ids,
                failure_bundle_artifact_id=bundle.artifact_id,
                reason=str(exc) or "worker exception",
            )

    def _load_dispatchable_row(self, *, job_id: str | None) -> Any:
        with self.runtime.database.connect() as connection:
            if job_id is not None:
                row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
                if row is None:
                    raise LocalJobRunnerError(f"job not found: {job_id}")
                return row
            row = connection.execute(
                """
                SELECT * FROM jobs
                WHERE current_status IN ('admitted', 'pending')
                ORDER BY created_at, job_id
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            raise LocalJobRunnerError("no admitted or pending job is available")
        return row

    def _job_from_row(self, row: Any) -> Job:
        manifest = json.loads(str(row["input_manifest_json"]))
        if not isinstance(manifest, dict):
            raise LocalJobRunnerError("job input manifest must be an object")
        inputs = dict(manifest.get("inputs", manifest)) if isinstance(manifest.get("inputs", manifest), dict) else dict(manifest)
        inputs.setdefault("dry_run", bool(row["dry_run"]))
        return Job(
            id=str(row["job_id"]),
            type=str(row["job_type"]),
            status=JobStatus(str(row["current_status"])),
            inputs=inputs,
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=None,
            max_runtime=float(manifest.get("max_runtime_seconds", 60)),
            memory_limit_mb=int(manifest.get("memory_limit_mb", 512)),
            metadata={"human_review_required": bool(row["human_review_required"])},
        )

    def _worker_context(self) -> BuiltinWorkerContext:
        return BuiltinWorkerContext(
            repo_root=self.runtime.repo_root,
            runtime_root=self.runtime.root,
            artifact_root=self.runtime.artifact_store.artifact_root,
            crash_dir=self.runtime.root / "crashes",
            database=self.runtime.database,
            sqlite_artifact_store=self.runtime.artifact_store,
            human_review_gate=self.runtime.human_review_gate,
            environment={},
        )

    def _record_result_artifacts(self, *, job: Job, result: WorkerRunResult) -> list[SQLiteArtifactRecord]:
        artifact_type = str(result.metadata.get("artifact_type", ArtifactType.MATERIALIZATION_SUMMARY.value))
        review_status = ReviewStatus.NEEDS_REVIEW if bool(result.metadata.get("requires_human_review")) else ReviewStatus.NEW
        records = []
        for path in result.artifact_paths:
            record = self.runtime.artifact_store.record_artifact(
                job_id=job.id,
                local_path=path,
                artifact_type=artifact_type,
                review_status=review_status,
                local_only=True,
                safe_to_publish=False,
            )
            self.runtime.job_queue.mark_artifact_discovered(
                job.id,
                artifact_id=record.artifact_id,
                artifact_type=artifact_type,
            )
            self.runtime.job_queue.mark_artifact_validated(
                job.id,
                artifact_id=record.artifact_id,
                validation={"passed": True, "dry_run": bool(job.inputs.get("dry_run", False))},
            )
            records.append(record)
        return records

    def _write_failure_bundle(self, *, job: Job, worker_name: str | None, reason: str) -> SQLiteArtifactRecord:
        validate_no_secret_like({"reason": reason})
        directory = self.runtime.artifact_store.artifact_root / "failure_bundles"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{job.id}.json"
        payload = {
            "created_at": utc_now_iso(),
            "job_id": job.id,
            "job_type": job.type,
            "reason": reason,
            "worker_name": worker_name or "",
            "quarantined": True,
        }
        path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return self.runtime.artifact_store.record_artifact(
            job_id=job.id,
            local_path=path,
            artifact_type=ArtifactType.FAILURE_BUNDLE,
            quarantine_status=QuarantineStatus.QUARANTINED,
            quarantine_reason=reason,
            local_only=True,
            safe_to_publish=False,
        )

    def _mark_failure_bundle_if_running(self, job_id: str, artifact_id: str) -> None:
        current = self.runtime.job_queue.get_job_state(job_id)
        if current.current_status == "running":
            self.runtime.job_queue.mark_artifact_discovered(
                job_id,
                artifact_id=artifact_id,
                artifact_type=ArtifactType.FAILURE_BUNDLE.value,
                reason="failure bundle written",
            )
            self.runtime.job_queue.mark_artifact_validated(
                job_id,
                artifact_id=artifact_id,
                validation={"passed": True, "failure_bundle": True},
                reason="failure bundle validated",
            )

    def _request_review(self, *, job_id: str, artifact_id: str, reason: str) -> None:
        reviews = self.runtime.human_review_gate.list_reviews(job_id=job_id, artifact_id=artifact_id)
        if not reviews:
            self.runtime.human_review_gate.request_review(job_id=job_id, artifact_id=artifact_id, reason=reason)

    def _quarantine_artifacts(self, records: list[SQLiteArtifactRecord], *, reason: str) -> None:
        for record in records:
            self.runtime.artifact_store.quarantine_artifact(record.artifact_id, reason=reason)

    def _result(
        self,
        *,
        job: Job,
        worker_name: str | None,
        final_status: str,
        ran: bool,
        artifact_ids: tuple[str, ...],
        failure_bundle_artifact_id: str | None,
        reason: str,
    ) -> LocalJobRunResult:
        final = self.runtime.job_queue.get_job_state(job.id)
        payload = {
            "artifact_ids": tuple(sorted(artifact_ids)),
            "dry_run": bool(job.inputs.get("dry_run", False)),
            "failure_bundle_artifact_id": failure_bundle_artifact_id or "",
            "final_claim_allowed": final.final_claim_allowed and not bool(job.inputs.get("dry_run", False)),
            "final_status": final_status,
            "job_id": job.id,
            "job_type": job.type,
            "ran": ran,
            "reason": reason,
            "worker_name": worker_name or "",
        }
        return LocalJobRunResult(
            content_hash=stable_content_hash(payload),
            artifact_ids=tuple(sorted(artifact_ids)),
            dry_run=bool(job.inputs.get("dry_run", False)),
            failure_bundle_artifact_id=failure_bundle_artifact_id,
            final_claim_allowed=bool(payload["final_claim_allowed"]),
            final_status=final_status,
            job_id=job.id,
            job_type=job.type,
            ran=ran,
            reason=reason,
            worker_name=worker_name,
        )

    def _result_from_row(
        self,
        *,
        row: Any,
        worker_name: str | None,
        final_status: str,
        ran: bool,
        artifact_ids: tuple[str, ...],
        failure_bundle_artifact_id: str | None,
        reason: str,
    ) -> LocalJobRunResult:
        dry_run = bool(row["dry_run"])
        state = self.runtime.job_queue.get_job_state(str(row["job_id"]))
        payload = {
            "artifact_ids": tuple(sorted(artifact_ids)),
            "dry_run": dry_run,
            "failure_bundle_artifact_id": failure_bundle_artifact_id or "",
            "final_claim_allowed": state.final_claim_allowed and not dry_run,
            "final_status": final_status,
            "job_id": str(row["job_id"]),
            "job_type": str(row["job_type"]),
            "ran": ran,
            "reason": reason,
            "worker_name": worker_name or "",
        }
        return LocalJobRunResult(
            content_hash=stable_content_hash(payload),
            artifact_ids=tuple(sorted(artifact_ids)),
            dry_run=dry_run,
            failure_bundle_artifact_id=failure_bundle_artifact_id,
            final_claim_allowed=bool(payload["final_claim_allowed"]),
            final_status=final_status,
            job_id=str(row["job_id"]),
            job_type=str(row["job_type"]),
            ran=ran,
            reason=reason,
            worker_name=worker_name,
        )


def _json_safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(metadata, sort_keys=True, default=str))
