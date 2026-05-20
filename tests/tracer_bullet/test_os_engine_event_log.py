"""Tracer bullet tests for the append-only OS engine event log."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.database import OSDatabase, UnsafePayloadError
from kernel.os_engine.event_log import EventLog, EventLogError, EventPayloadError, UnknownEventTypeError
from kernel.os_engine.event_types import JobEventType
from kernel.os_engine.job_projection import project_job_state


class OSEngineEventLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.log = EventLog(OSDatabase(root=root, db_path=root / "brain.sqlite3"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _create(self, job_id: str = "job_event") -> None:
        self.log.append_event(
            job_id=job_id,
            event_type=JobEventType.JOB_CREATED,
            payload={"job_type": "test", "input_manifest": {"asset": "HFX_008"}},
        )

    def test_append_order_and_per_job_sequence_are_stable(self) -> None:
        self._create()
        self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_ADMITTED, payload={"ok": True})
        self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_QUEUED, payload={"ok": True})
        events = self.log.get_events("job_event")
        self.assertEqual([event.sequence for event in events], [1, 2, 3])
        self.assertEqual([event.sequence for event in self.log.get_events("job_event")], [1, 2, 3])
        self.assertEqual(events[0].to_json(), events[0].to_json())

    def test_unknown_event_and_malformed_payload_are_rejected(self) -> None:
        self._create()
        with self.assertRaises(UnknownEventTypeError):
            self.log.append_event(job_id="job_event", event_type="NotReal", payload={})
        with self.assertRaises(EventPayloadError):
            self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_ADMITTED, payload=[])  # type: ignore[arg-type]

    def test_terminal_event_prevents_later_execution_event(self) -> None:
        self._create()
        self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_ADMITTED, payload={})
        self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_FAILED, payload={}, reason="unit failure")
        with self.assertRaises(EventLogError):
            self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_QUEUED, payload={})

    def test_failure_reason_and_success_evidence_are_required(self) -> None:
        self._create()
        self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_ADMITTED, payload={})
        with self.assertRaises(EventPayloadError):
            self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_FAILED, payload={})
        self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_QUEUED, payload={})
        self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_STARTED, payload={})
        with self.assertRaises(EventPayloadError):
            self.log.append_event(job_id="job_event", event_type=JobEventType.JOB_SUCCEEDED, payload={})

    def test_secret_payload_and_raw_env_values_are_rejected(self) -> None:
        with self.assertRaises(UnsafePayloadError):
            self.log.append_event(
                job_id="job_secret",
                event_type=JobEventType.JOB_CREATED,
                payload={"job_type": "test", "input_manifest": {"env": {"TOKEN": "raw"}}},
            )
        with self.assertRaises(UnsafePayloadError):
            self.log.append_event(
                job_id="job_secret",
                event_type=JobEventType.JOB_CREATED,
                payload={"job_type": "test", "input_manifest": {"value": "Bearer abcdefghijklmnopqrstuvwxyz"}},
            )

    def test_replay_is_deterministic(self) -> None:
        self._create()
        for event_type in (JobEventType.JOB_ADMITTED, JobEventType.JOB_QUEUED, JobEventType.JOB_STARTED):
            self.log.append_event(job_id="job_event", event_type=event_type, payload={})
        self.log.append_event(
            job_id="job_event",
            event_type=JobEventType.JOB_SUCCEEDED,
            payload={"artifact_ids": ["artifact_1"]},
        )
        first = project_job_state(self.log.get_events("job_event"))
        second = project_job_state(self.log.get_events("job_event"))
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.current_status, "succeeded")


if __name__ == "__main__":
    unittest.main()
