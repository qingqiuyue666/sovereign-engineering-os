import unittest

from kernel.dashboard.dashboard_model import build_dashboard_model, validate_dashboard_model


class DashboardModelTests(unittest.TestCase):
    def test_dashboard_data_model_no_runtime(self):
        model = build_dashboard_model(cards=[{"card_id": "security", "title": "Security"}], run_summary={"run_id": "run-1", "task_id": "task-1", "status": "dry_run", "event_count": 2}, security_status={"scanner_enabled": True, "redaction_enabled": True, "forbidden_surfaces_absent": {"network": True}})
        self.assertFalse(validate_dashboard_model(model))
        self.assertFalse(model["web_server_started"])
        self.assertFalse(model["frontend_build_performed"])


if __name__ == "__main__":
    unittest.main()
