"""Circuit breaker for fail-fast local control flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar
import threading
import time

from kernel.audit.trail import audit
from kernel.errors.hierarchy import CircuitBreakerOpenError

__all__ = ["CircuitBreaker", "CircuitBreakerConfig", "CircuitState"]

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass(frozen=True)
class CircuitBreakerConfig:
    failure_threshold: int = 3
    recovery_timeout_seconds: float = 30.0
    half_open_max_requests: int = 1
    consecutive_successes_to_close: int = 1

    def validate(self) -> None:
        if self.failure_threshold < 1:
            raise CircuitBreakerOpenError("failure_threshold_must_be_positive")
        if self.recovery_timeout_seconds < 0:
            raise CircuitBreakerOpenError("recovery_timeout_seconds_must_be_nonnegative")
        if self.half_open_max_requests < 1:
            raise CircuitBreakerOpenError("half_open_max_requests_must_be_positive")
        if self.consecutive_successes_to_close < 1:
            raise CircuitBreakerOpenError("consecutive_successes_to_close_must_be_positive")


class CircuitBreaker:
    """Thread-safe circuit breaker with explicit half-open request accounting."""

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(name, str) or not name:
            raise CircuitBreakerOpenError("circuit_breaker_name_required")
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.config.validate()
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_in_flight = 0
        self._opened_at: float | None = None
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._refresh_state()
            return self._state

    def call(self, fn: Callable[..., T], *args: object, **kwargs: object) -> T:
        self._reserve()
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            self.record_failure(error_type=exc.__class__.__name__)
            raise
        else:
            self.record_success()
            return result

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_in_flight = max(0, self._half_open_in_flight - 1)
                self._success_count += 1
                if self._success_count >= self.config.consecutive_successes_to_close:
                    self._close()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self, *, error_type: str = "operation_failed") -> None:
        if not isinstance(error_type, str) or not error_type:
            raise CircuitBreakerOpenError("error_type_required")
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_in_flight = max(0, self._half_open_in_flight - 1)
                self._open(error_type=error_type)
                return
            if self._state == CircuitState.OPEN:
                return
            self._failure_count += 1
            audit("circuit_breaker.failure", name=self.name, error_type=error_type, failures=self._failure_count)
            if self._failure_count >= self.config.failure_threshold:
                self._open(error_type=error_type)

    def reset(self) -> None:
        with self._lock:
            self._close()
            audit("circuit_breaker.reset", name=self.name)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            self._refresh_state()
            return {
                "failure_count": self._failure_count,
                "half_open_in_flight": self._half_open_in_flight,
                "name": self.name,
                "state": self._state.value,
                "success_count": self._success_count,
            }

    def _reserve(self) -> None:
        with self._lock:
            self._refresh_state()
            if self._state == CircuitState.OPEN:
                audit("circuit_breaker.rejected", name=self.name, state=self._state.value)
                raise CircuitBreakerOpenError(f"circuit_breaker_open:{self.name}")
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_in_flight >= self.config.half_open_max_requests:
                    audit("circuit_breaker.rejected", name=self.name, state=self._state.value)
                    raise CircuitBreakerOpenError(f"circuit_breaker_half_open_limit:{self.name}")
                self._half_open_in_flight += 1

    def _refresh_state(self) -> None:
        if self._state != CircuitState.OPEN or self._opened_at is None:
            return
        if self._clock() - self._opened_at >= self.config.recovery_timeout_seconds:
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
            self._half_open_in_flight = 0
            audit("circuit_breaker.half_open", name=self.name)

    def _open(self, *, error_type: str) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._success_count = 0
        self._half_open_in_flight = 0
        audit("circuit_breaker.opened", name=self.name, error_type=error_type, failures=self._failure_count)

    def _close(self) -> None:
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._failure_count = 0
        self._success_count = 0
        self._half_open_in_flight = 0
        audit("circuit_breaker.closed", name=self.name)
