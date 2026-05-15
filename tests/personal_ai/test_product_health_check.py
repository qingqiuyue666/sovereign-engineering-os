import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernel.personal_ai.product_health_check import (
    build_product_health_report,
    write_product_health_check,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ProductHealthCheckTests(unittest.TestCase):
    def make_output_dir(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        output_dir = Path(temp_dir.name) / "health"
        output_dir.mkdir()
        return output_dir

    def test_builds_health_report_from_current_repo(self):
        report = build_product_health_report(Path.cwd())

        self.assertTrue(report["complete"])
        self.assertTrue(report["structural_complete"])
        self.assertFalse(report["runtime_workflow_smoke_verified"])
        self.assertFalse(report["final_product_health_complete"])
        self.assertEqual(
            report["completion_scope"],
            "static_structural_health_only",
        )
        self.assertTrue(report["does_not_execute_launcher_workflows"])
        self.assertTrue(report["does_not_execute_real_runtime"])
        self.assertTrue(
            report["human_review_required_before_final_product_claim"]
        )
        self.assertTrue(report["dependencies"]["openpyxl"]["available"])
        self.assertTrue(report["adapter_registry_valid"])
        self.assertTrue(report["runtime_admission_defaults_fail_closed"])
        self.assertFalse(report["runtime_activation_performed"])
        self.assertIn("live_model_provider", report["deferred_real_runtimes"])
        self.assertIn("product_health_check_workflow", report["launcher_workflows"])
        self.assertTrue(report["launcher_workflows_complete"])
        self.assertTrue(report["cli_subcommands_complete"])
        self.assertTrue(
            report["launcher_static_checks"][
                "launcher_workflows_declared_complete"
            ]
        )
        self.assertTrue(
            report["launcher_static_checks"][
                "required_cli_subcommands_declared_complete"
            ]
        )
        self.assertTrue(report["docs"]["core_docs_complete"])
        self.assertTrue(report["tests"]["final_product_e2e_battery_present"])

    def test_writes_json_report_and_human_summary(self):
        output_dir = self.make_output_dir()

        result = write_product_health_check(output_dir, repo_root=Path.cwd())
        report = read_json(result.product_health_report_path)
        summary = result.product_health_summary_path.read_text(encoding="utf-8")

        self.assertTrue(result.complete)
        self.assertTrue(report["complete"])
        self.assertEqual(
            report["health_type"],
            "personal_ai_execution_os_product_health_v1",
        )
        self.assertIn("Product Health Check", summary)
        self.assertIn("Completion scope: static_structural_health_only", summary)
        self.assertIn("Runtime workflow smoke verified: false", summary)
        self.assertIn("Launcher workflows executed: false", summary)
        self.assertIn("Runtime activation performed: false", summary)

    def test_reports_missing_repo_docs_without_crashing(self):
        output_dir = self.make_output_dir()
        fake_repo = output_dir / "empty-repo"
        fake_repo.mkdir()

        report = build_product_health_report(fake_repo)

        self.assertFalse(report["complete"])
        self.assertFalse(report["structural_complete"])
        self.assertFalse(report["final_product_health_complete"])
        self.assertEqual(
            report["completion_scope"],
            "static_structural_health_only",
        )
        self.assertFalse(report["docs"]["core_docs_complete"])
        self.assertEqual(report["tests"]["personal_ai_test_files_count"], 0)

    def test_does_not_execute_launcher_workflows(self):
        launcher_functions = (
            "run_local_office_launcher",
            "run_model_fixture_launcher",
            "run_model_provider_dry_run_launcher",
            "run_browser_fixture_launcher",
            "run_browser_runtime_dry_run_launcher",
            "run_comfyui_dry_run_launcher",
            "run_blender_dry_run_launcher",
            "run_creative_handoff_launcher",
            "run_task_graph_launcher",
            "run_runtime_delivery_validation_launcher",
            "run_product_health_check_launcher",
        )
        patchers = [
            patch(
                "kernel.personal_ai.local_launcher." + function_name,
                side_effect=AssertionError("launcher workflow executed"),
            )
            for function_name in launcher_functions
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        report = build_product_health_report(Path.cwd())

        self.assertTrue(report["complete"])
        self.assertFalse(report["runtime_workflow_smoke_verified"])
        self.assertTrue(report["does_not_execute_launcher_workflows"])
        self.assertFalse(report["launcher_static_checks"]["workflows_executed"])

    def test_refuses_overwrite(self):
        output_dir = self.make_output_dir()
        write_product_health_check(output_dir, repo_root=Path.cwd())

        with self.assertRaisesRegex(ValueError, "already exists"):
            write_product_health_check(output_dir, repo_root=Path.cwd())


if __name__ == "__main__":
    unittest.main()
