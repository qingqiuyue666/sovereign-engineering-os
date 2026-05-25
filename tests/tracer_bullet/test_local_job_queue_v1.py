"""Tests for Local Job Queue V1."""

from __future__ import annotations

from io import StringIO
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.local_job_queue import LocalJobQueue, summarize_job_event_records
from tools.local_job_queue_viewer import main as queue_viewer_main


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "kernel" / "runtime" / "local_job_queue.py"
TOOL_PATH = ROOT / "tools" / "local_job_queue_viewer.py"
POLICY_PATH = ROOT / "governance" / "runtime" / "local_job_queue_v1.json"
DOC_PATH = ROOT / "docs" / "decisions" / "local_job_queue_v1.md"

CREATED_AT = "2026-05-25T00:00:00+00:00"
LEASED_AT = "2026-05-25T00:01:00+00:00"
HEARTBEAT_AT = "2026-05-25T00:02:00+00:00"
DONE_AT = "2026-05-25T00:03:00+00:00"


def enqueue(queue: LocalJobQueue, job_id: str = "job-001", **overrides):
    payload = {
        "job_id": job_id,
        "task_id": f"task-{job_id}",
        "command_id": "make_ci",
        "scope": "local_runner_validation",
        "priority": 10,
        "max_attempts": 2,
        "lease_timeout_seconds": 60,
        "created_at": CREATED_AT,
    }
    payload.update(overrides)
    return queue.enqueue(**payload)


class LocalJobQueueV1Tests(unittest.TestCase):
    def test_enqueue_lease_heartbeat_and_complete_flow(self) -> None:
        queue = LocalJobQueue(queue_id="queue-001")
        enqueued = enqueue(queue)
        self.assertEqual(enqueued.state, "queued")
        self.assertEqual(queue.events[0].event_type, "enqueued")

        leased = queue.lease_next(worker_id="worker-001", leased_at=LEASED_AT)
        self.assertEqual(leased.state, "leased")
        self.assertEqual(leased.attempts, 1)
        self.assertIsNotNone(leased.lease)
        original_expiry = leased.lease.expires_at

        heartbeat = queue.heartbeat(
            job_id="job-001",
            lease_id=leased.lease.lease_id,
            heartbeat_at=HEARTBEAT_AT,
        )
        self.assertGreater(heartbeat.lease.expires_at, original_expiry)

        completed = queue.complete(
            job_id="job-001",
            lease_id=heartbeat.lease.lease_id,
            completed_at=DONE_AT,
        )
        self.assertEqual(completed.state, "completed")
        self.assertEqual(queue.summary()["state_counts"]["completed"], 1)
        self.assertEqual([event.sequence for event in queue.events], [1, 2, 3, 4])

    def test_retry_policy_requeues_until_max_attempts_then_fails(self) -> None:
        queue = LocalJobQueue(queue_id="queue-001")
        enqueue(queue, max_attempts=2)
        first_lease = queue.lease_next(worker_id="worker-001", leased_at=LEASED_AT)
        retry = queue.fail(
            job_id="job-001",
            lease_id=first_lease.lease.lease_id,
            reason="validation_failed",
            failed_at=DONE_AT,
        )
        self.assertEqual(retry.state, "queued")
        self.assertEqual(queue.events[-1].event_type, "retry_scheduled")

        second_lease = queue.lease_next(worker_id="worker-001", leased_at="2026-05-25T00:04:00+00:00")
        failed = queue.fail(
            job_id="job-001",
            lease_id=second_lease.lease.lease_id,
            reason="validation_failed_again",
            failed_at="2026-05-25T00:05:00+00:00",
        )
        self.assertEqual(failed.state, "failed")
        self.assertEqual(failed.terminal_reason, "validation_failed_again")
        self.assertEqual(queue.summary()["state_counts"]["failed"], 1)

    def test_cancel_and_invalid_transitions_fail_closed(self) -> None:
        queue = LocalJobQueue(queue_id="queue-001")
        enqueue(queue)
        canceled = queue.cancel(
            job_id="job-001",
            reason="operator_cancelled",
            canceled_at=LEASED_AT,
        )
        self.assertEqual(canceled.state, "canceled")
        with self.assertRaisesRegex(ValueError, "terminal_job_cannot_cancel"):
            queue.cancel(job_id="job-001", reason="again", canceled_at=DONE_AT)
        with self.assertRaisesRegex(ValueError, "no_queued_jobs"):
            queue.lease_next(worker_id="worker-001", leased_at=DONE_AT)

    def test_timeout_classification_is_read_only(self) -> None:
        queue = LocalJobQueue(queue_id="queue-001")
        enqueue(queue, lease_timeout_seconds=10)
        leased = queue.lease_next(worker_id="worker-001", leased_at=LEASED_AT)
        before_event_count = len(queue.events)
        classifications = queue.classify_expired_leases(now="2026-05-25T00:01:11+00:00")
        self.assertEqual(len(classifications), 1)
        self.assertEqual(classifications[0].classification, "expired_lease_retryable")
        self.assertTrue(classifications[0].retry_allowed)
        self.assertEqual(len(queue.events), before_event_count)
        self.assertEqual(queue._get_job(leased.descriptor.job_id).state, "leased")

    def test_append_only_events_and_read_only_summary(self) -> None:
        queue = LocalJobQueue(queue_id="queue-001")
        enqueue(queue)
        first_event = queue.events[0]
        leased = queue.lease_next(worker_id="worker-001", leased_at=LEASED_AT)
        queue.complete(job_id="job-001", lease_id=leased.lease.lease_id, completed_at=DONE_AT)
        self.assertEqual(queue.events[0], first_event)

        records = [event.as_dict() for event in queue.events]
        summary = summarize_job_event_records(records)
        self.assertEqual(summary["event_count"], 3)
        self.assertEqual(summary["job_count"], 1)
        self.assertEqual(summary["state_counts"]["completed"], 1)

    def test_cli_visibility_reads_events_without_mutation(self) -> None:
        queue = LocalJobQueue(queue_id="queue-001")
        enqueue(queue)
        records = [event.as_dict() for event in queue.events]
        with tempfile.TemporaryDirectory() as tmp:
            events_path = Path(tmp) / "events.json"
            events_path.write_text(json.dumps(records), encoding="utf-8")
            out = StringIO()
            result = queue_viewer_main(["--events", str(events_path)], stdout=out)
        self.assertEqual(result, 0)
        rendered = json.loads(out.getvalue())
        self.assertEqual(rendered["state_counts"]["queued"], 1)

    def test_policy_doc_and_source_exclude_forbidden_runtime_surfaces(self) -> None:
        policy_text = POLICY_PATH.read_text(encoding="utf-8")
        doc_text = " ".join(DOC_PATH.read_text(encoding="utf-8").lower().split())
        source = SOURCE_PATH.read_text(encoding="utf-8") + TOOL_PATH.read_text(encoding="utf-8")
        for fragment in (
            '"job_execution_authorized": false',
            '"background_daemon_authorized": false',
            '"unbounded_scheduler_authorized": false',
            '"network_authorized": false',
            '"browser_authorized": false',
            '"provider_api_authorized": false',
            '"arbitrary_shell_authorized": false',
        ):
            self.assertIn(fragment, policy_text)
        for phrase in (
            "does not execute jobs",
            "starts no background daemon",
            "owns no unbounded scheduler",
            "calls no provider api",
            "integration with runner execution or token consumption must wait",
        ):
            self.assertIn(phrase, doc_text)
        for marker in (
            "subprocess",
            "shell=True",
            "os.system",
            "socket",
            "requests",
            "httpx",
            "urllib",
            "webbrowser",
            "playwright",
            "threading",
            "import sched",
            "time.sleep",
            "while True",
            "api_key",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
