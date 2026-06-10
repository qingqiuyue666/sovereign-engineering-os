"""Read-only tests for Operator Dashboard Model V1."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.dashboard.operator_dashboard_model_v1 import (
    OPERATOR_DASHBOARD_VIEWS,
    build_operator_dashboard_model,
    render_operator_dashboard_view,
)
from tools.operator_dashboard_viewer import main as operator_dashboard_viewer_main


class OperatorDashboardModelV1Tests(unittest.TestCase):
    def fixture(self) -> dict[str, object]:
        return {
            "jobs": [{"job_id": "job-1", "status": "queued", "task_id": "task-1"}],
            "pr_readiness": [{"pr": "#445", "status": "blocked", "branch": "feat/example"}],
            "artifacts": [{"artifact_id": "artifact-1", "status": "ready", "secret": "NOPE"}],
            "receipts": [{"receipt_id": "receipt-1", "status": "recorded"}],
            "failures": [{"failure_id": "failure-1", "status": "open", "raw_prompt": "NOPE"}],
            "approvals": [{"approval_id": "approval-1", "status": "pending", "token": "NOPE"}],
            "milestones": [{"milestone": "C2", "status": "in_review"}],
        }

    def test_builds_read_only_dashboard_summary(self) -> None:
        model = build_operator_dashboard_model(self.fixture())
        payload = model.summary()

        self.assertEqual(payload["model_type"], "operator_dashboard_model_v1")
        self.assertEqual(payload["job_count"], 1)
        self.assertEqual(payload["blocked_pr_count"], 1)
        self.assertEqual(payload["pending_approval_count"], 1)
        self.assertFalse(payload["mutation_performed"])
        self.assertFalse(payload["merge_performed"])
        self.assertFalse(payload["branch_deleted"])
        self.assertFalse(payload["execution_performed"])
        self.assertFalse(payload["network_accessed"])

    def test_all_expected_views_render_as_redacted_json(self) -> None:
        model = build_operator_dashboard_model(self.fixture())

        for view in OPERATOR_DASHBOARD_VIEWS:
            with self.subTest(view=view):
                rendered = render_operator_dashboard_view(model, view)
                payload = json.loads(rendered)
                self.assertEqual(payload["view"], view)
                self.assertTrue(payload["read_only"])
                self.assertFalse(payload["mutation_performed"])
                self.assertNotIn("NOPE", rendered)
                if view in {"artifacts", "failures", "approvals"}:
                    self.assertIn("[REDACTED]", rendered)

    def test_unknown_view_fails_closed(self) -> None:
        model = build_operator_dashboard_model(self.fixture())

        with self.assertRaisesRegex(ValueError, "view_unknown"):
            render_operator_dashboard_view(model, "merge")

    def test_cli_prints_selected_view_without_modifying_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dashboard.json"
            path.write_text(json.dumps(self.fixture(), sort_keys=True, indent=2), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = operator_dashboard_main_with_args([path.as_posix(), "--view", "jobs"])

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["view"], "jobs")
            self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_source_has_no_mutation_merge_deletion_runtime_or_network_surface(self) -> None:
        source = Path("kernel/dashboard/operator_dashboard_model_v1.py").read_text(encoding="utf-8")
        cli_source = Path("tools/operator_dashboard_viewer.py").read_text(encoding="utf-8")
        combined = source + "\n" + cli_source

        for marker in (
            "subprocess",
            "requests.",
            "urllib.",
            "socket",
            "webbrowser",
            "git merge",
            "gh pr merge",
            "delete_branch",
            "unlink(",
            "remove(",
        ):
            self.assertNotIn(marker, combined)


def operator_dashboard_main_with_args(args: list[str]) -> int:
    import sys

    original = sys.argv
    try:
        sys.argv = ["operator_dashboard_viewer.py", *args]
        return operator_dashboard_viewer_main()
    finally:
        sys.argv = original


if __name__ == "__main__":
    unittest.main()
