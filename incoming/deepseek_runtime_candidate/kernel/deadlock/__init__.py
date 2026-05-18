"""Deadlock detection and circuit breaker."""

from __future__ import annotations

from kernel.deadlock.detector import DeadlockDetector, LockHandle, LockGraph
from kernel.deadlock.breaker import CircuitBreaker, CircuitState

__all__ = ["DeadlockDetector", "LockHandle", "LockGraph", "CircuitBreaker", "CircuitState"]
