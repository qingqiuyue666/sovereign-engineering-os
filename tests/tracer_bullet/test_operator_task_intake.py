import tempfile
import unittest
from pathlib import Path

from kernel.runs.run_ledger import write_run_ledger
from kernel.tasks.task_contracts import create_operator_task_envelope


class OperatorTaskIntakeTests(unittest.TestCase):
    def payload(self):
        return {
            "objective": "validate local descriptor",
            "requested_capabilities": ["local_validation"],
            "classification": "PUBLIC",
            "policy_version": "v12",
            "code_version": "test",
            "descriptor": {
                "descriptor_type": "text",
                "content_digest": "sha256:abc",
            },
        }

    def test_accepts_digest_only_text_descriptor_and_assigns_task_id(self):
        result = create_operator_task_envelope(self.payload())

        self.assertTrue(result.accepted, result.failures)
        self.assertTrue(str(result.envelope["task_id"]).startswith("task_"))
        self.assertEqual(result.envelope["descriptor_type"], "text")
        self.assertTrue(str(result.envelope["descriptor_digest"]).startswith("sha256:"))
        self.assertFalse(result.envelope["raw_input_persisted"])
        self.assertFalse(result.envelope["ai_provider_call_performed"])

    def test_rejects_raw_or_secret_descriptor_fields(self):
        payload = self.payload()
        payload["descriptor"] = {"descriptor_type": "text", "raw_prompt": "forbidden"}

        result = create_operator_task_envelope(payload)

        self.assertFalse(result.accepted)
        self.assertIn("raw_or_secret_descriptor_field_forbidden", result.failures)

    def test_rejects_raw_input_persistence_request(self):
        payload = self.payload()
        payload["persist_raw_input"] = True

        result = create_operator_task_envelope(payload)

        self.assertFalse(result.accepted)
        self.assertIn("raw_input_persistence_forbidden", result.failures)

    def test_writes_digest_only_run_ledger_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            event = {
                "event_id": "evt-1",
                "run_id": "run-1",
                "task_id": "task-1",
                "stage": "intake",
                "event_type": "accepted",
                "logical_time": 1,
                "payload_digest": "sha256:abc",
            }

            result = write_run_ledger(output_dir=temp_dir, task_id="task-1", run_id="run-1", events=[event])
            duplicate = write_run_ledger(output_dir=temp_dir, task_id="task-1", run_id="run-1", events=[event])

        self.assertTrue(result.accepted, result.failures)
        self.assertTrue(Path(str(result.ledger_path)).name == "run_ledger_v1.json")
        self.assertTrue(str(result.report["ledger_digest"]).startswith("sha256:"))
        self.assertFalse(result.report["network_accessed"])
        self.assertFalse(duplicate.accepted)
        self.assertIn("run_ledger_overwrite_forbidden", duplicate.failures)


if __name__ == "__main__":
    unittest.main()
