import unittest

from kernel.providers.provider_response_receipt import build_provider_response_receipt, validate_provider_response_receipt


class ProviderResponseReceiptTests(unittest.TestCase):
    def test_receipt_contains_digest_and_no_raw_response(self):
        receipt = build_provider_response_receipt(provider_id="mock", request_digest="sha256:req", response_marker="ok", policy_version="v12", code_version="test")
        self.assertFalse(validate_provider_response_receipt(receipt))
        self.assertTrue(str(receipt["response_digest"]).startswith("sha256:"))
        receipt["raw_response"] = "forbidden"
        self.assertIn("raw_response_forbidden", validate_provider_response_receipt(receipt))


if __name__ == "__main__":
    unittest.main()
