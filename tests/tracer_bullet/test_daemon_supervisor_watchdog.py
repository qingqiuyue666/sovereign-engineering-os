import unittest

from kernel.daemon.supervisor import Supervisor, SupervisorConfig, WorkerStatus
from kernel.daemon.watchdog import Watchdog
from kernel.errors.hierarchy import DaemonCrashLoop, DaemonError, WatchdogExpiredError


class SupervisorTests(unittest.TestCase):
    def test_supervisor_records_dry_run_worker_state_without_execution(self):
        supervisor = Supervisor(name="unit", config=SupervisorConfig(max_restarts=2, crash_loop_threshold=3))
        supervisor.register_worker("worker_a", observed_at="2026-01-01T00:00:00Z")
        supervisor.mark_running("worker_a", observed_at="2026-01-01T00:00:01Z")

        state = supervisor.worker_status("worker_a")
        self.assertEqual(state.status, WorkerStatus.RUNNING)
        self.assertTrue(state.dry_run_only)
        self.assertNotIn("last_observed_at", state.deterministic_material())

    def test_supervisor_fails_closed_on_crash_loop(self):
        supervisor = Supervisor(name="unit", config=SupervisorConfig(max_restarts=5, crash_loop_threshold=2))
        supervisor.register_worker("worker_a")
        supervisor.record_failure("worker_a", error_type="RuntimeError")

        with self.assertRaises(DaemonCrashLoop):
            supervisor.record_failure("worker_a", error_type="RuntimeError")
        self.assertEqual(supervisor.worker_status("worker_a").status, WorkerStatus.CRASHED)

    def test_supervisor_rejects_unknown_worker(self):
        with self.assertRaises(DaemonError):
            Supervisor().mark_running("missing")


class WatchdogTests(unittest.TestCase):
    def test_watchdog_observed_at_is_not_deterministic_material(self):
        now = [0.0]
        watchdog = Watchdog(name="unit", deadline_seconds=5.0, clock=lambda: now[0])
        first = watchdog.feed(observed_at="2026-01-01T00:00:00Z")
        now[0] = 1.0
        second = watchdog.snapshot(observed_at="2027-01-01T00:00:00Z")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.deterministic_material(), second.deterministic_material())
        self.assertTrue(first.dry_run_only)

    def test_watchdog_expires_without_killing_process(self):
        now = [0.0]
        watchdog = Watchdog(name="unit", deadline_seconds=1.0, clock=lambda: now[0])
        now[0] = 2.0

        with self.assertRaises(WatchdogExpiredError):
            watchdog.check(observed_at="2026-01-01T00:00:02Z")


if __name__ == "__main__":
    unittest.main()
