import unittest

from kernel.daemon.scheduler_contract import validate_scheduler_config


class SchedulerContractTests(unittest.TestCase):
    def test_rejects_scheduler_runtime(self):
        failures = validate_scheduler_config({"single_run_mode": True, "max_runtime_seconds": 60, "unbounded_loop": False, "scheduler_runtime": True})
        self.assertIn("scheduler_runtime_forbidden", failures)


if __name__ == "__main__":
    unittest.main()
