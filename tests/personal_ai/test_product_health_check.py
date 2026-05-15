import json
import tempfile
import unittest
from pathlib import Path

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
        self.assertTrue(report["dependencies"]["openpyxl"]["available"])
        self.assertTrue(report["adapter_registry_valid"])
        self.assertTrue(report["runtime_admission_defaults_fail_closed"])
        self.assertFalse(report["runtime_activation_performed"])
        self.assertIn("live_model_provider", report["deferred_real_runtimes"])
        self.assertIn("product_health_check_workflow", report["launcher_workflows"])
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
        self.assertIn("Runtime activation performed: false", summary)

    def test_reports_missing_repo_docs_without_crashing(self):
        output_dir = self.make_output_dir()
        fake_repo = output_dir / "empty-repo"
        fake_repo.mkdir()

        report = build_product_health_report(fake_repo)

        self.assertFalse(report["complete"])
        self.assertFalse(report["docs"]["core_docs_complete"])
        self.assertEqual(report["tests"]["personal_ai_test_files_count"], 0)

    def test_refuses_overwrite(self):
        output_dir = self.make_output_dir()
        write_product_health_check(output_dir, repo_root=Path.cwd())

        with self.assertRaisesRegex(ValueError, "already exists"):
            write_product_health_check(output_dir, repo_root=Path.cwd())


if __name__ == "__main__":
    unittest.main()
