"""Tests: deadlock detector and circuit breaker.

Run:   python -m pytest 测试/test_deadlock.py -v
Expect: 10 tests pass — LockHandle is RAII-safe, cycle detection finds lock cycles,
        acquire timeout raises DeadlockDetectedError, circuit breaker transitions
        CLOSED→OPEN→HALF_OPEN→CLOSED correctly.
"""

from __future__ import annotations

import threading
import time
import pytest

from kernel.deadlock.detector import DeadlockDetector, LockGraph
from kernel.deadlock.breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig
from kernel.errors.hierarchy import DeadlockDetectedError, CircuitBreakerOpenError


# ── LockGraph tests ────────────────────────────────────────────

def test_lock_graph_no_cycle_empty():
    lg = LockGraph()
    assert lg.detect_cycle() is None


def test_lock_graph_single_lock_no_cycle():
    lg = LockGraph()
    lg.register("A")
    lg.acquire("A", 1)
    assert lg.detect_cycle() is None
    lg.release("A")


def test_lock_graph_cycle_detection():
    """Simulate: Thread-1 holds A and waits for B, Thread-2 holds B and waits for A."""
    lg = LockGraph()
    lg.register("A")
    lg.register("B")
    # Thread 1 holds A
    lg.acquire("A", 1)
    # Thread 1 waits for B
    lg.add_waiter("B", 1)
    # Thread 2 holds B
    lg.acquire("B", 2)
    # Thread 2 waits for A
    lg.add_waiter("A", 2)

    cycle = lg.detect_cycle()
    assert cycle is not None, "Expected a deadlock cycle to be detected"
    assert "A" in cycle
    assert "B" in cycle


def test_lock_graph_timeout_detection():
    lg = LockGraph()
    lg.register("A", timeout_seconds=0.01)
    lg.acquire("A", 1)
    time.sleep(0.05)
    timed_out = lg.check_timeouts()
    assert "A" in timed_out
    lg.release("A")


def test_lock_graph_register_existing():
    lg = LockGraph()
    lg.register("X", timeout_seconds=5.0)
    node = lg.register("X", timeout_seconds=10.0)  # Should return existing
    assert node.timeout_seconds == 5.0  # Original value preserved


# ── DeadlockDetector tests ─────────────────────────────────────

def test_detector_acquire_release():
    dd = DeadlockDetector()
    with dd.acquire("test_lock", timeout_seconds=1.0) as handle:
        assert handle is not None
        assert handle._released is False
    assert handle._released is True


def test_detector_acquire_timeout():
    dd = DeadlockDetector()
    # Hold the lock first
    dd._graph.register("held_lock", timeout_seconds=30.0)
    dd._graph.acquire("held_lock", 999)  # Held by another "thread"

    with pytest.raises(DeadlockDetectedError, match="acquire_timeout"):
        with dd.acquire("held_lock", timeout_seconds=0.1):
            pass


def test_detector_detects_existing_deadlock():
    dd = DeadlockDetector()
    dd._graph.register("L1")
    dd._graph.register("L2")
    dd._graph.acquire("L1", 1)
    dd._graph.add_waiter("L2", 1)
    dd._graph.acquire("L2", 2)
    dd._graph.add_waiter("L1", 2)

    with pytest.raises(DeadlockDetectedError, match="deadlock_detected"):
        with dd.acquire("L3"):
            pass


# ── Circuit breaker tests ──────────────────────────────────────

@pytest.fixture
def fast_cb():
    return CircuitBreaker("test_cb", CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout_seconds=0.1,
        half_open_max_requests=1,
        consecutive_successes_to_close=2,
    ))


def test_circuit_breaker_initial_state(fast_cb):
    assert fast_cb.state == CircuitState.CLOSED


def test_circuit_breaker_passes_calls(fast_cb):
    result = fast_cb.call(lambda: 42)
    assert result == 42


def test_circuit_breaker_opens_after_failures(fast_cb):
    for _ in range(3):
        try:
            fast_cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
    assert fast_cb.state == CircuitState.OPEN


def test_circuit_breaker_rejects_when_open(fast_cb):
    # Force open
    for _ in range(3):
        try:
            fast_cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
    with pytest.raises(CircuitBreakerOpenError):
        fast_cb.call(lambda: "should_not_run")


def test_circuit_breaker_half_open_then_closed(fast_cb):
    # Trip the breaker
    for _ in range(3):
        try:
            fast_cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
    assert fast_cb.state == CircuitState.OPEN

    # Wait for recovery
    time.sleep(0.2)
    assert fast_cb.state == CircuitState.HALF_OPEN

    # Two successes should close it
    fast_cb.call(lambda: "ok1")
    fast_cb.call(lambda: "ok2")
    assert fast_cb.state == CircuitState.CLOSED


def test_circuit_breaker_reset(fast_cb):
    for _ in range(3):
        try:
            fast_cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
    fast_cb.reset()
    assert fast_cb.state == CircuitState.CLOSED
