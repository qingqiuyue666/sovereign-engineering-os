import unittest

from kernel.dashboard.security_status_model import validate_security_status_model


class SecurityStatusModelTests(unittest.TestCase):
    def test_security_status_requires_enabled_scanner_and_redaction(self):
        failures = validate_security_status_model({"scanner_enabled": False, "redaction_enabled": False, "forbidden_surfaces_absent": {}})
        self.assertIn("scanner_enabled_required", failures)
        self.assertIn("redaction_enabled_required", failures)


if __name__ == "__main__":
    unittest.main()
