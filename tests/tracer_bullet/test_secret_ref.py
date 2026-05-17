import unittest

from kernel.vault.secret_ref import validate_secret_ref


class SecretRefTests(unittest.TestCase):
    def test_requires_secret_ref_metadata_fields(self):
        failures = validate_secret_ref({"key_ref": "key:1"})
        self.assertIn("secret_ref_required", failures)
        self.assertIn("scope_required", failures)
        self.assertIn("expiry_required", failures)
        self.assertIn("rotation_policy_required", failures)

    def test_rejects_plaintext_secret_value(self):
        metadata = {"key_ref": "key:1", "secret_ref": "secret:1", "scope": "x", "expiry": "2099", "rotation_policy": "manual", "secret_value": "x"}
        self.assertIn("plaintext_secret_value_forbidden", validate_secret_ref(metadata))


if __name__ == "__main__":
    unittest.main()
