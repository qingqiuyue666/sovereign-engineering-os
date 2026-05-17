import unittest

from kernel.domain.osint_task_contract import validate_osint_task_contract


class OsintTaskContractTests(unittest.TestCase):
    def test_no_live_ingestion(self):
        contract = {"task_id": "task-1", "source_refs": ["source:1"], "freshness_metadata": {"reliability_tier": "PRIMARY", "freshness_timestamp": "2026", "conflict_status": "none"}, "live_ingestion": True}
        self.assertIn("osint_live_ingestion_forbidden", validate_osint_task_contract(contract))


if __name__ == "__main__":
    unittest.main()
