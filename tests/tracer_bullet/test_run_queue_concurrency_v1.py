"""Tests for run queue and bounded concurrency."""

from __future__ import annotations

from threading import Lock
from time import sleep
import unittest

from execution_plane.permits.builder import create_execution_permit
from execution_plane.runtime.run_queue import InMemoryRunQueue
from execution_plane.runtime.worker_pool import run_bounded_jobs


class RunQueueConcurrencyV1Tests(unittest.TestCase):
    def test_queue_can_enqueue_inspect_and_cancel(self) -> None:
        queue = InMemoryRunQueue()
        job = queue.enqueue(_permit("fake_dcc", "smoke_generate_file"))
        self.assertEqual(queue.inspect(job.job_id)["status"], "QUEUED")
        self.assertTrue(queue.cancel(job.job_id))
        self.assertEqual(queue.inspect(job.job_id)["status"], "CANCELED")

    def test_worker_pool_enforces_per_adapter_budget(self) -> None:
        token = _permit("fake_dcc", "smoke_generate_file")
        token["concurrency"] = {
            "max_global_jobs": 3,
            "max_per_adapter_jobs": {
                "fake_dcc": 1,
                "houdini_hython": 1,
                "comfyui_local": 2,
                "davinci_resolve": 1,
            },
        }
        from execution_plane.permits.digest import attach_permit_digest

        token = attach_permit_digest(token)
        running = {"fake_dcc": 0}
        max_seen = {"fake_dcc": 0}
        lock = Lock()

        def dispatch(job):
            with lock:
                running["fake_dcc"] += 1
                max_seen["fake_dcc"] = max(max_seen["fake_dcc"], running["fake_dcc"])
            sleep(0.02)
            with lock:
                running["fake_dcc"] -= 1
            return {"job_id": job["job_id"], "status": "SUCCEEDED"}

        jobs = [{"job_id": f"job_{index}", "adapter": "fake_dcc"} for index in range(4)]
        results = run_bounded_jobs(jobs, token, dispatch)
        self.assertEqual(len(results), 4)
        self.assertEqual(max_seen["fake_dcc"], 1)


def _permit(adapter: str, action: str) -> dict[str, object]:
    return create_execution_permit(
        task_id="TASK_QUEUE",
        operator_approval_id="RCPT_QUEUE",
        allowed_adapter=adapter,
        allowed_action=action,
        allowed_output_root="work/run_queue_test",
        expires_at="2099-01-01T00:00:00Z",
    )


if __name__ == "__main__":
    unittest.main()
