import unittest

from kernel.providers.provider_contract import validate_provider_contract


class ProviderContractTests(unittest.TestCase):
    def test_mock_only_contract_is_accepted(self):
        result = validate_provider_contract({"provider_id": "mock", "mode": "mock_only", "network_allowed": False, "live_provider_allowed": False, "raw_response_persistence_allowed": False})
        self.assertTrue(result.accepted, result.failures)

    def test_live_provider_contract_rejected(self):
        result = validate_provider_contract({"provider_id": "real", "mode": "live", "network_allowed": True, "live_provider_allowed": True, "raw_response_persistence_allowed": True})
        self.assertFalse(result.accepted)
        self.assertIn("mock_only_mode_required", result.failures)


if __name__ == "__main__":
    unittest.main()
