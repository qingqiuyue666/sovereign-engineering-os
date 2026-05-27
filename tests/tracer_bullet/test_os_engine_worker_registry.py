"""Hardening tests for OS engine worker registry contracts."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from kernel.os_engine.job_queue import Job, JobStatus, JobValidationError, UnknownJobTypeError
from kernel.os_engine.worker_registry import (
    BaseWorker,
    GitWorker,
    WorkerAdmissionDecision,
    WorkerAdmissionError,
    WorkerContext,
    WorkerRegistry,
    WorkerRunResult,
    build_default_worker_registry,
    evaluate_worker_admission,
)


def _job(job_id: str = "job_worker_001") -> Job:
    return Job(
        id=job_id,
        type="git",
        status=JobStatus.CREATED,
        inputs={"command": ["git", "status", "--short"]},
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        max_runtime=5,
        memory_limit_mb=128,
    )


class UnsupportedCapabilityWorker(BaseWorker):
    name = "UnsupportedCapabilityWorker"
    capabilities = frozenset({"teleport"})

    async def run(self, job: Job, context: WorkerContext) -> WorkerRunResult:
        return WorkerRunResult(succeeded=True, quarantined=False)


class IncompleteWorker:
    name = "IncompleteWorker"


class OsEngineWorkerRegistryTests(unittest.IsolatedAsyncioTestCase):
    def test_unregistered_and_duplicate_worker_registration_fail_closed(self) -> None:
        registry = WorkerRegistry()
        registry.register("git", GitWorker())
        with self.assertRaises(ValueError):
            registry.register("git", GitWorker())
        with self.assertRaises(UnknownJobTypeError):
            registry.get("missing")

    def test_worker_must_declare_required_contract_fields_and_supported_capabilities(self) -> None:
        registry = WorkerRegistry()
        with self.assertRaises(WorkerAdmissionError):
            registry.register("bad", IncompleteWorker())  # type: ignore[arg-type]
        with self.assertRaises(WorkerAdmissionError):
            registry.register("unsupported", UnsupportedCapabilityWorker())

        worker = GitWorker()
        self.assertEqual(worker.name, "GitWorker")
        self.assertIn("git_read", worker.capabilities)
        self.assertTrue(worker.safety_boundary)
        self.assertFalse(worker.can_create_large_artifacts)
        self.assertFalse(worker.human_review_required)

    def test_worker_admission_decision_records_rejections_without_mutation(self) -> None:
        accepted = evaluate_worker_admission("git", GitWorker())
        rejected = evaluate_worker_admission("bad", UnsupportedCapabilityWorker())
        duplicate = evaluate_worker_admission(
            "git",
            GitWorker(),
            registered_types=("git",),
        )

        self.assertIsInstance(accepted, WorkerAdmissionDecision)
        self.assertTrue(accepted.accepted)
        self.assertTrue(accepted.content_hash.startswith("sha256:"))
        self.assertFalse(rejected.accepted)
        self.assertIn("unsupported_capability:teleport", rejected.reason_codes)
        self.assertFalse(duplicate.accepted)
        self.assertIn("duplicate_worker_type", duplicate.reason_codes)

    async def test_worker_must_not_run_without_job_id(self) -> None:
        worker = GitWorker()
        context = WorkerContext(
            repo_root=Path.cwd(),
            artifact_root=Path(tempfile.mkdtemp()),
            crash_dir=Path(tempfile.mkdtemp()),
        )
        with self.assertRaises(JobValidationError):
            await worker.preflight(_job(job_id=""), context)

    async def test_worker_result_is_structured_and_success_requires_output_validation(self) -> None:
        worker = GitWorker()
        context = WorkerContext(
            repo_root=Path.cwd(),
            artifact_root=Path(tempfile.mkdtemp()),
            crash_dir=Path(tempfile.mkdtemp()),
        )
        result = WorkerRunResult(succeeded=True, quarantined=False, exit_code=0)
        await worker.validate_outputs(_job(), result, context)
        self.assertTrue(result.succeeded)

        bad = WorkerRunResult(succeeded=True, quarantined=False, exit_code=2)
        with self.assertRaises(WorkerAdmissionError):
            await worker.validate_outputs(_job(), bad, context)

    async def test_command_worker_records_watchdog_receipt_artifact(self) -> None:
        worker = GitWorker()
        context = WorkerContext(
            repo_root=Path.cwd(),
            artifact_root=Path(tempfile.mkdtemp()),
            crash_dir=Path(tempfile.mkdtemp()),
        )

        result = await worker.run(_job(), context)

        self.assertTrue(result.succeeded)
        receipt_path = Path(str(result.metadata["watchdog_receipt_path"]))
        self.assertTrue(receipt_path.exists())
        self.assertTrue(receipt_path.is_relative_to(context.artifact_root.resolve()))
        self.assertIn(receipt_path, result.artifact_paths)
        self.assertEqual(
            result.metadata["watchdog_receipt_type"],
            "os_engine_process_watchdog_receipt_v1",
        )

    async def test_worker_failure_quarantines_and_cannot_bypass_queue_semantics(self) -> None:
        worker = GitWorker()
        context = WorkerContext(
            repo_root=Path.cwd(),
            artifact_root=Path(tempfile.mkdtemp()),
            crash_dir=Path(tempfile.mkdtemp()),
        )
        result = await worker.quarantine_failure(_job(), RuntimeError("boom"), context)
        self.assertTrue(result.quarantined)
        self.assertFalse(result.succeeded)
        self.assertIn("boom", result.stderr)
        with self.assertRaises(WorkerAdmissionError):
            await worker.preflight(
                Job(
                    id="job_mutating",
                    type="git",
                    status=JobStatus.CREATED,
                    inputs={"command": ["git", "commit", "-m", "nope"]},
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                    max_runtime=5,
                    memory_limit_mb=128,
                ),
                context,
            )

    def test_registry_serializes_deterministic_capability_reports(self) -> None:
        registry = build_default_worker_registry()
        once = registry.capability_report_json()
        twice = registry.capability_report_json()
        self.assertEqual(once, twice)
        report = json.loads(once)
        self.assertTrue(any(item["name"] == "GitWorker" for item in report))
        self.assertTrue(any(item["human_review_required"] for item in report))

    def test_registry_serializes_deterministic_admission_reports(self) -> None:
        registry = build_default_worker_registry()
        once = registry.admission_report_json()
        twice = registry.admission_report_json()

        self.assertEqual(once, twice)
        report = json.loads(once)
        git_entries = [item for item in report if item["worker_type"] == "git"]
        self.assertEqual(len(git_entries), 1)
        self.assertTrue(git_entries[0]["accepted"])
        self.assertTrue(git_entries[0]["content_hash"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
