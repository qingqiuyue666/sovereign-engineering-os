"""Job Queue model tests for Phase 1."""

from __future__ import annotations

import unittest
from pathlib import Path

from apps.ui import Qt
from apps.ui.models import JobQueueTableModel
from apps.ui.read_models import JobRow


class FakeIndex:
    def __init__(self, row: int, column: int) -> None:
        self._row = row
        self._column = column

    def isValid(self) -> bool:  # noqa: N802 - mirrors Qt API.
        return True

    def row(self) -> int:
        return self._row

    def column(self) -> int:
        return self._column


class SovereignConsoleJobQueueModelTests(unittest.TestCase):
    def test_model_can_be_built_from_fake_rows(self) -> None:
        row = JobRow(
            job_id="job_1",
            job_type="context_pack",
            status="running",
            worker="worker-a",
            created_at="2026-05-20T00:00:00+00:00",
            runtime="00:00:03",
            event_count=3,
            artifact_count=1,
            human_review_required=True,
            failure_reason="",
        )
        model = JobQueueTableModel([row])
        self.assertEqual(model.rowCount(), 1)
        self.assertEqual(model.columnCount(), 10)
        self.assertEqual(model.data(FakeIndex(0, 0), Qt.ItemDataRole.DisplayRole), "job_1")
        self.assertEqual(model.data(FakeIndex(0, 2), Qt.ItemDataRole.DisplayRole), "Running")
        self.assertEqual(model.data(FakeIndex(0, 8), Qt.ItemDataRole.DisplayRole), "Required")
        self.assertEqual(model.job_at(0), row)

    def test_job_queue_source_uses_table_view_model_and_not_table_widget(self) -> None:
        job_queue_source = Path("apps/ui/job_queue_page.py").read_text(encoding="utf-8")
        model_source = Path("apps/ui/models.py").read_text(encoding="utf-8")
        combined = job_queue_source + "\n" + model_source
        self.assertIn("QTableView", combined)
        self.assertIn("QAbstractTableModel", combined)
        self.assertNotIn("QTableWidget", combined)


if __name__ == "__main__":
    unittest.main()
