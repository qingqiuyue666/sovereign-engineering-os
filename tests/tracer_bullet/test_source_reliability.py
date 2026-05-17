import unittest

from kernel.domain.source_reliability import validate_source_metadata


class SourceReliabilityTests(unittest.TestCase):
    def test_valid_source_metadata(self):
        self.assertFalse(validate_source_metadata({"reliability_tier": "PRIMARY", "freshness_timestamp": "2026-01-01T00:00:00Z", "conflict_status": "none"}))

    def test_rejects_invalid_tier_and_network_fetch(self):
        failures = validate_source_metadata({"reliability_tier": "BAD", "freshness_timestamp": "", "conflict_status": "bad", "network_fetch_performed": True})
        self.assertIn("reliability_tier_invalid", failures)
        self.assertIn("network_fetch_forbidden", failures)


if __name__ == "__main__":
    unittest.main()
