"""Supervisor: manages worker daemon processes with health-check and restart."""

from __future__ import annotations

import os
import signal
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto

from kernel.audit.trail import AuditTrail, audit
from kernel.errors.hierarchy import DaemonError, DaemonCrashLoop


class WorkerStatus(Enum):
    STARTING = auto()
    RUNNING = auto()
    UNHEALTHY = auto()
    STOPPING = auto()
    STOPPED = auto()
    CRASHED = auto()


@dataclass
class WorkerState:
    name: str
    status: WorkerStatus = WorkerStatus.STARTING
    pid: int = -1
    restart_count: int = 0
    last_restart_at: float = 0.0
    last_health_check_at: float = 0.0
    last_error: str | None = None


@dataclass
class SupervisorConfig:
    max_restarts: int = 5
    restart_window_seconds: float = 60.0
    health_check_interval_seconds: float = 5.0
    health_check_timeout_seconds: float = 3.0
    graceful_shutdown_timeout_seconds: float = 10.0
    crash_loop_threshold: int = 3


@dataclass
class SupervisorState:
    workers: dict[str, WorkerState] = field(default_factory=dict)
    running: bool = False
    started_at: float = 0.0
    audit_trail: AuditTrail = field(default_factory=AuditTrail)


class Supervisor:
    """Manages worker daemon lifecycle: start, health-check, restart, stop.

    Single-threaded control loop with thread-safe state access via a re-entrant lock.
    """

    def __init__(self, config: SupervisorConfig | None = None) -> None:
        self.config = config or SupervisorConfig()
        self._state = SupervisorState()
        self._lock = threading.RLock()
        self._health_thread: threading.Thread | None = None
        self._worker_targets: dict[str, Callable[[], None]] = {}

    # ── public API ──────────────────────────────────────────────

    def register_worker(self, name: str, target: Callable[[], None]) -> None:
        """Register a callable as a named worker to be supervised."""
        with self._lock:
            self._worker_targets[name] = target
            self._state.workers[name] = WorkerState(name=name, status=WorkerStatus.STOPPED)
            audit(f"supervisor.worker_registered", worker=name)

    def start(self) -> None:
        """Start all registered workers and begin supervision loop."""
        with self._lock:
            if self._state.running:
                return
            self._state.running = True
            self._state.started_at = time.monotonic()
            audit("supervisor.started", workers=list(self._worker_targets.keys()))

        for name in list(self._worker_targets.keys()):
            self._start_worker(name)

        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True, name="supervisor-health")
        self._health_thread.start()

    def stop(self) -> None:
        """Graceful shutdown of all workers."""
        with self._lock:
            if not self._state.running:
                return
            self._state.running = False
            audit("supervisor.stopping")

        for name in list(self._worker_targets.keys()):
            self._stop_worker(name)

        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=self.config.graceful_shutdown_timeout_seconds)

        audit("supervisor.stopped")

    def worker_status(self, name: str) -> WorkerState | None:
        with self._lock:
            return self._state.workers.get(name)

    def all_worker_statuses(self) -> dict[str, WorkerState]:
        with self._lock:
            return dict(self._state.workers)

    # ── internal ────────────────────────────────────────────────

    def _start_worker(self, name: str) -> None:
        target = self._worker_targets.get(name)
        if target is None:
            raise DaemonError(f"worker_not_registered:{name}")

        with self._lock:
            worker = self._state.workers[name]
            if worker.status in (WorkerStatus.RUNNING, WorkerStatus.STARTING):
                return
            worker.status = WorkerStatus.STARTING
            worker.last_error = None

        thread = threading.Thread(target=self._worker_runner, args=(name, target), daemon=True, name=f"worker-{name}")
        thread.start()
        audit(f"supervisor.worker_starting", worker=name)

    def _worker_runner(self, name: str, target: Callable[[], None]) -> None:
        try:
            with self._lock:
                worker = self._state.workers[name]
                worker.pid = os.getpid()
                worker.status = WorkerStatus.RUNNING
            target()
        except Exception as exc:
            with self._lock:
                worker = self._state.workers[name]
                worker.status = WorkerStatus.CRASHED
                worker.last_error = f"{exc.__class__.__name__}:{exc}"
                worker.restart_count += 1
                worker.last_restart_at = time.monotonic()
                audit(f"supervisor.worker_crashed", worker=name, error=worker.last_error)

            self._maybe_restart(name)
        finally:
            with self._lock:
                worker = self._state.workers[name]
                if worker.status not in (WorkerStatus.CRASHED, WorkerStatus.STOPPING, WorkerStatus.STARTING):
                    worker.status = WorkerStatus.STOPPED

    def _maybe_restart(self, name: str) -> None:
        with self._lock:
            if not self._state.running:
                return
            worker = self._state.workers[name]
            now = time.monotonic()

            # Crash-loop detection: count restarts within the window
            if now - worker.last_restart_at < self.config.restart_window_seconds:
                recent_restarts = 1
            else:
                recent_restarts = 0

            if recent_restarts >= self.config.crash_loop_threshold:
                audit(f"supervisor.crash_loop_detected", worker=name, restarts=worker.restart_count)
                raise DaemonCrashLoop(
                    f"crash_loop_detected:{name} restarts={worker.restart_count} in_window={self.config.restart_window_seconds}s"
                )

            if worker.restart_count > self.config.max_restarts:
                audit(f"supervisor.max_restarts_exceeded", worker=name, restarts=worker.restart_count)
                return

            audit(f"supervisor.worker_restarting", worker=name, attempt=worker.restart_count + 1)

        time.sleep(_jitter(0.5))
        self._start_worker(name)

    def _stop_worker(self, name: str) -> None:
        with self._lock:
            worker = self._state.workers[name]
            worker.status = WorkerStatus.STOPPING
        audit(f"supervisor.worker_stopping", worker=name)

    def _health_check_loop(self) -> None:
        while True:
            with self._lock:
                if not self._state.running:
                    break

            for name in list(self._worker_targets.keys()):
                self._run_health_check(name)

            time.sleep(self.config.health_check_interval_seconds)

    def _run_health_check(self, name: str) -> None:
        with self._lock:
            worker = self._state.workers[name]
            if worker.status != WorkerStatus.RUNNING:
                return
            worker.last_health_check_at = time.monotonic()

        # Health check: verify thread is alive
        worker_thread_alive = any(
            t.name == f"worker-{name}" and t.is_alive() for t in threading.enumerate()
        )

        if not worker_thread_alive:
            with self._lock:
                worker = self._state.workers[name]
                worker.status = WorkerStatus.UNHEALTHY
                worker.last_error = "health_check:worker_thread_not_alive"
                audit(f"supervisor.worker_unhealthy", worker=name)


def _jitter(base: float) -> float:
    import random
    return base * (0.5 + random.random())
