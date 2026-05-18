"""Tests: state machine and task lifecycle transitions.

Run:   python -m pytest 测试/test_state_machine.py -v
Expect: 12 tests pass — valid transitions succeed, invalid ones raise,
        guards enforced, history recorded, task lifecycle walks all happy-path states.
"""

from __future__ import annotations

import pytest

from kernel.state.machine import StateMachine, Transition
from kernel.state.transitions import TaskLifecycle, build_task_lifecycle
from kernel.errors.hierarchy import InvalidTransitionError


# ── StateMachine core tests ────────────────────────────────────

def test_initial_state():
    sm = StateMachine("IDLE")
    assert sm.state == "IDLE"


def test_valid_transition():
    sm = StateMachine("IDLE", [Transition("IDLE", "RUNNING")])
    assert sm.fire("RUNNING") is True
    assert sm.state == "RUNNING"


def test_invalid_transition_raises():
    sm = StateMachine("IDLE", [Transition("IDLE", "RUNNING")])
    with pytest.raises(InvalidTransitionError, match="invalid_transition"):
        sm.fire("STOPPED")


def test_guard_allows_transition():
    sm = StateMachine("IDLE", [
        Transition("IDLE", "RUNNING", guard=lambda sm: sm.context.get("ready", False)),
    ])
    assert sm.can_fire("RUNNING") is False
    sm.context["ready"] = True
    assert sm.can_fire("RUNNING") is True
    assert sm.fire("RUNNING") is True


def test_guard_block_raises():
    sm = StateMachine("IDLE", [
        Transition("IDLE", "RUNNING", guard=lambda sm: False),
    ])
    with pytest.raises(InvalidTransitionError, match="guard_failed"):
        sm.fire("RUNNING")


def test_action_called_on_transition():
    calls: list[tuple[str, str]] = []

    def on_transition(sm, from_s, to_s):
        calls.append((from_s, to_s))

    sm = StateMachine("A", [Transition("A", "B", action=on_transition)])
    sm.fire("B")
    assert calls == [("A", "B")]


def test_history_recorded():
    sm = StateMachine("A", [
        Transition("A", "B"),
        Transition("B", "C"),
    ])
    sm.fire("B")
    sm.fire("C")
    assert len(sm.history) == 2
    assert sm.history[0]["from"] == "A"
    assert sm.history[0]["to"] == "B"
    assert sm.history[1]["from"] == "B"
    assert sm.history[1]["to"] == "C"


def test_reset_clears_state():
    sm = StateMachine("A", [Transition("A", "B")])
    sm.fire("B")
    sm.reset()
    assert sm.state == "A"
    assert len(sm.history) == 0


def test_available_transitions():
    sm = StateMachine("A", [
        Transition("A", "B"),
        Transition("A", "C", guard=lambda sm: False),
    ])
    available = sm.available_transitions()
    assert "B" in available
    assert "C" not in available


# ── TaskLifecycle tests ────────────────────────────────────────

def test_task_lifecycle_happy_path():
    """Walk PENDING → VALIDATING → VALIDATED → APPROVED → QUEUED → EXECUTING → COMPLETED."""
    sm = build_task_lifecycle("task-test-001")
    assert sm.state == TaskLifecycle.PENDING.value

    sm.fire(TaskLifecycle.VALIDATING.value)
    sm.fire(TaskLifecycle.VALIDATED.value)
    sm.fire(TaskLifecycle.APPROVED.value)
    sm.fire(TaskLifecycle.QUEUED.value)
    sm.fire(TaskLifecycle.EXECUTING.value)
    sm.fire(TaskLifecycle.COMPLETED.value)

    assert sm.state == TaskLifecycle.COMPLETED.value
    assert len(sm.history) == 6


def test_task_lifecycle_rejection_path():
    """PENDING → VALIDATING → REJECTED."""
    sm = build_task_lifecycle("task-reject-001")
    sm.fire(TaskLifecycle.VALIDATING.value)
    sm.fire(TaskLifecycle.REJECTED.value)
    assert sm.state == TaskLifecycle.REJECTED.value


def test_task_lifecycle_failure_with_retry():
    """EXECUTING → FAILED → RETRYING → EXECUTING → COMPLETED."""
    sm = build_task_lifecycle("task-retry-001")
    # Fast-forward to EXECUTING
    for s in ["VALIDATING", "VALIDATED", "APPROVED", "QUEUED", "EXECUTING"]:
        sm.fire(s)
    sm.fire(TaskLifecycle.FAILED.value)
    sm.fire(TaskLifecycle.RETRYING.value)
    sm.fire(TaskLifecycle.EXECUTING.value)
    sm.fire(TaskLifecycle.COMPLETED.value)
    assert sm.state == TaskLifecycle.COMPLETED.value
