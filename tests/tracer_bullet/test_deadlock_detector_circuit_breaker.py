import unittest

from kernel.deadlock.breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from kernel.deadlock.detector import DeadlockDetector, LockGraph
from kernel.errors.hierarchy import CircuitBreakerOpenError, DeadlockDetectedError


class DeadlockDetectorTests(unittest.TestCase):
    def test_wait_for_graph_detects_cycle(self):
        graph = LockGraph(clock=lambda: 0.0)
        graph.mark_acquired("lock_a", "thread_1")
        graph.mark_acquired("lock_b", "thread_2")
        graph.mark_waiting("lock_b", "thread_1")
        graph.mark_waiting("lock_a", "thread_2")

        self.assertEqual(graph.detect_cycle(), ("lock_a", "lock_b", "lock_a"))

    def test_detector_fails_closed_on_cycle_and_unavailable_lock(self):
        detector = DeadlockDetector(clock=lambda: 0.0)
        detector.mark_acquired("lock_a", "thread_1")

        with self.assertRaises(DeadlockDetectedError):
            with detector.acquire("lock_a", owner_id="thread_2"):
                pass

        detector.release("lock_a", owner_id="thread_1")
        with detector.acquire("lock_a", owner_id="thread_2"):
            self.assertEqual(detector.detect_deadlock(), ())

    def test_timeout_observation_fails_closed(self):
        now = [0.0]
        detector = DeadlockDetector(clock=lambda: now[0])
        detector.mark_acquired("lock_a", "thread_1", timeout_seconds=1.0)
        now[0] = 2.0

        with self.assertRaises(DeadlockDetectedError):
            detector.assert_clear()


class CircuitBreakerTests(unittest.TestCase):
    def test_circuit_opens_rejects_then_recovers_half_open(self):
        now = [0.0]
        breaker = CircuitBreaker(
            "provider",
            CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=5.0),
            clock=lambda: now[0],
        )

        breaker.record_failure(error_type="TimeoutError")
        breaker.record_failure(error_type="TimeoutError")
        self.assertEqual(breaker.state, CircuitState.OPEN)
        with self.assertRaises(CircuitBreakerOpenError):
            breaker.call(lambda: "blocked")

        now[0] = 5.0
        self.assertEqual(breaker.state, CircuitState.HALF_OPEN)
        self.assertEqual(breaker.call(lambda: "ok"), "ok")
        self.assertEqual(breaker.state, CircuitState.CLOSED)

    def test_half_open_failure_reopens(self):
        now = [0.0]
        breaker = CircuitBreaker(
            "provider",
            CircuitBreakerConfig(failure_threshold=1, recovery_timeout_seconds=1.0),
            clock=lambda: now[0],
        )
        breaker.record_failure(error_type="TimeoutError")
        now[0] = 1.0

        def fails():
            raise ValueError("temporary")

        with self.assertRaises(ValueError):
            breaker.call(fails)
        self.assertEqual(breaker.state, CircuitState.OPEN)


if __name__ == "__main__":
    unittest.main()
