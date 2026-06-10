import unittest

from apps.ui.read_models import fake_phase1_snapshot, project_operator_console_snapshot


class OperatorConsoleReadModelProjectionAcceptanceTests(unittest.TestCase):
    def test_projection_is_read_only_audit_safe_and_actionable(self):
        projection = project_operator_console_snapshot(fake_phase1_snapshot())

        self.assertEqual(projection.projection_type, "operator_console_projection_v1")
        self.assertEqual(projection.report_status, "action_required")
        self.assertTrue(projection.read_only)
        self.assertFalse(projection.write_actions_allowed)
        self.assertGreaterEqual(projection.queue_depth, 0)
        self.assertGreaterEqual(projection.warning_count, 1)
        self.assertTrue(projection.content_hash.startswith("sha256:"))
        self.assertIn("JobQuarantined", projection.latest_event_types)


if __name__ == "__main__":
    unittest.main()
