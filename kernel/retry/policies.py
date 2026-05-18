"""Named retry configurations."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar
import time

from .backoff import RetryConfig, RetryResult, retry

__all__ = ["RetryPolicy", "with_retry"]

T = TypeVar("T")


class RetryPolicy:
    NO_RETRY = RetryConfig(max_attempts=1, base_delay_seconds=0.0, max_delay_seconds=0.0)
    FAST = RetryConfig(max_attempts=3, base_delay_seconds=0.01, max_delay_seconds=0.05)
    STANDARD = RetryConfig(max_attempts=5, base_delay_seconds=0.1, max_delay_seconds=2.0)
    PERSISTENT = RetryConfig(max_attempts=8, base_delay_seconds=0.25, max_delay_seconds=5.0)


def with_retry(
    policy: RetryConfig,
    *,
    operation_name: str = "retry_operation",
    sleeper: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., T]], Callable[..., RetryResult]]:
    return retry(config=policy, operation_name=operation_name, sleeper=sleeper)
