"""Dry-run-only daemon supervisor metadata.

This module does not spawn processes, send signals, read secrets, or execute
worker targets. It records lifecycle observations and fails closed on crash-loop
conditions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
import threading

from kernel.audit.trail import audit
from kernel.errors.hierarchy import DaemonCrashLoop, DaemonError

__all__ = ["Supervisor", "SupervisorConfig", "WorkerState", "WorkerStatus"]


class WorkerStatus(str, Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    UNHEALTHY = "UNHEALTHY"
    CRASHED = "CRASHED"


@dataclass(frozen=True)
class WorkerState:
    name: str
    status: WorkerStatus
    restart_count: int = 0
    last_observed_at: str | None = None
    last_error_type: str | None = None
    restartable: bool = True
    dry_run_only: bool = True

    def deterministic_material(self) -> dict[str, object]:
        return {
            "dry_run_only": self.dry_run_only,
            "last_error_type": self.last_error_type,
            "name": self.name,
            "restart_count": self.restart_count,
            "restartable": self.restartable,
            "status": self.status.value,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["last_observed_at"] = self.last_observed_at
        return payload


@dataclass(frozen=True)
class SupervisorConfig:
    max_restarts: int = 3
    crash_loop_threshold: int = 3

    def validate(self) -> None:
        if self.max_restarts < 0:
            raise DaemonError("max_restarts_must_be_nonnegative")
        if self.crash_loop_threshold < 1:
            raise DaemonError("crash_loop_threshold_must_be_positive")


class Supervisor:
    """In-memory supervisor for dry-run daemon state."""

    def __init__(self, config: SupervisorConfig | None = None, *, name: str = "supervisor") -> None:
        self.config = config or SupervisorConfig()
        self.config.validate()
        self.name = name
        self._workers: dict[str, WorkerState] = {}
        self._lock = threading.RLock()

    def register_worker(self, name: str, *, restartable: bool = True, observed_at: str | None = None) -> WorkerState:
        _validate_worker_name(name)
        observed = _observed_at(observed_at)
        with self._lock:
            if name in self._workers:
                raise DaemonError(f"worker_already_registered:{name}")
            state = WorkerState(name=name, status=WorkerStatus.STOPPED, restartable=restartable, last_observed_at=observed)
            self._workers[name] = state
        audit("supervisor.worker_registered", supervisor=self.name, worker=name, restartable=restartable)
        return state

    def mark_running(self, name: str, *, observed_at: str | None = None) -> WorkerState:
        return self._replace_worker(name, status=WorkerStatus.RUNNING, last_error_type=None, observed_at=observed_at)

    def mark_stopped(self, name: str, *, observed_at: str | None = None) -> WorkerState:
        return self._replace_worker(name, status=WorkerStatus.STOPPED, observed_at=observed_at)

    def record_health(self, name: str, *, healthy: bool, error_type: str | None = None, observed_at: str | None = None) -> WorkerState:
        if healthy:
            return self._replace_worker(name, status=WorkerStatus.RUNNING, last_error_type=None, observed_at=observed_at)
        return self._replace_worker(name, status=WorkerStatus.UNHEALTHY, last_error_type=error_type or "health_check_failed", observed_at=observed_at)

    def record_failure(self, name: str, *, error_type: str, observed_at: str | None = None) -> WorkerState:
        if not isinstance(error_type, str) or not error_type:
            raise DaemonError("worker_failure_error_type_required")
        observed = _observed_at(observed_at)
        with self._lock:
            current = self._require_worker(name)
            restart_count = current.restart_count + 1
            crashed = restart_count > self.config.max_restarts or restart_count >= self.config.crash_loop_threshold
            state = replace(
                current,
                status=WorkerStatus.CRASHED if crashed else WorkerStatus.UNHEALTHY,
                restart_count=restart_count,
                last_error_type=error_type,
                last_observed_at=observed,
            )
            self._workers[name] = state
        audit("supervisor.worker_failed", supervisor=self.name, worker=name, error_type=error_type, restart_count=restart_count)
        if crashed:
            raise DaemonCrashLoop(f"crash_loop_detected:{name}:{restart_count}")
        return state

    def worker_status(self, name: str) -> WorkerState:
        with self._lock:
            return self._require_worker(name)

    def all_worker_statuses(self) -> dict[str, WorkerState]:
        with self._lock:
            return dict(self._workers)

    def deterministic_snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "name": self.name,
                "workers": {
                    name: self._workers[name].deterministic_material()
                    for name in sorted(self._workers)
                },
            }

    def _replace_worker(
        self,
        name: str,
        *,
        status: WorkerStatus,
        observed_at: str | None = None,
        last_error_type: str | None = None,
    ) -> WorkerState:
        observed = _observed_at(observed_at)
        with self._lock:
            current = self._require_worker(name)
            state = replace(current, status=status, last_error_type=last_error_type, last_observed_at=observed)
            self._workers[name] = state
        audit("supervisor.worker_status", supervisor=self.name, worker=name, status=status.value)
        return state

    def _require_worker(self, name: str) -> WorkerState:
        _validate_worker_name(name)
        try:
            return self._workers[name]
        except KeyError as exc:
            raise DaemonError(f"worker_not_registered:{name}") from exc


def _validate_worker_name(name: str) -> None:
    if not isinstance(name, str) or not name:
        raise DaemonError("worker_name_required")


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not isinstance(value, str) or not value:
        raise DaemonError("observed_at_must_be_nonempty_string")
    return value
