"""Tests: retry backoff and retry policies.

Run:   python -m pytest 测试/test_retry.py -v
Expect: 10 tests pass — exponential backoff produces correct delays, retry decorator
        retries on failure and succeeds on retry within limit, policies have correct
        attempt counts, RetryExhaustedError on max attempts exceeded.
"""

from __future__ import annotations

import pytest

from kernel.retry.backoff import RetryConfig, retry, exponential_backoff
from kernel.retry.policies import RetryPolicy, with_retry
from kernel.errors.hierarchy import RetryExhaustedError


def test_exponential_backoff_no_jitter():
    cfg = RetryConfig(base_delay_seconds=1.0, backoff_multiplier=2.0, jitter=False, max_delay_seconds=60.0)
    # attempt 1: 1.0, attempt 2: 2.0, attempt 3: 4.0
    assert exponential_backoff(1, cfg) == 1.0
    assert exponential_backoff(2, cfg) == 2.0
    assert exponential_backoff(3, cfg) == 4.0


def test_exponential_backoff_respects_max_delay():
    cfg = RetryConfig(base_delay_seconds=1.0, backoff_multiplier=10.0, max_delay_seconds=5.0, jitter=False)
    delay = exponential_backoff(5, cfg)
    assert delay <= 5.0, f"Expected delay <= 5.0, got {delay}"


def test_exponential_backoff_with_jitter():
    cfg = RetryConfig(base_delay_seconds=1.0, backoff_multiplier=2.0, jitter=True, max_delay_seconds=60.0)
    delay = exponential_backoff(1, cfg)
    # With jitter: 1.0 * (0.5 + random*0.5) ∈ [0.5, 1.0]
    assert 0.5 <= delay <= 1.0, f"Expected delay in [0.5, 1.0], got {delay}"


def test_retry_succeeds_first_attempt():
    call_count = [0]

    @retry(config=RetryConfig(max_attempts=3), operation_name="test_first")
    def succeed():
        call_count[0] += 1
        return "ok"

    result = succeed()
    assert result.success is True
    assert result.attempts == 1
    assert call_count[0] == 1


def test_retry_succeeds_after_failures():
    call_count = [0]

    @retry(config=RetryConfig(max_attempts=5, base_delay_seconds=0.01), operation_name="test_retry")
    def fail_then_succeed():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ValueError("transient")
        return "recovered"

    result = fail_then_succeed()
    assert result.success is True
    assert result.attempts == 3
    assert call_count[0] == 3


def test_retry_exhausted_raises():
    @retry(config=RetryConfig(max_attempts=2, base_delay_seconds=0.01), operation_name="test_exhausted")
    def always_fail():
        raise RuntimeError("persistent failure")

    with pytest.raises(RetryExhaustedError, match="retry_exhausted"):
        always_fail()


def test_retry_respects_retryable_exceptions():
    """Non-retryable exceptions should not be caught."""
    cfg = RetryConfig(max_attempts=3, base_delay_seconds=0.01, retryable_exceptions=(ValueError,))

    @retry(config=cfg, operation_name="test_non_retryable")
    def raise_type_error():
        raise TypeError("not retryable")

    with pytest.raises(TypeError):
        raise_type_error()


def test_retry_policy_fast():
    assert RetryPolicy.FAST.max_attempts == 3
    assert RetryPolicy.FAST.base_delay_seconds == 0.1


def test_retry_policy_standard():
    assert RetryPolicy.STANDARD.max_attempts == 5
    assert RetryPolicy.STANDARD.max_delay_seconds == 30.0


def test_with_retry_convenience():
    """with_retry applies a policy correctly."""
    @with_retry(RetryPolicy.FAST, operation_name="test_fast")
    def quick():
        return "fast"

    result = quick()
    assert result.success is True
    assert result.attempts == 1


def test_retry_result_contains_error():
    """When retries exhaust, the result's last_error is set (via exception)."""
    # We test via the exception path since RetryResult is raised, not returned
    @retry(config=RetryConfig(max_attempts=2, base_delay_seconds=0.01), operation_name="test_err")
    def fail():
        raise ConnectionError("no conn")

    with pytest.raises(RetryExhaustedError) as exc_info:
        fail()
    cause = exc_info.value.__cause__
    assert cause is not None
    assert isinstance(cause, ConnectionError)
