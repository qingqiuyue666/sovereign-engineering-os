import unittest

from kernel.security.environment_sanitizer import sanitize_environment
from kernel.security.secret_scanner import REDACTION


class EnvironmentSanitizerTests(unittest.TestCase):
    def test_returns_sanitized_copy_without_mutating_input(self):
        env = {"PATH": "/bin", "API_TOKEN": "abc123456789SECRET"}
        result = sanitize_environment(env)
        self.assertTrue(result.accepted)
        self.assertEqual(result.sanitized["PATH"], "/bin")
        self.assertEqual(result.sanitized["API_TOKEN"], REDACTION)
        self.assertEqual(env["API_TOKEN"], "abc123456789SECRET")

    def test_non_mapping_fails_closed(self):
        result = sanitize_environment(["not", "mapping"])  # type: ignore[arg-type]
        self.assertFalse(result.accepted)
        self.assertIn("environment_must_be_mapping", result.failures)


if __name__ == "__main__":
    unittest.main()
