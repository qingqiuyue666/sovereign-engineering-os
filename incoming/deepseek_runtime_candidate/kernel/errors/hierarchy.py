"""Exception hierarchy for Sovereign OS V12."""

from __future__ import annotations

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
]


class SovereignError(Exception):
    """Base error for all Sovereign OS exceptions."""

    code: str = "SOVEREIGN_ERROR"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "type": self.__class__.__name__}


# ── Daemon errors ──────────────────────────────────────────────

class DaemonError(SovereignError):
    """Daemon lifecycle error."""
    code = "DAEMON_ERROR"


class DaemonCrashLoop(DaemonError):
    """Worker entered crash loop — too many restarts in window."""
    code = "DAEMON_CRASH_LOOP"


class WatchdogExpiredError(DaemonError):
    """Watchdog deadman timer expired."""
    code = "WATCHDOG_EXPIRED"


# ── State machine errors ───────────────────────────────────────

class StateMachineError(SovereignError):
    """State machine invariant violation."""
    code = "STATE_MACHINE_ERROR"


class InvalidTransitionError(StateMachineError):
    """Attempted an invalid state transition."""
    code = "INVALID_TRANSITION"


# ── Retry errors ───────────────────────────────────────────────

class RetryExhaustedError(SovereignError):
    """All retry attempts exhausted."""
    code = "RETRY_EXHAUSTED"


# ── Deadlock errors ────────────────────────────────────────────

class DeadlockDetectedError(SovereignError):
    """Deadlock detected in lock graph."""
    code = "DEADLOCK_DETECTED"


class CircuitBreakerOpenError(SovereignError):
    """Operation rejected — circuit breaker is open."""
    code = "CIRCUIT_BREAKER_OPEN"


# ── Audit errors ───────────────────────────────────────────────

class AuditIntegrityError(SovereignError):
    """Audit hash chain integrity check failed."""
    code = "AUDIT_INTEGRITY_ERROR"


# ── Task errors ────────────────────────────────────────────────

class TaskContractError(SovereignError):
    """Task contract violation."""
    code = "TASK_CONTRACT_ERROR"


class TaskManifestError(SovereignError):
    """Task manifest validation failure."""
    code = "TASK_MANIFEST_ERROR"
