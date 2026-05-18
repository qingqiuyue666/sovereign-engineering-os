"""Task lifecycle state machine — predefined transitions for operator tasks."""

from __future__ import annotations

from kernel.state.machine import State, StateMachine, Transition

__all__ = ["TaskLifecycle", "TASK_LIFECYCLE_STATES", "build_task_lifecycle"]


class TaskLifecycle(State):
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    QUEUED = "QUEUED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"


TASK_LIFECYCLE_STATES = list(TaskLifecycle)

TASK_TRANSITIONS: list[Transition] = [
    Transition("PENDING", "VALIDATING", description="Begin manifest validation"),
    Transition("PENDING", "CANCELLED", description="Cancel before validation"),
    Transition("VALIDATING", "VALIDATED", description="Validation passed"),
    Transition("VALIDATING", "REJECTED", description="Validation failed"),
    Transition("VALIDATED", "APPROVED", description="Operator approval granted"),
    Transition("VALIDATED", "REJECTED", description="Operator rejection"),
    Transition("APPROVED", "QUEUED", description="Enqueue for execution"),
    Transition("APPROVED", "CANCELLED", description="Cancel approved task"),
    Transition("QUEUED", "EXECUTING", description="Begin execution"),
    Transition("QUEUED", "CANCELLED", description="Cancel queued task"),
    Transition("EXECUTING", "COMPLETED", description="Execution succeeded"),
    Transition("EXECUTING", "FAILED", description="Execution failed"),
    Transition("EXECUTING", "RETRYING", description="Retry after transient failure"),
    Transition("RETRYING", "EXECUTING", description="Re-enter execution"),
    Transition("RETRYING", "FAILED", description="Retries exhausted"),
    Transition("FAILED", "RETRYING", description="Manual retry of failed task"),
    Transition("CANCELLED", "PENDING", description="Re-open cancelled task"),
]


def build_task_lifecycle(task_id: str = "unknown") -> StateMachine:
    return StateMachine(
        initial_state=TaskLifecycle.PENDING.value,
        transitions=TASK_TRANSITIONS,
        name=f"task_lifecycle:{task_id}",
    )
