"""Deterministic retry backoff helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar
import time

from kernel.audit.trail import audit
from kernel.errors.hierarchy import RetryExhaustedError

__all__ = ["RetryConfig", "RetryResult", "exponential_backoff", "retry", "retry_call"]

T = TypeVar("T")


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3
    base_delay_seconds: float = 0.1
    max_delay_seconds: float = 5.0
    backoff_multiplier: float = 2.0
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,)


@dataclass(frozen=True)
class RetryResult:
    success: bool
    attempts: int
    total_delay_seconds: float
    result: object = None
    last_error_type: str | None = None


def _validate_config(config: RetryConfig) -> None:
    if config.max_attempts < 1:
        raise ValueError("max_attempts_must_be_positive")
    if config.base_delay_seconds < 0:
        raise ValueError("base_delay_seconds_must_be_nonnegative")
    if config.max_delay_seconds < 0:
        raise ValueError("max_delay_seconds_must_be_nonnegative")
    if config.backoff_multiplier < 1:
        raise ValueError("backoff_multiplier_must_be_at_least_one")
    if not config.retryable_exceptions or not all(
        isinstance(item, type) and issubclass(item, BaseException)
        for item in config.retryable_exceptions
    ):
        raise ValueError("retryable_exceptions_must_be_exception_types")


def exponential_backoff(attempt: int, config: RetryConfig) -> float:
    """Return deterministic delay for a one-indexed failed attempt."""

    _validate_config(config)
    if attempt < 1:
        raise ValueError("attempt_must_be_positive")
    delay = config.base_delay_seconds * (config.backoff_multiplier ** (attempt - 1))
    return min(delay, config.max_delay_seconds)


def retry_call(
    fn: Callable[[], T],
    *,
    config: RetryConfig | None = None,
    operation_name: str = "retry_operation",
    sleeper: Callable[[float], None] = time.sleep,
) -> RetryResult:
    """Call a zero-argument operation with bounded retry behavior."""

    cfg = config or RetryConfig()
    _validate_config(cfg)
    last_error_type: str | None = None
    total_delay = 0.0
    for attempt in range(1, cfg.max_attempts + 1):
        try:
            result = fn()
        except cfg.retryable_exceptions as exc:
            last_error_type = exc.__class__.__name__
            if attempt == cfg.max_attempts:
                audit("retry.exhausted", operation=operation_name, attempts=attempt, error_type=last_error_type)
                raise RetryExhaustedError(f"retry_exhausted:{operation_name}:{last_error_type}") from exc
            delay = exponential_backoff(attempt, cfg)
            total_delay += delay
            audit("retry.attempt_failed", operation=operation_name, attempt=attempt, delay_seconds=delay, error_type=last_error_type)
            if delay:
                sleeper(delay)
        else:
            audit("retry.success", operation=operation_name, attempt=attempt)
            return RetryResult(True, attempt, total_delay, result=result, last_error_type=last_error_type)
    raise RetryExhaustedError(f"retry_exhausted:{operation_name}")


def retry(
    config: RetryConfig | None = None,
    *,
    operation_name: str = "retry_operation",
    sleeper: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., T]], Callable[..., RetryResult]]:
    """Decorator form of retry_call."""

    def decorator(fn: Callable[..., T]) -> Callable[..., RetryResult]:
        def wrapper(*args: object, **kwargs: object) -> RetryResult:
            return retry_call(lambda: fn(*args, **kwargs), config=config, operation_name=operation_name, sleeper=sleeper)

        return wrapper

    return decorator
