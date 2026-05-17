import unittest

from kernel.runtime.failure_bundle import build_failure_bundle
from kernel.security.secret_scanner import REDACTION


class FailureBundleTests(unittest.TestCase):
    def test_failure_bundle_is_sanitized_and_digest_only(self):
        bundle = build_failure_bundle(task_id="task-1", run_id="run-1", stage="dry_run", error_class="ValueError", message="token=abc123456789SECRET", state_snapshot={"state": "x"}, input_snapshot={"input": "y"}, policy_version="v12", code_version="test", quarantine_ref="quarantine:1", rollback_ref="rollback:1")
        self.assertEqual(bundle["sanitized_message"], REDACTION)
        for field in ("failure_id", "task_id", "run_id", "stage", "error_class", "sanitized_message", "state_snapshot_digest", "input_snapshot_digest", "policy_version", "code_version", "quarantine_ref", "rollback_ref"):
            self.assertIn(field, bundle)
        self.assertTrue(str(bundle["state_snapshot_digest"]).startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
