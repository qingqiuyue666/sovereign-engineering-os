"""Error handling module."""

from __future__ import annotations

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
    TaskContractError,
    TaskManifestError,
)
from kernel.errors.boundaries import ErrorBoundary, error_boundary

__all__ = [
    "SovereignError",
    "DaemonError",
    "DaemonCrashLoop",
    "WatchdogExpiredError",
    "StateMachineError",
    "InvalidTransitionError",
    "RetryExhaustedError",
    "DeadlockDetectedError",
    "CircuitBreakerOpenError",
    "AuditIntegrityError",
    "TaskContractError",
    "TaskManifestError",
    "ErrorBoundary",
    "error_boundary",
]
