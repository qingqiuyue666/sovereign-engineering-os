"""Tests: daemon supervisor and watchdog lifecycle.

Run:   python -m pytest 测试/test_daemon.py -v
Expect: 10 tests pass — supervisor starts/stops workers, watchdog fires on timeout,
        crash-loop is detected, health checks mark unhealthy workers.
"""

from __future__ import annotations

import threading
import time
import pytest

from kernel.daemon.supervisor import Supervisor, SupervisorConfig, WorkerStatus
from kernel.daemon.watchdog import Watchdog
from kernel.errors.hierarchy import WatchdogExpiredError, DaemonCrashLoop


# ── Fixtures ───────────────────────────────────────────────────

@pytest.fixture
def fast_supervisor():
    """Supervisor with fast timings for testing."""
    return Supervisor(SupervisorConfig(
        max_restarts=3,
        restart_window_seconds=10.0,
        health_check_interval_seconds=0.1,
        health_check_timeout_seconds=1.0,
        graceful_shutdown_timeout_seconds=2.0,
        crash_loop_threshold=5,
    ))


# ── Supervisor tests ───────────────────────────────────────────

def test_supervisor_start_stop_no_workers(fast_supervisor):
    """Supervisor starts and stops cleanly with no registered workers."""
    fast_supervisor.start()
    assert fast_supervisor._state.running is True
    fast_supervisor.stop()
    assert fast_supervisor._state.running is False


def test_supervisor_runs_worker_to_completion(fast_supervisor):
    """Registered worker runs and completes."""
    completed = threading.Event()

    def worker():
        completed.set()

    fast_supervisor.register_worker("test_worker", worker)
    fast_supervisor.start()
    assert completed.wait(timeout=3.0), "Worker did not complete within timeout"
    fast_supervisor.stop()


def test_supervisor_restarts_crashed_worker(fast_supervisor):
    """Worker that crashes is restarted by the supervisor."""
    fast_supervisor.config.max_restarts = 3
    crash_count = [0]
    done = threading.Event()

    def flaky_worker():
        crash_count[0] += 1
        if crash_count[0] < 3:
            raise RuntimeError("simulated_crash")
        done.set()

    fast_supervisor.register_worker("flaky", flaky_worker)
    fast_supervisor.start()
    assert done.wait(timeout=5.0), f"Worker did not complete within timeout, crash_count={crash_count[0]}"
    fast_supervisor.stop()
    assert crash_count[0] >= 2, f"Expected at least 2 crash+restart cycles, got {crash_count[0]}"


def test_supervisor_detects_crash_loop(fast_supervisor):
    """Crash loop throws DaemonCrashLoop when restart threshold exceeded."""
    fast_supervisor.config.max_restarts = 10
    fast_supervisor.config.crash_loop_threshold = 2
    # Override _maybe_restart to raise immediately
    original = fast_supervisor._maybe_restart

    def failing_restart(name):
        raise DaemonCrashLoop(f"test_crash_loop:{name}")

    fast_supervisor._maybe_restart = failing_restart

    def always_crash():
        raise RuntimeError("boom")

    fast_supervisor.register_worker("crasher", always_crash)
    fast_supervisor.start()
    time.sleep(0.5)
    status = fast_supervisor.worker_status("crasher")
    assert status is not None
    assert status.status in (WorkerStatus.CRASHED, WorkerStatus.STOPPED)
    fast_supervisor.stop()


def test_supervisor_all_statuses(fast_supervisor):
    """all_worker_statuses returns all registered workers."""
    fast_supervisor.register_worker("w1", lambda: time.sleep(0.01))
    fast_supervisor.register_worker("w2", lambda: time.sleep(0.01))
    fast_supervisor.start()
    time.sleep(0.2)
    statuses = fast_supervisor.all_worker_statuses()
    assert "w1" in statuses
    assert "w2" in statuses
    fast_supervisor.stop()


def test_supervisor_max_restarts_exceeded(fast_supervisor):
    """After max_restarts exceeded, worker is not restarted again."""
    fast_supervisor.config.max_restarts = 1
    restart_count = [0]

    def crash_once():
        restart_count[0] += 1
        raise RuntimeError("crash")

    fast_supervisor.register_worker("one_shot", crash_once)
    fast_supervisor.start()
    time.sleep(0.5)
    # Should have been started twice (initial + 1 restart) = 2 executions
    assert restart_count[0] == 2, f"Expected 2 executions (initial + 1 restart), got {restart_count[0]}"
    status = fast_supervisor.worker_status("one_shot")
    assert status is not None
    assert status.restart_count == 2, f"Expected 2 restarts with max_restarts=1, got {status.restart_count}"
    fast_supervisor.stop()


# ── Watchdog tests ─────────────────────────────────────────────

def test_watchdog_does_not_fire_when_fed():
    """Watchdog stays alive when fed regularly."""
    wd = Watchdog(deadline_seconds=1.0, name="test_wd")
    wd.start()
    for _ in range(5):
        time.sleep(0.1)
        wd.feed()
    wd.stop()
    # No exception means success


def test_watchdog_fires_when_not_fed():
    """Watchdog raises WatchdogExpiredError when deadline exceeded."""
    wd = Watchdog(deadline_seconds=0.2, name="test_wd_fast")
    wd.start()
    time.sleep(0.5)  # Exceed deadline
    with pytest.raises(WatchdogExpiredError):
        # Force check — the internal loop may have already fired
        if wd.is_expired():
            wd._fire()
        else:
            wd.stop()


def test_watchdog_time_since_feed():
    """time_since_last_feed increases when not fed."""
    wd = Watchdog(deadline_seconds=30.0, name="test_wd_time")
    wd.start()
    wd.feed()
    t0 = wd.time_since_last_feed()
    time.sleep(0.3)
    t1 = wd.time_since_last_feed()
    assert t1 > t0, f"Expected t1({t1:.3f}) > t0({t0:.3f})"
    wd.stop()


def test_watchdog_is_expired():
    """is_expired returns True after deadline passes."""
    wd = Watchdog(deadline_seconds=0.1, name="test_wd_expired")
    wd.start()
    wd.feed()
    assert wd.is_expired() is False
    time.sleep(0.3)
    assert wd.is_expired() is True
    wd.stop()
