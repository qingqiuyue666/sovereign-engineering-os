import json
import unittest
from pathlib import Path

from kernel.security.environment_sanitizer import sanitize_environment

POLICY_PATH = Path("governance/security/environment_sanitizer_policy_v1.json")


class EnvironmentSanitizerTests(unittest.TestCase):
    def test_policy_exists_and_is_default_deny(self):
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["policy_type"], "seos_environment_sanitizer_policy_v1")
        self.assertTrue(payload["default_deny"])
        self.assertTrue(payload["read_only_gate"])

    def test_sanitizer_removes_unauthorized_keys(self):
        result = sanitize_environment({"PATH": "/bin", "CUSTOM_VALUE": "x"})
        self.assertTrue(result.accepted)
        self.assertIn("PATH", result.sanitized_env)
        self.assertIn("CUSTOM_VALUE", result.removed_keys)

    def test_sanitizer_redacts_allowed_values(self):
        result = sanitize_environment({"PATH": "/bin"})
        self.assertEqual(result.sanitized_env["PATH"], "[REDACTED]")

    def test_sanitizer_removes_sensitive_named_keys(self):
        result = sanitize_environment({"PATH": "/bin", "SERVICE_TOKEN": "value"})
        self.assertTrue(result.accepted)
        self.assertIn("SERVICE_TOKEN", result.removed_keys)
        self.assertIn("blocked_environment_key_removed", result.failures)

    def test_non_mapping_env_fails_closed(self):
        result = sanitize_environment(["not", "mapping"])
        self.assertFalse(result.accepted)
        self.assertIn("env_must_be_mapping", result.failures)


if __name__ == "__main__":
    unittest.main()
