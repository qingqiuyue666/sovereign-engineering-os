import unittest

from kernel.tasks.run_ledger import InMemoryRunLedger


class RunLedgerTests(unittest.TestCase):
    def event(self, event_id="evt-1", logical_time=1):
        return {"event_id": event_id, "run_id": "run-1", "task_id": "task-1", "stage": "dry_run", "event_type": "planned", "logical_time": logical_time, "payload_digest": "sha256:abc"}

    def test_append_only_accepts_valid_event(self):
        ledger = InMemoryRunLedger()
        self.assertTrue(ledger.append(self.event()).accepted)
        self.assertEqual(len(ledger.events), 1)

    def test_duplicate_event_id_rejected(self):
        ledger = InMemoryRunLedger()
        self.assertTrue(ledger.append(self.event()).accepted)
        result = ledger.append(self.event())
        self.assertFalse(result.accepted)
        self.assertIn("duplicate_event_id", result.failures)

    def test_sequence_regression_rejected(self):
        ledger = InMemoryRunLedger()
        self.assertTrue(ledger.append(self.event(event_id="evt-1", logical_time=2)).accepted)
        result = ledger.append(self.event(event_id="evt-2", logical_time=1))
        self.assertIn("sequence_regression", result.failures)


if __name__ == "__main__":
    unittest.main()
