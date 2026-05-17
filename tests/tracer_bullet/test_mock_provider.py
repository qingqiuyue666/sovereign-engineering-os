import unittest

from kernel.providers.mock_provider import run_mock_provider
from kernel.providers.provider_request_envelope import build_provider_request_envelope


class MockProviderTests(unittest.TestCase):
    def test_mock_provider_returns_deterministic_receipt_without_live_call(self):
        envelope = build_provider_request_envelope(task_id="task-1", request_digest="sha256:req", classification="PUBLIC", policy_version="v12", code_version="test")
        first = run_mock_provider(envelope)
        second = run_mock_provider(envelope)
        self.assertTrue(first["accepted"], first)
        self.assertEqual(first, second)
        self.assertEqual(first["provider_calls_executed"], 0)
        self.assertNotIn("raw_response", first["receipt"])


if __name__ == "__main__":
    unittest.main()
