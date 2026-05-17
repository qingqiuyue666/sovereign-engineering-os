import unittest
from datetime import datetime, timezone

from kernel.security.capability_token_policy import validate_capability_token_metadata


class CapabilityTokenPolicyTests(unittest.TestCase):
    def test_accepts_authorized_nonexpired_metadata(self):
        token = {"token_id": "cap-1", "scope": ["dry_run"], "expires_at": "2099-01-01T00:00:00+00:00"}
        self.assertTrue(validate_capability_token_metadata(token, requested_action="dry_run").accepted)

    def test_rejects_wildcard_expired_and_unauthorized(self):
        token = {"token_id": "cap-1", "scope": ["*"], "expires_at": "2020-01-01T00:00:00+00:00"}
        result = validate_capability_token_metadata(token, requested_action="dry_run", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertIn("wildcard_scope_forbidden", result.failures)
        self.assertIn("unauthorized_action", result.failures)
        self.assertIn("token_expired", result.failures)

    def test_rejects_secret_material(self):
        token = {"token_id": "cap-1", "scope": ["dry_run"], "expires_at": "2099-01-01T00:00:00+00:00", "secret_value": "abc123456789SECRET"}
        self.assertIn("secret_material_forbidden", validate_capability_token_metadata(token, requested_action="dry_run").failures)


if __name__ == "__main__":
    unittest.main()
