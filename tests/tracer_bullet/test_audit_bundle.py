import unittest

from kernel.audit.audit_bundle import validate_audit_bundle


class AuditBundleTests(unittest.TestCase):
    def bundle(self):
        return {"bundle_id": "bundle-1", "task_id": "task-1", "run_id": "run-1", "policy_version": "v12", "code_version": "test", "receipt_refs": ["receipt:1"], "event_digest_chain": ["sha256:a"], "failure_bundle_refs": [], "replay_verdict_ref": "replay:1", "redaction_status": "not_required", "classification": "INTERNAL"}

    def test_valid_bundle_is_accepted(self):
        self.assertTrue(validate_audit_bundle(self.bundle()).accepted)

    def test_unknown_classification_fails_closed(self):
        bundle = self.bundle()
        bundle["classification"] = "UNKNOWN"
        self.assertIn("classification_unknown", validate_audit_bundle(bundle).failures)


if __name__ == "__main__":
    unittest.main()
