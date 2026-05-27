"""Tests for Durable Job Queue Contract V1."""

from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from kernel.runtime import durable_job_queue_contract as contract


SOURCE_PATH = Path("kernel/runtime/durable_job_queue_contract.py")


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _event(
    sequence: int,
    event_type: str,
    previous_event_hash: str | None,
    **overrides: object,
) -> contract.DurableQueueEvent:
    payload: dict[str, object] = {
        "queue_event_id": f"queue-event-{sequence}",
        "queue_contract_version": contract.DURABLE_JOB_QUEUE_CONTRACT_VERSION,
        "sequence": sequence,
        "previous_event_hash": previous_event_hash,
        "event_type": event_type,
        "job_id": "job-001",
        "task_id": "task-001",
        "run_id": "run-001",
        "worker_id": "",
        "idempotency_key_hash": _hash("idempotency"),
        "payload_hash": _hash("payload"),
        "attempt": 0,
        "max_attempts": 2,
        "lease_id": "",
        "lease_expires_at": "",
        "retry_after": "",
        "cancellation_requested": False,
        "dead_letter_reason": "",
        "wal_record_hash": _hash(f"wal-{sequence}"),
        "human_invoked": True,
        "occurred_at": "2026-05-27T00:00:00Z",
    }
    if event_type in {"JOB_LEASED", "JOB_HEARTBEAT"}:
        payload.update(
            {
                "worker_id": "worker-001",
                "attempt": 1,
                "lease_id": "lease-001",
                "lease_expires_at": "2026-05-27T00:05:00Z",
            }
        )
    if event_type == "JOB_FAILED_RETRYABLE":
        payload.update({"attempt": 1, "retry_after": "2026-05-27T00:06:00Z"})
    if event_type == "JOB_FAILED_TERMINAL":
        payload.update({"attempt": 2})
    if event_type == "JOB_CANCELLATION_REQUESTED":
        payload.update({"cancellation_requested": True})
    if event_type == "JOB_DEAD_LETTERED":
        payload.update({"attempt": 2, "dead_letter_reason": "max_attempts_exhausted"})
    payload.update(overrides)
    return contract.DurableQueueEvent(**payload)  # type: ignore[arg-type]


class DurableJobQueueContractV1Tests(unittest.TestCase):
    def test_event_hash_is_deterministic_and_excludes_occurred_at(self) -> None:
        event = _event(1, "JOB_SUBMITTED", None)
        later = _event(1, "JOB_SUBMITTED", None, occurred_at="2030-01-01T00:00:00Z")

        self.assertEqual(event.event_hash, contract.compute_durable_queue_event_hash(event))
        self.assertEqual(event.event_hash, later.event_hash)

    def test_valid_submit_queue_lease_success_projection(self) -> None:
        first = _event(1, "JOB_SUBMITTED", None)
        second = _event(2, "JOB_QUEUED", first.event_hash)
        third = _event(3, "JOB_LEASED", second.event_hash)
        fourth = _event(4, "JOB_SUCCEEDED", third.event_hash, attempt=1)

        projection = contract.project_durable_queue_events((first, second, third, fourth))

        self.assertTrue(projection.accepted)
        self.assertEqual(len(projection.projected_jobs), 1)
        self.assertEqual(projection.projected_jobs[0].state, "succeeded")
        self.assertEqual(
            projection.projection_hash,
            contract.compute_durable_queue_projection_hash(projection),
        )

    def test_projection_detects_sequence_gap_and_previous_hash_mismatch(self) -> None:
        first = _event(1, "JOB_SUBMITTED", None)
        third = _event(3, "JOB_QUEUED", _hash("wrong-previous"))

        projection = contract.project_durable_queue_events((first, third))

        self.assertFalse(projection.accepted)
        self.assertIn("queue_sequence_gap_detected", projection.rejection_reasons)
        self.assertIn("previous_event_hash_mismatch", projection.rejection_reasons)

    def test_projection_rejects_invalid_transition_and_terminal_mutation(self) -> None:
        first = _event(1, "JOB_SUBMITTED", None)
        invalid = _event(2, "JOB_SUCCEEDED", first.event_hash)

        invalid_projection = contract.project_durable_queue_events((first, invalid))

        self.assertFalse(invalid_projection.accepted)
        self.assertIn("queue_transition_invalid", invalid_projection.rejection_reasons)

        queued = _event(2, "JOB_QUEUED", first.event_hash)
        leased = _event(3, "JOB_LEASED", queued.event_hash)
        succeeded = _event(4, "JOB_SUCCEEDED", leased.event_hash, attempt=1)
        cancelled = _event(5, "JOB_CANCELLED", succeeded.event_hash)
        terminal_projection = contract.project_durable_queue_events(
            (first, queued, leased, succeeded, cancelled)
        )
        self.assertFalse(terminal_projection.accepted)
        self.assertIn("terminal_job_cannot_transition", terminal_projection.rejection_reasons)

    def test_retry_and_dead_letter_contracts_are_explicit(self) -> None:
        first = _event(1, "JOB_SUBMITTED", None)
        queued = _event(2, "JOB_QUEUED", first.event_hash)
        leased = _event(3, "JOB_LEASED", queued.event_hash)
        retry = _event(4, "JOB_FAILED_RETRYABLE", leased.event_hash)
        leased_again = _event(5, "JOB_LEASED", retry.event_hash, lease_id="lease-002")
        dead = _event(6, "JOB_DEAD_LETTERED", leased_again.event_hash)

        projection = contract.project_durable_queue_events(
            (first, queued, leased, retry, leased_again, dead)
        )

        self.assertTrue(projection.accepted)
        self.assertEqual(projection.projected_jobs[0].state, "dead_lettered")
        self.assertEqual(
            projection.projected_jobs[0].dead_letter_reason,
            "max_attempts_exhausted",
        )

    def test_retryable_failure_at_max_attempts_rejected(self) -> None:
        first = _event(1, "JOB_SUBMITTED", None)
        queued = _event(2, "JOB_QUEUED", first.event_hash)
        leased = _event(3, "JOB_LEASED", queued.event_hash)
        retry = _event(4, "JOB_FAILED_RETRYABLE", leased.event_hash, attempt=2)

        projection = contract.project_durable_queue_events((first, queued, leased, retry))

        self.assertFalse(projection.accepted)
        self.assertIn(
            "retryable_failure_requires_remaining_attempts",
            projection.rejection_reasons,
        )

    def test_lease_event_requires_human_invoked_marker(self) -> None:
        with self.assertRaisesRegex(ValueError, "lease_event_requires_human_invoked"):
            _event(
                1,
                "JOB_LEASED",
                None,
                worker_id="worker-001",
                lease_id="lease-001",
                lease_expires_at="2026-05-27T00:05:00Z",
                human_invoked=False,
            )

    def test_mapping_rejects_execution_and_secret_surfaces(self) -> None:
        base = _event(1, "JOB_SUBMITTED", None).as_dict()
        for field_name in ("argv", "command_line", "raw_stdout", "stderr", "api_key"):
            payload = dict(base)
            payload[field_name] = "blocked"
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "queue_event_field_forbidden"):
                    contract.validate_durable_queue_event(payload)

    def test_event_hash_mismatch_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "event_hash_mismatch"):
            _event(1, "JOB_SUBMITTED", None, event_hash=_hash("wrong"))

    def test_source_has_no_forbidden_runtime_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        forbidden = {
            "argparse",
            "asyncio",
            "click",
            "httpx",
            "mcp",
            "openai",
            "playwright",
            "requests",
            "schedule",
            "selenium",
            "socket",
            "sqlite3",
            "subprocess",
            "threading",
            "typer",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imported_roots.intersection(forbidden))
        self.assertNotIn("while True", source)


if __name__ == "__main__":
    unittest.main()
