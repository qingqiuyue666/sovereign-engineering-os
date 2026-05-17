import unittest

from kernel.domain.macro_regime_contract import validate_macro_regime_contract


class MacroRegimeContractTests(unittest.TestCase):
    def test_macro_regime_shape(self):
        contract = {"regime_id": "regime-1", "classification": "PUBLIC", "evidence_digest_refs": ["sha256:a"], "conflict_status": "none"}
        self.assertFalse(validate_macro_regime_contract(contract))

    def test_live_data_fetch_forbidden(self):
        contract = {"regime_id": "regime-1", "classification": "PUBLIC", "evidence_digest_refs": ["sha256:a"], "conflict_status": "none", "live_data_fetch_performed": True}
        self.assertIn("live_data_fetch_forbidden", validate_macro_regime_contract(contract))


if __name__ == "__main__":
    unittest.main()
