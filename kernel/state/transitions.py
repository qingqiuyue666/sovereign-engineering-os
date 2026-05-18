"""Dry-run task lifecycle transitions."""

from __future__ import annotations

from .machine import State, StateMachine, Transition

__all__ = ["TASK_TRANSITIONS", "TaskLifecycle", "build_task_lifecycle"]


class TaskLifecycle(State):
    INTAKE = "INTAKE"
    VALIDATED = "VALIDATED"
    PLANNED = "PLANNED"
    DRY_RUN_COMPLETE = "DRY_RUN_COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TASK_TRANSITIONS: tuple[Transition, ...] = (
    Transition("INTAKE", "VALIDATED", description="Task manifest validated"),
    Transition("INTAKE", "FAILED", description="Task intake rejected"),
    Transition("INTAKE", "CANCELLED", description="Task cancelled before validation"),
    Transition("VALIDATED", "PLANNED", description="Dry-run plan prepared"),
    Transition("VALIDATED", "FAILED", description="Validated task rejected"),
    Transition("PLANNED", "DRY_RUN_COMPLETE", required_context={"dry_run_only": True}, description="Dry run completed"),
    Transition("PLANNED", "FAILED", description="Dry-run plan failed"),
)


def build_task_lifecycle(task_id: str = "unknown") -> StateMachine:
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("task_id_required")
    return StateMachine(
        initial_state=TaskLifecycle.INTAKE.value,
        transitions=TASK_TRANSITIONS,
        name=f"task_lifecycle:{task_id}",
    )
