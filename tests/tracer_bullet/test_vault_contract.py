import unittest

from kernel.vault.vault_contract import validate_vault_contract


class VaultContractTests(unittest.TestCase):
    def metadata(self):
        return {"key_ref": "key:1", "secret_ref": "secret:1", "scope": "provider_mock", "expiry": "2099-01-01", "rotation_policy": "manual"}

    def test_valid_metadata_only_contract(self):
        self.assertFalse(validate_vault_contract(self.metadata()))

    def test_rejects_plaintext_secret_and_secret_read(self):
        metadata = self.metadata()
        metadata["secret_value"] = "abc123456789SECRET"
        metadata["secret_value_read"] = True
        failures = validate_vault_contract(metadata)
        self.assertIn("plaintext_secret_value_forbidden", failures)
        self.assertIn("secret_value_read_forbidden", failures)


if __name__ == "__main__":
    unittest.main()
