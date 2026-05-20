"""Tests for safe built-in local workers."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from kernel.os_engine.builtin_workers import (
    ArtifactReviewWorker,
    ContextPackWorker,
    GitStatusWorker,
    Hfx008MaterializationDryRunWorker,
    build_builtin_worker_registry,
)
from kernel.os_engine.job_queue import Job, JobStatus, JobValidationError, UnknownJobTypeError
from kernel.os_engine.local_job_runner import LocalJobRunner
from kernel.os_engine.local_os_runtime import LocalOSRuntime
from kernel.os_engine.sqlite_artifact_store import ArtifactType


def _job(worker_type: str, *, job_id: str = "job_worker") -> Job:
    return Job(
        id=job_id,
        type=worker_type,
        status=JobStatus.PENDING,
        inputs={},
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        max_runtime=5,
        memory_limit_mb=128,
    )


class OSEngineBuiltinWorkersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_all_builtin_workers_register_and_reject_duplicates(self) -> None:
        registry = build_builtin_worker_registry()
        self.assertEqual(
            registry.registered_types(),
            ["artifact_review", "context_pack", "git_status", "hfx_008_materialization_dry_run"],
        )
        with self.assertRaises(ValueError):
            registry.register("git_status", GitStatusWorker())
        with self.assertRaises(UnknownJobTypeError):
            registry.get("missing")

    def test_workers_require_job_id(self) -> None:
        for worker in (GitStatusWorker(), ContextPackWorker(), ArtifactReviewWorker(), Hfx008MaterializationDryRunWorker()):
            with self.assertRaises(JobValidationError):
                _job("git_status", job_id="")
                self.fail("empty job id should fail before worker execution")

    def test_git_status_worker_writes_structured_artifact_and_events(self) -> None:
        with LocalOSRuntime(root=self.root, repo_root=Path.cwd()) as runtime:
            runtime.job_queue.create_job(
                job_id="job_git_status",
                job_type="git_status",
                input_manifest={"inputs": {"dry_run_git_status": True}},
                output_dir=str(runtime.artifact_store.artifact_root / "git_status"),
            )
            runtime.job_queue.admit_job("job_git_status")
            runtime.job_queue.enqueue_job("job_git_status")
            result = LocalJobRunner(runtime).run_next(job_id="job_git_status")
            self.assertEqual(result.final_status, "succeeded")
            events = [event.event_type for event in runtime.event_log.get_events("job_git_status")]
            self.assertIn("WorkerSelected", events)
            self.assertIn("ArtifactDiscovered", events)
            artifacts = runtime.artifact_store.list_artifacts(job_id="job_git_status")
            self.assertEqual(artifacts[0].artifact_type, ArtifactType.AUDIT_JSON.value)

    def test_hfx_dry_run_worker_cannot_claim_physical_proof_or_final_claim(self) -> None:
        with LocalOSRuntime(root=self.root, repo_root=Path.cwd()) as runtime:
            runtime.job_queue.create_job(
                job_id="job_hfx",
                job_type="hfx_008_materialization_dry_run",
                input_manifest={"inputs": {"stage": "single_frame_proof", "dry_run": True}},
                human_review_required=True,
                dry_run=True,
            )
            runtime.job_queue.admit_job("job_hfx")
            runtime.job_queue.enqueue_job("job_hfx")
            result = LocalJobRunner(runtime).run_next(job_id="job_hfx")
            self.assertEqual(result.final_status, "requires_human_review")
            self.assertFalse(result.final_claim_allowed)
            artifact_text = Path(runtime.artifact_store.list_artifacts(job_id="job_hfx")[0].local_path).read_text(encoding="utf-8")
            self.assertIn('"physical_proof_created": false', artifact_text)
            self.assertIn('"final_claim_allowed": false', artifact_text)

    def test_no_forbidden_execution_surface_in_builtin_workers(self) -> None:
        source = Path("kernel/os_engine/builtin_workers.py").read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urlopen", source)
        self.assertNotIn("QApplication(", source)


if __name__ == "__main__":
    unittest.main()
