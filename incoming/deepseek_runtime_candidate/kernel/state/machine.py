"""Finite state machine core with guard/action semantics."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from kernel.audit.trail import audit
from kernel.errors.hierarchy import InvalidTransitionError

__all__ = ["StateMachine", "Transition", "State", "Guard", "Action"]

Guard = Callable[["StateMachine"], bool]
Action = Callable[["StateMachine", str, str], None]


class State(str, Enum):
    """Base state enum. Subclass for domain-specific states."""
    def __new__(cls, value: str) -> State:
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj


@dataclass
class Transition:
    """A state transition: from_state → to_state, optionally guarded."""
    from_state: str
    to_state: str
    guard: Guard | None = None
    action: Action | None = None
    description: str = ""


class StateMachine:
    """Thread-safe finite state machine with audit logging.

    Usage:
        sm = StateMachine("PENDING", transitions=[
            Transition("PENDING", "VALIDATING", guard=lambda sm: sm.context.get("ready")),
            Transition("VALIDATING", "APPROVED"),
        ])
        sm.fire("VALIDATING")  # moves PENDING → VALIDATING if guard passes
    """

    def __init__(
        self,
        initial_state: str,
        transitions: list[Transition] | None = None,
        name: str = "state_machine",
    ) -> None:
        self._state: str = initial_state
        self._initial_state = initial_state
        self._transitions: dict[str, list[Transition]] = {}
        self._lock = threading.RLock()
        self.name = name
        self.context: dict[str, Any] = {}
        self.history: list[dict[str, object]] = []

        for t in (transitions or []):
            self.add_transition(t)

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def add_transition(self, transition: Transition) -> None:
        with self._lock:
            key = transition.from_state
            if key not in self._transitions:
                self._transitions[key] = []
            self._transitions[key].append(transition)

    def can_fire(self, to_state: str) -> bool:
        """Check whether a transition to `to_state` is permitted and passes guards."""
        with self._lock:
            available = self._transitions.get(self._state, [])
            for t in available:
                if t.to_state == to_state:
                    if t.guard and not t.guard(self):
                        continue
                    return True
            return False

    def available_transitions(self) -> list[str]:
        """List currently fireable target states."""
        with self._lock:
            available = self._transitions.get(self._state, [])
            result: list[str] = []
            for t in available:
                if t.guard and not t.guard(self):
                    continue
                result.append(t.to_state)
            return result

    def fire(self, to_state: str) -> bool:
        """Attempt to transition to `to_state`. Returns True if successful.

        Raises InvalidTransitionError if the transition is not defined or guard fails.
        """
        with self._lock:
            available = self._transitions.get(self._state, [])
            matched: Transition | None = None
            for t in available:
                if t.to_state == to_state:
                    if t.guard and not t.guard(self):
                        raise InvalidTransitionError(
                            f"guard_failed:{self._state}->{to_state} machine={self.name}"
                        )
                    matched = t
                    break

            if matched is None:
                raise InvalidTransitionError(
                    f"invalid_transition:{self._state}->{to_state} machine={self.name}"
                )

            from_state = self._state
            self._state = to_state

            entry: dict[str, object] = {
                "from": from_state,
                "to": to_state,
                "at": datetime.now(timezone.utc).isoformat(),
                "machine": self.name,
            }
            self.history.append(entry)

        if matched.action:
            matched.action(self, from_state, to_state)

        audit("state_machine.transition", **entry)
        return True

    def reset(self) -> None:
        """Reset to initial state, clearing history and context."""
        with self._lock:
            self._state = self._initial_state
            self.history.clear()
            self.context.clear()
            audit("state_machine.reset", machine=self.name)
