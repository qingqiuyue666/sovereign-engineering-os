import unittest

from kernel.runtime.event_journal import InMemoryEventJournal


class EventJournalTests(unittest.TestCase):
    def event(self, event_id="evt-1", logical_time=1):
        return {"event_id": event_id, "run_id": "run-1", "task_id": "task-1", "stage": "dry_run", "event_type": "planned", "logical_time": logical_time, "payload_digest": "sha256:abc"}

    def test_duplicate_and_sequence_regression_rejected(self):
        journal = InMemoryEventJournal()
        self.assertTrue(journal.append(self.event()).accepted)
        self.assertIn("duplicate_event_id", journal.append(self.event()).failures)
        self.assertIn("sequence_regression", journal.append(self.event("evt-2", 0)).failures)


if __name__ == "__main__":
    unittest.main()
