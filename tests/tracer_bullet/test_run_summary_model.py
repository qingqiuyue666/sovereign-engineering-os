import unittest

from kernel.dashboard.run_summary_model import validate_run_summary_model


class RunSummaryModelTests(unittest.TestCase):
    def test_run_summary_requires_event_count(self):
        self.assertIn("event_count_required", validate_run_summary_model({"run_id": "run-1", "task_id": "task-1", "status": "x"}))
        self.assertFalse(validate_run_summary_model({"run_id": "run-1", "task_id": "task-1", "status": "x", "event_count": 0}))


if __name__ == "__main__":
    unittest.main()
