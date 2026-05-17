import unittest

from kernel.tasks.task_intake import intake_task


class TaskIntakeTests(unittest.TestCase):
    def test_intake_returns_normalized_manifest(self):
        result = intake_task({"objective": "x", "requested_capabilities": ["local_dry_run"], "classification": "PUBLIC", "policy_version": "v12", "code_version": "test", "input_digest": "sha256:abc"})
        self.assertTrue(result.accepted, result.failures)
        self.assertIn("task_id", result.task_manifest)

    def test_intake_rejects_raw_prompt(self):
        result = intake_task({"objective": "x", "requested_capabilities": ["local_dry_run"], "classification": "PUBLIC", "policy_version": "v12", "code_version": "test", "input_digest": "sha256:abc", "raw_prompt": "not persisted"})
        self.assertFalse(result.accepted)
        self.assertIn("raw_prompt_forbidden", result.failures)


if __name__ == "__main__":
    unittest.main()
