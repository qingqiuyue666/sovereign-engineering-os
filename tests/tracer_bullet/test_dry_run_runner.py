import unittest

from kernel.runtime.dry_run_executor import execute_dry_run


class DryRunRunnerTests(unittest.TestCase):
    def valid_task(self):
        return {"objective": "x", "requested_capabilities": ["local_dry_run"], "classification": "PUBLIC", "policy_version": "v12", "code_version": "test", "input_digest": "sha256:abc"}

    def test_dry_run_returns_result_and_no_provider_calls(self):
        result = execute_dry_run(self.valid_task())
        self.assertTrue(result.accepted, result.failures)
        self.assertTrue(result.dry_run_result["dry_run_only"])
        self.assertEqual(result.dry_run_result["provider_calls_executed"], 0)
        self.assertEqual(len(result.dry_run_result["planned_events"]), 2)

    def test_blocks_provider_bound_secret_task(self):
        task = self.valid_task()
        task["classification"] = "SECRET"
        task["requested_capabilities"] = ["provider_adapter"]
        self.assertIn("provider_bound_sensitive_task_forbidden", execute_dry_run(task).failures)


if __name__ == "__main__":
    unittest.main()
