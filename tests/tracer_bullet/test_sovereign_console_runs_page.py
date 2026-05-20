"""Runs view tests."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.read_models import fake_phase1_snapshot
from apps.ui.runs_page import RunsPage


class SovereignConsoleRunsPageTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_runs_absorbs_job_queue_projection(self) -> None:
        page = RunsPage(language="en")
        page.render_snapshot(fake_phase1_snapshot())
        self.assertEqual(page.title.text(), "Runs")
        self.assertIn("Job Queue", page.absorbed_domains())
        for field in ("run table", "status chips", "worker", "runtime", "event count", "artifact count"):
            self.assertIn(field, page.required_fields())
        self.assertIn("job_id", page.column_keys())
        self.assertIn("human_review_required", page.column_keys())
        self.assertFalse(page.cancel_button.isEnabled())
        self.assertFalse(page.retry_button.isEnabled())

    def test_runs_source_uses_qtableview_model_not_tablewidget(self) -> None:
        source = Path("apps/ui/runs_page.py").read_text(encoding="utf-8")
        models = Path("apps/ui/models.py").read_text(encoding="utf-8")
        self.assertIn("QTableView", source)
        self.assertIn("QAbstractTableModel", models)
        self.assertNotIn("QTableWidget", source)


if __name__ == "__main__":
    unittest.main()
