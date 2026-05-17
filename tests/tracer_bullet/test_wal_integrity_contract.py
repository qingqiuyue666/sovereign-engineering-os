import unittest

from kernel.security.wal_integrity_contract import WalIntegrityContract


class WalIntegrityContractTests(unittest.TestCase):
    def test_accepts_metadata_only_segment(self):
        contract = WalIntegrityContract()
        result = contract.validate_segment_metadata({"segment_id": "seg-1", "logical_sequence": 1, "expected_hash": "sha256:a", "observed_hash": "sha256:a"})
        self.assertTrue(result.accepted, result.failures)

    def test_rejects_duplicate_segment_id_and_sequence_regression(self):
        contract = WalIntegrityContract()
        self.assertTrue(contract.validate_segment_metadata({"segment_id": "seg-1", "logical_sequence": 2, "expected_hash": "sha256:a", "observed_hash": "sha256:a"}).accepted)
        result = contract.validate_segment_metadata({"segment_id": "seg-1", "logical_sequence": 1, "expected_hash": "sha256:a", "observed_hash": "sha256:a"})
        self.assertFalse(result.accepted)
        self.assertIn("duplicate_segment_id", result.failures)
        self.assertIn("sequence_regression", result.failures)

    def test_rejects_hash_mismatch(self):
        result = WalIntegrityContract().validate_segment_metadata({"segment_id": "seg-1", "logical_sequence": 1, "expected_hash": "sha256:a", "observed_hash": "sha256:b"})
        self.assertIn("wal_hash_mismatch", result.failures)


if __name__ == "__main__":
    unittest.main()
