"""Tests for the one-job local dispatch loop."""

from __future__ import annotations

import tempfile
import unittest
import warnings
from pathlib import Path

from kernel.os_engine.local_job_runner import LocalJobRunner, LocalJobRunnerError
from kernel.os_engine.local_os_runtime import LocalOSRuntime
from kernel.os_engine.sqlite_artifact_store import ArtifactType


class OSEngineLocalJobRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _runtime(self, name: str = "runtime") -> LocalOSRuntime:
        return LocalOSRuntime(root=self.root / name, repo_root=Path.cwd())

    def _admit(self, runtime: LocalOSRuntime, *, job_id: str, job_type: str, inputs: dict[str, object] | None = None, human_review_required: bool = False, dry_run: bool = False) -> None:
        runtime.job_queue.create_job(
            job_id=job_id,
            job_type=job_type,
            input_manifest={"inputs": inputs or {}, "max_runtime_seconds": 30, "memory_limit_mb": 256},
            output_dir=str(runtime.artifact_store.artifact_root),
            human_review_required=human_review_required,
            dry_run=dry_run,
        )
        runtime.job_queue.admit_job(job_id)
        runtime.job_queue.enqueue_job(job_id)

    def test_successful_context_pack_job_path(self) -> None:
        with self._runtime() as runtime:
            self._admit(runtime, job_id="job_context", job_type="context_pack", inputs={"changed_files_only": False, "max_files": 4})
            result = LocalJobRunner(runtime).run_next(job_id="job_context")
            self.assertEqual(result.final_status, "succeeded")
            self.assertTrue(result.artifact_ids)
            self.assertEqual(runtime.artifact_store.list_artifacts(job_id="job_context")[0].artifact_type, ArtifactType.CONTEXT_PACKET.value)

    def test_git_status_job_path(self) -> None:
        with self._runtime("git") as runtime:
            self._admit(runtime, job_id="job_git", job_type="git_status", inputs={"dry_run_git_status": True})
            result = LocalJobRunner(runtime).run_next(job_id="job_git")
            self.assertEqual(result.final_status, "succeeded")
            self.assertEqual(runtime.job_queue.get_job_state("job_git").worker_name, "GitStatusWorker")

    def test_hfx_008_materialization_dry_run_path(self) -> None:
        with self._runtime("hfx") as runtime:
            self._admit(
                runtime,
                job_id="job_hfx",
                job_type="hfx_008_materialization_dry_run",
                inputs={"stage": "single_frame_proof", "dry_run": True},
                human_review_required=True,
                dry_run=True,
            )
            result = LocalJobRunner(runtime).run_next(job_id="job_hfx")
            self.assertEqual(result.final_status, "requires_human_review")
            self.assertFalse(result.final_claim_allowed)

    def test_worker_failure_and_unregistered_worker_write_failure_bundles(self) -> None:
        with self._runtime("failure") as runtime:
            self._admit(runtime, job_id="job_bad_review", job_type="artifact_review", inputs={"artifact_id": "missing"})
            result = LocalJobRunner(runtime).run_next(job_id="job_bad_review")
            self.assertEqual(result.final_status, "quarantined")
            self.assertIsNotNone(result.failure_bundle_artifact_id)
            self.assertTrue(any(item.artifact_type == ArtifactType.FAILURE_BUNDLE.value for item in runtime.artifact_store.list_artifacts(job_id="job_bad_review")))

            self._admit(runtime, job_id="job_missing_worker", job_type="missing_worker")
            result = LocalJobRunner(runtime).run_next(job_id="job_missing_worker")
            self.assertEqual(result.final_status, "failed")
            self.assertIsNotNone(result.failure_bundle_artifact_id)

    def test_missing_and_terminal_jobs_are_not_run(self) -> None:
        with self._runtime("terminal") as runtime:
            with self.assertRaises(LocalJobRunnerError):
                LocalJobRunner(runtime).run_next(job_id="missing")
            self._admit(runtime, job_id="job_git", job_type="git_status", inputs={"dry_run_git_status": True})
            runner = LocalJobRunner(runtime)
            runner.run_next(job_id="job_git")
            second = runner.run_next(job_id="job_git")
            self.assertFalse(second.ran)
            self.assertEqual(second.reason, "terminal job was not rerun")

    def test_replay_after_db_reopen_preserves_final_state(self) -> None:
        runtime = self._runtime("reopen")
        self._admit(runtime, job_id="job_git", job_type="git_status", inputs={"dry_run_git_status": True})
        LocalJobRunner(runtime).run_next(job_id="job_git")
        first = runtime.job_queue.get_job_state("job_git").content_hash
        runtime.close()
        reopened = self._runtime("reopen")
        try:
            self.assertEqual(first, reopened.job_queue.get_job_state("job_git").content_hash)
        finally:
            reopened.close()

    def test_runner_emits_no_resourcewarning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", ResourceWarning)
            with self._runtime("warnings") as runtime:
                self._admit(runtime, job_id="job_git", job_type="git_status", inputs={"dry_run_git_status": True})
                LocalJobRunner(runtime).run_next(job_id="job_git")


if __name__ == "__main__":
    unittest.main()
