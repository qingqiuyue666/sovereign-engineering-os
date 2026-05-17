import unittest

from kernel.daemon.daemon_contract import validate_daemon_config


class DaemonContractTests(unittest.TestCase):
    def test_requires_bounded_single_run_config(self):
        self.assertFalse(validate_daemon_config({"kill_switch": True, "max_runtime_seconds": 60, "single_run_mode": True, "unbounded_loop": False}))

    def test_rejects_unbounded_or_runtime_flags(self):
        failures = validate_daemon_config({"kill_switch": False, "max_runtime_seconds": 0, "single_run_mode": False, "unbounded_loop": True, "process_spawn": True})
        self.assertIn("kill_switch_required", failures)
        self.assertIn("unbounded_loop_forbidden", failures)
        self.assertIn("daemon_runtime_forbidden", failures)


if __name__ == "__main__":
    unittest.main()
