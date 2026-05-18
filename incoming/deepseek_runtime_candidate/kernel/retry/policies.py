"""Retry policies: pre-built retry configurations for common scenarios."""

from __future__ import annotations

from kernel.retry.backoff import RetryConfig, retry

__all__ = ["with_retry", "RetryPolicy"]


class RetryPolicy:
    """Named retry configurations for common scenarios."""

    FAST = RetryConfig(
        max_attempts=3,
        base_delay_seconds=0.1,
        max_delay_seconds=2.0,
        backoff_multiplier=2.0,
        jitter=True,
    )

    STANDARD = RetryConfig(
        max_attempts=5,
        base_delay_seconds=1.0,
        max_delay_seconds=30.0,
        backoff_multiplier=2.0,
        jitter=True,
    )

    PERSISTENT = RetryConfig(
        max_attempts=10,
        base_delay_seconds=2.0,
        max_delay_seconds=120.0,
        backoff_multiplier=2.0,
        jitter=True,
    )

    NO_RETRY = RetryConfig(
        max_attempts=1,
        base_delay_seconds=0.0,
        max_delay_seconds=0.0,
        jitter=False,
    )


def with_retry(policy: RetryConfig, operation_name: str = "retry_operation"):
    """Convenience: apply a named retry policy to a function."""
    return retry(config=policy, operation_name=operation_name)
