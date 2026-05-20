"""Tracer bullet tests for deterministic OS engine bootstrap."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.database import DatabasePathError
from kernel.os_engine.os_engine_bootstrap import OSEngineBootstrapError, bootstrap_os_engine


class OSEngineBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_bootstrap_creates_db_tables_and_workers_without_execution(self) -> None:
        summary = bootstrap_os_engine(root=self.root)
        self.assertTrue((self.root / "os_engine.sqlite3").exists())
        for table in {"jobs", "job_events", "artifacts", "materializations", "human_reviews"}:
            self.assertIn(table, summary.tables)
        self.assertIn("git", summary.worker_types)
        self.assertEqual(summary.executed_jobs, 0)
        self.assertFalse(summary.gui_launched)
        self.assertEqual(summary.external_programs_launched, 0)
        self.assertEqual(summary.network_calls, 0)

    def test_bootstrap_is_idempotent_and_summary_is_deterministic(self) -> None:
        first = bootstrap_os_engine(root=self.root)
        second = bootstrap_os_engine(root=self.root)
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.to_json(), second.to_json())

    def test_invalid_root_and_invalid_db_name_are_rejected(self) -> None:
        root_file = self.root / "not-a-dir"
        root_file.write_text("x", encoding="utf-8")
        with self.assertRaises(DatabasePathError):
            bootstrap_os_engine(root=root_file)
        with self.assertRaises(OSEngineBootstrapError):
            bootstrap_os_engine(root=self.root, db_name="../escape.sqlite3")


if __name__ == "__main__":
    unittest.main()
