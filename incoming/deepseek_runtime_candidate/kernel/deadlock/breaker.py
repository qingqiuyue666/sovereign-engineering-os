"""Circuit breaker: prevent cascading failures by failing fast when downstream is unhealthy."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import TypeVar

from kernel.audit.trail import audit
from kernel.errors.hierarchy import CircuitBreakerOpenError

__all__ = ["CircuitBreaker", "CircuitState"]

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = auto()       # Normal operation — requests flow through
    OPEN = auto()         # Failing fast — requests rejected
    HALF_OPEN = auto()    # Probing — one request allowed through


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_max_requests: int = 1
    consecutive_successes_to_close: int = 2


class CircuitBreaker:
    """Thread-safe circuit breaker.

    States:
        CLOSED → OPEN (after failure_threshold consecutive failures)
        OPEN → HALF_OPEN (after recovery_timeout_seconds)
        HALF_OPEN → CLOSED (after consecutive_successes_to_close)
        HALF_OPEN → OPEN (on any failure)
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._last_state_change = time.monotonic()
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._current_state()

    def _current_state(self) -> CircuitState:
        """Caller must hold _lock."""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_state_change >= self.config.recovery_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._last_state_change = time.monotonic()
                self._success_count = 0
                audit("circuit_breaker.half_open", name=self.name)
        return self._state

    def call(self, fn: Callable[..., T], *args: object, **kwargs: object) -> T:
        """Execute `fn` through the circuit breaker. Raises CircuitBreakerOpenError if open."""
        with self._lock:
            state = self._current_state()
            if state == CircuitState.OPEN:
                audit("circuit_breaker.rejected", name=self.name, state=state.name)
                raise CircuitBreakerOpenError(f"circuit_breaker_open:{self.name}")

            if state == CircuitState.HALF_OPEN:
                if self._success_count > self.config.half_open_max_requests:
                    audit("circuit_breaker.rejected_half_open", name=self.name)
                    raise CircuitBreakerOpenError(f"circuit_breaker_half_open_limit:{self.name}")

        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result

    def _on_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.consecutive_successes_to_close:
                    self._state = CircuitState.CLOSED
                    self._last_state_change = time.monotonic()
                    self._success_count = 0
                    audit("circuit_breaker.closed", name=self.name)

    def _on_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._last_state_change = time.monotonic()
                self._success_count = 0
                audit("circuit_breaker.reopened", name=self.name)
            elif self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                self._last_state_change = time.monotonic()
                audit("circuit_breaker.opened", name=self.name, failures=self._failure_count)

    def reset(self) -> None:
        """Force reset to CLOSED state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_state_change = time.monotonic()
            audit("circuit_breaker.reset", name=self.name)
