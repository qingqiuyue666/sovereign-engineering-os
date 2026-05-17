import unittest

from kernel.providers.provider_request_envelope import build_provider_request_envelope, validate_provider_request_envelope


class ProviderRequestEnvelopeTests(unittest.TestCase):
    def test_envelope_is_digest_only(self):
        envelope = build_provider_request_envelope(task_id="task-1", request_digest="sha256:req", classification="INTERNAL", policy_version="v12", code_version="test")
        self.assertFalse(validate_provider_request_envelope(envelope))
        self.assertTrue(envelope["digest_only"])

    def test_secret_payload_is_blocked(self):
        envelope = build_provider_request_envelope(task_id="task-1", request_digest="sha256:req", classification="SECRET", policy_version="v12", code_version="test")
        self.assertIn("sensitive_provider_payload_forbidden", validate_provider_request_envelope(envelope))


if __name__ == "__main__":
    unittest.main()
