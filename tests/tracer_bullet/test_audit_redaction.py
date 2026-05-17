import unittest

from kernel.audit.audit_redaction import redact_audit_payload
from kernel.security.secret_scanner import REDACTION


class AuditRedactionTests(unittest.TestCase):
    def test_redaction_preserves_shape_and_counts(self):
        result = redact_audit_payload({"safe": "x", "nested": {"secret": "token=abc123456789SECRET"}})
        self.assertEqual(set(result["redacted_payload"].keys()), {"safe", "nested"})
        self.assertEqual(result["redacted_payload"]["nested"]["secret"], REDACTION)
        self.assertEqual(result["redaction_count"], 1)


if __name__ == "__main__":
    unittest.main()
