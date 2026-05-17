import unittest

from kernel.audit.audit_exporter import export_audit_bundle_json


class AuditExporterTests(unittest.TestCase):
    def bundle(self):
        return {"bundle_id": "bundle-1", "task_id": "task-1", "run_id": "run-1", "policy_version": "v12", "code_version": "test", "receipt_refs": ["receipt:1"], "event_digest_chain": ["sha256:a"], "failure_bundle_refs": [], "replay_verdict_ref": "replay:1", "redaction_status": "not_required"}

    def test_deterministic_json_export(self):
        first = export_audit_bundle_json(self.bundle())
        second = export_audit_bundle_json(dict(reversed(list(self.bundle().items()))))
        self.assertEqual(first, second)
        self.assertTrue(first.endswith("\n"))

    def test_blocks_sensitive_export(self):
        bundle = self.bundle()
        bundle["receipt_refs"] = ["token=abc123456789SECRET"]
        with self.assertRaises(ValueError):
            export_audit_bundle_json(bundle)


if __name__ == "__main__":
    unittest.main()
