import unittest

from kernel.domain.asset_mapping_contract import validate_asset_mapping_contract


class AssetMappingContractTests(unittest.TestCase):
    def test_asset_mapping_shape(self):
        contract = {"mapping_id": "map-1", "macro_regime_ref": "regime-1", "asset_refs": ["asset:spy"], "mapping_digest": "sha256:a"}
        self.assertFalse(validate_asset_mapping_contract(contract))

    def test_execution_and_push_forbidden(self):
        contract = {"mapping_id": "map-1", "macro_regime_ref": "regime-1", "asset_refs": ["asset:spy"], "mapping_digest": "sha256:a", "trading_execution_performed": True, "telegram_push_performed": True}
        self.assertIn("execution_or_push_forbidden", validate_asset_mapping_contract(contract))


if __name__ == "__main__":
    unittest.main()
