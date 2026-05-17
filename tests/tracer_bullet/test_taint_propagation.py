import unittest

from kernel.security.taint_propagation import derive_artifact_taint, validate_taint_transition


class TaintPropagationTests(unittest.TestCase):
    def test_derived_artifact_inherits_highest_input_taint(self):
        taint = derive_artifact_taint([{"classification": "PUBLIC"}, {"classification": "SECRET"}])
        self.assertEqual(taint, "SECRET")

    def test_monotonic_escalation_allowed(self):
        result = validate_taint_transition(current_taint="PUBLIC", requested_taint="CONFIDENTIAL")
        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.resulting_taint, "CONFIDENTIAL")

    def test_downgrade_requires_declassification_receipt(self):
        result = validate_taint_transition(current_taint="SECRET", requested_taint="PUBLIC")
        self.assertFalse(result.accepted)
        self.assertIn("declassification_receipt_required", result.failures)
        receipt = {"receipt_type": "declassification_receipt_v1", "source_taint": "SECRET", "target_taint": "PUBLIC", "approved_by": "operator"}
        self.assertTrue(validate_taint_transition(current_taint="SECRET", requested_taint="PUBLIC", declassification_receipt=receipt).accepted)


if __name__ == "__main__":
    unittest.main()
