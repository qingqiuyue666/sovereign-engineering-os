"""Event type declarations for the v3 event-sourced job history."""

from __future__ import annotations

from enum import StrEnum


class JobEventType(StrEnum):
    JOB_CREATED = "JobCreated"
    JOB_ADMITTED = "JobAdmitted"
    JOB_QUEUED = "JobQueued"
    JOB_STARTED = "JobStarted"
    WORKER_SELECTED = "WorkerSelected"
    SUBPROCESS_STARTED = "SubprocessStarted"
    ARTIFACT_DISCOVERED = "ArtifactDiscovered"
    ARTIFACT_VALIDATED = "ArtifactValidated"
    HUMAN_REVIEW_REQUESTED = "HumanReviewRequested"
    HUMAN_APPROVED = "HumanApproved"
    HUMAN_REJECTED = "HumanRejected"
    JOB_SUCCEEDED = "JobSucceeded"
    JOB_FAILED = "JobFailed"
    JOB_QUARANTINED = "JobQuarantined"
    JOB_CANCELLED = "JobCancelled"


ALLOWED_EVENT_TYPES = frozenset(item.value for item in JobEventType)

REASON_REQUIRED_EVENT_TYPES = frozenset(
    {
        JobEventType.JOB_FAILED.value,
        JobEventType.JOB_QUARANTINED.value,
        JobEventType.HUMAN_REJECTED.value,
        JobEventType.JOB_CANCELLED.value,
    }
)

EXECUTION_EVENT_TYPES = frozenset(
    {
        JobEventType.JOB_ADMITTED.value,
        JobEventType.JOB_QUEUED.value,
        JobEventType.JOB_STARTED.value,
        JobEventType.WORKER_SELECTED.value,
        JobEventType.SUBPROCESS_STARTED.value,
        JobEventType.ARTIFACT_DISCOVERED.value,
        JobEventType.ARTIFACT_VALIDATED.value,
        JobEventType.JOB_SUCCEEDED.value,
    }
)

HARD_TERMINAL_EVENT_TYPES = frozenset(
    {
        JobEventType.JOB_SUCCEEDED.value,
        JobEventType.JOB_FAILED.value,
        JobEventType.JOB_QUARANTINED.value,
        JobEventType.JOB_CANCELLED.value,
        JobEventType.HUMAN_REJECTED.value,
    }
)
