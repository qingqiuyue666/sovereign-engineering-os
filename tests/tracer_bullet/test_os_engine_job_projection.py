"""Tracer bullet tests for replaying current job state from events."""

from __future__ import annotations

import unittest

from kernel.os_engine.job_projection import JobProjectionError, project_job_state


def _event(sequence: int, event_type: str, payload: dict[str, object] | None = None, reason: str | None = None) -> dict[str, object]:
    return {
        "event_id": f"evt_{sequence}",
        "job_id": "job_projection",
        "sequence": sequence,
        "event_type": event_type,
        "payload": payload or {},
        "reason": reason,
    }


class OSEngineJobProjectionTests(unittest.TestCase):
    def test_valid_event_chain_projects_current_state(self) -> None:
        state = project_job_state(
            [
                _event(1, "JobCreated", {"job_type": "test"}),
                _event(2, "JobAdmitted"),
                _event(3, "JobQueued"),
                _event(4, "WorkerSelected", {"worker_name": "TestWorker"}),
                _event(5, "JobStarted"),
                _event(6, "ArtifactDiscovered", {"artifact_id": "artifact_1"}),
                _event(7, "ArtifactValidated", {"artifact_id": "artifact_1"}),
                _event(8, "JobSucceeded", {"artifact_ids": ["artifact_1"]}),
            ]
        )
        self.assertEqual(state.current_status, "succeeded")
        self.assertEqual(state.worker_name, "TestWorker")
        self.assertEqual(state.artifact_ids, ("artifact_1",))
        self.assertTrue(state.final_claim_allowed)

    def test_missing_job_created_duplicate_terminal_and_execution_after_terminal_are_rejected(self) -> None:
        with self.assertRaises(JobProjectionError):
            project_job_state([_event(1, "JobQueued")])
        terminal = [
            _event(1, "JobCreated", {"job_type": "test"}),
            _event(2, "JobAdmitted"),
            _event(3, "JobQueued"),
            _event(4, "JobStarted"),
            _event(5, "JobSucceeded", {"artifact_ids": ["artifact_1"]}),
            _event(6, "JobFailed", {}, reason="late failure"),
        ]
        with self.assertRaises(JobProjectionError):
            project_job_state(terminal)
        with self.assertRaises(JobProjectionError):
            project_job_state([*terminal[:5], _event(6, "ArtifactDiscovered", {"artifact_id": "artifact_2"})])

    def test_human_review_requested_projects_review_state(self) -> None:
        state = project_job_state(
            [
                _event(1, "JobCreated", {"job_type": "test", "human_review_required": True}),
                _event(2, "JobAdmitted"),
                _event(3, "JobQueued"),
                _event(4, "JobStarted"),
                _event(5, "ArtifactDiscovered", {"artifact_id": "artifact_1"}),
                _event(6, "HumanReviewRequested", {"artifact_id": "artifact_1"}, reason="operator review"),
            ]
        )
        self.assertEqual(state.current_status, "requires_human_review")
        self.assertTrue(state.human_review_required)
        self.assertFalse(state.final_claim_allowed)

    def test_human_approved_unlocks_success_only_when_artifact_exists(self) -> None:
        base = [
            _event(1, "JobCreated", {"job_type": "test", "human_review_required": True}),
            _event(2, "JobAdmitted"),
            _event(3, "JobQueued"),
            _event(4, "JobStarted"),
        ]
        with self.assertRaises(JobProjectionError):
            project_job_state(
                [
                    *base,
                    _event(5, "HumanReviewRequested", {"artifact_id": "artifact_1"}, reason="review"),
                    _event(6, "HumanApproved", {"artifact_id": "artifact_1", "reviewer": "op"}),
                ]
            )
        state = project_job_state(
            [
                *base,
                _event(5, "ArtifactDiscovered", {"artifact_id": "artifact_1"}),
                _event(6, "HumanReviewRequested", {"artifact_id": "artifact_1"}, reason="review"),
                _event(7, "HumanApproved", {"artifact_id": "artifact_1", "reviewer": "op"}),
                _event(8, "JobSucceeded", {"artifact_ids": ["artifact_1"]}),
            ]
        )
        self.assertEqual(state.current_status, "succeeded")
        self.assertTrue(state.final_claim_allowed)

    def test_human_rejected_blocks_final_claim_and_projection_is_deterministic(self) -> None:
        events = [
            _event(1, "JobCreated", {"job_type": "test", "human_review_required": True}),
            _event(2, "JobAdmitted"),
            _event(3, "JobQueued"),
            _event(4, "JobStarted"),
            _event(5, "ArtifactDiscovered", {"artifact_id": "artifact_1"}),
            _event(6, "HumanReviewRequested", {"artifact_id": "artifact_1"}, reason="review"),
            _event(7, "HumanRejected", {"artifact_id": "artifact_1", "reviewer": "op"}, reason="bad frame"),
        ]
        first = project_job_state(events)
        second = project_job_state(events)
        self.assertEqual(first.current_status, "requires_human_review")
        self.assertFalse(first.final_claim_allowed)
        self.assertEqual(first.content_hash, second.content_hash)


if __name__ == "__main__":
    unittest.main()
