import unittest

from kernel.security.anti_exfiltration_gate import inspect_outbound_payload


class AntiExfiltrationGateTests(unittest.TestCase):
    def test_blocks_contaminated_payload(self):
        result = inspect_outbound_payload({"message": "Bearer abc123456789SECRETSECRET"})
        self.assertFalse(result.allowed)
        self.assertIn("payload_contaminated", result.failures)

    def test_blocks_secret_classification_even_without_secret_text(self):
        result = inspect_outbound_payload({"digest": "sha256:abc"}, classification="SECRET")
        self.assertFalse(result.allowed)
        self.assertIn("classification_not_exportable", result.failures)

    def test_allows_clean_digest_payload(self):
        result = inspect_outbound_payload({"digest": "sha256:abc"}, classification="INTERNAL")
        self.assertTrue(result.allowed, result.failures)


if __name__ == "__main__":
    unittest.main()
