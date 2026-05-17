import unittest

from kernel.status.health_plan import ordered_health_plan


class HealthPlanTests(unittest.TestCase):
    def test_health_plan_is_ordered(self):
        plan = ordered_health_plan()
        self.assertLess(plan.index("test-leak-prevention-foundation"), plan.index("test-task-foundation"))
        self.assertLess(plan.index("test-task-foundation"), plan.index("test-dry-run-runtime-foundation"))


if __name__ == "__main__":
    unittest.main()
