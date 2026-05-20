"""Hardening tests for the brokerless OS engine job queue."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from kernel.os_engine.job_queue import (
    FSM_TRANSITIONS,
    InMemoryJobStore,
    InvalidJobTransitionError,
    Job,
    JobQueueManager,
    JobStatus,
    JobValidationError,
    UnknownJobTypeError,
)
from kernel.os_engine.worker_registry import WorkerContext, build_default_worker_registry


def _created_job(**overrides: object) -> Job:
    payload = {
        "id": "job_traceable_001",
        "type": "git",
        "status": JobStatus.CREATED,
        "inputs": {"command": ["git", "status", "--short"]},
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "max_runtime": 30.0,
        "memory_limit_mb": 256,
        "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
        "metadata": {},
    }
    payload.update(overrides)
    return Job(**payload)  # type: ignore[arg-type]


class OsEngineJobQueueTests(unittest.IsolatedAsyncioTestCase):
    def test_expected_statuses_and_transitions_are_explicit(self) -> None:
        expected = {
            "created",
            "admitted",
            "pending",
            "running",
            "succeeded",
            "failed",
            "quarantined",
            "cancelled",
            "requires_human_review",
        }
        self.assertTrue(expected.issubset({status.value for status in JobStatus}))
        self.assertIn(JobStatus.CANCELLED, FSM_TRANSITIONS[JobStatus.CREATED])
        self.assertIn(JobStatus.REQUIRES_HUMAN_REVIEW, FSM_TRANSITIONS[JobStatus.PENDING])

    def test_job_creation_is_uniquely_traceable_and_requires_manifest(self) -> None:
        first = Job.create(job_type="git", inputs={"command": ["git", "status"]}, max_runtime=5, memory_limit_mb=128)
        second = Job.create(job_type="git", inputs={"command": ["git", "status"]}, max_runtime=5, memory_limit_mb=128)
        self.assertNotEqual(first.id, second.id)
        self.assertTrue(first.id.startswith("job_"))
        self.assertEqual(first.input_manifest["command"], ["git", "status"])
        with self.assertRaises(JobValidationError):
            Job.from_dict({"id": "job_missing_manifest", "type": "git"})

    def test_job_id_job_type_and_output_dir_requirements_fail_closed(self) -> None:
        with self.assertRaises(JobValidationError):
            _created_job(id="")
        with self.assertRaises(JobValidationError):
            _created_job(type="")
        with self.assertRaises(JobValidationError):
            _created_job(inputs={"produces_artifacts": True})
        job = _created_job(inputs={"produces_artifacts": True, "output_dir": "/tmp/out"})
        self.assertEqual(job.inputs["output_dir"], "/tmp/out")

    def test_valid_and_invalid_status_transitions_are_enforced(self) -> None:
        job = _created_job()
        job.transition_to(JobStatus.ADMITTED)
        job.transition_to(JobStatus.PENDING)
        job.transition_to(JobStatus.RUNNING)
        job.transition_to(JobStatus.SUCCEEDED, completion_record={"receipt": "ok"})
        self.assertEqual(job.status, JobStatus.SUCCEEDED)

        invalid = _created_job()
        with self.assertRaises(InvalidJobTransitionError):
            invalid.transition_to(JobStatus.RUNNING)

    def test_terminal_jobs_require_auditable_reasons_or_evidence(self) -> None:
        failed = _created_job(status=JobStatus.RUNNING)
        with self.assertRaises(JobValidationError):
            failed.transition_to(JobStatus.FAILED)
        failed.transition_to(JobStatus.FAILED, reason="unit-test failure")
        self.assertEqual(failed.metadata["failure_reason"], "unit-test failure")

        quarantined = _created_job(status=JobStatus.RUNNING)
        with self.assertRaises(JobValidationError):
            quarantined.transition_to(JobStatus.QUARANTINED)
        quarantined.transition_to(JobStatus.QUARANTINED, reason="runaway")
        self.assertEqual(quarantined.metadata["quarantine_reason"], "runaway")

        succeeded = _created_job(status=JobStatus.RUNNING)
        with self.assertRaises(JobValidationError):
            succeeded.transition_to(JobStatus.SUCCEEDED)
        succeeded.transition_to(JobStatus.SUCCEEDED, artifact_refs=["artifact_001"])
        self.assertEqual(succeeded.metadata["artifact_refs"], ["artifact_001"])

    def test_cancelled_review_and_dry_run_semantics_are_auditable(self) -> None:
        cancelled = _created_job()
        with self.assertRaises(JobValidationError):
            cancelled.transition_to(JobStatus.CANCELLED)
        cancelled.transition_to(JobStatus.CANCELLED, reason="operator cancelled")
        self.assertEqual(cancelled.metadata["cancellation_reason"], "operator cancelled")

        review = _created_job(status=JobStatus.PENDING)
        review.transition_to(JobStatus.REQUIRES_HUMAN_REVIEW, reason="large artifact")
        self.assertTrue(review.human_review_required)

        with self.assertRaises(JobValidationError):
            _created_job(inputs={"dry_run": True}, metadata={"physical_proof": True})

    def test_job_records_serialize_deterministically_and_malformed_payloads_fail_closed(self) -> None:
        job = _created_job()
        encoded_once = job.to_json()
        encoded_twice = job.to_json()
        self.assertEqual(encoded_once, encoded_twice)
        self.assertEqual(json.loads(encoded_once)["id"], "job_traceable_001")
        with self.assertRaises(JobValidationError):
            Job.from_dict({"id": "job_bad", "type": "git", "status": "created"})

    def test_secret_and_env_material_is_rejected_from_payloads(self) -> None:
        for inputs in (
            {"env": {"TOKEN": "raw"}},
            {"api_key": "raw"},
            {"command": ["echo", "Bearer abcdefghijklmnopqrstuvwxyz"]},
        ):
            with self.subTest(inputs=inputs):
                with self.assertRaises(JobValidationError):
                    Job.create(job_type="git", inputs=inputs, max_runtime=5, memory_limit_mb=128)

    async def test_jobs_cannot_execute_without_being_recorded_and_unregistered_types_are_blocked(self) -> None:
        queue = JobQueueManager(
            registry=build_default_worker_registry(),
            context=WorkerContext(
                repo_root=Path.cwd(),
                artifact_root=Path(tempfile.mkdtemp()),
                crash_dir=Path(tempfile.mkdtemp()),
            ),
            store=InMemoryJobStore(),
        )
        await queue.start()
        with self.assertRaises(UnknownJobTypeError):
            await queue.submit(job_type="unknown", inputs={}, max_runtime=5, memory_limit_mb=128)
        await queue._execute("job_not_recorded", worker_id=0)
        self.assertEqual(await queue.list_jobs(), [])
        await queue.stop()


if __name__ == "__main__":
    unittest.main()
