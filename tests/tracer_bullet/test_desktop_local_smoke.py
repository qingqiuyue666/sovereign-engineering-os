"""Headless desktop smoke tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps import desktop_local_smoke


class DesktopLocalSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_smoke_runs_headless_and_writes_artifact_through_runtime_path(self) -> None:
        report = desktop_local_smoke.run_desktop_local_smoke(
            repo_root=Path.cwd(),
            runtime_root=self.root / "runtime",
        )
        self.assertTrue(report.os_runtime_bootstrapped)
        self.assertTrue(report.gui_import_passive)
        self.assertFalse(report.gui_launched)
        self.assertTrue(report.job_submission_facade_exists)
        self.assertEqual(report.smoke_job_status, "succeeded")
        self.assertTrue(Path(report.smoke_artifact_path).is_file())

    def test_missing_pyside6_is_clean_report_not_crash(self) -> None:
        original = desktop_local_smoke.sovereign_desktop.PYSIDE6_AVAILABLE
        desktop_local_smoke.sovereign_desktop.PYSIDE6_AVAILABLE = False
        try:
            report = desktop_local_smoke.run_desktop_local_smoke(
                repo_root=Path.cwd(),
                runtime_root=self.root / "missing_qt",
                run_job=False,
            )
        finally:
            desktop_local_smoke.sovereign_desktop.PYSIDE6_AVAILABLE = original
        self.assertFalse(report.pyside6_available)
        self.assertFalse(report.gui_launched)
        self.assertEqual(report.smoke_job_status, "not_run")

    def test_no_forbidden_execution_surface(self) -> None:
        source = Path("apps/desktop_local_smoke.py").read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)
        self.assertNotIn("QApplication(", source)
        self.assertNotIn("requests.", source)


if __name__ == "__main__":
    unittest.main()
