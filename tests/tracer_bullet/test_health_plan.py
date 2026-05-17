"""Health plan tests — includes V12-05 through V12-08 gates."""

import unittest

from kernel.status.health_plan import ordered_health_plan


class HealthPlanTests(unittest.TestCase):
    def test_health_plan_is_ordered(self):
        plan = ordered_health_plan()
        self.assertLess(plan.index("test-leak-prevention-foundation"), plan.index("test-task-foundation"))
        self.assertLess(plan.index("test-task-foundation"), plan.index("test-dry-run-runtime-foundation"))

    def test_health_plan_includes_v12_05_runtime_runner_event_journal(self):
        plan = ordered_health_plan()
        self.assertIn("test-runtime-runner-event-journal", plan)

    def test_health_plan_includes_v12_06_failurebundle_replay(self):
        plan = ordered_health_plan()
        self.assertIn("test-failurebundle-replay-foundation", plan)

    def test_health_plan_includes_v12_07_evidence_vault_boundary(self):
        plan = ordered_health_plan()
        self.assertIn("test-evidence-vault-boundary-foundation", plan)

    def test_health_plan_includes_v12_08_provider_execution_plane(self):
        plan = ordered_health_plan()
        self.assertIn("test-provider-execution-plane-boundary", plan)

    def test_health_plan_preserves_v11_gates(self):
        plan = ordered_health_plan()
        for gate in ("test-leak-prevention-foundation", "test-security-truth-substrate",
                      "test-task-foundation", "test-cli-foundation"):
            self.assertIn(gate, plan)

    def test_production_autonomy_not_in_health_plan(self):
        plan = ordered_health_plan()
        self.assertNotIn("test-production-autonomy", plan)
