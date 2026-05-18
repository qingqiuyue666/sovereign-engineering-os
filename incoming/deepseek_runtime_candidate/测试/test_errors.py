"""Tests: exception hierarchy and error boundaries.

Run:   python -m pytest 测试/test_errors.py -v
Expect: 8 tests pass — all exception types instantiate correctly, to_dict works,
        ErrorBoundary catches and translates, error_boundary decorator wraps correctly.
"""

from __future__ import annotations

import pytest

from kernel.errors.hierarchy import (
    SovereignError,
    DaemonError,
    DaemonCrashLoop,
    WatchdogExpiredError,
    StateMachineError,
    InvalidTransitionError,
    RetryExhaustedError,
    DeadlockDetectedError,
    CircuitBreakerOpenError,
    AuditIntegrityError,
)
from kernel.errors.boundaries import ErrorBoundary, error_boundary


def test_sovereign_error_base():
    err = SovereignError("base error")
    assert err.message == "base error"
    assert err.code == "SOVEREIGN_ERROR"
    d = err.to_dict()
    assert d["code"] == "SOVEREIGN_ERROR"
    assert d["type"] == "SovereignError"


def test_exception_codes():
    """All exception types have distinct codes."""
    exceptions = [
        (DaemonError, "DAEMON_ERROR"),
        (DaemonCrashLoop, "DAEMON_CRASH_LOOP"),
        (WatchdogExpiredError, "WATCHDOG_EXPIRED"),
        (StateMachineError, "STATE_MACHINE_ERROR"),
        (InvalidTransitionError, "INVALID_TRANSITION"),
        (RetryExhaustedError, "RETRY_EXHAUSTED"),
        (DeadlockDetectedError, "DEADLOCK_DETECTED"),
        (CircuitBreakerOpenError, "CIRCUIT_BREAKER_OPEN"),
        (AuditIntegrityError, "AUDIT_INTEGRITY_ERROR"),
    ]
    for exc_cls, expected_code in exceptions:
        inst = exc_cls("test")
        assert inst.code == expected_code, f"{exc_cls.__name__}.code mismatch"


def test_exception_is_sovereign_error():
    """All domain exceptions inherit from SovereignError."""
    assert issubclass(DaemonError, SovereignError)
    assert issubclass(StateMachineError, SovereignError)
    assert issubclass(RetryExhaustedError, SovereignError)
    assert issubclass(DeadlockDetectedError, SovereignError)
    assert issubclass(CircuitBreakerOpenError, SovereignError)
    assert issubclass(AuditIntegrityError, SovereignError)


def test_error_boundary_catches_and_suppresses():
    """ErrorBoundary catches standard exceptions and suppresses them."""
    with ErrorBoundary(component="test_cmp"):
        raise ValueError("test_value_error")
    # Exception is suppressed — no raise


def test_error_boundary_passes_through_sovereign():
    """SovereignError passes through without wrapping."""
    with pytest.raises(DaemonError):
        with ErrorBoundary(component="test_cmp", reraise=DaemonError):
            raise DaemonError("original")


def test_error_boundary_reraises_as_sovereign():
    """Non-Sovereign exceptions are translated when reraise is set."""
    with pytest.raises(DaemonError):
        with ErrorBoundary(component="test_cmp", reraise=DaemonError):
            raise RuntimeError("raw")


def test_error_boundary_decorator():
    """@error_boundary decorator wraps function execution."""

    @error_boundary("decorated_fn")
    def will_raise():
        raise TypeError("bad type")

    # Should not propagate — suppressed by boundary
    result = will_raise()
    assert result is None


def test_error_boundary_decorator_success():
    """@error_boundary passes through on success."""

    @error_boundary("decorated_ok")
    def succeeds():
        return 42

    assert succeeds() == 42
