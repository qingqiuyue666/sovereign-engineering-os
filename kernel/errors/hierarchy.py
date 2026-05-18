"""Bounded exception hierarchy for runtime support modules."""

from __future__ import annotations

__all__ = [
    "AuditIntegrityError",
    "CircuitBreakerOpenError",
    "DaemonCrashLoop",
    "DaemonError",
    "DeadlockDetectedError",
    "InvalidTransitionError",
    "RetryExhaustedError",
    "SovereignError",
    "StateMachineError",
    "TaskContractError",
    "TaskManifestError",
    "WatchdogExpiredError",
]


class SovereignError(Exception):
    """Base error for bounded SEOS runtime-support failures."""

    code = "SOVEREIGN_ERROR"

    def __init__(self, reason: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.message = reason

    def to_dict(self, *, include_message: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {"code": self.code, "type": self.__class__.__name__}
        if include_message:
            payload["message"] = self.reason
        return payload


class DaemonError(SovereignError):
    code = "DAEMON_ERROR"


class DaemonCrashLoop(DaemonError):
    code = "DAEMON_CRASH_LOOP"


class WatchdogExpiredError(DaemonError):
    code = "WATCHDOG_EXPIRED"


class StateMachineError(SovereignError):
    code = "STATE_MACHINE_ERROR"


class InvalidTransitionError(StateMachineError):
    code = "INVALID_TRANSITION"


class RetryExhaustedError(SovereignError):
    code = "RETRY_EXHAUSTED"


class DeadlockDetectedError(SovereignError):
    code = "DEADLOCK_DETECTED"


class CircuitBreakerOpenError(SovereignError):
    code = "CIRCUIT_BREAKER_OPEN"


class AuditIntegrityError(SovereignError):
    code = "AUDIT_INTEGRITY_ERROR"


class TaskContractError(SovereignError):
    code = "TASK_CONTRACT_ERROR"


class TaskManifestError(SovereignError):
    code = "TASK_MANIFEST_ERROR"
