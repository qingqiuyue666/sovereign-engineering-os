"""Tests for the landed local OS runtime facade."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.database import DatabasePathError
from kernel.os_engine.local_os_runtime import LocalOSRuntime, LocalOSRuntimeError


class OSEngineLocalRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_runtime_initializes_deterministically_without_execution(self) -> None:
        with LocalOSRuntime(root=self.root, repo_root=Path.cwd()) as runtime:
            first = runtime.summary()
            second = runtime.summary()
            self.assertEqual(first.content_hash, second.content_hash)
            self.assertEqual(first.schema_version, 3)
            self.assertIn("git_status", first.registered_workers)
            self.assertEqual(first.executed_jobs_on_init, 0)
            self.assertFalse(first.gui_launched)
            self.assertEqual(first.external_programs_launched_on_init, 0)
            self.assertEqual(first.network_calls_on_init, 0)

    def test_runtime_close_and_context_manager_are_deterministic(self) -> None:
        runtime = LocalOSRuntime(root=self.root, repo_root=Path.cwd())
        runtime.close()
        runtime.close()
        self.assertTrue(runtime.closed)
        with self.assertRaises(LocalOSRuntimeError):
            runtime.summary()
        with LocalOSRuntime(root=self.root / "ctx", repo_root=Path.cwd()) as managed:
            self.assertFalse(managed.closed)
        self.assertTrue(managed.closed)

    def test_summary_includes_counts_and_paths(self) -> None:
        with LocalOSRuntime(root=self.root, repo_root=Path.cwd()) as runtime:
            summary = runtime.summary().to_dict()
            self.assertEqual(summary["job_count"], 0)
            self.assertEqual(summary["artifact_count"], 0)
            self.assertTrue(str(summary["db_path"]).endswith("os_engine.sqlite3"))
            self.assertTrue(str(summary["artifact_root"]).endswith("artifacts"))

    def test_invalid_root_and_path_escape_are_rejected(self) -> None:
        root_file = self.root / "not_a_dir"
        root_file.write_text("x", encoding="utf-8")
        with self.assertRaises(DatabasePathError):
            LocalOSRuntime(root=root_file, repo_root=Path.cwd())
        with self.assertRaises(LocalOSRuntimeError):
            LocalOSRuntime(root=self.root, repo_root=Path.cwd(), db_name="../escape.sqlite3")
        with LocalOSRuntime(root=self.root / "safe", repo_root=Path.cwd()) as runtime:
            with self.assertRaises(LocalOSRuntimeError):
                runtime.resolve_runtime_path("../escape")

    def test_runtime_does_not_persist_raw_environment_or_secret_values(self) -> None:
        os.environ["SEOS_TEST_DO_NOT_PERSIST"] = "raw-runtime-secret-value"
        try:
            with LocalOSRuntime(root=self.root, repo_root=Path.cwd()) as runtime:
                self.assertNotIn("raw-runtime-secret-value", runtime.summary().to_json())
        finally:
            os.environ.pop("SEOS_TEST_DO_NOT_PERSIST", None)


if __name__ == "__main__":
    unittest.main()
