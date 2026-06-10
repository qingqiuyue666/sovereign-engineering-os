"""Behavior tests for durable run queue and worker pool runtime."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from threading import Lock
from time import sleep

from creative.common import write_json
from execution_plane.permits.builder import create_execution_permit
from execution_plane.permits.digest import attach_permit_digest
from execution_plane.runtime.run_queue import FileRunQueue
from execution_plane.runtime.worker_pool import run_bounded_jobs


class RunQueueWorkerPoolV1Tests(unittest.TestCase):
    def test_enqueue_list_inspect_and_cancel(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            template = _template(Path(tempdir) / "template.json")
            queue = FileRunQueue(Path(tempdir) / "queue")
            run = queue.enqueue_rpc_template(template)
            listed = queue.list_runs()
            inspected = queue.inspect(run["run_id"])
            canceled = queue.cancel(run["run_id"])
            ledger = Path(tempdir) / "queue" / run["run_id"] / "state_ledger.jsonl"
            ledger_lines = ledger.read_text(encoding="utf-8").splitlines()
        self.assertEqual(listed[0]["status"], "QUEUED")
        self.assertEqual(inspected["status"], "QUEUED")
        self.assertEqual(canceled["status"], "CANCELED")
        self.assertEqual([json.loads(line)["state"] for line in ledger_lines], ["QUEUED", "CANCELED"])

    def test_worker_claims_job_and_records_success_terminal_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            template = _template(Path(tempdir) / "template.json")
            queue = FileRunQueue(Path(tempdir) / "queue")
            run = queue.enqueue_rpc_template(template)

            def dispatch(_path: Path) -> dict[str, object]:
                return {"jsonrpc": "2.0", "result": {"terminal_status": "TERMINAL_SUCCEEDED"}}

            finished = queue.process_next(dispatch=dispatch)
            inspected = queue.inspect(run["run_id"])
        self.assertEqual(finished["status"], "SUCCEEDED")
        self.assertEqual(inspected["status"], "SUCCEEDED")
        self.assertEqual(
            [event["state"] for event in inspected["state_transitions"]],
            ["QUEUED", "RUNNING", "SUCCEEDED"],
        )

    def test_worker_records_failure_terminal_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            template = _template(Path(tempdir) / "template.json")
            queue = FileRunQueue(Path(tempdir) / "queue")
            run = queue.enqueue_rpc_template(template)

            def dispatch(_path: Path) -> dict[str, object]:
                return {"jsonrpc": "2.0", "result": {"terminal_status": "TERMINAL_FAILED"}}

            finished = queue.process_next(dispatch=dispatch)
            inspected = queue.inspect(run["run_id"])
        self.assertEqual(finished["status"], "FAILED")
        self.assertEqual(inspected["status"], "FAILED")

    def test_worker_records_timeout_transition_and_failure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            template = _template(Path(tempdir) / "template.json")
            queue = FileRunQueue(Path(tempdir) / "queue")
            run = queue.enqueue_rpc_template(template)

            def dispatch(_path: Path) -> dict[str, object]:
                raise TimeoutError("deadline")

            finished = queue.process_next(dispatch=dispatch)
            bundle = json.loads(
                (Path(tempdir) / "queue" / run["run_id"] / "failure_bundle.json").read_text(encoding="utf-8")
            )
        self.assertEqual(finished["status"], "TIMED_OUT")
        self.assertIn("TIMEOUT", bundle["error"])

    def test_queue_order_is_fifo(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            first = _template(Path(tempdir) / "first.json", request_id="first")
            second = _template(Path(tempdir) / "second.json", request_id="second")
            queue = FileRunQueue(Path(tempdir) / "queue")
            first_run = queue.enqueue_rpc_template(first)
            second_run = queue.enqueue_rpc_template(second)
            seen: list[str] = []

            def dispatch(path: Path) -> dict[str, object]:
                payload = json.loads(Path(path).read_text(encoding="utf-8"))
                seen.append(str(payload["id"]))
                return {"jsonrpc": "2.0", "result": {"terminal_status": "TERMINAL_SUCCEEDED"}}

            queue.process_next(dispatch=dispatch)
            queue.process_next(dispatch=dispatch)
        self.assertEqual(seen, ["first", "second"])
        self.assertNotEqual(first_run["run_id"], second_run["run_id"])

    def test_worker_pool_enforces_global_budget(self) -> None:
        token = _permit_with_concurrency(max_global=1, fake_budget=2, comfy_budget=2)
        running = {"total": 0}
        max_seen = {"total": 0}
        lock = Lock()

        def dispatch(job: dict[str, object]) -> dict[str, object]:
            with lock:
                running["total"] += 1
                max_seen["total"] = max(max_seen["total"], running["total"])
            sleep(0.02)
            with lock:
                running["total"] -= 1
            return {"job_id": job["job_id"], "status": "SUCCEEDED"}

        jobs = [
            {"job_id": "a", "adapter": "fake_dcc"},
            {"job_id": "b", "adapter": "comfyui_local"},
        ]
        results = run_bounded_jobs(jobs, token, dispatch)
        self.assertEqual(len(results), 2)
        self.assertEqual(max_seen["total"], 1)

    def test_worker_pool_enforces_per_adapter_budget(self) -> None:
        token = _permit_with_concurrency(max_global=3, fake_budget=1, comfy_budget=2)
        running = {"fake_dcc": 0}
        max_seen = {"fake_dcc": 0}
        lock = Lock()

        def dispatch(job: dict[str, object]) -> dict[str, object]:
            adapter = str(job["adapter"])
            with lock:
                running[adapter] += 1
                max_seen[adapter] = max(max_seen[adapter], running[adapter])
            sleep(0.02)
            with lock:
                running[adapter] -= 1
            return {"job_id": job["job_id"], "status": "SUCCEEDED"}

        jobs = [{"job_id": f"fake_{index}", "adapter": "fake_dcc"} for index in range(3)]
        results = run_bounded_jobs(jobs, token, dispatch)
        self.assertEqual(len(results), 3)
        self.assertEqual(max_seen["fake_dcc"], 1)


def _template(path: Path, *, request_id: str = "queue-test") -> Path:
    write_json(
        path,
        {
            "id": request_id,
            "jsonrpc": "2.0",
            "method": "adapter.execute",
            "params": {
                "adapter": "fake_dcc",
                "action": "smoke_generate_file",
                "output_root": "work/run_queue_worker_pool_test",
            },
        },
    )
    return path


def _permit_with_concurrency(*, max_global: int, fake_budget: int, comfy_budget: int) -> dict[str, object]:
    permit = create_execution_permit(
        task_id="TASK_QUEUE_POOL",
        operator_approval_id="RCPT_QUEUE_POOL",
        allowed_adapter="fake_dcc",
        allowed_action="smoke_generate_file",
        allowed_output_root="work/run_queue_worker_pool_test",
        expires_at="2099-01-01T00:00:00Z",
    )
    permit["concurrency"] = {
        "max_global_jobs": max_global,
        "max_per_adapter_jobs": {
            "fake_dcc": fake_budget,
            "houdini_hython": 1,
            "comfyui_local": comfy_budget,
            "davinci_resolve": 1,
        },
    }
    return attach_permit_digest(permit)


if __name__ == "__main__":
    unittest.main()
