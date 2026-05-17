import unittest

from kernel.vault.keyring_contract import validate_keyring_contract


class KeyringContractTests(unittest.TestCase):
    def test_rejects_keyring_and_kms_runtime(self):
        metadata = {"key_ref": "key:1", "secret_ref": "secret:1", "scope": "provider_mock", "expiry": "2099-01-01", "rotation_policy": "manual", "keyring_access_performed": True, "kms_runtime": True}
        failures = validate_keyring_contract(metadata)
        self.assertIn("keyring_access_forbidden", failures)
        self.assertIn("kms_or_encryption_runtime_forbidden", failures)


if __name__ == "__main__":
    unittest.main()
