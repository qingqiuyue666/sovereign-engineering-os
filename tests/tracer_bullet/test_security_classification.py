import json
import unittest
from pathlib import Path

from kernel.security.security_classification import classify_record, is_sink_allowed

POLICY_PATH = Path("governance/security/security_classification_policy_v1.json")


class SecurityClassificationTests(unittest.TestCase):
    def test_policy_exists_and_declares_levels(self):
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["policy_type"], "seos_security_classification_policy_v1")
        self.assertEqual(payload["classification_levels"], ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET", "CROWN_JEWEL"])
        self.assertTrue(payload["fail_closed_on_unknown_level"])

    def test_default_classification_is_internal(self):
        result = classify_record({})
        self.assertTrue(result.accepted)
        self.assertEqual(result.classification, "INTERNAL")

    def test_unknown_classification_fails_closed(self):
        result = classify_record({"classification": "UNKNOWN"})
        self.assertFalse(result.accepted)
        self.assertIn("classification_invalid", result.failures)

    def test_sensitive_material_requires_sensitive_classification(self):
        result = classify_record({"classification": "INTERNAL", "contains_secret_material": True})
        self.assertFalse(result.accepted)
        self.assertIn("secret_material_requires_secret_classification", result.failures)

    def test_sink_rules_block_secret_to_ai_context(self):
        self.assertFalse(is_sink_allowed("SECRET", "ai_context"))
        self.assertFalse(is_sink_allowed("CROWN_JEWEL", "provider_request"))
        self.assertTrue(is_sink_allowed("PUBLIC", "ai_context"))


if __name__ == "__main__":
    unittest.main()
