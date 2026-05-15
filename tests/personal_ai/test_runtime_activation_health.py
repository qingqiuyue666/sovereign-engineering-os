import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.runtime_activation_health import (
    build_runtime_activation_health_report,
    write_runtime_activation_health_report,
)


class RuntimeActivationHealthTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_builds_static_runtime_activation_health_report(self):
        report = build_runtime_activation_health_report(Path.cwd())

        self.assertTrue(report["complete"])
        self.assertTrue(report["static_health_only"])
        self.assertTrue(report["does_not_execute_runtime"])
        self.assertTrue(report["does_not_call_model_provider"])
        self.assertTrue(report["does_not_launch_browser"])
        self.assertTrue(report["does_not_call_comfyui_endpoint"])
        self.assertTrue(report["does_not_launch_blender"])
        self.assertFalse(report["network_used"])
        self.assertFalse(report["subprocess_used"])
        self.assertFalse(report["api_key_value_persisted"])
        self.assertFalse(report["api_key_value_logged"])
        self.assertTrue(report["live_runtimes_still_disabled_by_default"])
        self.assertIn(
            "model_provider_controlled_activation_package",
            report["activation_surfaces"],
        )

    def test_writes_health_report_and_summary(self):
        output_dir = self.make_output_dir()

        result = write_runtime_activation_health_report(
            output_dir,
            repo_root=Path.cwd(),
        )

        self.assertTrue(result.complete)
        report = json.loads(result.report_path.read_text(encoding="utf-8"))
        summary = result.summary_path.read_text(encoding="utf-8")
        self.assertEqual(
            report["health_type"],
            "personal_ai_runtime_activation_health_v1",
        )
        self.assertIn("Runtime Activation Health", summary)
        self.assertIn("Static health only: true", summary)
        self.assertIn("Runtime executed: false", summary)

    def test_reports_incomplete_fake_repo(self):
        fake_repo = self.make_output_dir()
        report = build_runtime_activation_health_report(fake_repo)

        self.assertFalse(report["complete"])
        self.assertFalse(all(report["required_modules"].values()))
        self.assertFalse(all(report["required_tests"].values()))

    def test_refuses_overwrite(self):
        output_dir = self.make_output_dir()
        write_runtime_activation_health_report(output_dir, repo_root=Path.cwd())

        with self.assertRaisesRegex(ValueError, "already exists"):
            write_runtime_activation_health_report(output_dir, repo_root=Path.cwd())


if __name__ == "__main__":
    unittest.main()
