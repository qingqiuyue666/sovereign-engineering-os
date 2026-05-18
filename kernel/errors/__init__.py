"""Fail-closed runtime support error hierarchy."""

from .hierarchy import (
    AuditIntegrityError,
    CircuitBreakerOpenError,
    DaemonCrashLoop,
    DaemonError,
    DeadlockDetectedError,
    InvalidTransitionError,
    RetryExhaustedError,
    SovereignError,
    StateMachineError,
    TaskContractError,
    TaskManifestError,
    WatchdogExpiredError,
)
from .boundaries import ErrorBoundary, error_boundary

__all__ = [
    "AuditIntegrityError",
    "CircuitBreakerOpenError",
    "DaemonCrashLoop",
    "DaemonError",
    "DeadlockDetectedError",
    "ErrorBoundary",
    "InvalidTransitionError",
    "RetryExhaustedError",
    "SovereignError",
    "StateMachineError",
    "TaskContractError",
    "TaskManifestError",
    "WatchdogExpiredError",
    "error_boundary",
]
