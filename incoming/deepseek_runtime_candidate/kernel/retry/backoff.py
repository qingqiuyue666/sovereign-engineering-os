"""Exponential backoff with jitter and max-retry enforcement."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TypeVar

from kernel.audit.trail import audit
from kernel.errors.hierarchy import RetryExhaustedError

__all__ = ["retry", "RetryConfig", "exponential_backoff", "RetryResult"]

F = TypeVar("F", bound=Callable)
T = TypeVar("T")


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,)


@dataclass
class RetryResult:
    success: bool
    attempts: int
    total_delay_seconds: float
    last_error: BaseException | None = None
    result: object = None


def exponential_backoff(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for attempt `attempt` (1-indexed)."""
    delay = config.base_delay_seconds * (config.backoff_multiplier ** (attempt - 1))
    delay = min(delay, config.max_delay_seconds)
    if config.jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    return delay


def retry(
    config: RetryConfig | None = None,
    operation_name: str = "retry_operation",
) -> Callable[[Callable[..., T]], Callable[..., RetryResult]]:
    """Decorator: wrap a function in retry logic with exponential backoff."""

    cfg = config or RetryConfig()

    def decorator(fn: Callable[..., T]) -> Callable[..., RetryResult]:
        def wrapper(*args: object, **kwargs: object) -> RetryResult:
            last_error: BaseException | None = None
            total_delay = 0.0

            for attempt in range(1, cfg.max_attempts + 1):
                try:
                    result = fn(*args, **kwargs)
                    audit("retry.success", operation=operation_name, attempt=attempt)
                    return RetryResult(success=True, attempts=attempt, total_delay_seconds=total_delay, result=result)
                except cfg.retryable_exceptions as exc:
                    last_error = exc
                    if attempt == cfg.max_attempts:
                        audit("retry.exhausted", operation=operation_name, attempts=attempt, error=str(exc))
                        raise RetryExhaustedError(
                            f"retry_exhausted:{operation_name} attempts={attempt} last_error={exc}"
                        ) from exc
                    delay = exponential_backoff(attempt, cfg)
                    audit("retry.attempt_failed", operation=operation_name, attempt=attempt, delay_seconds=delay, error=str(exc))
                    total_delay += delay
                    time.sleep(delay)

            raise RetryExhaustedError(f"retry_exhausted:{operation_name}")

        return wrapper

    return decorator
